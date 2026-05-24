# python tests/test_logger_smoke.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import sqlite3

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
