# Walkthrough: `logger/audit.py`

## Purpose

This file writes the complete audit record for every exception Huginn processes, to every applicable destination. It is called exactly once per exception, by the `log_result` node, at the end of every execution path. The design constraint is that no exception can exit the system without an audit record — the terminal node structure in `agent/graph.py` enforces this at the graph level, and this file handles the mechanics.

The logger exists as a separate component — rather than inline writes inside `log_result` — because three write destinations have different routing logic. The audit log always receives a write. SQLite always receives a write. The escalation queue receives a write only on escalations. That routing condition is a business rule that belongs in a dedicated component, not embedded in a node function that also has other responsibilities (Decision 27).

## Relationships

- **Imports from:** Standard library only (`json`, `sqlite3`, `pathlib`)
- **Imported by:** `agent/nodes.py` (the `log_result` node calls `log()`); `api/main.py` imports `AUDIT_DB` as a path reference for the GET endpoints
- **Does not touch:** The agent graph, Mimir, the exception schema, or any LLM-related code

## Decision Rationale

**Why `_db_initialized` is a module-level flag**: `_init_db()` runs `CREATE TABLE IF NOT EXISTS`, which is idempotent — it won't fail if the table already exists. The flag avoids the connection overhead on every `log()` call after the first successful initialization. The additional `AUDIT_DB.exists()` check handles the case where the process restarts and the in-memory flag is reset to `False` but the database file already exists.

**Why `json.dumps(event, default=str)` is used for both the JSONL write and the `full_event_json` column**: the event dict can contain Python types that are not JSON-serializable by default — specifically `UUID` and `datetime` objects if they weren't converted to strings upstream. `default=str` serializes them as strings. This is a defensive choice: the audit log should never fail to write because of a serialization edge case.

**Why `full_event_json` stores the entire event dict** rather than assembling individual columns: v3 will add new fields to the event dict. The individual column list (`job_id`, `outcome`, `confidence_score`, etc.) supports efficient queries on common fields. But any field not in the column list would be permanently lost without `full_event_json`. The full dict stored as JSON means no data is ever dropped, and a v3 migration can add new queryable columns while still having complete historical records (Decision 17).

**Why `INSERT OR REPLACE`** rather than `INSERT OR IGNORE` or a standard `INSERT`: `job_id` is the primary key. In practice it's a UUID generated per request, so collisions don't occur. But `INSERT OR REPLACE` is the defensive choice — if somehow the same `job_id` were written twice, the second write updates the record rather than silently failing or raising an exception.

**Why routing to `escalation_queue.jsonl` is internal** to this function rather than exposed as a separate function: from the caller's perspective, an escalation is just a `log()` call. The decision that escalations also go to a separate queue is an implementation detail of the audit logger, not a concern for the node that calls it. Separating them into `log_decision()` and `log_escalation()` would push routing knowledge into the caller (Decision 27).

**Why `logs/` is not created at module import time**: the directory is created lazily by `_init_db()` and by the JSONL write. This is documented as intentional in the setup notes (Known Issue 5). The directory is a runtime artifact — it is in `.gitignore` and should not exist in a fresh clone. Creating it at import time would mean any test that imports the logger creates the directory, which is unexpected.

**Why `AUDIT_DB` is a module-level `Path` constant** rather than a local variable: `api/main.py`'s GET endpoints need this path to open the database. Exporting it as a named constant from the logger — rather than having the API layer hardcode the path — means the database location is defined once.

## What It Does Not Do

- No log rotation, archiving, or size management
- No filtering or transformation of the event dict — it writes whatever it receives
- No separate public functions for different event types
- No reading from any destination — the logger is write-only; reading is done by `api/main.py` directly via `sqlite3`
- No validation that the event dict contains the expected fields — the caller is responsible for constructing a complete event

## V3 Touch Points

`full_event_json` means any new fields added to the event dict in v3 appear in the JSONL and `full_event_json` column automatically, without modifying this file. Adding a new queryable column to the SQLite schema would require a migration, but the data is already there in `full_event_json`.

The escalation queue write to a flat file may be replaced by a real notification system in v3 — an email, a webhook, or a queue message. When that happens, the routing condition (`if event.get("outcome") == "escalate"`) and the write destination change here, not in the caller.
