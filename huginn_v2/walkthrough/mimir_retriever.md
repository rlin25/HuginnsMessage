# Walkthrough: `mimir/retriever.py`

## Purpose

This file implements two-pass retrieval over the regulatory knowledge base and exposes exactly one public function. Everything about how retrieval works — the two passes, the cross-reference detection, the deduplication — is internal. The agent calls `retrieve(query)` and receives a flat list of chunks. It does not know whether one pass ran or three.

The isolation is deliberate. Two-pass retrieval is a v2-specific mechanism. In v3, a third pass or a different retrieval strategy might be introduced. If the agent were coupled to the retrieval mechanism, that change would require modifying the agent. Because the boundary is a single function with a stable signature, the agent requires no changes (Decision 38).

## Relationships

- **Imports from:** `mimir/index.py` (shared constants), `langchain_chroma`, `langchain_huggingface`
- **Imported by:** `agent/nodes.py` — the `retrieve` node is the only caller
- **Does not touch:** The exception schema, the audit logger, the LLM, the API layer, or any business domain logic

## Decision Rationale

**Why `_vectorstore` is a module-level singleton** initialized lazily on first call: loading the HuggingFace embedding model and the persisted Chroma index is expensive — the model weights are loaded into memory. Doing this once at module load time (or on the first `retrieve()` call) means all subsequent calls reuse the same in-memory store. Initializing it inside `retrieve()` on every call would load the model weights repeatedly, once per request.

**Why `SUBSTRING_TO_DOCUMENT_ID` is one dict** rather than two separate constants (`KNOWN_DOCUMENT_IDS` and a mapping dict): the design document specified two constants, but the implementation collapses them into one. Iterating `SUBSTRING_TO_DOCUMENT_ID.items()` gives both the substring for detection and the full `document_id` for filtering in a single pass. Adding a new document requires updating only one data structure. Two constants that must be kept in sync are one future bug (from glossary, Decision 38 reasoning).

**Why cross-reference detection uses `combined_text.lower()` on the concatenated text of all Pass 1 chunks**: regulatory documents reference each other by rule number (`"Rule 11810"`, `"Rule 15c6-1"`) scattered throughout prose. Lowercasing the combined text before substring matching makes detection case-insensitive — `"rule 11810"` and `"Rule 11810"` both trigger a Pass 2 fetch. Regex matching was considered but rejected in favor of simple substring search against known identifiers; the known identifiers are short and distinctive enough that false positives are not a concern.

**Why Pass 2 has its own inner `try/except`** per referenced rule: a metadata filter failure on one referenced document (e.g. if a document ID were somehow absent from the index) should not abort retrieval for all other referenced documents. The outer `except Exception: return []` handles complete retrieval failures; the inner exception handling handles partial Pass 2 failures gracefully.

**Why deduplication keeps the `"primary"` tagged version over `"cross_reference"`** when the same chunk appears in both passes: a chunk that appears in Pass 1 was the most relevant result for the query. If Pass 2 retrieves the same chunk filtered by document ID, the Pass 1 version is more meaningful for audit purposes — it means the chunk was retrieved because it was semantically relevant, not just because another chunk cross-referenced its document. The `seen` dict with its `"primary"` preference records this accurately (Decision 44).

**Why the outer `except Exception: return []`** covers the entire retrieval function: the agent handles an empty list gracefully — an empty retrieval produces a low confidence score and escalates, which is the correct behavior when the knowledge base is unavailable. An unhandled exception from the retriever would propagate to the agent and crash the pipeline. Returning an empty list keeps the failure mode contained and auditable (from interface contract).

**Why `TOP_K_CROSS_REF = 2`** is smaller than the default `top_k = 3`: Pass 2 is targeted context-fetching for a specific referenced rule, not a broad relevance search. Two chunks from the referenced rule are sufficient to give the LLM the cross-reference context it needs without overwhelming the prompt with content from documents that may only be tangentially relevant.

## What It Does Not Do

- No confidence scoring
- No relevance ranking or re-ranking after retrieval
- No caching of query results
- No knowledge of exception types, sub-types, or any business domain logic
- No logging — the audit trail is built by `log_result` using the chunks already in agent state
- No exposure of how many passes ran — the public interface hides this

## V3 Touch Points

`SUBSTRING_TO_DOCUMENT_ID` grows when new regulatory documents are added for new exception types. Each addition is a one-line dict entry. The retrieval logic itself doesn't change.

If v2 audit log data reveals that certain cross-references are never useful (adding noise without improving confidence scores), `TOP_K_CROSS_REF` can be tuned down or the detection logic can be made more selective. If cross-references are being missed (low confidence scores on exceptions where the answer was in the knowledge base), `top_k` in Pass 1 or `TOP_K_CROSS_REF` in Pass 2 can be increased.

A third pass — for example, fetching chunks related to regulatory glossary definitions — would be added here without touching the agent.
