import uuid

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from models.exception import TradeException
from agent.graph import huginn_graph

app = FastAPI(title="Huginn v2 — Trade Exception Triage")


@app.post("/exceptions")
def submit_exception(payload: dict) -> dict:
    try:
        exc = TradeException(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    job_id = str(uuid.uuid4())
    state = {"exception": exc.model_dump(mode="json"), "job_id": job_id}
    result = huginn_graph.invoke(state)

    return {
        "job_id": job_id,
        "outcome": result["outcome"],
        "confidence_score": result.get("confidence_score"),
        "reasoning_trace": result.get("reasoning_trace"),
        "resolution_steps": result.get("resolution_steps"),
        "escalation_reason": result.get("escalation_reason"),
        "retrieved_document_ids": result.get("retrieved_document_ids", []),
    }


@app.get("/exceptions/{job_id}")
def get_result(job_id: str) -> dict:
    import sqlite3
    import json
    from logger.audit import AUDIT_DB

    if not AUDIT_DB.exists():
        raise HTTPException(status_code=404, detail="job_id not found")

    con = sqlite3.connect(AUDIT_DB)
    row = con.execute(
        "SELECT full_event_json FROM audit_log WHERE job_id = ?", (job_id,)
    ).fetchone()
    con.close()

    if row is None:
        raise HTTPException(status_code=404, detail="job_id not found")

    return json.loads(row[0])


@app.get("/escalations")
def get_escalations() -> dict:
    import sqlite3
    import json
    from logger.audit import AUDIT_DB

    if not AUDIT_DB.exists():
        return {"escalations": []}

    con = sqlite3.connect(AUDIT_DB)
    rows = con.execute(
        "SELECT full_event_json FROM audit_log WHERE outcome = 'escalate'"
    ).fetchall()
    con.close()

    return {"escalations": [json.loads(row[0]) for row in rows]}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
