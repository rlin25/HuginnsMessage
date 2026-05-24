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
LLM_MODEL = "claude-sonnet-4-6"


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
# Node 5 — escalate_fast_exit
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
