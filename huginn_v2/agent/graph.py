from langgraph.graph import StateGraph, END

from agent.state import AgentState
import agent.nodes as nodes


def _route_after_classify(state: AgentState) -> str:
    return "fast_exit" if state.get("triggered_keyword") else "standard"


def _route_after_decide(state: AgentState) -> str:
    return state.get("outcome", "escalate")


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify", nodes.classify)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("reason", nodes.reason)
    graph.add_node("decide", nodes.decide)
    graph.add_node("escalate_fast_exit", nodes.escalate_fast_exit)
    graph.add_node("log_result", nodes.log_result)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        _route_after_classify,
        {"fast_exit": "escalate_fast_exit", "standard": "retrieve"},
    )

    graph.add_edge("escalate_fast_exit", "log_result")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "decide")

    graph.add_conditional_edges(
        "decide",
        _route_after_decide,
        {"auto_resolve": "log_result", "escalate": "log_result"},
    )

    graph.add_edge("log_result", END)

    return graph.compile()


huginn_graph = build_graph()
