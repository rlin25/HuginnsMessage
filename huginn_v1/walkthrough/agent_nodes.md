# Walkthrough: `agent/nodes.py`

## Purpose

This file contains the logic for every node in the LangGraph agent. Each node is a pure function: it receives the full agent state, reads whatever fields it needs, and returns a partial state update. No node modifies shared state directly. No node has side effects except `log_result`, which writes to the audit log.

The pure function design is not aesthetic preference — it is what makes individual nodes unit-testable in isolation without running the full graph (Decision 9, architecture document). Every node in the test suite is called directly with a handcrafted state dict, with no LangGraph machinery involved.

Decisions 4, 9, 10, 17, 24, 25, 26, and 28 are all expressed in this file.

## Relationships

- **Imported by:** `agent/graph.py` (which wires the nodes into the state machine)
- **Imports from:** `mimir/retriever.py` (for `retrieve`), `logger/audit.py` (for `log`), `anthropic` (Claude API client), standard library
- **Does not touch:** the exception schema directly (receives exception as a plain dict), the API layer, or Chroma

## Decision Rationale

### `classify` node

**Why keyword detection happens here rather than in a separate node:**
Decision 10. The keyword scan is a property of the exception itself — it needs only the description field, nothing retrieved or reasoned over. Placing it in the classify node keeps it as early as possible in the graph, before any expensive operations run. A separate keyword-scan node between classify and retrieve was considered and rejected: it adds a graph node without adding capability, and the routing decision after classify already branches on `triggered_keyword`.

**Why the scan is case-insensitive:**
A compliance rule that fires only on lowercase "sanctions" but not "SANCTIONS" would be a compliance failure. Case-insensitivity is not a feature — it is correctness.

### `retrieve_node`

**Why the query is constructed as `"{sub_type}: {description}"`:**
Decision 23. The sub_type prefix anchors the similarity search. In v1 the knowledge base has exactly three documents, one per sub_type. Including the sub_type in the query makes it significantly harder to retrieve the wrong document — which matters because "the right document was retrieved" is one of the things the test suite verifies. A query using only the description could return the right result by coincidence rather than by retrieval working correctly.

### `reason` node

**Why the scoring rubric is hardcoded in this file:**
Decision 25 specifies that a rubric exists; Decision 25's reasoning is that an unguided LLM produces inconsistent confidence scores across runs. The rubric's exact wording is an implementation detail, not part of the interface contract. It lives here rather than in a config file because it is tightly coupled to the prompt structure and is iterated during the feedback loop phase.

**Why the markdown fence stripping exists:**
This is an implementation discovery from the feedback loop, not a design decision. The Claude API sometimes wraps JSON responses in markdown code fences (` ```json ... ``` `). The stripping logic handles this gracefully rather than failing with a JSON parse error. The model is instructed to return raw JSON, but defensive parsing is cheaper than debugging intermittent failures.

**Why `confidence_score` is clamped to `[0.0, 1.0]` after parsing:**
The LLM is prompted to return a float between 0.0 and 1.0, but the clamping ensures the downstream threshold comparison in the `decide` node behaves correctly regardless. A confidence score of 1.01 or -0.02 from a malformed LLM response would produce incorrect routing without the clamp.

**Why API failure auto-escalates rather than raising:**
Decision 28. An exception that entered the pipeline but received no decision is worse than a conservative escalation. The failure is recorded in the audit log with `escalation_reason = "system_error: ..."` so the cause is traceable. The `confidence_score: None` return value flows into the `decide` node, which has an explicit branch for `None` that routes to escalation.

### `decide` node

**Why the threshold comparison is deterministic code rather than asking the LLM:**
Decision 26. The LLM produces the confidence score; deterministic code makes the escalation decision. Asking the LLM to also recommend an action creates an authority conflict — what happens if the LLM recommends auto-resolve but the confidence score is 0.43? Separating concerns keeps the system auditable: the LLM's reasoning is in the reasoning trace, and the escalation decision is a simple `>=` comparison against a documented constant.

**Why `ESCALATION_THRESHOLD = 0.75` is a module-level constant:**
Decision 24. A single threshold is honest about what v1 is — a demonstration that the pipeline works, not a calibrated system. The constant is at the top of the file, clearly labeled, easy to change. In v2 it becomes a per-sub_type lookup — that change is localized to this file and the `decide` node, with no interface changes required.

### `escalate_fast_exit` node

**Why this node explicitly nulls out LLM-related fields:**
The API response for a fast-exit escalation has `retrieved_document_id: null` and `confidence_score: null`. Those null values are meaningful — they confirm Mimir and the LLM were never called. This node sets them explicitly so the audit log and API response accurately reflect what happened, rather than leaving those fields at whatever value they had from a previous state (which in practice is also null, but the explicit assignment documents the intent).

### `log_result` node

**Why logging is the last node rather than happening inside each path:**
Every path — standard, fast-exit, API failure — terminates at `log_result`. Putting logging at the terminal node means there is one place where logging happens, one function called, one set of fields assembled. If logging happened inside each path separately, a new path added in v2 could silently omit logging. The architecture makes the omission impossible.

## What It Does Not Do

This file does not validate the exception schema. Schema validation happened at the API layer before the agent was invoked. Nodes receive a plain dict and trust it is valid.

It does not manage the Chroma index or the embedding model. Those are Mimir's concern.

It does not decide where log entries go. Routing to JSONL, SQLite, and the escalation queue is the logger's concern (Decision 27).

## V2 Touch Points

The scoring rubric in `SCORING_RUBRIC` is the primary v2 iteration surface. As the feedback loop produces real audit log data, the rubric's weighting factors and score band definitions will be refined.

`severity` is passed to the LLM prompt in v2 (Decision 16). The `reason` node's `user_message` construction gains a severity line, and the scoring rubric gains a severity weighting factor.

`ESCALATION_THRESHOLD` becomes a per-sub_type dictionary in v2 (Decision 24), calibrated against real audit log data.
