# Walkthrough: `api/main.py`

## Purpose

This file is the system's front door. It validates every incoming exception, hands it to the agent, and returns structured responses. It is the only component in Huginn that is reachable from outside the process.

The API layer exists as a separate component — rather than just calling the agent directly from a script — because the interface contract specifies three endpoints with specific request and response schemas (Decisions 7, 19, 20, 21). Those schemas are a deliberate design choice: they make the full demo narrative executable through API calls alone, without opening any files.

## Relationships

- **Imported by:** nothing in the project — this is the entry point
- **Imports from:** `models/exception.py` (for `TradeException`), `agent/graph.py` (for `huginn_graph`)
- **Does not touch:** Mimir, the logger, or Chroma directly — those are the agent's dependencies

## Decision Rationale

**Why `POST /exceptions` returns immediately rather than blocking until the full result is available as a separate response body:**
Decision 19, combined with the fake async job ID pattern from Decision 7. In v1 processing is synchronous — the result is always ready before the response is sent. But the interface mimics async: submit gets a job ID, retrieve gets the result. This means v2 can slot in a real queue between submission and processing without any change to the client-facing API contract. Three lines of code in v1 prevent a breaking interface change in v2.

**Why `_result_store` is an in-memory dict:**
V1 is synchronous and single-process. The result is computed before `POST /exceptions` returns, stored in memory, and immediately retrievable via `GET /exceptions/{job_id}`. A persistent result store (database, Redis) would add operational complexity with no benefit in v1. V2's async processing requires a persistent store — that is where this changes.

**Why `exception.model_dump_json()` followed by `json.loads()` rather than `exception.model_dump()`:**
Pydantic's `model_dump()` returns a dict but preserves Python types — UUID objects, datetime objects. The agent state and the audit logger need serializable strings, not Python objects. `model_dump_json()` serializes to a JSON string first, then `json.loads()` parses it back into a plain dict with strings throughout. This is the correct way to get a fully serializable dict from a Pydantic model with UUID and datetime fields.

**Why the initial state explicitly sets all fields to `None` rather than letting them be absent:**
Covered in `agent/state.py` walkthrough — LangGraph requires all fields to be present to avoid key errors in downstream nodes. This is where those initial values are set.

**Why `GET /escalations` reads from `escalation_queue.jsonl` rather than from `_result_store`:**
The escalation queue is the source of truth for escalated exceptions, not the in-memory store. The logger writes to `escalation_queue.jsonl` regardless of how the exception arrived — directly through the API or through the test harness. Reading from the file means the endpoint reflects reality, not just what went through this process instance. It also means the endpoint works correctly after a server restart.

**Why malformed lines in `escalation_queue.jsonl` are silently skipped:**
The file is append-only and written by the logger. A malformed line indicates a write failure during a previous run, not a bug in the current request. Skipping it and returning the valid escalations is better than failing the entire endpoint. Structured error logging for malformed lines is a v2 addition.

## What It Does Not Do

This file does not make any triage decisions. It passes the validated exception to the agent and returns whatever the agent produces. The agent is the decision-maker.

It does not write to the audit log. That is the agent's terminal node's responsibility — `log_result` calls the logger directly. The API layer does not participate in logging.

It does not authenticate requests. Authentication is not in scope for v1.

## V2 Touch Points

`_result_store` is the primary v2 replacement target. When async processing is added in v2, the in-memory dict is replaced with a persistent queue and result store. The endpoint signatures do not change — only the implementation of how results are stored and retrieved.

The `submit_exception` function is synchronous (`def`, not `async def`). V2's async queue pattern requires it to become `async def` — enqueuing the exception and returning a job ID without waiting for the agent to complete. FastAPI supports this transition without any changes to the endpoint signature.
