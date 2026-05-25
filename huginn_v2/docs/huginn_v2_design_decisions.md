# Huginn v2 — Locked Design Decisions

**Status:** Implementation complete. Phase 7 (Feedback Loop) complete. All decisions locked.
**Last updated:** May 2026
**Source of truth:** This document supersedes `huginn_v1_design_decisions.md` for v2. V1 decisions are carried forward unchanged unless explicitly noted as updated.
**Next phase:** Phase 7 complete. Ready for v3 design.

---

## Project Summary

Huginn is an AI agent that receives flagged financial trade exceptions, classifies them, retrieves relevant resolution procedures from Mimir (its internal RAG knowledge base), reasons over them using the Claude API, and decides whether to auto-resolve the exception or escalate it to a human reviewer. Every decision is recorded in a structured audit log. V1 handled settlement mismatches only against a synthetic SOP knowledge base. V2 handles settlement mismatches against a real regulatory document knowledge base (FINRA and SEC rules) with two-pass iterative retrieval.

---

## Decision 1 — Exception Type Scope

**Decision:** V2 accepts settlement mismatches only. All other exception types are rejected at the API validation layer with a structured error before reaching the agent.

**Reasoning:** Unchanged from v1. New exception types deferred to v3 — see Decision 40.

**Rejected option:** Accepting all exception types but only having tested regulatory documents for settlement mismatches.

---

## Decision 2 — Settlement Mismatch Sub-Types

**Decision:** V2 handles three settlement mismatch sub-types: price mismatch, quantity mismatch, and wrong settlement date.

**Reasoning:** Unchanged from v1. Three sub-types give Mimir a real retrieval job across a real regulatory knowledge base.

**Rejected option:** Single sub-type only.

---

## Decision 3 — Audit Log Storage

**Decision:** Every decision is written to both `logs/audit.jsonl` (human-readable append-only flat file) and a local SQLite database (queryable by exception type, outcome, confidence score, date range).

**Reasoning:** Unchanged from v1.

**Rejected option:** Flat file only.

---

## Decision 4 — LLM Reasoning at Runtime

**Decision:** The LLM (Claude API) reasons over the retrieved regulatory document chunks at runtime. It produces the confidence score, full reasoning trace, and resolution steps in natural language. Non-negotiable across all versions.

**Reasoning:** Unchanged from v1.

**Rejected option:** Hardcoded rule-based scoring with no LLM at runtime.

---

## Decision 5 — LLM Choice

**Decision:** Huginn calls the Claude API (Anthropic) at runtime.

**Reasoning:** Unchanged from v1.

**Rejected option:** GPT-4o (OpenAI).

---

## Decision 6 — Escalation Queue

**Decision:** When Huginn escalates an exception, it writes the full exception and reasoning trace to a separate `logs/escalation_queue.jsonl` file in addition to the audit log.

**Reasoning:** Unchanged from v1.

**Rejected option:** Escalation recorded only as a field in the audit log.

---

## Decision 7 — FastAPI Endpoints

**Decision:** V2 exposes exactly three FastAPI endpoints:
1. `POST /exceptions` — submit an exception, returns a job ID
2. `GET /exceptions/{job_id}` — retrieve result by job ID
3. `GET /escalations` — returns current escalation queue as a JSON list

**Reasoning:** Unchanged from v1.

**Rejected option:** Two endpoints only.

[Implementation-phase update: `GET /escalations` was initially not implemented. `GET /health` (returning `{"status": "ok"}`) was added instead, which was not in the specification. After the Phase 7 inspection pass confirmed the spec deviation, `GET /escalations` was implemented — see Decision 53. V2 now exposes all three specified endpoints plus `GET /health`.]

---

## Decision 8 — Knowledge Base Composition

**Decision:** V2 knowledge base consists of six real regulatory documents in full, sourced directly from FINRA and the SEC:
- SEC Rule 15c6-1 (T+1 settlement cycle)
- SEC Rule 15c6-2 (same-day affirmation)
- FINRA Rule 11100 (Uniform Practice Code — Scope)
- FINRA Rule 11710 (General Provisions — reclamations)
- FINRA Rule 11810 (Buy-In Procedures and Requirements)
- FINRA Rule 11820 (Selling-Out)

No synthetic SOP documents. The synthetic nature of the v1 knowledge base is disclosed in the project README; v2 README discloses the real regulatory documents used.

**Reasoning:** Real regulatory documents replace synthetic SOPs entirely. FINRA 11710 is included as a dependency of 11820 — an exception involving a disputed reclamation cannot be reasoned against 11820 without understanding what a valid reclamation looks like. Full text of each rule is indexed rather than curated sections, because curating requires predicting in advance which sections are relevant. A retriever that returns noise from an irrelevant section produces a low confidence score and escalates (safe outcome); a retriever that silently excludes a relevant section produces a confidently wrong answer (worse outcome).

**Rejected option:** Synthetic SOPs retained alongside real regulatory documents. Rejected because mixing document types creates retrieval ambiguity about which type is authoritative for a given exception.

**Rejected option:** Curated sections only. Rejected because relevance cannot be predicted in advance for all possible exception descriptions.

---

## Decision 9 — LangGraph State Machine Structure

**Decision:** V2 LangGraph agent retains the three-path structure from v1:

1. **Invalid type exit** — fires at API layer (Pydantic validation). Agent never receives an invalid type.
2. **Mandatory escalation fast-exit** — fires at classify node if a trigger keyword is detected. Skips Mimir and LLM entirely.
3. **Standard path** — classify → retrieve → reason → decide → log.

**Reasoning:** Unchanged from v1. The two-pass retrieval change (Decision 37) is internal to the retrieve node and does not affect the graph structure.

**Rejected option:** Strictly linear graph with no branching.

---

## Decision 10 — Keyword Scan Timing

**Decision:** The mandatory escalation keyword scan runs immediately after classification, before Mimir retrieval.

**Reasoning:** Unchanged from v1.

**Rejected option:** Keyword scan after retrieval.

---

## Decision 11 — Frontend

**Decision:** No frontend in v2. FastAPI's auto-generated `/docs` interface is the demo surface.

**Reasoning:** Unchanged from v1. Frontend deferred to v3.

**Rejected option:** Minimal read-only frontend.

---

## Decision 12 — Vector Store

**Decision:** Chroma is the vector store for Mimir. Persists to disk, runs locally, supports metadata filtering.

**Reasoning:** Unchanged from v1.

---

## Decision 13 — Versioning Strategy

**Decision:** Each version of Huginn is regenerated from scratch by Claude Code using a new masterplan. Design documents carry intent across versions. Code is disposable.

**Reasoning:** Unchanged from v1.

**Rejected option:** Iterating on the v1 codebase for v2.

---

## Decision 14 — Exception Schema Fields and Data Types

**Decision:** The exception schema is unchanged from v1:

| Field | Type | Notes |
|---|---|---|
| `exception_id` | `UUID` | Uniquely identifies this exception |
| `trade_id` | `str` | References the originating trade |
| `type` | `ExceptionType` enum | Must be `settlement_mismatch` in v2 |
| `sub_type` | `SettlementMismatchSubType` enum | Must match parent type |
| `description` | `str` | Natural language description — used in Mimir query construction |
| `timestamp` | `datetime` | ISO 8601 |
| `severity` | `Severity` enum | `low`, `medium`, `high` — metadata only in v2, see Decision 42 |

**Reasoning:** Unchanged from v1.

**Rejected option:** Looser typing with strings.

---

## Decision 15 — Sub-Type Scoping

**Decision:** Valid sub_types are scoped to their parent type and enforced at the Pydantic layer via a model validator.

**Reasoning:** Unchanged from v1.

**Rejected option:** Flat unscoped enums.

---

## Decision 16 — Severity Field Treatment

**Decision:** The `severity` field is included in the exception schema in v2 but treated as metadata only — captured and written to the audit log but not passed to the LLM.

**Reasoning:** See Decision 42. Activation deferred to v3 to avoid compounding variables while the regulatory reasoning rubric is being proven.

**Rejected option:** Using severity as a reasoning input in v2.

---

## Decision 17 — Audit Log Full Fidelity

**Decision:** The audit log record contains full fidelity — complete original exception payload, all retrieved document chunks (with `section_id` and `retrieved_via` fields), raw LLM response, confidence score, reasoning trace, resolution steps, outcome, escalation reason, triggered keyword, retrieved document IDs, and all timestamps.

**Reasoning:** Unchanged from v1. `retrieved_document_ids` (plural) replaces `retrieved_document_id` — see Decision 45.

**Rejected option:** Decision-focused records omitting raw retrieved chunks and raw LLM response.

---

## Decision 18 — Escalation Queue Record Format

**Decision:** Escalation queue records are identical to audit log records — full fidelity, same schema.

**Reasoning:** Unchanged from v1.

**Rejected option:** Subset of audit log fields.

---

## Decision 19 — POST /exceptions Response Schema

**Decision:** `POST /exceptions` returns:
```json
{
  "job_id": "uuid",
  "status": "received",
  "exception_id": "uuid",
  "timestamp": "datetime"
}
```

**Reasoning:** Unchanged from v1.

**Rejected option:** Minimal response returning only `job_id` and `status`.

[Implementation-phase update: The implemented response does not match this schema. Because v2 processing is synchronous, the full agent result is available before the POST response is sent. The implementation returns the full result immediately:
```json
{
  "job_id": "uuid",
  "outcome": "auto_resolve | escalate",
  "confidence_score": "float | null",
  "reasoning_trace": "str | null",
  "resolution_steps": "str | null",
  "escalation_reason": "str | null",
  "retrieved_document_ids": ["str", ...]
}
```
`GET /exceptions/{job_id}` still works as a second read path (reads from SQLite audit log), but the POST response already contains the complete result. See Decision 50 for the full rationale. The fake-async minimal response was not used.]

---

## Decision 20 — GET /exceptions/{job_id} Response Schema

**Decision:** `GET /exceptions/{job_id}` returns:
```json
{
  "job_id": "uuid",
  "exception_id": "uuid",
  "outcome": "auto_resolve | escalate",
  "confidence_score": "float (0.0–1.0) | null",
  "reasoning_trace": "str | null",
  "resolution_steps": "str | null",
  "retrieved_document_ids": ["str", ...],
  "escalation_reason": "str | null",
  "timestamp": "datetime"
}
```

[Updated v2: `retrieved_document_id` (single string) replaced by `retrieved_document_ids` (list of strings) — see Decision 45.]

**Reasoning:** A list of unique `document_id` values across all retrieved chunks is more meaningful to a reviewer than a single top-result ID, particularly with two-pass retrieval that may draw from multiple rules.

**Rejected option:** Single `retrieved_document_id`. Rejected because it misrepresents which rules were consulted when two-pass retrieval fetches from multiple documents.

---

## Decision 21 — GET /escalations Response Schema

**Decision:** `GET /escalations` returns:
```json
{
  "escalations": [
    {
      "job_id": "uuid",
      "exception_id": "uuid",
      "trade_id": "str",
      "type": "str",
      "sub_type": "str",
      "outcome": "escalate",
      "confidence_score": "float | null",
      "reasoning_trace": "str | null",
      "escalation_reason": "str",
      "retrieved_document_ids": ["str", ...],
      "timestamp": "datetime"
    }
  ]
}
```

[Updated v2: `retrieved_document_id` replaced by `retrieved_document_ids` — see Decision 45.]

**Reasoning:** Unchanged from v1 except for the document IDs field update.

**Rejected option:** Lightweight summary list.

---

## Decision 22 — Mimir Retriever Function Signature

**Decision:** Mimir's single public function signature is unchanged:
```python
def retrieve(query: str, top_k: int = 3) -> list[dict]
```
Returns a list of dictionaries. Each dict contains: `text`, `document_id`, `section_id`, `similarity_score`, `retrieved_via`.

[Updated v2: `sub_type` field removed from returned dict. `section_id` and `retrieved_via` fields added — see Decision 38.]

**Reasoning:** The public interface is kept stable. Two-pass retrieval complexity is internal to Mimir. `retrieved_via` provides auditability of pass behavior without exposing internals through the interface.

**Rejected option:** New signature exposing pass metadata. Rejected because it couples the agent to Mimir's implementation details.

---

## Decision 23 — Query Construction for Mimir

**Decision:** The agent constructs the Mimir query string by combining `sub_type` and `description`: `"{sub_type}: {description}"`.

**Reasoning:** Unchanged from v1. Sub-type prefix anchors the semantic search against a regulatory knowledge base just as it did against synthetic SOPs.

**Rejected option:** Passing raw `description` field only.

---

## Decision 24 — Confidence Score Format and Escalation Threshold

**Decision:** The confidence score is a float between 0.0 and 1.0 produced by the LLM at runtime. A single threshold of 0.75 applies to all sub-types in v2. Exceptions scoring below 0.75 are escalated; at or above are auto-resolved.

[Updated v2: Threshold value confirmed at 0.75 carried forward from v1. V1 audit log data (7 entries, bimodal distribution) was insufficient to justify a change. Threshold is explicitly provisional — recalibrate after v2 audit log data accumulates against real regulatory documents. Per sub-type thresholds deferred to v3.]

**Reasoning:** The new regulatory reasoning rubric (Decision 39) will shift the confidence score distribution. Recalibrating before v2 produces real data would be premature.

**Rejected option:** Per sub-type thresholds in v2. Rejected because values would be arbitrary without v2 audit log data.

---

## Decision 25 — LLM Prompt Inputs

**Decision:** The LLM reasoning prompt contains three inputs: the full exception payload, the retrieved regulatory document chunks from Mimir, and an explicit scoring rubric. The LLM is instructed to return structured JSON only.

[Updated v2: Scoring rubric replaced — see Decision 39. Retrieved chunks now include `section_id` and `retrieved_via` fields, formatted as labeled regulatory context in the prompt.]

**Reasoning:** Unchanged structure from v1. Rubric content updated for regulatory reasoning.

**Rejected option:** Prompt with no rubric.

---

## Decision 26 — LLM Structured Output Schema

**Decision:** The LLM is prompted to return a structured JSON object with exactly three fields:
```json
{
  "confidence_score": 0.82,
  "reasoning_trace": "str",
  "resolution_steps": "str"
}
```

**Reasoning:** Unchanged from v1.

**Rejected option:** Richer output schema including `recommended_action`.

---

## Decision 27 — Audit Logger Interface

**Decision:** The audit logger exposes a single public function:
```python
def log(event: dict) -> None
```

**Reasoning:** Unchanged from v1.

**Rejected option:** Separate `log_decision()` and `log_escalation()` functions.

---

## Decision 28 — Claude API Failure Handling

**Decision:** If the Claude API call fails during the reasoning node, Huginn auto-escalates the exception with `escalation_reason = "system_error: {error description}"` and null values for all LLM fields.

**Reasoning:** Unchanged from v1.

**Rejected option:** Return structured error to caller with no audit log entry.

---

## Decision 29 — LLM Scoring Rubric

[Updated v2: Rubric replaced entirely. V1 rubric was calibrated for synthetic SOPs with procedural step-by-step guidance. V2 rubric is built around regulatory reasoning against legal text.]

**Decision:** The LLM reasoning prompt in `agent/nodes.py` uses a regulatory reasoning rubric built around four factors:

1. **Condition match** — Do the exception facts satisfy the triggering conditions specified in the retrieved regulatory rule? Does the scenario described in the exception meet the threshold or criteria the rule requires for a specific obligation or remedy to apply?

2. **Obligation clarity** — Does the retrieved rule specify a clear required action given the exception facts? Or does the rule leave the required response ambiguous, conditional on additional facts not present in the exception description?

3. **Exception applicability** — Do any of the rule's carve-outs, exceptions, or exclusions apply to this exception? (e.g. Does Rule 15c6-1's T+1 requirement apply, or does the late-pricing T+2 exception apply? Does Rule 11810 apply, or is the contract subject to a registered clearing agency's buy-in requirements instead?)

4. **Cross-reference resolution** — Were all rules referenced within the retrieved chunks also retrieved and considered? Unresolved cross-references lower confidence because the complete regulatory picture is not available.

Scoring guidance:
- Score 0.85–1.00: Condition match is clear, obligation is unambiguous, no exceptions apply, all cross-references resolved.
- Score 0.75–0.84: Condition match is probable, obligation is mostly clear, minor ambiguity exists but resolution path is defensible.
- Score 0.50–0.74: Condition match is uncertain, or an exception may apply but cannot be determined from available facts, or cross-references are unresolved.
- Score 0.00–0.49: Condition match cannot be established, or the rule explicitly requires human judgment, or critical cross-references are missing.

The rubric text is the primary artifact for v3 prompt engineering — every confidence score in the v2 audit log was produced by this rubric against the model string in Decision 32.

**Rejected option:** V1 SOP-oriented rubric. Rejected because its weighting factors (sub-type match, SOP completeness) do not map to regulatory reasoning tasks.

---

## Decision 30 — Chunking Strategy

[Updated v2: Strategy replaced. V1 used RecursiveCharacterTextSplitter with character-based boundaries. V2 uses rule-section-aware splitting on lettered subsections.]

**Decision:** `scripts/build_index.py` chunks regulatory documents using a custom section-aware parser. Documents are stored as sourced — one PDF per rule (e.g. `FINRA-11810.pdf`). The indexing script extracts text from each PDF using `pypdf`, then parses section boundaries by detecting lettered subsection headers using regex pattern `^\([a-z]\)` combined with two distinct protective mechanisms: a false-split filter and a minimum chunk length threshold.

The parent rule identifier and section header are prepended to every chunk as context.

**Two mechanisms — clarified post-implementation:**

*False-split filter (`_is_real_section()`)* — Rejects `(x)` regex matches that are not real section headers. After each regex match, the filter looks at the first non-whitespace, non-quote, non-parenthesis character following the `(x)` marker. If it is lowercase, the match is discarded as a mid-sentence parenthetical, not a section boundary. Discovered necessary during Subplan 2 validation: FINRA-11810 contains the phrase `(b) through (g) of this Rule shall apply` embedded mid-sentence, which the regex would have split on. Without the filter, FINRA-11810 produced 15 chunks (including a spurious 292-char mid-sentence fragment); with it, 14 correct chunks.

*Minimum chunk length (200 chars)* — After filtering and splitting, chunks shorter than 200 characters are merged with the preceding chunk. This handles genuinely short subsections (e.g. a single-sentence subsection that passed the false-split filter) that would be too small to retrieve meaningfully. This is a separate mechanism from false-split prevention; the design documents initially described it as preventing false splits, which was inaccurate.

**Reasoning:** Regulatory rules are divided into logical units by their authors — lettered subsections are the natural semantic boundaries. A chunk containing Rule 11810(b) with its header is more retrievable and self-contained than a character-boundary slice that crosses subsection lines.

**Rejected option:** RecursiveCharacterTextSplitter with increased chunk_size. Rejected because it imposes arbitrary character boundaries on documents whose authors already defined logical boundaries.

**Rejected option:** One file per section stored as `.txt`. Rejected because regulatory documents are sourced as PDFs and splitting them manually is unnecessary given the section parser.

---

## Decision 31 — Embedding Model

**Decision:** `mimir/index.py` generates vector embeddings using `HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")`.

**Reasoning:** Unchanged from v1. Runs locally, no API key required.

**Rejected option:** OpenAI `text-embedding-ada-002`.

---

## Decision 32 — Claude API Model String

**Decision:** `agent/nodes.py` uses `LLM_MODEL = "claude-sonnet-4-6"` as the Claude API model identifier, defined as a module-level constant.

**Reasoning:** Unchanged from v1.

**Rejected option:** Model string hardcoded inline.

---

## Decision 33 — Claude API Error Handling

**Decision:** `agent/nodes.py` catches all exceptions from the Claude API call with a bare `except Exception as e`. On any exception, the reason node returns null values for all LLM fields and `escalation_reason = f"system_error: {str(e)}"`.

**Reasoning:** Unchanged from v1.

**Rejected option:** Catching specific Anthropic SDK exception types.

---

## Decision 34 — Pydantic Validation Error Format

**Decision:** `api/main.py` does not define a custom exception handler for Pydantic `ValidationError`. FastAPI's default 422 handler is used.

**Reasoning:** Unchanged from v1.

**Rejected option:** Custom exception handler returning simplified flat error message.

---

## Decision 35 — Knowledge Base Document Set

**Decision:** The v2 knowledge base contains exactly six documents: SEC Rule 15c6-1, SEC Rule 15c6-2, FINRA Rule 11100, FINRA Rule 11710, FINRA Rule 11810, FINRA Rule 11820. This list is exhaustive for v2. Additional document types (e.g. FINRA Rule 7000 series for trade reporting) are deferred to v3 when exception type scope expands.

**Reasoning:** These six documents cover the full regulatory surface for settlement mismatch triage. 11710 is included as a direct dependency of 11820 — the sell-out rule references the Uniform Reclamation Form defined in 11710. Excluding it would leave an unresolvable cross-reference in the knowledge base.

**Rejected option:** Adding FINRA Rule 7000 series (trade reporting violations) in v2. Rejected because exception type scope is unchanged — adding regulatory documents for exception types Huginn doesn't handle creates retrieval noise without adding capability.

---

## Decision 36 — Chunking Implementation

**Decision:** `build_index.py` uses a custom section-aware parser. See Decision 30 for full specification.

Chunk metadata attached at index time:
- `document_id` — identifies the source rule (e.g. `FINRA-11810`)
- `section_id` — identifies the specific subsection (e.g. `FINRA-11810-b`)

No `sub_type` metadata. Sub-type relevance is determined by the LLM at reasoning time, not encoded at index time.

**Reasoning:** `sub_type` metadata required manual curation of relevance mappings for every chunk. Regulatory documents span multiple sub-types — 11810 is relevant to all three settlement mismatch sub-types at different stages. Incorrect tags actively hurt retrieval. The LLM is better positioned to determine sub-type relevance from chunk content than a static metadata tag.

**Rejected option:** Including `applicable_sub_types` as chunk metadata. Rejected because the mapping is not clean and incorrect tags degrade retrieval accuracy.

---

## Decision 37 — Iterative Retrieval

**Decision:** Mimir performs two-pass retrieval internally:

**Pass 1 — Semantic search:** Standard vector similarity search against the full index. Returns top-k chunks ranked by similarity score. Each chunk is tagged `retrieved_via: "primary"`.

**Pass 2 — Cross-reference resolution:** After Pass 1, the retriever scans returned chunks for explicit rule cross-references (patterns like "pursuant to Rule 11710", "in accordance with Rule 11820", "as provided in Rule 15c6-1"). For each unique referenced rule found, a targeted retrieval query is run against the index filtered by `document_id` of the referenced rule. Pass 2 results are tagged `retrieved_via: "cross_reference"` and combined with Pass 1 results before returning.

Pass 2 uses `document_id` metadata filtering, not a free semantic search, to keep the second pass deterministic.

**Reasoning:** Regulatory documents cross-reference each other heavily. A chunk containing "the remedy is provided for by Rules 11810 and 11820" without those rules' content leaves the LLM with incomplete regulatory context. Targeted second-pass retrieval by `document_id` resolves references deterministically without adding semantic uncertainty.

**Rejected option:** Single pass, same as v1. Rejected because unresolved cross-references produce artificially low confidence scores that route to escalation, even when the answer is fully available in the knowledge base.

**Rejected option:** Free semantic search for second pass. Rejected because it adds another layer of semantic uncertainty rather than resolving a known reference.

---

## Decision 38 — Mimir Public Interface

**Decision:** Mimir's public interface is unchanged: `retrieve(query: str, top_k: int = 3) -> list[dict]`.

Returned chunk dict structure for v2:

| Field | Type | Notes |
|---|---|---|
| `text` | `str` | Chunk content — passed to LLM reasoning prompt |
| `document_id` | `str` | Identifies the source rule (e.g. `FINRA-11810`) |
| `section_id` | `str` | Identifies the specific subsection (e.g. `FINRA-11810-b`) |
| `similarity_score` | `float` | Cosine similarity to query — from Chroma |
| `retrieved_via` | `str` | `"primary"` or `"cross_reference"` |

`sub_type` field removed. Two-pass logic is entirely internal to Mimir.

**Reasoning:** Keeping the public interface stable means the agent requires no changes to accommodate two-pass retrieval. `retrieved_via` provides full auditability of retrieval behavior through the existing chunk dict without changing the interface contract.

**Rejected option:** New signature exposing `RetrievalResult` with pass metadata. Rejected because it couples the agent to Mimir implementation details.

---

## Decision 39 — Scoring Rubric

See Decision 29. Decision 39 is the canonical location of the v2 rubric specification; Decision 29 is updated to reflect the replacement.

---

## Decision 40 — Exception Type Scope

**Decision:** V2 handles settlement mismatches only. Exception type scope is unchanged from v1. New exception types deferred to v3.

**Reasoning:** V2's changes — real regulatory documents, section-aware chunking, two-pass retrieval, new reasoning rubric — are substantial. Each represents a genuine system change that needs to be proven before layering on new exception types. V2's signal is "settlement mismatch handled correctly against real regulations." V3 expands the type taxonomy once that is proven.

**Rejected option:** Adding trade reporting violations (FINRA Rule 7000 series) as a new exception type in v2.

---

## Decision 41 — Confidence Threshold

**Decision:** Single threshold of 0.75 carried forward from v1. Explicitly provisional — recalibrate after v2 audit log data accumulates against real regulatory documents. Per sub-type thresholds deferred to v3.

**Reasoning:** V1 audit log data was insufficient to justify a change (7 entries, bimodal distribution, integration test fixtures only). The new regulatory reasoning rubric will shift the confidence score distribution — calibrating against v1 data that used a different rubric is methodologically unsound. 0.75 is retained as a reasonable starting point pending real v2 data.

**Rejected option:** Per sub-type thresholds set from v1 data. Rejected because v1 data was produced by a different rubric and is not a valid calibration signal for v2.

---

## Decision 42 — Severity Field Treatment

**Decision:** The `severity` field remains metadata only in v2. Captured and written to the audit log but not passed to the LLM reasoning prompt. Activation as reasoning input deferred to v3.

**Reasoning:** V2 already introduces a new rubric and real regulatory documents. Activating severity simultaneously means two variables change at once — rubric and inputs — making it harder to isolate which change is responsible for any shift in confidence score distribution. The audit log captures severity on every record, so v3 can use real v2 data to understand severity-outcome correlation before weighting it in the rubric.

**Rejected option:** Activating severity as a reasoning input in v2.

---

## Decision 43 — Mandatory Escalation Keywords

**Decision:** Five keywords trigger immediate escalation fast-exit in v2, bypassing Mimir and the LLM entirely:
- `sanctions`
- `AML`
- `regulatory hold`
- `buy-in`
- `sell-out`

Detection is case-insensitive. This list is exhaustive for v2.

[Updated v2: `buy-in` and `sell-out` added. Both terms indicate an exception has progressed past normal triage into formal regulatory close-out procedures, at which point automated confidence scoring is inappropriate regardless of retrieval quality.]

**Reasoning:** `buy-in` and `sell-out` signal the counterparty relationship has broken down to the point of formal FINRA Rule 11810/11820 remedy. An exception at this stage should not be auto-resolved — it requires human review regardless of confidence score, for the same reason sanctions and AML trigger fast-exit.

**Rejected option:** Three keywords only, same as v1. Rejected because the Phase 1 regulatory document review revealed that buy-in and sell-out are qualitatively different from earlier-stage settlement mismatches.

---

## Decision 44 — AgentState

**Decision:** `AgentState` requires minimal changes for v2. `retrieved_chunks` carries the updated chunk dict structure (with `section_id` and `retrieved_via` fields, without `sub_type`). No new top-level state fields. Two-pass retrieval behavior is invisible at the state level — the agent receives a flat list of chunks regardless of how many passes produced them.

**Reasoning:** The `retrieved_via` field on each chunk captures which chunks came from cross-reference passes. A compliance reviewer reading `retrieved_chunks` in the audit log can reconstruct retrieval behavior from that field without a separate `retrieval_pass_count` field. Adding top-level state fields for internal Mimir behavior leaks implementation details into the state contract.

**Rejected option:** Adding `retrieval_pass_count` and `cross_referenced_rules` to `AgentState`. Rejected because the same information is recoverable from chunk-level `retrieved_via` fields.

---

## Decision 45 — Retrieved Document IDs in API Response and Audit Log

**Decision:** `retrieved_document_id` (single string) is replaced by `retrieved_document_ids` (list of unique `document_id` strings across all retrieved chunks) in the `GET /exceptions/{job_id}` response, the `GET /escalations` response, the `AgentState`, and the audit log event dict.

**Reasoning:** With two-pass retrieval against a six-document knowledge base, a single top-result document ID misrepresents which rules were consulted. A list of unique `document_id` values communicates the full regulatory scope of the retrieval without requiring the reviewer to parse the full `retrieved_chunks` list.

**Rejected option:** Single `retrieved_document_id` unchanged from v1. Rejected because it is factually incomplete when two-pass retrieval fetches from multiple rules.

---

## Decision 46 — PDF Handling in build_index.py

**Decision:** `build_index.py` handles both `.txt` and `.pdf` source files. PDF text extraction uses `pypdf`. The section boundary parser applies to both file types after text extraction.

**Reasoning:** Regulatory documents are sourced as PDFs from FINRA and the SEC. Requiring manual conversion to text before indexing adds an unnecessary preprocessing step. `pypdf` was identified in v1 setup_notes (Known Issue 8) as the v2 candidate for PDF parsing.

**Rejected option:** Text conversion pre-processing outside the indexing pipeline. Rejected because it creates a manual step that must be repeated whenever a regulatory document is updated.

---

## Mandatory Escalation Keywords (V2)

The following keywords trigger an immediate escalation fast-exit regardless of confidence score:
- `sanctions`
- `AML`
- `regulatory hold`
- `buy-in`
- `sell-out`

This list is exhaustive for v2.

---

## Exception Type Taxonomy (V2)

Valid exception types in v2:
- `settlement_mismatch`

All other values are rejected at the API layer with a structured Pydantic validation error.

---

## Settlement Mismatch Sub-Types (V2)

- `price_mismatch`
- `quantity_mismatch`
- `wrong_settlement_date`

Each sub-type is covered by the v2 regulatory knowledge base, though not by a dedicated single document as in v1.

---

## Decision 47 — LLM max_tokens

**Decision:** `agent/nodes.py` sets `max_tokens=2048` in the Claude API call.

**Reasoning:** The masterplan specified `max_tokens=1000`. During the Subplan 5 gate, the Claude API response was truncated mid-JSON at char 2829, producing the error `Unterminated string starting at: line 4 column 23 (char 2829)`. The reasoning trace and resolution steps are both long natural-language strings that expand significantly when applied to multi-paragraph regulatory document chunks. 2048 tokens was sufficient for all observed responses. 1000 tokens was not.

**Rejected option:** `max_tokens=1000`. Rejected because it causes JSON parse failures when the regulatory context produces long reasoning traces.

---

## Decision 48 — dotenv Loading Strategy

**Decision:** `agent/nodes.py` calls `load_dotenv(find_dotenv(usecwd=True))` at module level to load the `ANTHROPIC_API_KEY`.

**Reasoning:** `load_dotenv()` without arguments only searches the current working directory. The project's `.env` file lives in the parent directory of `huginn_v2/` (at `/root/HuginnsMessage/.env`). `find_dotenv(usecwd=True)` searches upward from the CWD until it finds a `.env` file, making it resilient to the file's location. `usecwd=True` starts from the actual working directory rather than using Python frame introspection, which fails in non-interactive execution contexts (bash heredocs, test runners).

**Rejected option:** Hardcoding the `.env` path. Rejected because it breaks portability.

**Rejected option:** `load_dotenv()` without arguments. Rejected because it does not search parent directories.

---

## Decision 49 — False-Split Filter Implementation

**Decision:** `scripts/build_index.py` implements `_is_real_section(text, match)` to filter regex matches that are not true section boundaries. After each `^\([a-z]\)` match, the function reads up to 60 characters of following text, strips leading whitespace and optional leading quote/parenthesis characters, and requires the first character to be uppercase. Matches followed by lowercase-starting text are discarded.

**Reasoning:** FINRA-11810 contains the phrase `(b) through (g) of this Rule shall apply` embedded mid-sentence in section (k). The regex `^\([a-z]\)` with `re.MULTILINE` fires on this match because PDF text extraction places it at the start of a line. Without the filter, FINRA-11810 produced 15 chunks including a spurious 292-char mid-sentence fragment. With the filter it produces 14 semantically correct chunks. All real section headers in the six regulatory documents start with uppercase words or section titles — the filter does not discard any true boundaries.

**Rejected option:** Relying on the 200-char minimum alone to eliminate false splits. Rejected because the false split produced a 292-char fragment that would have passed the minimum threshold and been indexed as a real section.

---

## Decision 50 — POST /exceptions Returns Full Result

**Decision:** `POST /exceptions` returns the full agent result immediately rather than the `{job_id, status, exception_id, timestamp}` minimal response specified in Decision 19.

**Reasoning:** V2 processing is synchronous — `huginn_graph.invoke()` runs to completion before the POST response is sent. The full result is available at zero marginal cost. Returning only a job ID and then requiring a second GET request adds a round trip with no benefit. The fake-async minimal response exists to support v3 async processing, where the result may not be ready when POST returns. In v2, returning the full result is strictly more useful. Decision 19 addendum documents the schema change.

The two-endpoint pattern is preserved: `GET /exceptions/{job_id}` still provides a read path (from the SQLite audit log), supporting the v3 transition and enabling result lookup after the POST response has been consumed.

**Rejected option:** Fake-async minimal response as specified. Rejected because it forces unnecessary client complexity (a second HTTP round trip) when the result is already available.

---

## Decision 51 — GET /exceptions/{job_id} Reads from SQLite

**Decision:** `GET /exceptions/{job_id}` looks up `job_id` in the SQLite audit database (`logs/audit.db`) and returns the stored `full_event_json` column. It does not use an in-memory dict.

**Reasoning:** The masterplan specified an in-memory `results: dict[str, dict]` store, which would be cleared on server restart. Reading from SQLite is persistent — a job ID submitted in a previous server session remains retrievable. Since the audit logger already writes every result to SQLite, using that as the read-path store adds no new code. The `full_event_json` column stores the complete event dict, which contains all fields needed for the GET response.

**Rejected option:** In-memory dict as specified in the masterplan. Rejected because it loses results on server restart, which is a regression from the audit log's durability guarantee.

---

## Decision 52 — GET /health Endpoint

**Decision:** `api/main.py` includes a `GET /health` endpoint returning `{"status": "ok"}`. This endpoint was not in the original specification.

**Reasoning:** Added during Subplan 6 implementation. Standard FastAPI service practice. Required by any container orchestration or reverse proxy health check. Low risk, no state, no dependencies.

**Rejected option:** No health endpoint. Rejected because it makes the service harder to integrate with deployment infrastructure.

---

## Decision 53 — GET /escalations Implementation

**Decision:** `GET /escalations` is implemented in `api/main.py`. Queries `logs/audit.db` filtered by `outcome = 'escalate'` and returns `{"escalations": [...]}` where each entry is the full event dict from `full_event_json`. Returns `{"escalations": []}` when no escalations exist or the database does not yet exist.

**Reasoning:** Initially deferred during the Phase 7 inspection pass. Resolved in the same session after review confirmed: it was in the original v2 spec (Decision 7), the escalation data was already being written to SQLite by the logger, and the implementation was a simple filtered read — no new design decisions required.

**Rejected option:** Reading from `logs/escalation_queue.jsonl` directly. Rejected because the SQLite audit database already contains all the same records, is queryable without line-by-line parsing, and is the source used by `GET /exceptions/{job_id}` for consistency.

---

## Decision 54 — requirements.txt

**Decision:** `requirements.txt` is generated from `pip freeze` and committed to the repository. It contains all installed packages including transitive dependencies (151 packages in the known-working environment).

**Reasoning:** Absent during initial implementation — new developers had no reproducible install path. Generated and committed after the Phase 7 inspection identified it as a known issue. Full `pip freeze` output is used rather than a curated list because transitive dependency versions affect embedding model loading and LangGraph behavior; partial version pinning creates false confidence.

**Rejected option:** Curated list of top-level dependencies only. Rejected because transitive dependency version mismatches are a known source of silent failures in the LangGraph + Chroma + sentence-transformers stack.

---

## What V2 Is Not

The following are explicitly out of scope for v2 and deferred:

**V3:**
- Multiple exception types beyond settlement mismatches
- Per sub-type escalation thresholds (requires v2 audit log data)
- Severity as a reasoning input (requires v2 audit log data)
- Expanded mandatory escalation keyword list
- Frontend of any kind
- Asynchronous queue processing
- Evaluation harness with golden datasets
- Real notification system for escalations
- Multi-agent or distributed processing
