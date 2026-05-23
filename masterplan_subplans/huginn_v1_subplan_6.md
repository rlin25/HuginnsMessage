# Huginn v1 — Subplan 6: Integration Tests

**Component:** `tests/test_api.py`, `tests/test_agent.py`, `tests/test_mimir.py`
**Depends on:** Subplan 5 gate must be confirmed passing.
**Gate:** All pytest tests pass across all three test files.

---

## Reference Documents

- `huginn_v1_interface_contract.md` — all components
- `huginn_v1_architecture.md` — Build Sequence Step 6

---

## What to Build

Three pytest test files. Each covers a distinct scope:

| File | Scope | LLM calls |
|---|---|---|
| `tests/test_mimir.py` | Mimir retriever in isolation | None |
| `tests/test_agent.py` | Agent nodes and graph paths | Yes (reason node) |
| `tests/test_api.py` | Full HTTP stack end-to-end | Yes (via agent) |

Run all tests:
```bash
pytest tests/ -v
```

---

## File 1 — `tests/test_mimir.py`

No LLM calls. Tests Mimir retrieval in isolation.

```python
# tests/test_mimir.py

import pytest
from mimir.retriever import retrieve


class TestMimirRetrieve:

    def test_price_mismatch_returns_correct_document(self):
        query = "price_mismatch: counterparty confirms different price at settlement"
        chunks = retrieve(query)
        assert len(chunks) > 0
        top = chunks[0]
        assert top["document_id"] == "SOP-SM-001"
        assert top["sub_type"] == "price_mismatch"

    def test_quantity_mismatch_returns_correct_document(self):
        query = "quantity_mismatch: our records indicate different number of shares than counterparty"
        chunks = retrieve(query)
        assert len(chunks) > 0
        top = chunks[0]
        assert top["document_id"] == "SOP-SM-002"
        assert top["sub_type"] == "quantity_mismatch"

    def test_wrong_settlement_date_returns_correct_document(self):
        query = "wrong_settlement_date: settlement date in our system does not match counterparty"
        chunks = retrieve(query)
        assert len(chunks) > 0
        top = chunks[0]
        assert top["document_id"] == "SOP-SM-003"
        assert top["sub_type"] == "wrong_settlement_date"

    def test_each_chunk_has_required_fields(self):
        query = "price_mismatch: bond settlement discrepancy"
        chunks = retrieve(query)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "text" in chunk
            assert "document_id" in chunk
            assert "sub_type" in chunk
            assert "similarity_score" in chunk
            assert isinstance(chunk["text"], str)
            assert len(chunk["text"]) > 0
            assert isinstance(chunk["similarity_score"], float)

    def test_returns_empty_list_not_exception_on_unusual_query(self):
        # Unusual query should return something or empty — never raise
        result = retrieve("xyzzy completely unrelated query with no settlement context")
        assert isinstance(result, list)

    def test_top_k_parameter_respected(self):
        query = "price_mismatch: settlement discrepancy"
        chunks = retrieve(query, top_k=1)
        assert len(chunks) <= 1

        chunks = retrieve(query, top_k=2)
        assert len(chunks) <= 2
```

---

## File 2 — `tests/test_agent.py`

Tests individual nodes in isolation (no LLM) and full graph paths (LLM required for standard path).

```python
# tests/test_agent.py

import json
import pytest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from agent.nodes import classify, retrieve_node, escalate_fast_exit, decide, log_result
from agent.graph import huginn_graph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path("tests/fixtures")

def load_fixture(name: str) -> dict:
    data = json.loads((FIXTURES_DIR / name).read_text())
    data["exception_id"] = str(data["exception_id"])
    return data

def make_initial_state(exception: dict, job_id: str) -> dict:
    return {
        "exception": exception,
        "job_id": job_id,
        "exception_type": None,
        "exception_sub_type": None,
        "triggered_keyword": None,
        "retrieved_chunks": [],
        "retrieved_document_id": None,
        "confidence_score": None,
        "reasoning_trace": None,
        "resolution_steps": None,
        "llm_raw_response": None,
        "outcome": None,
        "escalation_reason": None,
        "current_node": "",
    }


# ---------------------------------------------------------------------------
# Unit tests — classify node
# ---------------------------------------------------------------------------

class TestClassifyNode:

    def test_classify_price_mismatch_no_keyword(self):
        exc = load_fixture("fixture_price_mismatch.json")
        result = classify({"exception": exc})
        assert result["exception_type"] == "settlement_mismatch"
        assert result["exception_sub_type"] == "price_mismatch"
        assert result["triggered_keyword"] is None

    def test_classify_quantity_mismatch_no_keyword(self):
        exc = load_fixture("fixture_quantity_mismatch.json")
        result = classify({"exception": exc})
        assert result["exception_sub_type"] == "quantity_mismatch"
        assert result["triggered_keyword"] is None

    def test_classify_detects_sanctions_keyword(self):
        exc = load_fixture("fixture_mandatory_escalation.json")
        result = classify({"exception": exc})
        assert result["triggered_keyword"] == "sanctions"

    def test_classify_detects_AML_keyword(self):
        exc = load_fixture("fixture_price_mismatch.json")
        exc = dict(exc)
        exc["description"] = "Settlement discrepancy. Counterparty flagged for AML investigation."
        result = classify({"exception": exc})
        assert result["triggered_keyword"] == "AML"

    def test_classify_detects_regulatory_hold_keyword(self):
        exc = load_fixture("fixture_price_mismatch.json")
        exc = dict(exc)
        exc["description"] = "Trade is under regulatory hold pending review."
        result = classify({"exception": exc})
        assert result["triggered_keyword"] == "regulatory hold"

    def test_classify_keyword_detection_is_case_insensitive(self):
        exc = load_fixture("fixture_price_mismatch.json")
        exc = dict(exc)
        exc["description"] = "Counterparty subject to SANCTIONS review."
        result = classify({"exception": exc})
        assert result["triggered_keyword"] == "sanctions"


# ---------------------------------------------------------------------------
# Unit tests — decide node
# ---------------------------------------------------------------------------

class TestDecideNode:

    def test_decide_auto_resolve_at_threshold(self):
        state = {"confidence_score": 0.75}
        result = decide(state)
        assert result["outcome"] == "auto_resolve"
        assert result["escalation_reason"] is None

    def test_decide_auto_resolve_above_threshold(self):
        state = {"confidence_score": 0.92}
        result = decide(state)
        assert result["outcome"] == "auto_resolve"

    def test_decide_escalate_below_threshold(self):
        state = {"confidence_score": 0.74}
        result = decide(state)
        assert result["outcome"] == "escalate"
        assert "0.74" in result["escalation_reason"]
        assert "0.75" in result["escalation_reason"]

    def test_decide_escalate_on_none_confidence(self):
        # Decision 28: API failure
        state = {"confidence_score": None, "escalation_reason": "system_error: timeout"}
        result = decide(state)
        assert result["outcome"] == "escalate"

    def test_decide_escalate_at_zero(self):
        state = {"confidence_score": 0.0}
        result = decide(state)
        assert result["outcome"] == "escalate"


# ---------------------------------------------------------------------------
# Unit tests — escalate_fast_exit node
# ---------------------------------------------------------------------------

class TestEscalateFastExitNode:

    def test_fast_exit_sets_correct_outcome(self):
        state = {"triggered_keyword": "sanctions"}
        result = escalate_fast_exit(state)
        assert result["outcome"] == "escalate"
        assert "sanctions" in result["escalation_reason"]

    def test_fast_exit_nulls_llm_fields(self):
        state = {"triggered_keyword": "AML"}
        result = escalate_fast_exit(state)
        assert result["retrieved_chunks"] == []
        assert result["retrieved_document_id"] is None
        assert result["confidence_score"] is None
        assert result["reasoning_trace"] is None
        assert result["resolution_steps"] is None
        assert result["llm_raw_response"] is None


# ---------------------------------------------------------------------------
# Integration tests — full graph
# ---------------------------------------------------------------------------

class TestAgentGraph:

    def setup_method(self):
        """Clean logs before each test."""
        Path("logs/audit.jsonl").unlink(missing_ok=True)
        Path("logs/escalation_queue.jsonl").unlink(missing_ok=True)
        Path("logs/audit.db").unlink(missing_ok=True)

    def test_fast_exit_path_sanctions(self):
        exc = load_fixture("fixture_mandatory_escalation.json")
        state = make_initial_state(exc, "test-fast-exit-001")
        result = huginn_graph.invoke(state)

        assert result["outcome"] == "escalate"
        assert result["triggered_keyword"] == "sanctions"
        assert result["retrieved_document_id"] is None
        assert result["confidence_score"] is None
        assert result["reasoning_trace"] is None
        assert "sanctions" in result["escalation_reason"]

        # Escalation queue should have been written
        assert Path("logs/escalation_queue.jsonl").exists()

    def test_standard_path_produces_valid_outcome(self):
        exc = load_fixture("fixture_price_mismatch.json")
        state = make_initial_state(exc, "test-standard-001")
        result = huginn_graph.invoke(state)

        # Outcome must be one of the two valid values
        assert result["outcome"] in ("auto_resolve", "escalate")

        # Standard path must have called Mimir
        assert result["retrieved_document_id"] is not None
        assert result["retrieved_document_id"] == "SOP-SM-001"

        # Standard path must have called LLM
        assert result["confidence_score"] is not None
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert result["reasoning_trace"] is not None
        assert len(result["reasoning_trace"]) > 0

    def test_standard_path_quantity_mismatch(self):
        exc = load_fixture("fixture_quantity_mismatch.json")
        state = make_initial_state(exc, "test-standard-002")
        result = huginn_graph.invoke(state)

        assert result["outcome"] in ("auto_resolve", "escalate")
        assert result["retrieved_document_id"] == "SOP-SM-002"

    def test_audit_log_written_for_all_paths(self):
        # Fast-exit
        exc = load_fixture("fixture_mandatory_escalation.json")
        huginn_graph.invoke(make_initial_state(exc, "audit-test-001"))

        # Standard
        exc = load_fixture("fixture_price_mismatch.json")
        huginn_graph.invoke(make_initial_state(exc, "audit-test-002"))

        assert Path("logs/audit.jsonl").exists()
        lines = Path("logs/audit.jsonl").read_text().strip().split("\n")
        assert len(lines) == 2

    def test_escalation_queue_only_contains_escalated(self):
        """If at least one exception escalates, it should appear in the queue."""
        exc = load_fixture("fixture_mandatory_escalation.json")
        huginn_graph.invoke(make_initial_state(exc, "escalation-test-001"))

        assert Path("logs/escalation_queue.jsonl").exists()
        records = [
            json.loads(line)
            for line in Path("logs/escalation_queue.jsonl").read_text().strip().split("\n")
            if line.strip()
        ]
        assert all(r["outcome"] == "escalate" for r in records)
```

---

## File 3 — `tests/test_api.py`

Full end-to-end tests via HTTP using FastAPI's `TestClient`.

```python
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
        # The mandatory escalation fixture always escalates — use a standard fixture
        # and check that if the outcome is auto_resolve, it's not in the queue.
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
```

---

## Running the Tests

```bash
# All tests
pytest tests/ -v

# Individual files
pytest tests/test_mimir.py -v
pytest tests/test_agent.py -v
pytest tests/test_api.py -v

# Skip slow LLM tests (unit tests only)
pytest tests/test_mimir.py tests/test_agent.py::TestClassifyNode tests/test_agent.py::TestDecideNode tests/test_agent.py::TestEscalateFastExitNode -v
```

---

## Gate Criteria

All tests pass:
```
tests/test_mimir.py       PASSED (6 tests)
tests/test_agent.py       PASSED (16 tests)
tests/test_api.py         PASSED (16 tests)
```

The `test_get_escalations_does_not_contain_auto_resolved` test is conditional — it only asserts when the LLM happens to produce an `auto_resolve` outcome. This is expected behavior and not a flaky test.

---

## Notes

- FastAPI's `TestClient` runs the app in-process — no server needs to be running during pytest
- The `setup_method` hook cleans log files and the in-memory result store before each test — tests are fully isolated
- LLM tests (standard path) will make real API calls and consume tokens — run them deliberately, not in CI loops
- If the LLM produces a low confidence score on a standard path fixture, the outcome will be `escalate` — this is correct behavior and the test asserts on the structure, not on a specific outcome value
