# Walkthrough: `agent/state.py`

## Purpose

This file defines the data structure that flows through every node in the LangGraph graph. It is the shared memory of the execution pipeline — everything a node knows comes from this state, and everything a node produces goes back into it.

The file exists as a separate module — rather than defined inline in `graph.py` — because it is referenced by both `graph.py` (for the `StateGraph` type parameter) and `nodes.py` (for the type annotation on every node function). Separating the type definition from the graph wiring prevents a circular import.

## Relationships

- **Imports from:** Standard library only (`typing.TypedDict`)
- **Imported by:** `agent/nodes.py` and `agent/graph.py`
- **Does not touch:** Mimir, the logger, the exception schema, the API layer, or anything with side effects

## Decision Rationale

**Why `TypedDict`** rather than a Pydantic model or a `dataclass`: LangGraph's `StateGraph` requires a `TypedDict` as its state type. Nodes receive the full state dict and return plain dicts; LangGraph merges the partial return into the full state. Using Pydantic here would require converting to and from dicts at every node boundary. `TypedDict` is the right type for this role — it provides type hints without runtime overhead.

**Why no default values**: State fields are populated by specific nodes. A field that has a default value but was never actually written by the expected node would silently carry that default through the rest of the execution — the audit log would record a default value as if it were a real result. No defaults means a node that fails to write its expected fields will surface as a `KeyError` or a `None` in a downstream node, which is more debuggable than a silent default.

**Why `retrieved_document_ids` is `list[str]`** rather than `str | None`: two-pass retrieval may return chunks from multiple regulatory documents. A single string would misrepresent the retrieval scope. An empty list is the correct representation when no retrieval occurred (fast-exit path) — it is factually different from `None`, which would imply retrieval wasn't attempted (Decision 45).

**Why `retrieved_chunks` and `retrieved_document_ids` are both stored** rather than deriving document IDs from chunks on access: the retrieve node sets both at once. Storing the derived list avoids recomputing `list(dict.fromkeys(c["document_id"] for c in chunks))` at every downstream point that needs the document ID list — which includes the API response construction in `log_result`, the audit log event dict, and the API layer.

**Why `llm_raw_response`** is stored in state: if the JSON parsing step in the `reason` node fails, `llm_raw_response` contains exactly what the Claude API returned. This field exists to support debugging without re-running the exception — a `system_error` escalation that otherwise has no human-readable context about what went wrong becomes diagnosable from the audit log.

**Why `current_node`** is a string field updated by every node: LangGraph doesn't natively expose "currently executing node" as a readable value. During debugging and audit review, knowing which node last wrote to the state is useful context. The field is set by every node as a consistent convention, even `log_result` which is otherwise side-effect-only.

**Why the comments in the file are grouped by which node sets each field**: the state is the contract between nodes. When a developer reads this file, they should immediately understand the lifecycle of each field — when it's set, by whom, and under what conditions it might be `None`. The group structure makes that contract explicit without requiring the reader to trace execution through the graph.

## What It Does Not Do

- No validation — it's a type definition, not a validation layer
- No methods or computed properties
- No default values
- No business logic of any kind

## V3 Touch Points

When `severity` becomes a reasoning input (Decision 42 deferred), it may be useful to add a dedicated state field like `severity_weight: float | None` that the reason node uses when constructing the LLM prompt — keeping the derived value separate from the raw `exception["severity"]` string.

If new exception types are added, the state schema itself may not need to change — the `exception: dict` field already carries the full exception payload. But if a new processing step is introduced (e.g. a severity triage node), new state fields would be added here.
