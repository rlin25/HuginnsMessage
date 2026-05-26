# Huginn v1 — Locked Design Decisions

**Status:** Implementation complete. Phase 7 (Feedback Loop) complete. All decisions locked.
**Last updated:** May 2026
**Next phase:** Phase 7 complete. Ready for v2 design.

---

## Project Summary

Huginn is an AI agent that receives flagged financial trade exceptions, classifies them, retrieves relevant resolution procedures from Mimir (its internal RAG knowledge base), reasons over them using an LLM, and decides whether to auto-resolve the exception or escalate it to a human reviewer. Every decision is recorded in a structured audit log. V1 handles settlement mismatches only and is demonstrated entirely through a FastAPI interface.

---

## Decision 1 — Exception Type Scope

**Decision:** V1 accepts settlement mismatches only. All other exception types are rejected at the API validation layer with a structured error before reaching the agent.

**Reasoning:** Limiting to one exception type eliminates an entire category of debugging ambiguity. When a result is bad, the cause is unambiguous — it's not a retrieval gap from an untested exception type. Enforced via a Pydantic enum on the `type` field. Takes three lines of code.

**Rejected option:** Accepting all exception types but only having tested SOPs for settlement mismatches. Rejected because unpredictable outputs on untested types would obscure whether core reasoning logic is working correctly.

---

## Decision 2 — Settlement Mismatch Sub-Types

**Decision:** V1 handles three settlement mismatch sub-types: price mismatch, quantity mismatch, and wrong settlement date.

**Reasoning:** One sub-type makes Mimir's retrieval trivially easy — it will always return the same document regardless of the query, which doesn't prove retrieval is working. Three sub-types keeps v1 simple while giving Mimir a real job to do. Each sub-type has its own SOP document in the knowledge base.

**Rejected option:** Single sub-type only (price mismatch). Rejected because it makes Mimir a rubber stamp rather than a functioning retrieval system.

---

## Decision 3 — Audit Log Storage

**Decision:** Every decision is written to both `logs/audit.jsonl` (human-readable append-only flat file) and a local SQLite database (queryable by exception type, outcome, confidence score, date range).

**Reasoning:** The `.jsonl` file provides a human-readable compliance trail. SQLite adds queryability at near-zero complexity cost — it's built into Python's standard library, requires no external service, and sets up the v2 evaluation harness naturally. The logger is an isolated component; nothing else in the codebase touches it directly.

**Rejected option:** Flat file only. Rejected because it makes performance analysis during v2 development significantly harder — every query requires writing a file parsing script.

---

## Decision 4 — LLM Reasoning at Runtime

**Decision:** The LLM (Claude API) reasons over the retrieved SOP document at runtime. It produces the confidence score, full reasoning trace, and resolution steps in natural language. This is non-negotiable across all three versions.

**Reasoning:** The entire point of Huginn as a portfolio piece is demonstrating agentic AI reasoning. Rule-based scoring with no LLM in the reasoning loop produces a rules engine with a vector store attached, not an AI agent. The LLM reasoning step is the core of what makes this project interesting and interview-worthy.

**Rejected option:** Hardcoded rule-based scoring with no LLM at runtime. Rejected because it defeats the purpose of the project.

---

## Decision 5 — LLM Choice

**Decision:** Huginn calls the Claude API (Anthropic) at runtime. Claude Code is the primary development environment.

**Reasoning:** Familiarity with Claude's reasoning patterns reduces debugging time meaningfully. Using the API of the model actively used during development creates a tighter feedback loop. Claude Code as the development environment creates a coherent three-part story: built with Claude Code, reasoned with Claude API, iterated with Claude as a thinking partner.

**Rejected option:** GPT-4o (OpenAI). Rejected in favor of Claude due to development familiarity and workflow coherence.

---

## Decision 6 — Escalation Queue

**Decision:** When Huginn escalates an exception, it writes the full exception and reasoning trace to a separate `logs/escalation_queue.jsonl` file in addition to the audit log. This file represents the human reviewer's inbox.

**Reasoning:** Makes the human-in-the-loop concept physically visible as a separate artifact rather than just a boolean flag in a JSON object. Costs three lines of code inside the logger. Sets up v3's real notification layer naturally. More demonstrable in an interview — two distinct files tell the story clearly.

**Rejected option:** Escalation recorded only as a field in the audit log. Rejected because it makes the escalation pathway invisible without manually parsing the full audit log.

---

## Decision 7 — FastAPI Endpoints

**Decision:** V1 exposes exactly three FastAPI endpoints:
1. `POST /exceptions` — submit an exception, returns a job ID
2. `GET /exceptions/{job_id}` — retrieve result by job ID
3. `GET /escalations` — returns current escalation queue as a JSON list

**Reasoning:** The third endpoint makes the escalation pathway fully demonstrable via API calls alone without anyone needing to open a file. The full demo narrative flows in three API calls: submit exception → retrieve decision → check escalation queue. Utility-to-complexity ratio strongly favors inclusion.

**Rejected option:** Two endpoints only (no `/escalations`). Rejected because it forces file inspection to demonstrate escalation, breaking the clean API-only demo narrative.

---

## Decision 8 — Knowledge Base Composition

**Decision:** V1 knowledge base consists of three to four synthetic SOP documents only — one per settlement mismatch sub-type — written for a fictional financial firm. Real FINRA/SEC regulatory documents are added in v2.

**Reasoning:** A fully controlled knowledge base eliminates one entire category of debugging ambiguity during initial development. When Mimir retrieves the wrong document, the cause is unambiguously a retrieval bug, not noise from an unexpected source document. The synthetic nature must be disclosed in the README.

**Rejected option:** Synthetic SOPs plus real FINRA/SEC documents from day one. Rejected because uncontrolled source material complicates debugging before the retrieval pipeline is proven.

---

## Decision 9 — LangGraph State Machine Structure

**Decision:** V1 LangGraph agent has three distinct paths:

1. **Invalid type exit** — fires at classification if exception type is not in the approved taxonomy. Returns a structured error. Nothing else runs.
2. **Mandatory escalation fast-exit** — fires at classification if a trigger keyword is detected in the exception (e.g. "sanctions", "AML", "regulatory hold"). Skips Mimir retrieval and LLM reasoning entirely. Routes directly to escalate. Audit log records the specific keyword that triggered it.
3. **Standard path** — classify → retrieve → reason → decide → log. Single branch at the end: escalate or auto-resolve based on confidence score.

**Reasoning:** The invalid type exit provides a second line of defense inside the agent (API validation is the first). The mandatory escalation fast-exit short-circuits expensive LLM calls for obvious escalation cases and is more defensible from a compliance perspective — fewer moving parts between a sanctions flag and the escalation decision. Both branches have clear, defensible reasons for existing.

**Rejected option:** Strictly linear graph with no branching except the final escalate/resolve decision. Rejected because it provides no error handling and forces every exception through the full reasoning pipeline regardless of obvious disqualifying conditions.

---

## Decision 10 — Keyword Scan Timing

**Decision:** The mandatory escalation keyword scan runs immediately after classification, before Mimir retrieval. If a trigger keyword is found, the graph exits to escalation without ever calling Mimir.

**Reasoning:** Mandatory escalation keywords are properties of the exception itself, not Mimir's documents. No reason to pay for a retrieval call that will be ignored. The audit log entry is cleaner — "escalated immediately: sanctions keyword detected" is more honest than a log entry that includes a retrieved document that played no role in the decision.

**Rejected option:** Keyword scan after retrieval. Rejected because it incurs unnecessary retrieval cost and produces a misleading audit trail.

---

## Decision 11 — Frontend

**Decision:** No frontend in v1. FastAPI's auto-generated `/docs` interface is the demo surface.

**Reasoning:** FastAPI's `/docs` page exposes the API contract directly — request schema, response schema, and all three endpoints in a clean browser interface. This is a better signal to technical interviewers than a barebones HTML wrapper. The audience for v1 is the developer and technical reviewers. A non-technical demo surface is a v3 feature.

**Rejected option:** Minimal read-only frontend showing escalation queue and recent decisions. Rejected due to scope creep risk and because the target audience for v1 doesn't require it.

---

## Decision 12 — Vector Store

**Decision:** Chroma is the vector store for Mimir. It persists to disk (no re-indexing on every run), runs locally (no external service), supports metadata filtering, and is the most commonly used local vector store in LangChain projects.

**Reasoning:** Established in earlier conversations. FAISS was the original recommendation but Chroma was confirmed as the better call due to persistence and metadata filtering support.

---

## Decision 13 — Versioning Strategy

**Decision:** Each version of Huginn (v1, v2, v3) is regenerated from scratch by Claude Code using a new masterplan. The previous version's codebase is never the starting point for the next version. Design documents — the interface contract, locked decisions, and architecture document — are the artifacts that carry intent across versions. Code is disposable.

**Reasoning:** Iterating on existing code requires Claude Code to simultaneously reason about what exists, what to change, and what to leave alone — a significantly harder task than building fresh, and a common source of subtle bugs and drift from the interface contract. Regenerating from scratch keeps each Claude Code session unambiguous: build this spec, nothing more. Matches the vertical slicing principle as originally designed — each version is a complete, independently demonstrable system, not a patch on the previous one.

**Rejected option:** Iterating on the v1 codebase for v2 and beyond. Rejected because it burdens Claude Code with legacy context, increases the risk of interface drift, and conflicts with the vertical slicing philosophy.

**Implications:** The interface contract document and masterplan must be complete and self-contained for each version — they are the only continuity between versions. Any capability carried forward from a previous version must be explicitly re-specified, not assumed.

---

## Decision 14 — Exception Schema Fields and Data Types

**Decision:** The exception schema contains the following fields with strict typing:

| Field | Type | Notes |
|---|---|---|
| `exception_id` | `UUID` | Guarantees uniqueness without additional logic |
| `trade_id` | `str` | Plain string — real-world trade IDs are not standardized |
| `type` | `Enum` | Constrained to approved taxonomy |
| `sub_type` | `Enum` | Scoped to parent type — see Decision 15 |
| `description` | `str` | Natural language description of the exception |
| `timestamp` | `datetime` | Enables date range queries in SQLite directly |
| `severity` | `Enum` (`low`, `medium`, `high`) | Metadata only in v1 — see Decision 16 |

**Reasoning:** Strong typing at the API boundary means invalid values are rejected before the agent ever sees them. `UUID` for `exception_id` eliminates collision bugs. `datetime` for timestamp enables SQLite date range queries without parsing. `trade_id` as plain string reflects real-world heterogeneity in trade ID formats.

**Rejected option:** Looser typing with strings for `exception_id`, `timestamp`, and `severity`. Rejected because it pushes validation burden downstream and makes the SQLite audit log harder to query.

---

## Decision 15 — Sub-Type Scoping

**Decision:** Valid sub_types are scoped to their parent type and enforced at the Pydantic layer via a model validator. `settlement_mismatch` maps exclusively to `price_mismatch`, `quantity_mismatch`, and `wrong_settlement_date`. Any sub_type submitted with a mismatched parent type is rejected at the API layer.

**Reasoning:** The relationship between type and sub_type is a real-world constraint, not just a v1 scoping decision. Encoding it in the schema means the data model reflects reality. When v2 adds new exception types with their own sub_types, the validator naturally enforces the new relationships without retrofitting. A flat unscoped enum would accumulate sub_types from multiple exception types with no enforcement of which belongs to which.

**Rejected option:** Flat unscoped enums — any sub_type valid with any type. Rejected because it fails to reflect the real-world relationship between types and sub_types and complicates v2 expansion.

---

## Decision 16 — Severity Field Treatment

**Decision:** The `severity` field (`low`, `medium`, `high`) is included in the exception schema in v1 but is treated as metadata only — it is captured and written to the audit log but the agent does not reason over it. In v2, severity becomes an explicit input to the LLM reasoning prompt.

**Reasoning:** Including the field in v1 costs nothing and means no schema change is required in v2. Keeping it metadata-only in v1 is consistent with the locked design decisions, which make no mention of severity as a reasoning input, and keeps the reasoning loop clean and debuggable. Acting on severity before the core pipeline is proven adds complexity without payoff.

**Rejected option:** Using severity as a reasoning input in v1. Rejected because the core reasoning pipeline should be validated before adding additional input signals, and because severity thresholds cannot be meaningfully calibrated without real data.

---

## Decision 17 — Audit Log Full Fidelity

**Decision:** The audit log record contains full fidelity — the complete original exception payload, all retrieved document chunks, the LLM's raw response before parsing, the confidence score, the reasoning trace, the resolution steps, the outcome, the escalation reason (if applicable), the triggered keyword (if applicable), the retrieved document ID, and all timestamps.

**Reasoning:** The audit log serves two purposes: compliance trail and v2 evaluation harness. Full fidelity satisfies both. For compliance, every decision is fully reconstructible from the log. For the evaluation harness, full fidelity means exceptions can be replayed against known good outcomes without any missing context. Partial records require retrofitting when the evaluation harness is built.

**Rejected option:** Decision-focused records omitting raw retrieved chunks and raw LLM response. Rejected because it is insufficient for debugging and makes the v2 evaluation harness impossible to build without schema migration.

---

## Decision 18 — Escalation Queue Record Format

**Decision:** Escalation queue records in `logs/escalation_queue.jsonl` are identical to audit log records — full fidelity, same schema.

**Reasoning:** The human reviewer acting on an escalation needs full context to make a resolution decision. A summary record would force a second lookup against the audit log. Identical records require no transformation logic inside the logger. One entry point, one record format, two destinations.

**Rejected option:** Subset of audit log fields focused on reviewer needs. Rejected because it requires a transformation step and forces reviewers to cross-reference the audit log for full context.

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

**Reasoning:** Echoing back `exception_id` and `timestamp` confirms exactly what was received without requiring a second API call. Makes the demo narrative cleaner — the submission response itself is meaningful, not just a bare acknowledgement. The extra fields cost nothing to produce.

**Rejected option:** Minimal response returning only `job_id` and `status`. Rejected because it provides no confirmation of what was received and weakens the demo narrative.

---

## Decision 20 — GET /exceptions/{job_id} Response Schema

**Decision:** `GET /exceptions/{job_id}` returns:
```json
{
  "job_id": "uuid",
  "exception_id": "uuid",
  "outcome": "auto_resolve | escalate",
  "confidence_score": "float",
  "reasoning_trace": "str",
  "resolution_steps": "str",
  "retrieved_document_id": "str | null",
  "escalation_reason": "str | null",
  "timestamp": "datetime"
}
```

**Reasoning:** The combination of `outcome`, `escalation_reason`, `confidence_score`, and `retrieved_document_id` fingerprints exactly which state machine path fired. `escalation_reason` is populated with either the keyword that triggered fast-exit or a low confidence explanation. `retrieved_document_id` is `null` on the fast-exit path — that null is meaningful, confirming Mimir was never called. Together these fields make the three-path state machine fully legible through the API surface alone, with no file inspection required.

**Rejected option:** Decision-focused response omitting `retrieved_document_id` and `escalation_reason`. Rejected because it makes the state machine paths indistinguishable from the API response alone.

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
      "confidence_score": "float",
      "reasoning_trace": "str",
      "escalation_reason": "str",
      "retrieved_document_id": "str | null",
      "timestamp": "datetime"
    }
  ]
}
```

**Reasoning:** The escalation queue is the human reviewer's inbox. A reviewer acting on an escalation needs full context — the original exception details, why the agent escalated, and the reasoning trace — without making a second API call. A summary list would force cross-referencing and slow the review process.

**Rejected option:** Lightweight summary list returning only `job_id`, `exception_id`, `escalation_reason`, and `timestamp`. Rejected because it forces a second lookup for the context needed to act on the escalation.

---

## Decision 22 — Mimir Retriever Function Signature

**Decision:** Mimir's single public function signature is:
```python
def retrieve(query: str, top_k: int = 3) -> list[dict]
```
Returns a list of dictionaries, each containing the chunk text, `document_id`, `sub_type`, and `similarity_score`. `top_k` defaults to 3 and is configurable.

**Reasoning:** Returning structured dicts rather than raw strings provides metadata — `document_id` is directly needed to populate `retrieved_document_id` in the audit log and API response. `similarity_score` gives the LLM additional signal about retrieval confidence. Chroma provides this metadata natively at no additional cost. `top_k` as a configurable parameter with a sensible default sets up v2 retrieval experimentation without requiring an interface change.

**Rejected option:** Simple `retrieve(query: str) -> list[str]` returning raw text only. Rejected because it discards metadata Chroma provides for free and forces `retrieved_document_id` to be populated through additional logic elsewhere.

---

## Decision 23 — Query Construction for Mimir

**Decision:** The agent constructs the Mimir query string by combining `sub_type` and `description`: `"{sub_type}: {description}"`. Example: `"price_mismatch: counterparty confirms different price than recorded"`.

**Reasoning:** Including `sub_type` in the query anchors the similarity search semantically. In v1 the knowledge base has exactly three documents, one per sub_type. The sub_type prefix makes it significantly harder for Mimir to retrieve the wrong document, which is important for proving the retrieval pipeline is working correctly rather than returning the right result by accident.

**Rejected option:** Passing the raw `description` field as the query string. Rejected because it relies on the description alone to differentiate between sub_types, which is less reliable and makes retrieval errors harder to diagnose.

---

## Decision 24 — Confidence Score Format and Escalation Threshold

**Decision:** The confidence score is a float between 0.0 and 1.0 produced by the LLM at runtime. A single hardcoded threshold of 0.75 applies to all sub_types in v1. Exceptions scoring below 0.75 are escalated; at or above are auto-resolved. Per sub_type thresholds replace the single threshold in v2.

**Reasoning:** A single threshold is honest about what v1 is — a demonstration that the pipeline works, not a calibrated production system. Per sub_type thresholds require real audit log data to calibrate meaningfully; applying arbitrary values per sub_type would add complexity without adding accuracy. The threshold is a single constant in the decision node — changing it to a dictionary lookup in v2 requires no interface changes.

**Rejected option:** Per sub_type hardcoded thresholds in v1. Rejected because the specific values would be arbitrary without data, and arbitrary precision is worse than honest simplicity.

---

## Decision 25 — LLM Prompt Inputs

**Decision:** The LLM reasoning prompt contains three inputs: the full exception payload, the retrieved SOP chunks from Mimir, and an explicit scoring rubric. The rubric defines what constitutes a high versus low confidence decision and how to weight the sub_type, description, and SOP content. The LLM is instructed to return structured JSON only.

**Reasoning:** An unguided LLM produces inconsistent confidence scores across runs because it has no rubric to anchor against. A scoring rubric makes scores more consistent and the reasoning trace more defensible. The rubric lives in `agent/nodes.py` as an implementation detail — the interface contract specifies that a rubric exists, not its exact wording. Prompt wording is iterated during the feedback loop phase.

**Rejected option:** Prompt containing only exception payload and retrieved chunks with no rubric. Rejected because it produces inconsistent confidence scores that are difficult to explain or defend.

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

**Reasoning:** These three fields are what the agent needs to make its decision and populate the audit log. Simpler output schemas produce more reliable structured output — the more fields specified, the more likely the LLM is to produce overlapping content or inconsistent values across fields. Deterministic decisions (escalate vs auto-resolve) are made in code using the confidence score as input, not by asking the LLM to recommend an action. This keeps the boundary between LLM reasoning and deterministic logic clean.

**Rejected option:** Richer output schema including `sop_relevance`, `confidence_rationale`, and `recommended_action`. Rejected because additional fields risk producing a `recommended_action` that conflicts with the threshold-based decision in code, creating an ambiguous authority conflict, and because the reasoning trace already captures the LLM's thinking in full.

---

## Decision 27 — Audit Logger Interface

**Decision:** The audit logger exposes a single public function:
```python
def log(event: dict) -> None
```
The logger handles all routing internally — writing to `audit.jsonl`, SQLite, and conditionally to `escalation_queue.jsonl` based on the event's `outcome` field. Callers do not need to know which destinations are written to.

**Reasoning:** Routing logic belongs inside the logger, not at the call site. A single entry point means callers cannot accidentally write to the wrong destination or forget to write to one. The logger remains a fully isolated component — nothing in the codebase needs to know its internals. Easy to unit test with a single mock target.

**Rejected option:** Separate `log_decision()` and `log_escalation()` functions. Rejected because it exposes routing logic to callers and creates the possibility of calling the wrong function or omitting a destination.

---

## Decision 28 — Claude API Failure Handling

**Decision:** If the Claude API call fails during the reasoning node, Huginn auto-escalates the exception. The audit log and escalation queue receive a full-fidelity record with `outcome = "escalate"`, `escalation_reason = "system_error: {error description}"`, and `confidence_score`, `reasoning_trace`, and `resolution_steps` set to null. No schema changes are required — all fields already support null on the fast-exit path.

**Reasoning:** An exception that entered the pipeline but received no decision is a worse outcome than a conservative escalation. Silent failures produce audit log gaps, which are a compliance problem, and leave real trade exceptions unresolved with no human reviewer aware of them. Auto-escalating on failure ensures every exception that enters the pipeline gets a disposition, the audit trail is complete, and the human reviewer inbox catches anything the system could not handle.

**Rejected option:** Return a structured error to the caller with no audit log entry written. Rejected because it creates an audit gap, puts the resolution burden on the caller, and does not guarantee the exception is reviewed by a human.

---

## Decision 29 — LLM Scoring Rubric (Implementation Detail)

**Decision:** The LLM reasoning prompt in `agent/nodes.py` uses the following scoring rubric, reproduced exactly as implemented:

```
You are a settlement exception triage specialist at a financial firm.
You have been given a trade exception and relevant Standard Operating Procedure (SOP) excerpts.
Your task is to evaluate the exception against the SOP and produce a structured JSON response.

SCORING RUBRIC:
- Confidence score reflects how clearly the SOP applies to this specific exception.
- Score 0.85–1.00: The SOP directly addresses this exact scenario. Resolution steps are unambiguous and complete.
- Score 0.75–0.84: The SOP is relevant and mostly applicable. Minor gaps exist but resolution path is clear.
- Score 0.50–0.74: The SOP is partially relevant. The scenario has elements not covered by the SOP, or the SOP provides conflicting guidance.
- Score 0.00–0.49: The SOP does not adequately cover this scenario. Human review is required.

Weighting factors:
- Sub-type match: Does the retrieved SOP cover this specific sub-type? (High weight)
- Description clarity: Is the exception description specific enough to act on? (Medium weight)
- SOP completeness: Does the SOP provide complete resolution steps for this scenario? (Medium weight)
- Presence of complicating factors not addressed in SOP: (Lowers score significantly)

IMPORTANT: You must respond with valid JSON only. No preamble, no explanation, no markdown.
Respond with exactly this structure:
{
  "confidence_score": <float between 0.0 and 1.0>,
  "reasoning_trace": "<step-by-step explanation of how you arrived at the score>",
  "resolution_steps": "<specific steps to resolve this exception per the SOP>"
}
```

**Reasoning:** Decision 25 specified that a scoring rubric would exist as an implementation detail in `agent/nodes.py`, to be iterated in v2 based on audit log data. This decision records the exact rubric text implemented in v1. The rubric is the primary artifact for v2 prompt engineering — without recording it now, v2 prompt work loses its baseline. Every confidence score in the v1 audit log was produced by this rubric against `claude-sonnet-4-6` (Decision 32).

**Rejected option:** Not recording the rubric text, treating it as an ephemeral implementation detail. Rejected because the rubric drives the confidence score distribution across all v1 audit log entries — understanding v1 scoring behavior and calibrating v2 thresholds requires knowing exactly what rubric produced it.

---

## Decision 30 — Chunking Strategy (Implementation Detail)

**Decision:** `scripts/build_index.py` chunks SOP documents using `RecursiveCharacterTextSplitter` with `chunk_size=500`, `chunk_overlap=50`, and `separators=["\n\n", "\n", " "]`.

**Reasoning:** `RecursiveCharacterTextSplitter` respects document structure by attempting to split on paragraph boundaries (`"\n\n"`) before line breaks (`"\n"`) before word boundaries (`" "`), producing chunks that are more semantically coherent than fixed-length splits. `chunk_size=500` is a v1 baseline appropriate for short SOP paragraphs — small enough that each chunk covers one procedural step, large enough that context is not fragmented. `chunk_overlap=50` prevents relevant sentences from being cut across two chunks where neither chunk has sufficient context alone.

**Rejected option:** Fixed-length character splitting with no overlap. Rejected because it ignores document structure and creates chunks that cut across sentence boundaries, reducing semantic coherence and retrieval accuracy.

---

## Decision 31 — Embedding Model (Implementation Detail)

**Decision:** `mimir/index.py` generates vector embeddings using `HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")`.

**Reasoning:** `all-mpnet-base-v2` is a high-quality general-purpose sentence embedding model that runs entirely locally with no API key required. Downloads approximately 420MB on first use, then caches. This was established in setup_notes.md during pre-build and confirmed unchanged during implementation. Running embeddings locally eliminates a runtime API dependency and avoids per-query embedding cost.

**Rejected option:** OpenAI `text-embedding-ada-002`. Rejected because it requires an API key and incurs per-token cost for both the one-time indexing step and every runtime retrieval query.

---

## Decision 32 — Claude API Model String (Implementation Detail)

**Decision:** `agent/nodes.py` uses `LLM_MODEL = "claude-sonnet-4-6"` as the Claude API model identifier, defined as a module-level constant.

**Reasoning:** `claude-sonnet-4-6` provides sufficient reasoning quality for v1's structured JSON output task at lower cost than Opus-tier models. Defining it as a module-level constant makes it visible at the top of the file without reading node implementations, and makes updating to a newer model a single-line change. The exact string must be recorded because model behavior affects confidence score distributions — v2 prompt engineering and calibration requires knowing which model produced the v1 audit log.

**Rejected option:** Model string hardcoded inline in the API call. Rejected because it makes the model identifier invisible at module level and requires reading the full node implementation to find it.

---

## Decision 33 — Claude API Error Handling (Implementation Detail)

**Decision:** `agent/nodes.py` catches all exceptions from the Claude API call with a bare `except Exception as e`. On any exception, the reason node returns `confidence_score=None`, `reasoning_trace=None`, `resolution_steps=None`, `llm_raw_response=None`, and `escalation_reason=f"system_error: {str(e)}"`. The decide node, seeing `confidence_score=None`, routes to escalation per Decision 28.

**Reasoning:** Decision 28 specified that any Claude API failure should auto-escalate. A bare `except Exception` is the broadest possible catch — it handles timeouts, network errors, authentication failures, rate limit errors, malformed responses, and any other exception type without requiring explicit handling of each Anthropic SDK exception class. The full error string is captured in `escalation_reason` and written to the audit log, preserving the failure cause for debugging. All failure modes produce the same outcome (escalation with `system_error` reason), so differentiating exception types adds complexity without changing behavior.

**Rejected option:** Catching specific Anthropic SDK exception types (e.g., `anthropic.APIConnectionError`, `anthropic.RateLimitError`). Rejected because exhaustively handling every SDK exception class adds code complexity without changing the outcome — all failure modes produce escalation with a `system_error` reason.

---

## Decision 34 — Pydantic Validation Error Format (Implementation Detail)

**Decision:** `api/main.py` does not define a custom exception handler for Pydantic `ValidationError`. FastAPI's default handler converts `RequestValidationError` to HTTP 422 with the standard response structure:
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error description",
      "type": "error_type"
    }
  ]
}
```

**Reasoning:** FastAPI's default 422 behavior matches the interface contract specification exactly. Adding a custom handler would require maintaining the same output structure manually — more code, same result. The default handler is well-tested, familiar to FastAPI API consumers, and the interface contract already documented this exact format.

**Rejected option:** Custom exception handler returning a simplified flat error message. Rejected because the structured `loc`/`msg`/`type` format is more informative for API consumers debugging validation failures, and the default behavior already satisfied the spec.

---

## Mandatory Escalation Keywords (V1)

The following keywords trigger an immediate escalation fast-exit regardless of confidence score:
- `sanctions`
- `AML`
- `regulatory hold`

This list is explicitly defined and exhaustive for v1. Additional keywords are added in v2.

---

## Exception Type Taxonomy (V1)

Valid exception types in v1:
- `settlement_mismatch`

All other values are rejected at the API layer with a structured validation error.

---

## Settlement Mismatch Sub-Types (V1)

Valid sub-types handled by the agent:
- `price_mismatch`
- `quantity_mismatch`
- `wrong_settlement_date`

Each has a corresponding synthetic SOP document in the knowledge base.

---

## What V1 Is Not

The following are explicitly out of scope for v1 and deferred to later versions:

- Multiple exception types beyond settlement mismatches (v2)
- Real FINRA/SEC regulatory documents in the knowledge base (v2)
- Iterative retrieval in Mimir (v2)
- Principled confidence scoring replacing hardcoded thresholds (v2)
- Per sub_type escalation thresholds (v2)
- Severity as a reasoning input (v2)
- Expanded mandatory escalation keyword list (v2)
- Frontend of any kind (v3)
- Asynchronous queue processing (v3)
- Evaluation harness with golden datasets (v3)
- Real notification system for escalations (v3)
- Multi-agent or distributed processing (v3)
