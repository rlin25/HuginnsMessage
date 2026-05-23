# Huginn v1 — Subplan 4: LangGraph Agent

**Component:** `agent/state.py`, `agent/nodes.py`, `agent/graph.py`
**Depends on:** Subplan 3 gate must be confirmed passing. Mimir and the logger must be working.
**Gate:** All three state machine paths (standard resolve, standard escalate, mandatory escalation fast-exit) produce correct structured output when the graph is invoked directly — before Subplan 5 begins.

---

## Reference Documents

- `huginn_v1_interface_contract.md` — Component 3 (LangGraph Agent), Component 5 (LLM Reasoning)
- `huginn_v1_design_decisions.md` — Decisions 4, 5, 9, 10, 24, 25, 26, 28

---

## What to Build

Three files, in order:

1. `agent/state.py` — the shared state TypedDict
2. `agent/nodes.py` — one function per node (pure functions: state in, dict out)
3. `agent/graph.py` — the LangGraph state machine

Build and test each node in isolation before wiring the graph.

---

## Step 1 — Agent State

```python
# agent/state.py

from typing import TypedDict
from uuid import UUID


class AgentState(TypedDict):
    # Input — set at entry, never modified by nodes
    exception: dict          # Full TradeException serialized as dict
    job_id: str              # Assigned by API layer (or test harness)

    # Set by classify node
    exception_type: str
    exception_sub_type: str
    triggered_keyword: str | None

    # Set by retrieve node (standard path only)
    retrieved_chunks: list[dict]
    retrieved_document_id: str | None

    # Set by reason node (standard path only)
    confidence_score: float | None
    reasoning_trace: str | None
    resolution_steps: str | None
    llm_raw_response: str | None

    # Set by decide/escalate nodes
    outcome: str | None
    escalation_reason: str | None

    # Debugging
    current_node: str
```

---

## Step 2 — Node Implementations

### Important: Node Design Rules

- Every node is a pure function: `(AgentState) -> dict`
- Each node returns **only the fields it modifies** — not a full state copy
- Nodes never directly modify the state object
- All nodes call `logger.audit.log()` only from `log_result` — never from individual nodes

```python
# agent/nodes.py

import json
import os
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

from mimir.retriever import retrieve
from logger.audit import log

load_dotenv()

# Hard-coded v1 values — see masterplan for change locations
ESCALATION_THRESHOLD = 0.75
MANDATORY_ESCALATION_KEYWORDS = ["sanctions", "AML", "regulatory hold"]
LLM_MODEL = "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Node 1 — classify
# ---------------------------------------------------------------------------

def classify(state: dict) -> dict:
    """
    Reads the exception, extracts type/sub_type, scans for mandatory
    escalation keywords. Returns classification fields.
    """
    exception = state["exception"]
    description = exception.get("description", "")

    triggered_keyword = None
    for keyword in MANDATORY_ESCALATION_KEYWORDS:
        if keyword.lower() in description.lower():
            triggered_keyword = keyword
            break

    return {
        "exception_type": exception.get("type"),
        "exception_sub_type": exception.get("sub_type"),
        "triggered_keyword": triggered_keyword,
        "current_node": "classify",
    }


# ---------------------------------------------------------------------------
# Node 2 — retrieve
# ---------------------------------------------------------------------------

def retrieve_node(state: dict) -> dict:
    """
    Constructs a query from sub_type + description and calls Mimir.
    Only called on the standard path (no triggered keyword).
    """
    exception = state["exception"]
    query = f"{exception['sub_type']}: {exception['description']}"
    chunks = retrieve(query)

    retrieved_document_id = None
    if chunks:
        retrieved_document_id = chunks[0].get("document_id")

    return {
        "retrieved_chunks": chunks,
        "retrieved_document_id": retrieved_document_id,
        "current_node": "retrieve",
    }


# ---------------------------------------------------------------------------
# Node 3 — reason
# ---------------------------------------------------------------------------

SCORING_RUBRIC = """
You are a settlement exception triage specialist at a financial firm.
You have been given a trade exception and relevant Standard Operating Procedure (SOP) excerpts.
Your task is to evaluate the exception against the SOP and produce a structured JSON response.

SCORING RUBRIC:
- Confidence score reflects how clearly the SOP applies to this specific exception.
- Score 0.85–1.00: The SOP directly addresses this exact scenario. Resolution steps are unambiguous and complete.
- Score 0.75–0.84: The SOP is relevant and mostly applicable. Minor gaps exist but resolution path is clear.
- Score 0.50–0.74: The SOP is partially relevant. The scenario has elements not covered by the SOP, or the SOP provides conflicting guidance.
- Score 0.00–0.49: The SOP does not adequately cover this scenario. Human review is required.

Weighting factors:
- Sub-type match: Does the retrieved SOP cover this specific sub-type? (High weight)
- Description clarity: Is the exception description specific enough to act on? (Medium weight)
- SOP completeness: Does the SOP provide complete resolution steps for this scenario? (Medium weight)
- Presence of complicating factors not addressed in SOP: (Lowers score significantly)

IMPORTANT: You must respond with valid JSON only. No preamble, no explanation, no markdown. 
Respond with exactly this structure:
{
  "confidence_score": <float between 0.0 and 1.0>,
  "reasoning_trace": "<step-by-step explanation of how you arrived at the score>",
  "resolution_steps": "<specific steps to resolve this exception per the SOP>"
}
"""


def reason(state: dict) -> dict:
    """
    Calls the Claude API with the exception, retrieved SOP chunks, and scoring rubric.
    Returns confidence_score, reasoning_trace, resolution_steps, and raw response.
    On API failure, returns fields that trigger auto-escalation in the decide node.
    """
    exception = state["exception"]
    chunks = state.get("retrieved_chunks", [])

    # Format retrieved chunks for the prompt
    chunks_text = ""
    for i, chunk in enumerate(chunks, 1):
        chunks_text += f"\n--- SOP Excerpt {i} (document: {chunk['document_id']}, similarity: {chunk['similarity_score']:.3f}) ---\n"
        chunks_text += chunk["text"] + "\n"

    if not chunks_text:
        chunks_text = "No SOP documents retrieved."

    user_message = f"""
RETRIEVED SOP EXCERPTS:
{chunks_text}

TRADE EXCEPTION:
Exception ID: {exception.get('exception_id')}
Trade ID: {exception.get('trade_id')}
Type: {exception.get('type')}
Sub-type: {exception.get('sub_type')}
Severity: {exception.get('severity')}
Description: {exception.get('description')}
Timestamp: {exception.get('timestamp')}

Evaluate this exception against the SOP excerpts and respond with the JSON structure specified in your instructions.
"""

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model=LLM_MODEL,
            max_tokens=1000,
            system=SCORING_RUBRIC,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_response = message.content[0].text
        parsed = json.loads(raw_response)

        confidence_score = float(parsed["confidence_score"])
        # Clamp to valid range
        confidence_score = max(0.0, min(1.0, confidence_score))

        return {
            "confidence_score": confidence_score,
            "reasoning_trace": parsed["reasoning_trace"],
            "resolution_steps": parsed["resolution_steps"],
            "llm_raw_response": raw_response,
            "current_node": "reason",
        }

    except Exception as e:
        # Decision 28: API failure → fields that trigger auto-escalation
        return {
            "confidence_score": None,
            "reasoning_trace": None,
            "resolution_steps": None,
            "llm_raw_response": None,
            "escalation_reason": f"system_error: {str(e)}",
            "current_node": "reason",
        }


# ---------------------------------------------------------------------------
# Node 4 — decide
# ---------------------------------------------------------------------------

def decide(state: dict) -> dict:
    """
    Compares confidence_score against threshold.
    Sets outcome and escalation_reason.
    """
    confidence_score = state.get("confidence_score")

    # Handles API failure case (confidence_score is None → escalate)
    if confidence_score is None:
        return {
            "outcome": "escalate",
            # escalation_reason already set by reason node on failure
            "current_node": "decide",
        }

    if confidence_score >= ESCALATION_THRESHOLD:
        return {
            "outcome": "auto_resolve",
            "escalation_reason": None,
            "current_node": "decide",
        }
    else:
        return {
            "outcome": "escalate",
            "escalation_reason": f"confidence score {confidence_score} below threshold {ESCALATION_THRESHOLD}",
            "current_node": "decide",
        }


# ---------------------------------------------------------------------------
# Node 5 — escalate (fast-exit path)
# ---------------------------------------------------------------------------

def escalate_fast_exit(state: dict) -> dict:
    """
    Fires when a mandatory escalation keyword is detected.
    Sets outcome and escalation_reason. Does not call Mimir or LLM.
    """
    triggered_keyword = state.get("triggered_keyword")
    return {
        "outcome": "escalate",
        "escalation_reason": f"mandatory escalation keyword detected: {triggered_keyword}",
        "retrieved_chunks": [],
        "retrieved_document_id": None,
        "confidence_score": None,
        "reasoning_trace": None,
        "resolution_steps": None,
        "llm_raw_response": None,
        "current_node": "escalate_fast_exit",
    }


# ---------------------------------------------------------------------------
# Node 6 — log_result
# ---------------------------------------------------------------------------

def log_result(state: dict) -> dict:
    """
    Assembles the full event dict and calls the audit logger.
    Side-effect only — returns minimal state update.
    """
    exception = state["exception"]

    event = {
        "job_id": state.get("job_id"),
        "exception_id": str(exception.get("exception_id")),
        "trade_id": exception.get("trade_id"),
        "type": exception.get("type"),
        "sub_type": exception.get("sub_type"),
        "description": exception.get("description"),
        "timestamp": str(exception.get("timestamp")),
        "severity": exception.get("severity"),
        "outcome": state.get("outcome"),
        "triggered_keyword": state.get("triggered_keyword"),
        "retrieved_chunks": state.get("retrieved_chunks", []),
        "retrieved_document_id": state.get("retrieved_document_id"),
        "confidence_score": state.get("confidence_score"),
        "reasoning_trace": state.get("reasoning_trace"),
        "resolution_steps": state.get("resolution_steps"),
        "escalation_reason": state.get("escalation_reason"),
        "llm_raw_response": state.get("llm_raw_response"),
        "decision_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    log(event)

    return {"current_node": "log_result"}
```

---

## Step 3 — Graph Wiring

```python
# agent/graph.py

from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import (
    classify,
    retrieve_node,
    reason,
    decide,
    escalate_fast_exit,
    log_result,
)


def should_fast_exit(state: dict) -> str:
    """Routing function after classify node."""
    if state.get("triggered_keyword"):
        return "fast_exit"
    return "standard"


def should_escalate(state: dict) -> str:
    """Routing function after decide node."""
    if state.get("outcome") == "escalate":
        return "escalate"
    return "resolve"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify", classify)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("reason", reason)
    graph.add_node("decide", decide)
    graph.add_node("escalate_fast_exit", escalate_fast_exit)
    graph.add_node("log_result", log_result)

    # Entry point
    graph.set_entry_point("classify")

    # classify → branch
    graph.add_conditional_edges(
        "classify",
        should_fast_exit,
        {
            "fast_exit": "escalate_fast_exit",
            "standard": "retrieve",
        },
    )

    # Standard path
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "decide")

    # decide → branch
    graph.add_conditional_edges(
        "decide",
        should_escalate,
        {
            "escalate": "log_result",
            "resolve": "log_result",
        },
    )

    # fast-exit → log
    graph.add_edge("escalate_fast_exit", "log_result")

    # log → end
    graph.add_edge("log_result", END)

    return graph.compile()


# Module-level compiled graph — import this in the API layer
huginn_graph = build_graph()
```

---

## Gate Verification Script

This requires a valid `ANTHROPIC_API_KEY` in `.env`. The fast-exit test does NOT call the LLM.

```python
# python tests/test_agent_smoke.py

import json
from pathlib import Path
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
```

---

## Initial State Initialization

When invoking the graph, the caller must provide all required `AgentState` keys. The API layer (Subplan 5) will handle this. For direct testing, initialize with the full state dict as shown in the smoke test above — all non-input fields initialized to `None` or `[]`.

---

## Notes

- `retrieve_node` is named with `_node` suffix to avoid shadowing the imported `retrieve` function from Mimir
- The `reason` node catches all exceptions from the Claude API call and returns a `system_error` escalation reason (Decision 28) — the decide node will set `outcome = "escalate"` when `confidence_score` is `None`
- The graph is compiled once at module import time via `huginn_graph = build_graph()` — the API layer imports this compiled graph
- Do not import from `api/` in this component
