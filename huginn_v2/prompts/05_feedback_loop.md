# Prompt: Phase 7 — Feedback Loop Documentation Update

**Phase:** Post-implementation feedback loop  
**When to use:** After all subplans are complete and all tests pass. Run this before beginning v3 design.  
**Produces:** Updated versions of all five `docs/` files and `prompts/01_design_methodology.md`, reconciled against the implemented codebase.

---

## What This Prompt Does

The design documents were written before the code. This prompt reconciles them with what was actually built. It does not redesign anything — it records reality. Every update must be traceable to something observable in the codebase.

The output is a set of fully integrated updated documents, not bolt-ons. Each document is regenerated as a complete, clean file. Nothing is appended to the end.

---

## Inputs

Read every file in the following locations before doing anything else:

**Source files (the implemented codebase):**
- `models/exception.py`
- `mimir/retriever.py`
- `mimir/index.py`
- `logger/audit.py`
- `agent/state.py`
- `agent/nodes.py`
- `agent/graph.py`
- `api/main.py`
- `scripts/build_index.py`
- `tests/test_models.py`
- `tests/test_retriever.py`
- `tests/test_integration.py`
- `requirements.txt`

**Design documents (the plan):**
- `docs/huginn_v2_masterplan.md`
- `docs/huginn_v2_design_decisions.md`
- `docs/huginn_v2_glossary.md`
- `docs/huginn_v2_interface_contract.md`
- `docs/huginn_v2_setup_notes.md`
- `prompts/01_design_methodology.md`

Read all of them before forming any conclusions. Do not update any document until all source files have been read.

---

## Inspection Pass

Before writing any updates, work through the following four inspection categories systematically. For each finding, note: which document it affects, what the discrepancy is, and whether it is a correction (the plan was wrong), a gap (the plan was silent), or a status update (the plan was right but the status language is stale).

Do not skip categories because they seem unlikely to have findings. Every category must be checked.

### Category 1 — Interface Drift

Compare every interface specification in `docs/huginn_v2_interface_contract.md` against the actual implemented code.

Check each of the following explicitly:

- **`models/exception.py`** — do the field names, types, enums, and validator behavior match the contract exactly?
- **`mimir/retriever.py`** — does `retrieve()` have the exact signature and return type specified? Does it return the exact fields (`text`, `document_id`, `section_id`, `retrieved_via`, `similarity_score`) specified?
- **`logger/audit.py`** — does the public interface match `log(event: dict) -> None` exactly? Does the routing logic (audit.jsonl, SQLite, escalation_queue.jsonl) match the spec?
- **`agent/state.py`** — does `AgentState` contain exactly the fields specified in the contract?
- **`agent/nodes.py`** — do all node function signatures match `(state: AgentState) -> dict`? Do the fields each node reads and writes match the contract?
- **`agent/graph.py`** — does the graph wiring match the three-path structure specified?
- **`api/main.py`** — do all four endpoint response schemas match the contract exactly, including field names, types, and nullable fields?
- **SQLite schema** — does the implemented schema in `logger/audit.py` match the schema in the contract exactly?

Flag any discrepancy, no matter how small. A field renamed from `document_id` to `doc_id` is a discrepancy.

### Category 2 — Decisions That Changed Under Implementation Pressure

Read through `docs/huginn_v2_design_decisions.md`. For each decision, ask: does the implemented code actually reflect this decision, or was it quietly adjusted during the build?

Pay particular attention to:
- The confidence threshold (0.75) — is it still the value in code?
- The mandatory escalation keywords (`sanctions`, `AML`, `regulatory hold`, `buy-in`, `sell-out`) — are these exactly the keywords implemented, with this exact casing and matching logic?
- The three-path branching structure — does the graph implement exactly three paths as described?
- Claude API failure handling — does the implemented behavior match Decision 28 exactly?
- The job ID pattern — does `POST /exceptions` return synchronously as described?

If any decision was modified, record the modification as a new decision addendum with the same format: what changed, why it changed, and what was rejected.

### Category 3 — Implementation Details That Became Decisions

The interface contract explicitly defers the following to implementation. Read the relevant source files and record what was actually decided for each:

- **LLM scoring rubric** (`agent/nodes.py`) — extract the exact four-factor regulatory reasoning rubric text and record it as a locked implementation detail. This is the rubric that will be iterated in v3 based on audit log data.
- **Two-pass retrieval configuration** (`mimir/retriever.py`) — what are the exact k values for pass 1 and pass 2? What is the cross-reference query template used in pass 2?
- **Section-aware chunking** (`mimir/index.py`, `scripts/build_index.py`) — what chunker is used, what chunk size, what overlap? What is the exact `_is_real_section()` logic and the minimum character threshold?
- **Embedding model** (`mimir/index.py`) — what model name, what configuration?
- **Claude API model string and max_tokens** (`agent/nodes.py`) — what exact model string and token limit are used in the API call?
- **Error handling for Claude API failures** (`agent/nodes.py`) — what exception types are caught, what triggers the auto-escalation path?
- **Pydantic validation error format** (`api/main.py`) — how are validation errors surfaced to the caller?

Each of these should be added to `docs/huginn_v2_design_decisions.md` as new decisions (Decision 55 onward) using the same format as existing decisions. They are not new design choices — they are implementation choices that need to be recorded so they are not lost before v3.

### Category 4 — New Known Issues

Read `requirements.txt` and note the actual pinned versions of all dependencies. Compare against the install command in `docs/huginn_v2_setup_notes.md`.

Then check: were there any dependency conflicts, version issues, import errors, or runtime surprises encountered during the build that are not currently recorded in `docs/huginn_v2_setup_notes.md`? If any test files contain comments about workarounds or unexpected behavior, those are candidates.

Add any new issues to `docs/huginn_v2_setup_notes.md` in the existing Known Issues format.

---

## Output Documents

Generate fully integrated updated versions of all six documents. Do not append to existing documents — regenerate each one clean.

### 1. `docs/huginn_v2_design_decisions.md`

- Update the status header to reflect that implementation is complete.
- Update "Next phase" to "Phase 7 complete. Ready for v3 design."
- Record any decisions that changed (Category 2 findings) as addenda to the relevant existing decisions, clearly marked as implementation-phase updates.
- Add all Category 3 findings as new numbered decisions (Decision 55 onward) using the standard format: Decision, Reasoning, Rejected option.
- Do not alter any existing decision text. Additions only.

### 2. `docs/huginn_v2_interface_contract.md`

- Update the status header to reflect implementation complete.
- Correct any interface drift found in Category 1. For each correction, add a one-line note: `[Updated post-implementation: <what changed and why>]` directly below the corrected specification.
- Do not alter specifications that matched the implementation.

### 3. `docs/huginn_v2_masterplan.md`

- Update all status headers to reflect implementation complete.
- Update the folder structure diagram if the actual folder structure differs from the plan.
- Update component descriptions if any component behaves differently than described.
- Do not redesign anything — only correct descriptions that no longer match the code.

### 4. `docs/huginn_v2_setup_notes.md`

- Update the status header.
- Update the install command if `requirements.txt` reveals the actual installed packages differ from the listed command.
- Add a pinned versions table drawn from `requirements.txt` — this is the version set that is known to work.
- Add any new known issues found in Category 4.

### 5. `docs/huginn_v2_glossary.md`

- Update any term definitions that no longer match the implementation. Cross-reference with the actual source files, not the design documents.
- Do not add new terms — that is the job of `04_rewrite_glossary.md`.

### 6. `prompts/01_design_methodology.md`

- Update the status line at the top of the document to reflect the current phase.
- Do not alter any other section.

---

## Constraints

- Every update must be traceable to something in the source files. Do not infer, assume, or invent.
- If a source file is ambiguous, flag the ambiguity explicitly rather than guessing.
- If a design document section has no corresponding discrepancy, reproduce it unchanged.
- Generate all six documents in a single pass after completing the full inspection. Do not generate documents mid-inspection.
- Use the pending changes list method: maintain a running list of all findings as you inspect, then generate documents from the list at the end.
