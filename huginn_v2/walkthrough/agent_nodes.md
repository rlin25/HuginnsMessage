# Walkthrough: `agent/nodes.py`

## Purpose

This file contains all the node functions — the actual business logic of the agent. It is the most behavior-dense file in the system. Every decision that matters — keyword detection, regulatory retrieval, LLM reasoning, confidence thresholding, audit event construction — happens in one of the six functions here.

The file is organized so that the module-level constants at the top are the primary tuning surface. `SCORING_RUBRIC` is the most important: every confidence score in the v2 audit log was produced by that text. The constants are readable before any function code.

## Relationships

- **Imports from:** `agent/state.py` (for type annotation), `mimir/retriever.py` (called by `retrieve`), `logger/audit.py` (called by `log_result`), `anthropic` (Claude API client), `dotenv` (API key loading)
- **Imported by:** `agent/graph.py` — the graph registers every function in this file as a node
- **Does not touch:** The exception schema (`models/exception.py`), the API layer, or the Chroma index directly

## Decision Rationale

**Why `load_dotenv(find_dotenv(usecwd=True))` runs at module level**, not inside a function: the Anthropic client is instantiated inside `reason()` on every call. The API key must be in the environment before that instantiation. Placing the dotenv load at module level ensures it runs at import time — before any request is processed — regardless of how the module is imported (Decision 48).

**Why `find_dotenv(usecwd=True)`** rather than `load_dotenv()` without arguments: `load_dotenv()` only searches the current working directory. The project's `.env` lives in the parent of `huginn_v2/`. `usecwd=True` makes `find_dotenv` start from the actual working directory rather than using Python frame introspection, which fails in test runners and other non-interactive contexts (Decision 48).

**Why `SCORING_RUBRIC` is a module-level constant** rather than assembled inside `reason()`: it is the primary artifact for v3 prompt engineering. Keeping it at the top of the file — visible and isolated — makes it easy to find and modify without reading through function logic. It is the text that most directly governs the confidence score distribution (Decision 29).

**Why `ESCALATION_KEYWORDS` is a list** rather than a set: keyword matching iterates the list in order and stops at the first match, returning the matched keyword in `triggered_keyword`. Order is significant — earlier keywords are checked first. A set has no order guarantee. The specific ordering in v2 (`sanctions`, `AML`, `regulatory hold`, `buy-in`, `sell-out`) reflects descending sensitivity, though all five trigger the same outcome.

**Why `classify` lowercases the description before matching** rather than doing case-insensitive matching: `keyword.lower() in description_lower` produces no false negatives and handles mixed-case inputs from upstream systems. Detection is case-insensitive per the interface contract (Decision 43).

**Why `retrieve` uses `dict.fromkeys(c["document_id"] for c in chunks)`** to derive `retrieved_document_ids`: `dict.fromkeys()` deduplicates while preserving insertion order, which `set()` does not. The order reflects which documents appeared first in the combined chunk list (Pass 1 results before Pass 2 results), which is a more meaningful ordering than arbitrary set ordering.

**Why the prompt in `reason` places the rubric first**, before the retrieved chunks and the exception: the LLM reads the scoring framework before encountering the content it's scoring. This ordering reflects how the rubric is meant to work — the four factors should be active in the LLM's context as it reads the regulatory chunks, not introduced after.

**Why each chunk is formatted as `[{section_id}] ({retrieved_via})\n{text}\n---`**: the `section_id` and `retrieved_via` fields are visible to the LLM in the prompt. This supports the fourth rubric factor — cross-reference resolution — where the LLM should be able to identify which chunks came from the primary search and which were fetched specifically because they were cross-referenced. The separator `---` is a conventional markdown horizontal rule that provides visual structure without adding tokens.

**Why the markdown fence stripping exists in `reason`**: the Claude API is instructed to return raw JSON with no preamble. The model sometimes wraps its response in triple-backtick fences anyway. Without stripping, `json.loads()` raises an exception, which the broad `except Exception` catches and turns into a `system_error` escalation. The stripping is a defensive measure against a known model behavior pattern.

**Why `max_tokens=2048`**: the masterplan specified 1000. During the Subplan 5 gate, responses were truncated mid-JSON at character 2829. Regulatory reasoning traces on multi-paragraph document chunks are consistently longer than 1000 tokens. 2048 was sufficient for all observed responses (Decision 47).

**Why the broad `except Exception as e`** in `reason` rather than catching specific Anthropic SDK exceptions: any failure in the reason node — API error, network timeout, JSON parse failure, missing field in the parsed response — should produce the same outcome: escalation with `escalation_reason = "system_error: ..."`. Catching specific exception types would require enumerating every possible failure mode. The broad catch is the correct fail-fast behavior specified in Decision 28 (also Decision 33).

**Why `decide` checks `score is not None` before the threshold comparison**: `None` means the LLM call failed; that is an automatic escalation regardless of any threshold value. The `or` chain in the `escalation_reason` construction prefers any existing `escalation_reason` (set by `reason` on failure) over the generic threshold message, so the audit log records the actual cause of the `system_error`.

**Why `log_result` constructs the event dict explicitly** rather than passing `state` directly to `audit_logger.log()`: the event dict has a specific shape defined in the interface contract (Component 6). The explicit construction ensures only the expected fields are written — not every field in `AgentState`, which includes internal fields like `current_node` that are not audit log fields. It also handles the `str(exc.get("exception_id", ""))` conversion from UUID to string that the JSONL writer requires.

**Why `decision_timestamp` uses `datetime.now(timezone.utc)`**: naive datetimes (without timezone) in a financial audit log are a compliance liability — there is no way to know whether a naive `2026-05-01T09:30:00` is UTC, EST, or local time. UTC timestamps are unambiguous and comparable across records.

## What It Does Not Do

- No graph wiring or edge routing — that lives in `agent/graph.py`
- No schema validation — that lives in `models/exception.py`
- No retry logic on Claude API failures — fail fast and escalate (Decision 28)
- No caching of LLM responses
- No severity input to the LLM prompt — severity is metadata only in v2 (Decision 42)

## V3 Touch Points

`SCORING_RUBRIC` is the primary iteration target for v3 prompt engineering. The v2 audit log provides real data on which exception descriptions produced high-confidence correct outcomes and which produced low-confidence escalations. The rubric text — specifically the four factor descriptions and the scoring guidance bands — will be refined based on that data.

`ESCALATION_KEYWORDS` may expand based on v2 operational experience.

`severity` will be injected into the LLM prompt. The most likely approach is including it in the `exc_context` section of the prompt with guidance in the rubric on how to weight it — or as a fifth rubric factor.

When v3 introduces asynchronous processing, the `anthropic.Anthropic()` client instantiation inside `reason()` may move to a module-level singleton for connection pooling.
