from typing import TypedDict


class AgentState(TypedDict):
    # Input — set at entry, never modified
    exception: dict
    job_id: str

    # Set by classification node
    exception_type: str
    exception_sub_type: str
    triggered_keyword: str | None

    # Set by retrieval node (standard path only)
    retrieved_chunks: list[dict]
    retrieved_document_ids: list[str]

    # Set by reasoning node (standard path only)
    confidence_score: float | None
    reasoning_trace: str | None
    resolution_steps: str | None
    llm_raw_response: str | None

    # Set by decision node
    outcome: str | None
    escalation_reason: str | None

    # Debugging
    current_node: str
