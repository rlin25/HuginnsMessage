# Walkthrough: `agent/state.py`

## Purpose

This file defines the shape of the data that flows through the LangGraph agent. Every node receives the full state object and returns a partial update. This file specifies what fields exist, what types they carry, and — through its comments — which node populates which section.

It exists as a separate file rather than being defined inside `agent/graph.py` or `agent/nodes.py` for the same reason the exception schema exists separately: the state is a shared contract, not the property of any one node. Both `graph.py` and `nodes.py` import from here.

The interface contract document defines the state object's fields. This file implements that specification exactly.

## Relationships

- **Imported by:** `agent/graph.py` (to type the `StateGraph`) and `agent/nodes.py` (implicitly, through the state dict each node receives and returns)
- **Imports from:** Python standard library only (`typing`)
- **Does not touch:** Mimir, the logger, the API layer, or the exception schema

## Decision Rationale

**Why `TypedDict` rather than a Pydantic model or dataclass:**
LangGraph's `StateGraph` expects a `TypedDict` as its state type. This is a LangGraph convention, not a choice. Using `TypedDict` also means each node returns a plain `dict` partial update, which LangGraph merges into the state — no special serialization required.

**Why `llm_raw_response` is a field on the state:**
Decision 17 (full fidelity audit logging). The raw LLM response before parsing is captured so the audit log can record exactly what the API returned — including any parsing anomalies. This field flows from the `reason` node through to `log_result` without being transformed. If the audit log only recorded the parsed confidence score and reasoning trace, debugging a malformed LLM response would require re-running the exception.

**Why all nullable fields default to `None` rather than being absent:**
LangGraph merges partial state updates into the full state object. If a field is not present in the initial state and a node doesn't set it (because it's on the wrong path), LangGraph will raise a key error when a downstream node tries to read it. Initializing all fields — including path-specific ones — to `None` at entry means every node can safely read any field without defensive checks for key existence.

**Why `current_node` exists:**
This field is a debugging aid. It records which node most recently ran, making it possible to inspect intermediate state during development or trace incorrect decisions in the audit log. It has no effect on routing or outcomes.

## What It Does Not Do

This file does not validate values. There is no enforcement that `confidence_score` is between 0.0 and 1.0, or that `outcome` is one of two specific strings. Validation of those values happens inside the nodes that produce them — the `reason` node clamps `confidence_score`, and the `decide` node produces only the two valid `outcome` strings.

It does not define default values. Initial state construction happens in `api/main.py` and in the test harness — both explicitly set all fields to their starting values.

## V2 Touch Points

New fields added to the agent state in v2 — for example, a `severity_reasoning` field if severity becomes a reasoning input (Decision 16) — belong in this file. Each new field requires a corresponding update to the initial state construction in `api/main.py` and to the node that populates it.

The `TypedDict` type hints are v1 approximations. In v2, more precise typing (e.g. `Literal["auto_resolve", "escalate"]` for `outcome`) would catch bugs at development time. Keeping it loose in v1 was appropriate while the state schema was still being established.
