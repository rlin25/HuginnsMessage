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
