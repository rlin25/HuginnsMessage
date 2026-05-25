# Walkthrough: `api/main.py`

## Purpose

This file is the system's only HTTP entry point. It accepts requests, validates them, invokes the agent, and reads results from the audit log. It does not contain business logic — it delegates immediately to the components that do.

Four endpoints cover the full interaction surface: submitting an exception, retrieving a result, inspecting the escalation queue, and checking service health. The first three form the demo story. The fourth is a deployment standard.

## Relationships

- **Imports from:** `models/exception.py` (for `TradeException` validation), `agent/graph.py` (for `huginn_graph`), `logger/audit.py` (for `AUDIT_DB` path in GET endpoints)
- **Imported by:** Test suite (`tests/test_integration.py` creates a `TestClient(app)`); the Uvicorn server imports `app` via `api.main:app`
- **Does not touch:** Mimir directly, the audit logger's write functions, or any internal agent state

## Decision Rationale

**Why `submit_exception` takes `payload: dict`** rather than `exc: TradeException` as a FastAPI parameter: if `TradeException` were the parameter type, FastAPI would perform automatic validation and return its own 422 format on failure. By taking a raw dict and catching `ValidationError` explicitly, the endpoint controls the 422 response body — returning `e.errors()`, which is the same structured Pydantic error format but surfaced through an explicit `HTTPException` (Decision 34). The behavior is equivalent, but the explicit catch makes the validation path visible.

**Why `exc.model_dump(mode="json")`** converts the `TradeException` to a dict before passing it to the agent state: `TradeException` contains `UUID` and `datetime` fields that are not JSON-serializable by default. `model_dump(mode="json")` serializes them to strings — UUID as a hyphenated string, datetime as ISO 8601 — so the resulting dict can flow through the agent state, be passed to `json.dumps()` in the logger, and appear in the API response without serialization errors. The alternative (`model_dump_json()` + `json.loads()`) achieves the same result with an unnecessary JSON round-trip (from glossary, Decision 51).

**Why `POST /exceptions` returns the full result immediately** rather than just a `job_id`: processing is synchronous in v2. `huginn_graph.invoke(state)` runs to completion before the response is sent. The full result is available at zero marginal cost. Returning only a job ID forces an unnecessary second HTTP round trip when the result is already in hand (Decision 50). The `GET /exceptions/{job_id}` endpoint remains as a second read path for clients that need to look up results by ID after the fact.

**Why `GET /exceptions/{job_id}` reads from SQLite** rather than an in-memory dict: the masterplan specified an in-memory `results: dict` store. An in-memory store is cleared on server restart — a job ID submitted in a previous session is unrecoverable. The audit logger already writes every result to `full_event_json` in SQLite. Reading from there is persistent at no additional code cost (Decision 51).

**Why `sqlite3` and `json` are imported inside `get_result` and `get_escalations`** rather than at module level: these are standard library modules that always succeed, so deferred import is not for error isolation. The pattern here is a practical choice made during Subplan 6 implementation — it keeps the module-level imports focused on FastAPI and the project components, and avoids loading modules that are only needed by specific endpoints at application startup.

**Why `GET /escalations` checks `AUDIT_DB.exists()` and returns `{"escalations": []}`** rather than raising a 404: an empty escalation queue is a valid state, not an error. The database file doesn't exist until the first exception is processed. Returning an empty list correctly represents "no escalations yet" (from interface contract).

**Why `GET /health`** exists despite not being in the original specification: any container orchestration system (Kubernetes, ECS) or reverse proxy needs a health check endpoint. Without one, the service appears unhealthy and gets restarted or removed from the load balancer. The endpoint is three lines and has no dependencies (Decision 52).

**Why `import uuid` is at module level** but `sqlite3` and `json` are deferred: `uuid` is used on every POST request; it belongs at module level. `sqlite3` and `json` are only needed on GET requests.

## What It Does Not Do

- No authentication or authorization
- No rate limiting
- No background task processing — v2 is synchronous only
- No retry logic for agent failures — the agent handles its own error cases and always returns a result
- No custom exception handlers beyond the explicit `ValidationError` catch in `submit_exception`
- No caching of results — all reads go to SQLite

## V3 Touch Points

The primary change for v3 is asynchronous processing. When `huginn_graph.invoke(state)` becomes a background task, `POST /exceptions` returns the minimal `{job_id, status, exception_id, timestamp}` response specified in Decision 19 (the original spec that v2 chose not to implement because synchronous processing made it unnecessary). `GET /exceptions/{job_id}` becomes the primary result path — clients poll it until the result is available.

The two-endpoint pattern (`POST` → `GET`) is already in place. The transition requires changing the POST handler to enqueue the job and return immediately, not adding new endpoints.
