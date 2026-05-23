# Huginn v1 — Subplan 5: FastAPI Layer

**Component:** `api/main.py`
**Depends on:** Subplan 4 gate must be confirmed passing.
**Gate:** All three endpoints return correct HTTP responses when called against the running server — before Subplan 6 begins.

---

## Reference Documents

- `huginn_v1_interface_contract.md` — Component 2 (API Layer)
- `huginn_v1_design_decisions.md` — Decisions 7, 19, 20, 21

---

## What to Build

A single file: `api/main.py`

The agent already works. This step is purely plumbing — wrap the working agent in HTTP.

---

## In-Memory Result Store

V1 uses a simple dict as an in-memory result store (job_id → result). This is intentional — the fake async pattern means results are always ready when the GET endpoint is called.

```
POST /exceptions  →  runs agent synchronously  →  stores result  →  returns job_id
GET /exceptions/{job_id}  →  looks up result  →  returns it
GET /escalations  →  reads escalation_queue.jsonl  →  returns list
```

---

## Implementation

```python
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
```

---

## Running the Server

From the project root with the virtual environment active:

```bash
uvicorn api.main:app --reload
```

The interactive docs are available at:
```
http://127.0.0.1:8000/docs
```

This is the v1 demo surface.

---

## Gate Verification — Manual curl Tests

Run these from a second terminal while the server is running.

### Test 1 — Submit a valid price mismatch exception

```bash
curl -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "trade_id": "TRD-001",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Counterparty confirms settlement at 102.50 but our records show 101.75 for bond CUSIP 123456789.",
    "timestamp": "2026-05-15T09:30:00Z",
    "severity": "high"
  }'
```

**Expected:** HTTP 200 with `job_id`, `status: "received"`, `exception_id`, `timestamp`

Copy the returned `job_id` for the next test.

---

### Test 2 — Retrieve the result

```bash
curl http://127.0.0.1:8000/exceptions/<job_id_from_test_1>
```

**Expected:** HTTP 200 with `outcome`, `confidence_score`, `reasoning_trace`, `resolution_steps`, `retrieved_document_id`

---

### Test 3 — Submit a sanctions exception (mandatory escalation fast-exit)

```bash
curl -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
    "trade_id": "TRD-004",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Price discrepancy flagged. Counterparty account subject to sanctions review.",
    "timestamp": "2026-05-15T11:30:00Z",
    "severity": "high"
  }'
```

**Expected:** HTTP 200 — retrieve the result and verify `outcome: "escalate"`, `retrieved_document_id: null`, `confidence_score: null`, `escalation_reason` contains "sanctions"

---

### Test 4 — Submit an invalid exception type (validation error)

```bash
curl -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
    "trade_id": "TRD-005",
    "type": "corporate_action_failure",
    "sub_type": "price_mismatch",
    "description": "Invalid type test.",
    "timestamp": "2026-05-15T12:00:00Z",
    "severity": "low"
  }'
```

**Expected:** HTTP 422 with Pydantic validation error details — the agent is never called

---

### Test 5 — Check escalation queue

```bash
curl http://127.0.0.1:8000/escalations
```

**Expected:** HTTP 200 with `escalations` list containing the sanctions exception from Test 3

---

## Gate Criteria

All five manual tests return the expected HTTP status codes and response structures. Specifically:
- Test 1 + 2: standard path produces `outcome`, `confidence_score`, `retrieved_document_id` (non-null)
- Test 3: fast-exit produces `outcome: "escalate"`, `retrieved_document_id: null`, `confidence_score: null`
- Test 4: invalid type produces HTTP 422
- Test 5: escalation queue is non-empty and contains the sanctions exception

---

## Notes

- `exception.model_dump_json()` followed by `json.loads()` is the cleanest way to serialize a Pydantic model with UUID and datetime fields to a plain dict that the agent can work with
- The in-memory `_result_store` resets when the server restarts — this is acceptable in v1
- The `GET /escalations` endpoint reads from disk on every call — it always reflects the current state of the file, even for exceptions submitted in previous server sessions
- Pydantic validation errors on `POST /exceptions` are automatically converted to HTTP 422 responses by FastAPI — no additional error handling is needed for this case
- Do not add any logic to this file that belongs in the agent or logger — this file is purely HTTP plumbing
