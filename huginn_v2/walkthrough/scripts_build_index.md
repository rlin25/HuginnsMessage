# Walkthrough: `scripts/build_index.py`

## Purpose

This script runs once, before the server starts, to extract text from six regulatory PDFs, split it into section-aware chunks, and build the Chroma vector index that `mimir/retriever.py` queries at runtime. It is not imported by any other module — it is a standalone build artifact.

The script's output is the knowledge base that determines what Huginn can reason about. Getting the chunking right is more consequential than almost any other implementation choice in the system. A chunk that contains half of a regulatory subsection is less retrievable than one that contains it whole. The gate check — inspecting the chunk log before proceeding — exists because a misconfigured indexer produces a knowledge base that looks functional but returns degraded results silently.

## Relationships

- **Imports from:** `mimir/index.py` (shared constants), `pypdf`, `langchain_core`, `langchain_huggingface`, `langchain_chroma`
- **Imported by:** Nothing — runs as a standalone script
- **Does not touch:** The agent, the API layer, the audit logger, or any runtime component

## Decision Rationale

**Why `sys.path.insert(0, ...)`** at the top of the file: the script is invoked from the project root as `python scripts/build_index.py`. Without the path insert, `from mimir.index import ...` would fail — Python would not find `mimir` as a package because `scripts/` is not the project root. The path insert makes the project root importable at runtime. This is a script-specific concern; modules don't need it because they're imported with the project root already on the path.

**Why `DOCUMENT_MAP` is an explicit dict** mapping filenames to document IDs rather than deriving document IDs dynamically from filenames: if a file is in `knowledge_base/raw/` but not in `DOCUMENT_MAP`, it is skipped with a warning rather than auto-included. This prevents an unknown or incorrectly named PDF from silently entering the knowledge base with an unexpected `document_id`. The explicit mapping also makes the filename-to-ID relationship auditable — a future developer can read the dict and know exactly which files are expected and what IDs they produce (from masterplan).

**Why `SECTION_PATTERN` is compiled at module level**: the same regex is applied to every document. Pre-compiling at module level avoids recompiling on every `parse_sections()` call. This is a minor optimization but a good habit for frequently-called regex patterns.

**Why `_is_real_section(text, match)`** exists as a separate function: the false-split problem it solves is specific enough to deserve a named function with a docstring. FINRA-11810 contains `(b) through (g) of this Rule shall apply` mid-sentence. Without `_is_real_section`, the `^\([a-z]\)` regex fires on this match and produces a 292-character mid-sentence chunk that would pass the 200-character minimum and be indexed as a real section. The uppercase-continuation check rejects it (Decision 49).

**Why `_is_real_section` reads 60 characters of lookahead**: enough to clear any leading whitespace or optional quote/parenthesis characters that might precede the first word of a real section header. A real header like `"(a) General Rule."` has `"General"` immediately after `"(a) "` — the lookahead captures this comfortably. A mid-sentence parenthetical like `"(b) through"` has `"through"` — lowercase — so it's rejected.

**Why sequential suffixing always applies**, not only to documents with duplicate section letters: `FINRA-11810-a-1` is more consistent than `FINRA-11810-a` for some documents and `FINRA-11810-b-1` only for FINRA-11810. Consistent `-N` suffixes mean the deduplication logic in `mimir/retriever.py` can rely on `section_id` uniqueness without special-casing any document (from masterplan).

**Why short preambles are prepended to the first section** rather than discarded: the preamble text in eCFR-sourced PDFs (SEC-15c6-1, SEC-15c6-2) includes header and scope language that may contain relevant regulatory context. Prepending it to the first section preserves it within a retrievable chunk rather than losing it. Long preambles (≥ 200 chars) become their own preamble chunks.

**Why the 200-character minimum merges into the preceding chunk** rather than discarding the short chunk: regulatory subsections are never meaningless — a single-sentence subsection may be the most relevant chunk for a particular query. Discarding it would silently remove regulatory text. Merging with the preceding chunk keeps the text retrievable as part of a larger section (Decision 30).

**Why the gate check for duplicate `section_id` values runs before building the Chroma index**: a `section_id` collision means two chunks would share an identifier. The deduplication in `mimir/retriever.py` uses `section_id` as its key — a collision would cause one chunk to be silently dropped on every retrieval that encounters both. Catching the collision at index-build time, with an `sys.exit(1)`, forces the operator to fix the parser before the knowledge base exists (from masterplan).

**Why the chunk inspection log prints before `Chroma.from_documents()`**: the log is the gate validation artifact — the operator must inspect section boundaries before the index is written. If the log revealed a spurious chunk, the operator would need to fix `_is_real_section` and re-run. Printing after building would mean a broken index was already written before the operator could catch the problem (from setup notes).

## What It Does Not Do

- No incremental updates — runs from scratch every time; re-indexing is fast enough that incremental updates were not worth the complexity
- No `sub_type` metadata on chunks — sub-type relevance is determined by the LLM at reasoning time, not at index time (Decision 36)
- No filtering or exclusion of any regulatory section based on content — full text of every section is indexed
- Not imported by any runtime module — changes here have no effect on the running server until the index is rebuilt

## V3 Touch Points

`DOCUMENT_MAP` grows when new regulatory documents are added for new exception types. Each new document requires: placing the PDF in `knowledge_base/raw/`, adding one line to `DOCUMENT_MAP`, and re-running the script.

If v3 targets regulatory documents with different structural conventions — numbered sections (`1.`, `2.`) rather than lettered subsections (`(a)`, `(b)`) — `SECTION_PATTERN` and `_is_real_section` would need to be generalized. The current parser is calibrated specifically for FINRA and SEC regulatory text formatting.

If the embedding model changes (`mimir/index.py`), the index must be rebuilt. The script handles this correctly as-is — `Chroma.from_documents()` builds a fresh index on every run.
