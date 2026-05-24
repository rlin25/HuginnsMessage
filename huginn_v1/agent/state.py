# agent/state.py

from typing import TypedDict


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
