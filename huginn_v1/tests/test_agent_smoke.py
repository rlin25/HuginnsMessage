# python tests/test_agent_smoke.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from dotenv import load_dotenv
load_dotenv()

from agent.graph import huginn_graph

# Clean logs before testing
Path("logs/audit.jsonl").unlink(missing_ok=True)
Path("logs/escalation_queue.jsonl").unlink(missing_ok=True)
Path("logs/audit.db").unlink(missing_ok=True)

fixtures_dir = Path("tests/fixtures")

def load_fixture(name: str) -> dict:
    data = json.loads((fixtures_dir / name).read_text())
    # Convert to plain dict with string values for the agent
    data["exception_id"] = str(data["exception_id"])
    return data

all_pass = True

# --- Test 1: Standard path (should resolve or escalate based on LLM confidence) ---
print("Test 1: Standard path — price_mismatch")
exc = load_fixture("fixture_price_mismatch.json")
result = huginn_graph.invoke({
    "exception": exc,
    "job_id": "smoke-test-001",
    "retrieved_chunks": [],
    "retrieved_document_id": None,
    "confidence_score": None,
    "reasoning_trace": None,
    "resolution_steps": None,
    "llm_raw_response": None,
    "outcome": None,
    "escalation_reason": None,
    "triggered_keyword": None,
    "exception_type": None,
    "exception_sub_type": None,
    "current_node": "",
})

outcome = result.get("outcome")
if outcome in ("auto_resolve", "escalate"):
    print(f"  PASS: outcome = {outcome}")
    print(f"  confidence_score = {result.get('confidence_score')}")
    print(f"  retrieved_document_id = {result.get('retrieved_document_id')}")
else:
    print(f"  FAIL: unexpected outcome = {outcome}")
    all_pass = False

# --- Test 2: Mandatory escalation fast-exit ---
print("\nTest 2: Mandatory escalation fast-exit — sanctions keyword")
exc = load_fixture("fixture_mandatory_escalation.json")
result = huginn_graph.invoke({
    "exception": exc,
    "job_id": "smoke-test-002",
    "retrieved_chunks": [],
    "retrieved_document_id": None,
    "confidence_score": None,
    "reasoning_trace": None,
    "resolution_steps": None,
    "llm_raw_response": None,
    "outcome": None,
    "escalation_reason": None,
    "triggered_keyword": None,
    "exception_type": None,
    "exception_sub_type": None,
    "current_node": "",
})

outcome = result.get("outcome")
escalation_reason = result.get("escalation_reason", "")
retrieved_doc = result.get("retrieved_document_id")
confidence = result.get("confidence_score")

fast_exit_correct = (
    outcome == "escalate"
    and "sanctions" in escalation_reason
    and retrieved_doc is None
    and confidence is None
)

if fast_exit_correct:
    print(f"  PASS: outcome=escalate, escalation_reason='{escalation_reason}', retrieved_document_id=None, confidence_score=None")
else:
    print(f"  FAIL: outcome={outcome}, escalation_reason={escalation_reason}, retrieved_document_id={retrieved_doc}, confidence_score={confidence}")
    all_pass = False

# --- Verify audit log was written ---
print("\nVerifying audit log...")
if Path("logs/audit.jsonl").exists():
    lines = Path("logs/audit.jsonl").read_text().strip().split("\n")
    print(f"  PASS: audit.jsonl has {len(lines)} entries")
else:
    print("  FAIL: audit.jsonl not found")
    all_pass = False

if Path("logs/escalation_queue.jsonl").exists():
    lines = Path("logs/escalation_queue.jsonl").read_text().strip().split("\n")
    print(f"  PASS: escalation_queue.jsonl has {len(lines)} entries (should be ≥1)")
else:
    print("  FAIL: escalation_queue.jsonl not found — fast-exit escalation should have written to it")
    all_pass = False

print()
if all_pass:
    print("Agent smoke tests passed. Gate cleared for Subplan 5.")
else:
    print("One or more tests failed. Do not proceed to Subplan 5.")
