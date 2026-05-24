# Walkthrough: `logger/audit.py`

## Purpose

This file is the entire audit logging system. It accepts a structured event dict and writes it to every applicable destination. Callers — specifically the `log_result` node in the agent — call one function and walk away. Where the data goes is not their concern.

The isolation is enforced by design. Decision 27 explicitly states that routing logic belongs inside the logger, not at call sites. A single entry point means callers cannot accidentally write to the wrong destination, forget a destination, or develop inconsistent logging behavior across different code paths.

The logger exists as a standalone module — not inside `agent/` or `api/` — because it serves the whole system, not one component. Both the standard path and the fast-exit path ultimately reach `log_result`, which calls this file. The logger's isolation is what makes that convergence clean.

Decisions 3, 6, 17, 18, and 27 govern this file.

## Relationships

- **Imported by:** `logger/audit.py` is imported by `agent/nodes.py` (the `log_result` node only)
- **Imports from:** Python standard library only (`json`, `sqlite3`, `datetime`, `pathlib`) — no Huginn dependencies
- **Does not touch:** the agent state directly, Mimir, the API layer, or the exception schema

The logger is a terminal component. Nothing calls it and then waits for a result. It writes and returns `None`.

## Decision Rationale

**Why dual-write to both JSONL and SQLite:**
Decision 3. The `.jsonl` file provides a human-readable compliance trail — a compliance officer can open it and read it without any tooling. SQLite adds queryability: exception type, outcome, confidence score, date range queries. These are different access patterns serving different audiences. SQLite is Python's standard library — zero additional dependency. The dual-write costs a few milliseconds per event in v1 and makes v2 evaluation harness construction trivial.

**Why the escalation queue is a separate file rather than a flag:**
Decision 6. Making the escalation pathway physically visible as a separate file means a human reviewer's inbox is demonstrable without parsing the full audit log. It also sets up v3's notification layer naturally — the notification system reads from `escalation_queue.jsonl`. If escalation were only a field in the audit log, extracting it for notifications would require filtering logic at the notification layer.

**Why `full_event_json` in the SQLite schema:**
Decision 17. Full fidelity means every field that exists now and every field added in v2 is captured without schema migration. The individual SQLite columns support queries on the most common fields (type, outcome, confidence, date). `full_event_json` stores the complete record so no information is ever lost, regardless of what the SQLite columns capture. When v2 adds new fields, they appear automatically in `full_event_json` without a migration.

**Why the `_db_initialized and AUDIT_DB.exists()` guard:**
This is a bug fix that emerged during implementation, not a design decision. The module-level `_db_initialized` flag prevents `CREATE TABLE IF NOT EXISTS` from running on every log call. But in the test suite, `setup_method` deletes `audit.db` between tests. Without the `.exists()` check, the flag would remain `True` after deletion, and the next test would attempt to insert into a table that no longer existed. The guard catches this: if the flag is set but the file is gone, re-initialize.

**Why routing to `escalation_queue.jsonl` is based on `outcome == "escalate"` inside the logger:**
Decision 27. The caller passes an event dict with an `outcome` field. The logger reads that field and routes accordingly. This means the caller never needs to know that a separate escalation queue exists — it just calls `log()`. If a new destination were added in v2 (say, a real-time notification queue), the change happens entirely inside this file.

## What It Does Not Do

This file does not make any decisions. It does not examine the exception, assess the confidence score, or determine whether an outcome is correct. It writes what it receives.

It does not expose any functions other than `log()`. The internal `_write_jsonl`, `_write_sqlite`, and `_init_db` functions are implementation details — not part of the public interface.

It does not send notifications. The escalation queue file is the notification mechanism in v1. Real notifications (email, Slack, webhook) are a v3 feature.

## V2 Touch Points

The SQLite schema is the primary v2 touch point. When new fields are added to the audit log in v2, they appear in `full_event_json` automatically. Individual SQLite columns that support queries may need to be added — that is a schema migration, but `full_event_json` ensures no data is lost in the interim.

The `_db_initialized` guard is a v1 workaround for test isolation. A v2 cleanup might replace the module-level flag with a more robust initialization pattern — for instance, connection pooling or a context manager. For v1 the current approach is sufficient.
