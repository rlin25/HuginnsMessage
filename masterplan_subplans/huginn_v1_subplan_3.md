# Huginn v1 — Subplan 3: Audit Logger

**Component:** `logger/audit.py`
**Depends on:** Subplan 2 gate must be confirmed passing.
**Gate:** A test call to `log()` produces correct entries in `logs/audit.jsonl`, `logs/audit.db` (SQLite), and — when `outcome == "escalate"` — in `logs/escalation_queue.jsonl`, before Subplan 4 begins.

---

## Reference Documents

- `huginn_v1_interface_contract.md` — Component 6 (Audit Logger)
- `huginn_v1_design_decisions.md` — Decisions 3, 6, 17, 18, 27, 28

---

## What to Build

A single file: `logger/audit.py`

It exposes one public function: `log(event: dict) -> None`

The logger handles all routing internally. Callers do not specify destinations.

---

## Implementation

```python
# logger/audit.py

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path("logs")
AUDIT_JSONL = LOGS_DIR / "audit.jsonl"
AUDIT_DB = LOGS_DIR / "audit.db"
ESCALATION_JSONL = LOGS_DIR / "escalation_queue.jsonl"

_db_initialized = False


def _ensure_logs_dir():
    LOGS_DIR.mkdir(exist_ok=True)


def _init_db():
    global _db_initialized
    if _db_initialized:
        return
    _ensure_logs_dir()
    conn = sqlite3.connect(AUDIT_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            job_id TEXT PRIMARY KEY,
            exception_id TEXT,
            trade_id TEXT,
            type TEXT,
            sub_type TEXT,
            outcome TEXT,
            confidence_score REAL,
            triggered_keyword TEXT,
            retrieved_document_id TEXT,
            escalation_reason TEXT,
            decision_timestamp TEXT,
            exception_timestamp TEXT,
            severity TEXT,
            full_event_json TEXT
        )
    """)
    conn.commit()
    conn.close()
    _db_initialized = True


def _write_jsonl(path: Path, event: dict):
    _ensure_logs_dir()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


def _write_sqlite(event: dict):
    _init_db()
    conn = sqlite3.connect(AUDIT_DB)
    conn.execute(
        """
        INSERT OR REPLACE INTO audit_log (
            job_id, exception_id, trade_id, type, sub_type,
            outcome, confidence_score, triggered_keyword,
            retrieved_document_id, escalation_reason,
            decision_timestamp, exception_timestamp, severity,
            full_event_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(event.get("job_id")),
            str(event.get("exception_id")),
            event.get("trade_id"),
            event.get("type"),
            event.get("sub_type"),
            event.get("outcome"),
            event.get("confidence_score"),
            event.get("triggered_keyword"),
            event.get("retrieved_document_id"),
            event.get("escalation_reason"),
            event.get("decision_timestamp"),
            event.get("timestamp"),
            event.get("severity"),
            json.dumps(event, default=str),
        ),
    )
    conn.commit()
    conn.close()


def log(event: dict) -> None:
    """
    Accepts a structured event dict and writes it to all applicable destinations:
      - Always: logs/audit.jsonl (append-only)
      - Always: logs/audit.db (SQLite)
      - If outcome == "escalate": logs/escalation_queue.jsonl (append-only)

    Callers do not specify destinations. Routing is internal.
    """
    # Stamp a log_written_at timestamp for the file record itself
    event_to_write = dict(event)
    event_to_write["log_written_at"] = datetime.now(timezone.utc).isoformat()

    # Always write to audit log
    _write_jsonl(AUDIT_JSONL, event_to_write)

    # Always write to SQLite
    _write_sqlite(event_to_write)

    # Conditionally write to escalation queue
    if event.get("outcome") == "escalate":
        _write_jsonl(ESCALATION_JSONL, event_to_write)
```

---

## Expected Event Dict Schema

The caller (the agent's `log_result` node) passes a dict with these fields. All fields must be present; nullable fields may be `None`.

| Field | Always present | Nullable |
|---|---|---|
| `job_id` | Yes | No |
| `exception_id` | Yes | No |
| `trade_id` | Yes | No |
| `type` | Yes | No |
| `sub_type` | Yes | No |
| `description` | Yes | No |
| `timestamp` | Yes | No |
| `severity` | Yes | No |
| `outcome` | Yes | No |
| `triggered_keyword` | Yes | Yes (None on standard path) |
| `retrieved_chunks` | Yes | No (empty list on fast-exit) |
| `retrieved_document_id` | Yes | Yes (None on fast-exit) |
| `confidence_score` | Yes | Yes (None on fast-exit) |
| `reasoning_trace` | Yes | Yes (None on fast-exit) |
| `resolution_steps` | Yes | Yes (None on fast-exit) |
| `escalation_reason` | Yes | Yes (None on auto-resolve) |
| `llm_raw_response` | Yes | Yes (None on fast-exit) |
| `decision_timestamp` | Yes | No |

---

## Gate Verification Script

```python
# python tests/test_logger_smoke.py

import json
import sqlite3
from pathlib import Path
import sys

# Temporarily clean up test artifacts if they exist
Path("logs/audit.jsonl").unlink(missing_ok=True)
Path("logs/escalation_queue.jsonl").unlink(missing_ok=True)
Path("logs/audit.db").unlink(missing_ok=True)

from logger.audit import log

# --- Test 1: Auto-resolve event ---
auto_resolve_event = {
    "job_id": "test-job-001",
    "exception_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "trade_id": "TRD-001",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Price discrepancy on bond settlement.",
    "timestamp": "2026-05-15T09:30:00Z",
    "severity": "high",
    "outcome": "auto_resolve",
    "triggered_keyword": None,
    "retrieved_chunks": [{"text": "Step 1...", "document_id": "SOP-SM-001", "sub_type": "price_mismatch", "similarity_score": 0.85}],
    "retrieved_document_id": "SOP-SM-001",
    "confidence_score": 0.87,
    "reasoning_trace": "The exception matches the price mismatch SOP. High confidence.",
    "resolution_steps": "Step 1: Verify both confirmations. Step 2: Amend record.",
    "escalation_reason": None,
    "llm_raw_response": '{"confidence_score": 0.87, "reasoning_trace": "...", "resolution_steps": "..."}',
    "decision_timestamp": "2026-05-15T09:31:00Z",
}

log(auto_resolve_event)

# --- Test 2: Escalate event (fast-exit) ---
escalate_event = {
    "job_id": "test-job-002",
    "exception_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "trade_id": "TRD-004",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Price discrepancy. Counterparty subject to sanctions review.",
    "timestamp": "2026-05-15T11:30:00Z",
    "severity": "high",
    "outcome": "escalate",
    "triggered_keyword": "sanctions",
    "retrieved_chunks": [],
    "retrieved_document_id": None,
    "confidence_score": None,
    "reasoning_trace": None,
    "resolution_steps": None,
    "escalation_reason": "mandatory escalation keyword detected: sanctions",
    "llm_raw_response": None,
    "decision_timestamp": "2026-05-15T11:30:01Z",
}

log(escalate_event)

# --- Verification ---
all_pass = True

# Check audit.jsonl
audit_lines = Path("logs/audit.jsonl").read_text().strip().split("\n")
if len(audit_lines) == 2:
    print("PASS: audit.jsonl contains 2 entries")
else:
    print(f"FAIL: audit.jsonl contains {len(audit_lines)} entries (expected 2)")
    all_pass = False

# Check escalation_queue.jsonl — should contain only the escalated event
escalation_lines = Path("logs/escalation_queue.jsonl").read_text().strip().split("\n")
if len(escalation_lines) == 1:
    escalation_record = json.loads(escalation_lines[0])
    if escalation_record["job_id"] == "test-job-002":
        print("PASS: escalation_queue.jsonl contains 1 entry with correct job_id")
    else:
        print(f"FAIL: escalation_queue.jsonl job_id mismatch")
        all_pass = False
else:
    print(f"FAIL: escalation_queue.jsonl contains {len(escalation_lines)} entries (expected 1)")
    all_pass = False

# Check SQLite
conn = sqlite3.connect("logs/audit.db")
rows = conn.execute("SELECT job_id, outcome FROM audit_log ORDER BY job_id").fetchall()
conn.close()

if len(rows) == 2:
    print(f"PASS: SQLite contains 2 rows")
    for row in rows:
        print(f"  {row[0]} → {row[1]}")
else:
    print(f"FAIL: SQLite contains {len(rows)} rows (expected 2)")
    all_pass = False

# Check auto_resolve event is NOT in escalation queue
auto_resolve_in_escalation = any(
    json.loads(line).get("job_id") == "test-job-001"
    for line in Path("logs/escalation_queue.jsonl").read_text().strip().split("\n")
)
if not auto_resolve_in_escalation:
    print("PASS: auto_resolve event correctly absent from escalation_queue.jsonl")
else:
    print("FAIL: auto_resolve event should not appear in escalation_queue.jsonl")
    all_pass = False

print()
if all_pass:
    print("All logger smoke tests passed. Gate cleared for Subplan 4.")
else:
    print("One or more tests failed. Do not proceed to Subplan 4.")
```

**Expected output:**
```
PASS: audit.jsonl contains 2 entries
PASS: escalation_queue.jsonl contains 1 entry with correct job_id
PASS: SQLite contains 2 rows
  test-job-001 → auto_resolve
  test-job-002 → escalate
PASS: auto_resolve event correctly absent from escalation_queue.jsonl

All logger smoke tests passed. Gate cleared for Subplan 4.
```

---

## Notes

- The `logs/` directory is created automatically if it does not exist — do not pre-create it
- The SQLite connection is opened and closed on each call — no connection pooling needed in v1
- `INSERT OR REPLACE` on `job_id` means re-logging the same job ID overwrites the SQLite row (idempotent) but appends to the `.jsonl` files — this is acceptable in v1
- `json.dumps(event, default=str)` handles `UUID` and `datetime` objects by converting them to strings — this ensures the logger never fails on non-serializable types from the agent
- Do not import from `agent/`, `mimir/`, `api/`, or `models/` in this component
