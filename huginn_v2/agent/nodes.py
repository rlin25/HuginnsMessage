import json
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

from agent.state import AgentState
import mimir.retriever as mimir
import logger.audit as audit_logger

ESCALATION_THRESHOLD = 0.75
LLM_MODEL = "claude-sonnet-4-6"

ESCALATION_KEYWORDS = [
    "sanctions",
    "AML",
    "regulatory hold",
    "buy-in",
    "sell-out",
]

SCORING_RUBRIC = """You are a financial trade exception triage agent. Your task is to assess whether a settlement mismatch exception can be auto-resolved based on the retrieved regulatory document context.

Score the exception on a scale of 0.0 to 1.0 using the following four factors:

1. CONDITION MATCH (0.0–1.0)
Do the exception facts satisfy the triggering conditions specified in the retrieved regulatory rule? Does the scenario described meet the threshold or criteria the rule requires for a specific obligation or remedy to apply?

2. OBLIGATION CLARITY (0.0–1.0)
Does the retrieved rule specify a clear required action given the exception facts? Or does the rule leave the required response ambiguous, conditional on additional facts not present in the exception description?

3. EXCEPTION APPLICABILITY (0.0–1.0)
Do any of the rule's carve-outs, exceptions, or exclusions apply to this exception? Consider whether any exception provisions (e.g. T+2 late-pricing exception in Rule 15c6-1, clearing agency carve-outs in Rule 11810) apply to the described scenario.

4. CROSS-REFERENCE RESOLUTION (0.0–1.0)
Were all rules referenced within the retrieved chunks also retrieved and considered? Unresolved cross-references lower confidence because the complete regulatory picture is not available.

Scoring guidance:
- 0.85–1.00: Condition match is clear, obligation is unambiguous, no exceptions apply, all cross-references resolved.
- 0.75–0.84: Condition match is probable, obligation is mostly clear, minor ambiguity exists but resolution path is defensible.
- 0.50–0.74: Condition match is uncertain, or an exception may apply but cannot be determined from available facts, or cross-references are unresolved.
- 0.00–0.49: Condition match cannot be established, or the rule explicitly requires human judgment, or critical cross-references are missing.

Respond with a JSON object only. No preamble. No explanation outside the JSON. Exactly three fields:
{
  "confidence_score": <float between 0.0 and 1.0>,
  "reasoning_trace": "<step-by-step explanation of how you reached this score>",
  "resolution_steps": "<specific steps to resolve this exception per the retrieved regulatory guidance>"
}"""


def classify(state: AgentState) -> dict:
    exc = state["exception"]
    description = exc.get("description", "").lower()

    triggered = None
    for keyword in ESCALATION_KEYWORDS:
        if keyword.lower() in description:
            triggered = keyword
            break

    return {
        "exception_type": exc.get("type", ""),
        "exception_sub_type": exc.get("sub_type", ""),
        "triggered_keyword": triggered,
        "current_node": "classify",
    }


def retrieve(state: AgentState) -> dict:
    query = f"{state['exception_sub_type']}: {state['exception']['description']}"
    chunks = mimir.retrieve(query)
    doc_ids = list(dict.fromkeys(c["document_id"] for c in chunks))
    return {
        "retrieved_chunks": chunks,
        "retrieved_document_ids": doc_ids,
        "current_node": "retrieve",
    }


def reason(state: AgentState) -> dict:
    chunks = state["retrieved_chunks"]
    exc = state["exception"]

    chunk_context = "\n".join(
        f"[{c['section_id']}] ({c['retrieved_via']})\n{c['text']}\n---"
        for c in chunks
    ) or "No regulatory documents retrieved."

    exc_context = "\n".join(f"{k}: {v}" for k, v in exc.items())

    prompt = (
        f"{SCORING_RUBRIC}\n\n"
        f"Retrieved regulatory context:\n{chunk_context}\n\n"
        f"Exception:\n{exc_context}"
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=LLM_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[: text.rfind("```")]

        parsed = json.loads(text)
        return {
            "confidence_score": float(parsed["confidence_score"]),
            "reasoning_trace": parsed["reasoning_trace"],
            "resolution_steps": parsed["resolution_steps"],
            "llm_raw_response": raw,
            "current_node": "reason",
        }
    except Exception as e:
        return {
            "confidence_score": None,
            "reasoning_trace": None,
            "resolution_steps": None,
            "llm_raw_response": None,
            "escalation_reason": f"system_error: {e}",
            "current_node": "reason",
        }


def decide(state: AgentState) -> dict:
    score = state.get("confidence_score")
    if score is not None and score >= ESCALATION_THRESHOLD:
        return {"outcome": "auto_resolve", "escalation_reason": None,
                "current_node": "decide"}
    reason = (
        state.get("escalation_reason")
        or f"confidence score {score} below threshold {ESCALATION_THRESHOLD}"
    )
    return {"outcome": "escalate", "escalation_reason": reason,
            "current_node": "decide"}


def escalate_fast_exit(state: AgentState) -> dict:
    keyword = state.get("triggered_keyword", "")
    return {
        "outcome": "escalate",
        "escalation_reason": f"mandatory escalation keyword detected: {keyword}",
        "current_node": "escalate_fast_exit",
    }


def log_result(state: AgentState) -> dict:
    exc = state["exception"]
    event = {
        "job_id": state["job_id"],
        "exception_id": str(exc.get("exception_id", "")),
        "trade_id": exc.get("trade_id", ""),
        "type": exc.get("type", ""),
        "sub_type": exc.get("sub_type", ""),
        "description": exc.get("description", ""),
        "timestamp": str(exc.get("timestamp", "")),
        "severity": exc.get("severity", ""),
        "outcome": state.get("outcome"),
        "triggered_keyword": state.get("triggered_keyword"),
        "retrieved_chunks": state.get("retrieved_chunks", []),
        "retrieved_document_ids": state.get("retrieved_document_ids", []),
        "confidence_score": state.get("confidence_score"),
        "reasoning_trace": state.get("reasoning_trace"),
        "resolution_steps": state.get("resolution_steps"),
        "escalation_reason": state.get("escalation_reason"),
        "llm_raw_response": state.get("llm_raw_response"),
        "decision_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    audit_logger.log(event)
    return {"current_node": "log_result"}
