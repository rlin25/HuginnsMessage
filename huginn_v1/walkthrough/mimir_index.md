# Walkthrough: `mimir/index.py`

## Purpose

This file manages the lifecycle of the Chroma vector store — loading it from disk on first access and caching it for the duration of the process. It is the boundary between the retriever (which talks to the rest of the system) and the vector store (which is an external library with its own initialization cost).

The separation from `mimir/retriever.py` exists for a concrete reason: initializing the vector store and querying the vector store are different concerns. If they lived in the same function, every query would pay the initialization cost, or the retriever would need to manage its own caching state. Neither is acceptable. This file owns the lifecycle; the retriever owns the query.

Decision 12 governs the choice of Chroma as the vector store.

## Relationships

- **Imported by:** `mimir/retriever.py` only — `get_vectorstore()` is the only export
- **Imports from:** `langchain_huggingface`, `langchain_chroma` — external libraries only
- **Does not touch:** anything in the Huginn codebase other than being called by the retriever

Nothing in the agent, API layer, or logger should ever import directly from this file. All access goes through `mimir/retriever.py`.

## Decision Rationale

**Why the module-level `_vectorstore = None` singleton:**
Loading the embedding model and connecting to the Chroma index takes several seconds on first call. Doing this on every retrieval query would make each exception take significantly longer to process. The module-level singleton ensures the initialization happens once and the loaded instance is reused. Python's module system guarantees that `_vectorstore` is shared across all callers within a process.

**Why `get_vectorstore()` rather than initializing at import time:**
Initializing at import time would load the embedding model whenever any module imports from `mimir/` — including test files that only want to test other components. Lazy initialization means the model is only loaded when a query is actually made. This keeps the test suite faster and avoids side effects on import.

**Why `all-mpnet-base-v2` as the embedding model:**
This model produces high-quality general-purpose sentence embeddings and is one of the most widely used models in the sentence-transformers library. It runs entirely locally with no API key. The choice is consistent with Decision 12's preference for local, offline components where possible.

**Why `PERSIST_DIR = "knowledge_base/processed"` as a relative path:**
The server is always started from `huginn_v1/` as the working directory (established during setup). Relative paths from that root resolve correctly. An absolute path would break portability across machines.

## What It Does Not Do

This file does not build the index. Index construction happens in `scripts/build_index.py` as a one-time offline operation. This file assumes the index already exists at `PERSIST_DIR` and loads it. If the index does not exist, the error surfaces in the retriever's `try/except` as an empty list — not a crash.

It does not re-index on changes to the knowledge base. If a new SOP document is added to `knowledge_base/raw/`, `scripts/build_index.py` must be re-run manually.

## V2 Touch Points

The embedding model is a v2 tuning surface. `all-mpnet-base-v2` is a strong general-purpose baseline but v2 may benefit from a domain-specific financial text model once the retrieval pipeline is proven. Changing the model requires re-running `scripts/build_index.py` to rebuild the index with the new embeddings — the two must always match.

The `PERSIST_DIR` path is duplicated between this file and `scripts/build_index.py`. If the index location ever changes, both must be updated together. A v2 cleanup would centralize this constant.
