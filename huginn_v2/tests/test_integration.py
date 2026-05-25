"""
Integration tests for the full agent pipeline via the FastAPI layer.

Each test invokes a live Claude API call or a path that bypasses it (fast-exit,
invalid-type). Set ANTHROPIC_API_KEY in the environment before running.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

_BASE = {
    "exception_id": str(uuid.uuid4()),
    "trade_id": "TRD-IT-001",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "timestamp": "2025-01-15T10:30:00Z",
    "severity": "medium",
}


def _post(overrides: dict) -> dict:
    payload = {**_BASE, "exception_id": str(uuid.uuid4()), **overrides}
    resp = client.post("/exceptions", json=payload)
    return resp


# ---------------------------------------------------------------------------
# 1. Invalid exception type → 422 before the graph runs
# ---------------------------------------------------------------------------
def test_invalid_type_returns_422():
    resp = _post({"type": "not_a_real_type", "description": "irrelevant"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 2–6. Mandatory escalation keywords — fast-exit path (no LLM call)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("keyword", [
    "sanctions",
    "AML",
    "regulatory hold",
    "buy-in",
    "sell-out",
])
def test_mandatory_keyword_escalates(keyword):
    resp = _post({"description": f"This trade involves a {keyword} flag."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "escalate"
    assert body["confidence_score"] is None
    assert keyword.lower() in (body.get("escalation_reason") or "").lower()


# ---------------------------------------------------------------------------
# 7. Standard path — LLM scores the exception
# ---------------------------------------------------------------------------
def test_standard_path_returns_score_and_outcome():
    resp = _post({
        "description": (
            "Trade TRD-IT-STD settled at $101.50 vs contract price $100.00 "
            "on 1000 shares — $1.50 discrepancy."
        ),
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] in ("auto_resolve", "escalate")
    assert isinstance(body["confidence_score"], float)
    assert 0.0 <= body["confidence_score"] <= 1.0
    assert body["reasoning_trace"]
    assert len(body["retrieved_document_ids"]) > 0


# ---------------------------------------------------------------------------
# 8. GET /exceptions/{job_id} round-trip — result persisted to SQLite
# ---------------------------------------------------------------------------
def test_get_result_round_trip():
    resp = _post({
        "description": "Wrong settlement date by one business day on TRD-IT-RT.",
        "sub_type": "wrong_settlement_date",
    })
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    get_resp = client.get(f"/exceptions/{job_id}")
    assert get_resp.status_code == 200
    record = get_resp.json()
    assert record["job_id"] == job_id
    assert record["outcome"] in ("auto_resolve", "escalate")


# ---------------------------------------------------------------------------
# 9. GET /exceptions/{job_id} — unknown id returns 404
# ---------------------------------------------------------------------------
def test_get_unknown_job_id_returns_404():
    resp = client.get(f"/exceptions/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 10. Standard path, low-confidence escalation — vague description
# ---------------------------------------------------------------------------
def test_low_confidence_escalates_with_reason():
    resp = _post({"description": "quantity issue", "sub_type": "quantity_mismatch"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] == "escalate"
    assert body["confidence_score"] is not None
    assert isinstance(body["confidence_score"], float)
    assert body["confidence_score"] < 0.75
    assert "confidence score" in (body.get("escalation_reason") or "").lower()
    assert len(body["retrieved_document_ids"]) > 0


# ---------------------------------------------------------------------------
# 11. wrong_settlement_date — SEC-15c6-1 must appear in retrieved docs
# ---------------------------------------------------------------------------
def test_wrong_settlement_date_retrieves_sec_rule():
    resp = _post({
        "sub_type": "wrong_settlement_date",
        "description": (
            "Trade recorded settlement date of T+2 but counterparty insists T+1 "
            "applies under SEC Rule 15c6-1 as amended in May 2024."
        ),
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome"] in ("auto_resolve", "escalate")
    assert "SEC-15c6-1" in body["retrieved_document_ids"]


# ---------------------------------------------------------------------------
# 12. GET /escalations — returns escalated entries with correct schema
# ---------------------------------------------------------------------------
def test_get_escalations_returns_queue():
    # Submit a sanctions exception to guarantee at least one escalation entry
    _post({"description": "Trade involves sanctions screening flag."})

    resp = client.get("/escalations")
    assert resp.status_code == 200
    body = resp.json()
    assert "escalations" in body
    assert isinstance(body["escalations"], list)
    assert len(body["escalations"]) >= 1
    for entry in body["escalations"]:
        assert entry["outcome"] == "escalate"
        assert "job_id" in entry
        assert "exception_id" in entry
