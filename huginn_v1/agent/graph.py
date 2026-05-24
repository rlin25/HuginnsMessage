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
