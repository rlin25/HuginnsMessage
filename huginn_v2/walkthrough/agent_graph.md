# Walkthrough: `agent/graph.py`

## Purpose

This file defines the structure of the LangGraph graph — which nodes exist, how they connect, and how routing decisions are made. It contains no business logic. The node functions themselves live in `agent/nodes.py`; this file only wires them together.

The separation is intentional. A graph file that contains node logic would conflate two distinct concerns: what the system does at each step (nodes) with how it decides what to do next (edges). Keeping them separate means the graph structure is readable independently of the processing logic.

## Relationships

- **Imports from:** `agent/state.py` (the state type), `agent/nodes.py` (the node functions), `langgraph.graph`
- **Imported by:** `api/main.py` — imports `huginn_graph` directly; `tests/` — imports `build_graph()` for structural testing
- **Does not touch:** Mimir, the logger, the exception schema, or any business domain logic

## Decision Rationale

**Why routing functions are defined in this file** rather than in `nodes.py`: `_route_after_classify` and `_route_after_decide` are not nodes — they produce no state update and have no side effects. They are graph-level concerns: they read state and return routing keys. Placing them in `nodes.py` would imply they are nodes, which they are not. They belong with the graph definition (from the interface contract).

**Why `_route_after_classify` uses `state.get("triggered_keyword")`** rather than `state["triggered_keyword"]`: `triggered_keyword` is `str | None`. Using `state.get()` handles both the `None` case and the case where the field is not yet set in the state dict — both evaluate as falsy and route to `"standard"`. A direct key access would raise `KeyError` if the field were somehow absent.

**Why both `"auto_resolve"` and `"escalate"` from `_route_after_decide` route to the same `log_result` node**: both outcomes terminate at the same place. The conditional edge after `decide` is not for routing to different terminal nodes — it exists because LangGraph requires an explicit mapping from routing function return values to destination nodes. Making the branching explicit in the graph definition makes the execution paths readable from the graph structure alone. If a future version needed to route `auto_resolve` and `escalate` to different post-processing nodes, the conditional edge is already in place (Decision 9).

**Why `huginn_graph = build_graph()` runs at module level**: the compiled graph is the expensive part — it validates node registrations, compiles edge routing, and prepares the execution engine. Running this once at import time means every request handled by the FastAPI server uses the same compiled graph instance. Compiling on every request would be costly.

**Why `build_graph()` is a function** rather than just inline code at module level: the test suite imports `build_graph()` to exercise the graph structure independently of the `huginn_graph` singleton. A function also makes the initialization boundary explicit — the compiled graph is the return value, not a side effect of module import.

**Why the graph uses `graph.add_edge("log_result", END)`** rather than just not defining an outgoing edge from `log_result`: LangGraph requires an explicit termination condition. `END` is LangGraph's sentinel for "execution completes here." Without this edge, the graph compile would succeed but execution would hang waiting for the next node.

## What It Does Not Do

- No node logic — all processing lives in `agent/nodes.py`
- No imports from anything outside `agent/` — no Mimir, no logger, no API layer
- No error handling at the graph level — errors surface inside individual nodes, not here

## V3 Touch Points

If a new processing step is added in v3 — for example, a severity triage node that adjusts the confidence threshold based on `severity` before the `decide` node — the edge between `reason` and `decide` becomes `reason` → `severity_triage` → `decide`, and this file gains one `graph.add_node()` and one `graph.add_edge()` call. The rest of the graph is unchanged.

The three-path structure itself — invalid type exit (API layer), fast-exit, standard path — is unlikely to change. New exception types in v3 don't require new paths; they require new keyword lists and regulatory documents, which are handled in `nodes.py` and `mimir/retriever.py`.
