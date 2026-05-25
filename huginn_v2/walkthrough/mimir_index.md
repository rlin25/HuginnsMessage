# Walkthrough: `mimir/index.py`

## Purpose

This file exists to prevent a silent failure mode: if `build_index.py` and `mimir/retriever.py` each define their own copy of the embedding model name or the persist directory path, they can drift independently. When they do, `retriever.py` tries to query an index built by a different model, and every similarity search returns garbage — silently. No error is raised. The system appears to work.

Two constants in a single file eliminate that risk. `PERSIST_DIR` and `EMBEDDING_MODEL` are the shared configuration that both the indexer and the retriever must agree on. A change to either value is a single-line edit in a single file.

## Relationships

- **Imports from:** Nothing — this file has no imports
- **Imported by:** `mimir/retriever.py` and `scripts/build_index.py` — both import both constants
- **Does not touch:** Any LangChain, Chroma, or HuggingFace code — this is pure configuration

## Decision Rationale

**Why a separate file for two constants** rather than defining them in `retriever.py` and importing from there into `build_index.py`, or vice versa: neither module should be the "owner" of shared configuration that the other depends on. Putting configuration in a neutral shared module makes the dependency direction explicit — both consumers depend on the config module, neither depends on the other (Decision 31 implies this architectural choice).

**Why `PERSIST_DIR` is a string** (not a `Path`): LangChain's `Chroma` constructor and the `Chroma.from_documents()` call both accept a string for `persist_directory`. Using `Path` would require calling `str()` at every usage site.

## What It Does Not Do

- No functions
- No classes
- No initialization logic
- No validation that the directory exists or the model is available

Both callers handle their own error cases. This file's only job is to ensure they use the same values.

## V3 Touch Points

`EMBEDDING_MODEL` is the first thing to revisit if a better sentence transformer is adopted for the v3 knowledge base expansion. Changing it requires rebuilding the index — the retriever cannot query an index built with a different model. The constant name exists partly to make this dependency visible: any developer changing `EMBEDDING_MODEL` in this file will see immediately that it affects both the build script and the retriever.

`PERSIST_DIR` may change if the knowledge base storage strategy changes (e.g. moving to a shared volume or a managed vector database in v3).
