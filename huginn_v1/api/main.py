# api/main.py

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from models.exception import TradeException
from agent.graph import huginn_graph

load_dotenv()

app = FastAPI(
    title="Huginn",
    description="AI agent for financial trade exception triage.",
    version="1.0.0",
)

# In-memory result store: job_id (str) → result dict
_result_store: dict[str, dict] = {}

ESCALATION_QUEUE_PATH = Path("logs/escalation_queue.jsonl")


# ---------------------------------------------------------------------------
# POST /exceptions
# ---------------------------------------------------------------------------

@app.post("/exceptions")
def submit_exception(exception: TradeException):
    """
    Accept a trade exception, validate it, run the agent, return a job ID.
    Processing is synchronous in v1 — the result is available immediately.
    """
    job_id = str(uuid.uuid4())
    received_at = datetime.now(timezone.utc).isoformat()

    # Serialize the exception for the agent (UUID and datetime → str)
    exception_dict = json.loads(exception.model_dump_json())

    # Initialize full agent state
    initial_state = {
        "exception": exception_dict,
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

    # Run agent synchronously
    final_state = huginn_graph.invoke(initial_state)

    # Build result record
    result = {
        "job_id": job_id,
        "exception_id": exception_dict["exception_id"],
        "outcome": final_state.get("outcome"),
        "confidence_score": final_state.get("confidence_score"),
        "reasoning_trace": final_state.get("reasoning_trace"),
        "resolution_steps": final_state.get("resolution_steps"),
        "retrieved_document_id": final_state.get("retrieved_document_id"),
        "escalation_reason": final_state.get("escalation_reason"),
        "timestamp": received_at,
    }

    _result_store[job_id] = result

    # Return acknowledgement response (Decision 19)
    return {
        "job_id": job_id,
        "status": "received",
        "exception_id": exception_dict["exception_id"],
        "timestamp": received_at,
    }


# ---------------------------------------------------------------------------
# GET /exceptions/{job_id}
# ---------------------------------------------------------------------------

@app.get("/exceptions/{job_id}")
def get_exception_result(job_id: str):
    """
    Retrieve the full agent decision for a previously submitted exception.
    """
    result = _result_store.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")
    return result


# ---------------------------------------------------------------------------
# GET /escalations
# ---------------------------------------------------------------------------

@app.get("/escalations")
def get_escalations():
    """
    Return the full current escalation queue — the human reviewer's inbox.
    Reads from logs/escalation_queue.jsonl.
    Returns empty list if no escalations exist.
    """
    if not ESCALATION_QUEUE_PATH.exists():
        return {"escalations": []}

    escalations = []
    for line in ESCALATION_QUEUE_PATH.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            escalations.append({
                "job_id": record.get("job_id"),
                "exception_id": record.get("exception_id"),
                "trade_id": record.get("trade_id"),
                "type": record.get("type"),
                "sub_type": record.get("sub_type"),
                "outcome": record.get("outcome"),
                "confidence_score": record.get("confidence_score"),
                "reasoning_trace": record.get("reasoning_trace"),
                "escalation_reason": record.get("escalation_reason"),
                "retrieved_document_id": record.get("retrieved_document_id"),
                "timestamp": record.get("timestamp"),
            })
        except json.JSONDecodeError:
            continue  # Skip malformed lines

    return {"escalations": escalations}
