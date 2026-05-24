# tests/test_api.py

import json
import pytest
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()

from api.main import app

client = TestClient(app)

FIXTURES_DIR = Path("tests/fixtures")


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestAPIEndpoints:

    def setup_method(self):
        """Clean logs and result store before each test."""
        Path("logs/audit.jsonl").unlink(missing_ok=True)
        Path("logs/escalation_queue.jsonl").unlink(missing_ok=True)
        Path("logs/audit.db").unlink(missing_ok=True)

        # Reset the in-memory result store
        import api.main as main_module
        main_module._result_store.clear()

    # -----------------------------------------------------------------------
    # POST /exceptions
    # -----------------------------------------------------------------------

    def test_post_exception_valid_returns_200(self):
        payload = load_fixture("fixture_price_mismatch.json")
        response = client.post("/exceptions", json=payload)
        assert response.status_code == 200

    def test_post_exception_response_schema(self):
        payload = load_fixture("fixture_price_mismatch.json")
        response = client.post("/exceptions", json=payload)
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert "exception_id" in data
        assert "timestamp" in data
        assert data["status"] == "received"

    def test_post_exception_invalid_type_returns_422(self):
        payload = load_fixture("fixture_invalid_type.json")
        response = client.post("/exceptions", json=payload)
        assert response.status_code == 422

    def test_post_exception_missing_field_returns_422(self):
        payload = load_fixture("fixture_price_mismatch.json")
        del payload["trade_id"]
        response = client.post("/exceptions", json=payload)
        assert response.status_code == 422

    # -----------------------------------------------------------------------
    # GET /exceptions/{job_id}
    # -----------------------------------------------------------------------

    def test_get_exception_result_returns_200(self):
        payload = load_fixture("fixture_price_mismatch.json")
        post_response = client.post("/exceptions", json=payload)
        job_id = post_response.json()["job_id"]

        get_response = client.get(f"/exceptions/{job_id}")
        assert get_response.status_code == 200

    def test_get_exception_result_schema(self):
        payload = load_fixture("fixture_price_mismatch.json")
        post_response = client.post("/exceptions", json=payload)
        job_id = post_response.json()["job_id"]

        data = client.get(f"/exceptions/{job_id}").json()
        assert "job_id" in data
        assert "exception_id" in data
        assert "outcome" in data
        assert "timestamp" in data
        assert data["outcome"] in ("auto_resolve", "escalate")

    def test_get_exception_unknown_job_id_returns_404(self):
        response = client.get("/exceptions/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    # -----------------------------------------------------------------------
    # Standard path — verify Mimir was called
    # -----------------------------------------------------------------------

    def test_standard_path_price_mismatch_has_retrieved_document(self):
        payload = load_fixture("fixture_price_mismatch.json")
        post_response = client.post("/exceptions", json=payload)
        job_id = post_response.json()["job_id"]
        result = client.get(f"/exceptions/{job_id}").json()

        assert result["retrieved_document_id"] == "SOP-SM-001"
        assert result["confidence_score"] is not None
        assert result["reasoning_trace"] is not None

    # -----------------------------------------------------------------------
    # Fast-exit path — verify Mimir and LLM were NOT called
    # -----------------------------------------------------------------------

    def test_fast_exit_path_sanctions_keyword(self):
        payload = load_fixture("fixture_mandatory_escalation.json")
        post_response = client.post("/exceptions", json=payload)
        job_id = post_response.json()["job_id"]
        result = client.get(f"/exceptions/{job_id}").json()

        assert result["outcome"] == "escalate"
        assert result["retrieved_document_id"] is None
        assert result["confidence_score"] is None
        assert "sanctions" in result["escalation_reason"]

    # -----------------------------------------------------------------------
    # GET /escalations
    # -----------------------------------------------------------------------

    def test_get_escalations_returns_200(self):
        response = client.get("/escalations")
        assert response.status_code == 200

    def test_get_escalations_empty_when_no_escalations(self):
        response = client.get("/escalations")
        data = response.json()
        assert "escalations" in data
        assert isinstance(data["escalations"], list)

    def test_get_escalations_contains_escalated_exception(self):
        payload = load_fixture("fixture_mandatory_escalation.json")
        client.post("/exceptions", json=payload)

        response = client.get("/escalations")
        data = response.json()
        assert len(data["escalations"]) >= 1

        escalation = data["escalations"][0]
        assert escalation["outcome"] == "escalate"
        assert escalation["escalation_reason"] is not None

    def test_get_escalations_does_not_contain_auto_resolved(self):
        """Submit exceptions until one auto-resolves, confirm it's absent from queue."""
        payload = load_fixture("fixture_price_mismatch.json")
        post_response = client.post("/exceptions", json=payload)
        job_id = post_response.json()["job_id"]
        result = client.get(f"/exceptions/{job_id}").json()

        if result["outcome"] == "auto_resolve":
            escalations = client.get("/escalations").json()["escalations"]
            assert not any(e["job_id"] == job_id for e in escalations)

    # -----------------------------------------------------------------------
    # Audit log verification
    # -----------------------------------------------------------------------

    def test_audit_jsonl_written_after_submission(self):
        payload = load_fixture("fixture_price_mismatch.json")
        client.post("/exceptions", json=payload)

        assert Path("logs/audit.jsonl").exists()
        lines = Path("logs/audit.jsonl").read_text().strip().split("\n")
        assert len(lines) >= 1

    def test_sqlite_record_written_after_submission(self):
        payload = load_fixture("fixture_quantity_mismatch.json")
        post_response = client.post("/exceptions", json=payload)
        job_id = post_response.json()["job_id"]

        conn = sqlite3.connect("logs/audit.db")
        row = conn.execute(
            "SELECT job_id, outcome FROM audit_log WHERE job_id = ?", (job_id,)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == job_id
        assert row[1] in ("auto_resolve", "escalate")

    def test_escalation_queue_written_for_fast_exit(self):
        payload = load_fixture("fixture_mandatory_escalation.json")
        client.post("/exceptions", json=payload)

        assert Path("logs/escalation_queue.jsonl").exists()
        lines = Path("logs/escalation_queue.jsonl").read_text().strip().split("\n")
        assert len(lines) >= 1

        record = json.loads(lines[0])
        assert record["outcome"] == "escalate"
