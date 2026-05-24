# Walkthrough: `mimir/retriever.py`

## Purpose

This file is Mimir's entire public surface. It contains one function. Everything a caller needs to know about Mimir is expressible through that function's signature and return type — nothing else is exposed.

The isolation is the point. The agent queries this function and receives chunks. It has no visibility into whether those chunks came from Chroma, a flat file, or an API call. That implementation detail lives in `mimir/index.py` and is deliberately hidden here. The retriever is the contract; the index is the mechanism.

Decision 22 defines the function signature. Decision 23 governs how the agent constructs the query string before calling this function.

## Relationships

- **Imported by:** `agent/nodes.py` (the `retrieve_node` function)
- **Imports from:** `mimir/index.py` (the `get_vectorstore` function — the only internal Mimir dependency)
- **Does not touch:** the agent state, the audit logger, the exception schema, or any API layer

The retriever knows nothing about exceptions, decisions, or escalations. It only answers: "given this query string, what are the most relevant chunks?"

## Decision Rationale

**Why return structured dicts rather than raw strings:**
Decision 22 explains this. `document_id` is needed by the agent to populate `retrieved_document_id` in the audit log and API response. `similarity_score` is additional signal for the LLM reasoning prompt. Chroma provides both natively at no extra cost. Returning raw strings would silently discard metadata that is already available and that downstream components need.

**Why the try/except returns an empty list instead of raising:**
The agent handles empty retrieval gracefully — if no chunks come back, it still runs the LLM with a "no SOP documents retrieved" message and the confidence score will naturally be low. An exception bubbling up from Mimir would bypass that graceful handling and require the caller to have its own error path. Returning `[]` keeps the failure mode in a predictable channel. Decision 28 (Claude API failure handling) establishes the same principle for the LLM layer: conservative behavior on failure is better than a crash.

**Why `top_k` has a default of 3 rather than 1:**
A single chunk risks cutting off relevant SOP content mid-section. Three chunks provides enough context for the LLM without overwhelming the prompt. The parameter is configurable (Decision 22) so v2 can experiment with retrieval depth without an interface change.

## What It Does Not Do

This file does not construct the query string. Query construction — combining `sub_type` and `description` — happens in `agent/nodes.py`. Mimir accepts whatever string it receives and searches against it. This separation means the query construction strategy can change in v2 without touching Mimir.

It does not filter, rank, or re-rank results beyond what Chroma's similarity search provides. Iterative retrieval and re-ranking are v2 features.

It does not log. If a retrieval returns no results or fails, the `print` statement is diagnostic only. Structured logging of retrieval events is a v2 addition.

## V2 Touch Points

The function signature is intentionally forward-compatible. `top_k` as a configurable parameter with a default enables v2 retrieval experimentation without an interface change.

Iterative retrieval — querying Mimir multiple times with refined queries based on initial results — is explicitly deferred to v2 (architecture document). When that lands, this file gains a loop and the single `similarity_search_with_score` call becomes one step in a multi-pass process.

Real FINRA/SEC regulatory documents enter the knowledge base in v2 (Decision 8). This file is unaffected — the retriever is indifferent to what documents are in the index.
