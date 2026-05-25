# Huginn v2 — Demo

Five-minute walkthrough of all three execution paths.

## Prerequisites

**1. Environment and API key**

```bash
# From huginn_v2/
source venv/bin/activate          # or use the system Python if packages are installed globally
```

`.env` must exist at the project root (parent of `huginn_v2/`) with your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

**2. Knowledge base index**

The index must be built before the server starts. If `knowledge_base/processed/` is empty or missing:
```bash
python scripts/build_index.py
```
Inspect the chunk log printed to stdout and confirm six documents are indexed before proceeding.

**3. Start the server**

```bash
uvicorn api.main:app --reload
```

Confirm the server is up:
```bash
curl -s http://127.0.0.1:8000/health
# → {"status":"ok"}
```

---

## Path 1 — Pydantic Validation Rejection

These requests never reach the agent. FastAPI validates the schema and returns HTTP 422 immediately.

**Invalid `type` value:**
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440010",
    "trade_id": "TRD-DEMO-422A",
    "type": "wrong_type",
    "sub_type": "price_mismatch",
    "description": "Test invalid type.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "low"
  }' | python3 -m json.tool
```

**What to look for:** HTTP 422. The `detail` array shows which field failed and why. The agent, Mimir, and Claude API were never called.

---

**Missing required field (`exception_id` omitted):**
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "trade_id": "TRD-DEMO-422B",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Test missing field.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "low"
  }' | python3 -m json.tool
```

**What to look for:** HTTP 422. `detail[0].loc` identifies the missing field: `["body", "exception_id"]`.

---

## Path 2 — Mandatory Escalation Fast-Exit

Five keywords trigger immediate escalation before Mimir or the Claude API are called. The response is instant — no retrieval, no LLM reasoning.

**`sanctions`:**
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440020",
    "trade_id": "TRD-DEMO-SANCTIONS",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Counterparty account flagged under active sanctions screening. Settlement on hold pending compliance review.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "high"
  }' | python3 -m json.tool
```

**`AML`:**
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440021",
    "trade_id": "TRD-DEMO-AML",
    "type": "settlement_mismatch",
    "sub_type": "quantity_mismatch",
    "description": "Transaction flagged by AML monitoring system. Suspicious activity report filed.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "high"
  }' | python3 -m json.tool
```

**`regulatory hold`:**
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440022",
    "trade_id": "TRD-DEMO-HOLD",
    "type": "settlement_mismatch",
    "sub_type": "wrong_settlement_date",
    "description": "Position subject to regulatory hold pending SEC inquiry. Cannot settle until hold is lifted.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "high"
  }' | python3 -m json.tool
```

**`buy-in`:**
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440023",
    "trade_id": "TRD-DEMO-BUYIN",
    "type": "settlement_mismatch",
    "sub_type": "quantity_mismatch",
    "description": "Seller failed to deliver 1000 MSFT shares. Initiating formal buy-in procedure under FINRA Rule 11810.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "high"
  }' | python3 -m json.tool
```

**`sell-out`:**
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440024",
    "trade_id": "TRD-DEMO-SELLOUT",
    "type": "settlement_mismatch",
    "sub_type": "quantity_mismatch",
    "description": "Buyer refused delivery of 500 NVDA shares. Seller initiating sell-out per FINRA Rule 11820.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "high"
  }' | python3 -m json.tool
```

**What to look for across all five:**
- `outcome`: `"escalate"` in every case
- `confidence_score`: `null` — the LLM was never called
- `retrieved_document_ids`: `[]` — Mimir was never called
- `escalation_reason`: names the specific keyword that triggered the fast-exit

---

## Path 3 — Standard Path

These take 10–30 seconds each — Mimir retrieves regulatory chunks, Claude scores them.

**Wrong settlement date** — exercises the T+1/T+2 regulatory question; expect `SEC-15c6-1` in `retrieved_document_ids`:
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440030",
    "trade_id": "TRD-DEMO-DATE",
    "type": "settlement_mismatch",
    "sub_type": "wrong_settlement_date",
    "description": "Trade recorded settlement date T+2 (2026-05-27) but counterparty insists T+1 (2026-05-26) applies under SEC Rule 15c6-1 as amended May 2024. Neither party flagged an exception at execution time.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "medium"
  }' | python3 -m json.tool
```

**Vague description** — expect low `confidence_score` and escalation:
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440031",
    "trade_id": "TRD-DEMO-VAGUE",
    "type": "settlement_mismatch",
    "sub_type": "quantity_mismatch",
    "description": "quantity issue",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "low"
  }' | python3 -m json.tool
```

**Specific description** — best chance of `auto_resolve`:
```bash
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440032",
    "trade_id": "TRD-DEMO-SPECIFIC",
    "type": "settlement_mismatch",
    "sub_type": "quantity_mismatch",
    "description": "Internal records show 1000 shares AAPL delivered 2026-05-25. Counterparty DTCC advice reflects 900 shares received. 100-share shortfall confirmed by DTC participant statement. Seller acknowledges partial delivery failure. T+1 settlement date was 2026-05-25.",
    "timestamp": "2026-05-25T09:00:00Z",
    "severity": "medium"
  }' | python3 -m json.tool
```

**What to look for:**
- `confidence_score`: float between 0.0 and 1.0. At or above 0.75 → `auto_resolve`. Below → `escalate`.
- `reasoning_trace`: the LLM's step-by-step analysis across four rubric factors — condition match, obligation clarity, exception applicability, cross-reference resolution.
- `retrieved_document_ids`: which regulatory rules Mimir consulted. The wrong_settlement_date example should include `SEC-15c6-1`.
- `resolution_steps`: specific regulatory guidance for resolving the exception.
- `escalation_reason`: on escalation, explains whether it was a low confidence score or a keyword trigger.

---

## Retrieving Results

**Look up any result by job_id** (copy the `job_id` from any POST response):
```bash
curl -s http://127.0.0.1:8000/exceptions/PASTE-JOB-ID-HERE | python3 -m json.tool
```

The GET response is the full audit log record — includes every field written at decision time, including `decision_timestamp`, `retrieved_chunks` with the actual regulatory text, and `llm_raw_response`.

**View the escalation queue:**
```bash
curl -s http://127.0.0.1:8000/escalations | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'{len(d[\"escalations\"])} escalation(s)')
for e in d['escalations']:
    score = e['confidence_score']
    score_str = f'{score:.2f}' if score is not None else 'null'
    print(f'  [{score_str}] {e[\"trade_id\"]:30s} {e[\"escalation_reason\"]}')
"
```

Every exception that escalated — across all three paths — appears here. Fast-exit escalations show `null` confidence scores. Standard-path escalations show the score that fell below 0.75.

---

## Response Field Reference

| Field | Standard path | Fast-exit path |
|---|---|---|
| `outcome` | `"auto_resolve"` or `"escalate"` | `"escalate"` |
| `confidence_score` | float 0.0–1.0 | `null` |
| `reasoning_trace` | LLM step-by-step analysis | `null` |
| `resolution_steps` | LLM regulatory guidance | `null` |
| `escalation_reason` | `"confidence score X below threshold 0.75"` or `null` | `"mandatory escalation keyword detected: <keyword>"` |
| `retrieved_document_ids` | list of rule IDs consulted | `[]` |
