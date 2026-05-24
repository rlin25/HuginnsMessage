# Walkthrough: `agent/graph.py`

## Purpose

This file wires the nodes from `agent/nodes.py` into a LangGraph state machine and compiles the result into a runnable graph object. It contains no business logic. Its only job is to declare which nodes exist, in what order they connect, and what the branching conditions are.

The separation from `agent/nodes.py` matters because the graph structure and the node logic are different kinds of things. Nodes are testable as pure functions with no LangGraph machinery. The graph is the orchestration of those functions. Mixing them would make the nodes untestable in isolation.

Decision 9 defines the three-path state machine structure this file implements.

## Relationships

- **Imported by:** `api/main.py` (imports `huginn_graph` — the compiled module-level graph instance)
- **Imports from:** `langgraph.graph`, `agent/state.py`, `agent/nodes.py`
- **Does not touch:** Mimir, the logger, the exception schema, or the API layer directly

## Decision Rationale

**Why routing functions (`should_fast_exit`, `should_escalate`) are separate from nodes:**
LangGraph's conditional edge API requires a function that takes state and returns a string key. These routing functions are not nodes — they produce no state updates and have no side effects. Keeping them separate from nodes makes their role clear: they read a single field and return a routing decision. The simplicity of `if state.get("triggered_keyword"): return "fast_exit"` is the point — routing should be inspectable at a glance.

**Why both branches of `should_escalate` route to `log_result`:**
Decision 9 establishes that logging happens on every path. Whether the outcome is `auto_resolve` or `escalate`, the graph must reach `log_result`. Using a conditional edge here — rather than a direct edge from `decide` to `log_result` — keeps the routing model consistent: every branch after `decide` is explicitly declared. If a third outcome were added in v2, the conditional edge pattern makes it obvious where to add it.

**Why `huginn_graph = build_graph()` is at module level:**
Compiling a LangGraph graph is not free — it validates the node connections, edge definitions, and state type. Running this at import time means the API layer and test suite import a pre-compiled graph rather than compiling it on every request. The module-level instance also ensures there is only one compiled graph in the process, which is the correct behavior.

**Why `build_graph()` is a function rather than just top-level statements:**
Wrapping the graph construction in a function makes it callable from tests that want to construct a fresh graph rather than importing the shared module-level instance. In v1 the test suite uses the shared `huginn_graph` directly, but having the factory function available is an explicit extensibility decision.

## What It Does Not Do

This file does not implement any node logic. It does not read exception fields, call the Claude API, query Mimir, or write to the audit log. Every one of those behaviors lives in `agent/nodes.py`.

It does not validate the agent state. State validation is the responsibility of the nodes that read each field.

It does not expose multiple graph variants. There is one graph, one entry point, one compiled instance. Multi-graph configurations are not a v1 concern.

## V2 Touch Points

New paths added in v2 — for instance, a separate path for a new exception type added alongside `settlement_mismatch` — would be new conditional edges in this file. The `should_fast_exit` function gains additional routing keys; new nodes from `agent/nodes.py` are registered here.

Iterative retrieval in v2 (deferred from v1 per the architecture document) would add a loop construct — a conditional edge from a re-query node back to `retrieve`, conditional on whether the initial retrieval confidence was sufficient. LangGraph supports cycles; this file is where that cycle would be declared.
