# Walkthrough: `scripts/build_index.py`

## Purpose

This script is a one-time preprocessing step. It reads the raw SOP documents from `knowledge_base/raw/`, chunks them, embeds them, and writes the resulting vector index to `knowledge_base/processed/`. It runs manually before the server starts and does not run again unless the knowledge base changes.

It exists as a script in `scripts/` rather than as part of Mimir because it is a build-time operation, not a runtime operation. Mimir loads and queries the index at runtime — it does not build it. Separating the build step from the runtime prevents initialization cost from appearing on the hot path and makes the build process explicit and repeatable.

Decision 8 governs the knowledge base composition. Decision 12 governs the choice of Chroma.

## Relationships

- **Called by:** a developer running `python scripts/build_index.py` from the project root — never called at runtime
- **Imports from:** `langchain_community`, `langchain_text_splitters`, `langchain_huggingface`, `langchain_chroma`
- **Does not touch:** Mimir's retriever, the agent, the API layer, or the logger

This script and `mimir/index.py` share `PERSIST_DIR` and `EMBEDDING_MODEL` values. They must stay in sync — the index and the loader must use the same embedding model or queries will return nonsense.

## Decision Rationale

**Why metadata is attached to every chunk rather than just to documents:**
Chroma stores chunks, not documents. When the retriever returns a chunk, it needs to know which document it came from and which sub_type that document covers — without joining back to any external table. Attaching `document_id` and `sub_type` to every chunk at index time means each chunk is self-describing at query time. This is what makes `retrieved_document_id` and `sub_type` available in Mimir's return dict at zero additional cost.

**Why the `DOCUMENT_METADATA` dict is keyed on filename stems:**
The mapping from filename to metadata (`document_id`, `sub_type`) needs to live somewhere. Keying on the filename stem makes the mapping explicit and auditable — adding a new SOP document requires adding one entry to this dict and dropping the file in `knowledge_base/raw/`. Files without a metadata entry produce a warning and are skipped, rather than being indexed with unknown metadata.

**Why `chunk_size=500` with `chunk_overlap=50`:**
500 characters is large enough to contain a complete SOP procedure step with context, but small enough that a single chunk doesn't span multiple unrelated steps. The 50-character overlap prevents a relevant sentence from being split across two chunks where neither chunk alone has enough context for the LLM. These values are v1 baselines — Decision 8's controlled knowledge base means retrieval correctness is verifiable, which will inform v2 tuning.

**Why LangChain is used here but not in the runtime agent:**
The architecture document notes this explicitly. LangChain's document loaders and text splitters are genuinely useful for the preprocessing step — they handle file reading, encoding, and splitting cleanly. But none of that functionality is needed at runtime. The runtime agent calls Mimir's `retrieve()` function, which uses Chroma directly. LangChain is a build-time dependency only.

**Why `sys.path.insert` is at the top:**
The script is run from the project root (`huginn_v1/`), but Python's path resolution when running a script adds the script's directory (`scripts/`) to the path, not the project root. The insert ensures `from mimir.index import ...` would resolve correctly if needed. In this script it is defensive — the script doesn't import from the project's own modules at runtime, but the pattern is consistent with how the test suite handles the same problem.

## What It Does Not Do

This script does not run incrementally. If one SOP document changes, the entire index is rebuilt from scratch. Incremental index updates are a v2 consideration.

It does not validate the content of SOP documents — it loads whatever text is in the files. Content quality is a knowledge base curation concern, not an indexing concern.

It does not configure any runtime behavior. The server's query behavior is entirely determined by what `mimir/index.py` loads at startup.

## V2 Touch Points

Real FINRA/SEC regulatory documents enter `knowledge_base/raw/` in v2 (Decision 8). Each new document requires a corresponding entry in `DOCUMENT_METADATA`. The chunking parameters (`chunk_size`, `chunk_overlap`) may need tuning once real documents with different structure are included.

The embedding model (`all-mpnet-base-v2`) is a v2 tuning surface. Any change to the embedding model requires re-running this script to rebuild the index with the new model — the index and the loader in `mimir/index.py` must always use the same model.
