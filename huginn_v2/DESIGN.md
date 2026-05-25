# Huginn v2 — Architecture and Design

**Audience:** Technical recruiters and hiring managers who want architectural depth.

---

## System Overview

Huginn is a FastAPI service that accepts flagged financial trade exceptions over HTTP, classifies them, and decides whether to resolve them automatically or escalate them to a human reviewer. When an exception arrives, it is validated against a strict schema — only settlement_mismatch exceptions with a valid sub-type are accepted. Inside the agent, two fast exits fire before any expensive operations: exceptions with an invalid type return a structured error, and exceptions whose description contains a mandatory escalation keyword (sanctions, AML, regulatory hold, buy-in, sell-out) are immediately escalated without touching the knowledge base or the LLM. All other exceptions follow the standard path: the agent queries Mimir — a Chroma-backed RAG retrieval layer — for the most relevant chunks from a real regulatory document knowledge base (SEC Rules 15c6-1 and 15c6-2, FINRA Rules 11100, 11710, 11810, and 11820). Mimir performs two-pass retrieval: a semantic search pass followed by a targeted cross-reference resolution pass that fetches additional chunks from any regulatory rules explicitly referenced in the first-pass results. The combined chunks are passed along with the exception and a regulatory reasoning scoring rubric to the Claude API, which returns a confidence score used to decide whether to auto-resolve (≥ 0.75) or escalate (< 0.75). Every decision — on every path — is written in full fidelity to logs/audit.jsonl, a local SQLite database, and, if escalated, to logs/escalation_queue.jsonl. Three FastAPI endpoints expose the full system: POST /exceptions to submit an exception and receive a job ID, GET /exceptions/{job_id} to retrieve the full decision, and GET /escalations to inspect the human reviewer's inbox.

---

## The Five Components

### Component 1 — Exception Schema (`models/exception.py`)

**Responsibility:** Define and validate every incoming trade exception before it enters the agent.

The schema is the foundation. Every other component either consumes it or produces records that reference it. `TradeException` is a Pydantic model with strict typing: `UUID` for `exception_id`, `datetime` for `timestamp`, string enums for `type`, `sub_type`, and `severity`. A model validator enforces sub-type scoping — `price_mismatch`, `quantity_mismatch`, and `wrong_settlement_date` are only valid when `type` is `settlement_mismatch`. All fields are required; there are no defaults.

**What it does not do:** No helper methods. No custom JSON serializers. No default values. The validator exists as a separate function — not collapsed into the enum definition — so v3 can add new type/sub-type pairs by extending the map, not modifying the enum.

---

### Component 2 — API Layer (`api/main.py`)

**Responsibility:** The only entry point to the system. Validates, routes, and responds.

Four endpoints:
- `POST /exceptions` — validates the request body as `TradeException`, runs the agent synchronously, returns the full result immediately
- `GET /exceptions/{job_id}` — reads from the SQLite audit log and returns the full stored decision
- `GET /escalations` — returns all escalated entries from the SQLite audit log
- `GET /health` — service liveness check

Pydantic validation errors surface as FastAPI's default HTTP 422 response. No custom exception handler.

**What it does not do:** No authentication. No rate limiting. No background task processing — v2 is synchronous only. The fake-async two-endpoint pattern (`POST` returns job ID, `GET` retrieves result) was preserved in the interface but not needed in v2 — `POST` returns the full result immediately because synchronous processing makes the result available before the response is sent.

---

### Component 3 — LangGraph Agent (`agent/`)

**Responsibility:** Orchestrate the three-path execution flow from classification through decision to logging.

The agent is implemented as a `StateGraph` with a single shared state object (`AgentState`) that flows through every node. Nodes are pure functions: `(AgentState) -> dict` (partial state update). The graph compiles once at import time. Routing functions (`_route_after_classify`, `_route_after_decide`) handle the conditional branching — they read state fields and return routing keys but produce no state updates themselves.

Five nodes implement the logic: `classify`, `retrieve`, `reason`, `decide`, `escalate_fast_exit`. All paths terminate at `log_result`.

**What it does not do:** No error handling at the graph level — error handling lives inside individual nodes. No node logic in `graph.py` — only graph structure and edge routing.

---

### Component 4 — Mimir Retriever (`mimir/`)

**Responsibility:** Retrieve the most relevant regulatory document chunks for a given query. Nothing else.

Mimir's only public function is `retrieve(query: str, top_k: int = 3) -> list[dict]`. Two-pass retrieval is entirely internal. `mimir/index.py` holds shared constants (`PERSIST_DIR`, `EMBEDDING_MODEL`) used by both the indexer script and the retriever — they must stay synchronized or the retriever loads a mismatched index.

The knowledge base is built once by `scripts/build_index.py`. Six PDFs are extracted, split into section-aware chunks using a regex parser with a false-split filter and a 200-character minimum length, and indexed into Chroma with `section_id` and `document_id` metadata.

**What it does not do:** No escalation logic. No confidence scoring. No knowledge of trade operations. No public functions other than `retrieve()`. Two-pass retrieval complexity is invisible through the public interface — the agent receives a flat list of chunk dicts regardless of how many passes occurred.

---

### Component 5 — Audit Logger (`logger/audit.py`)

**Responsibility:** Write the full event dict to all applicable destinations for every decision.

The logger's only public function is `log(event: dict) -> None`. It always writes to `logs/audit.jsonl` and `logs/audit.db` (SQLite). If `outcome == "escalate"`, it additionally writes to `logs/escalation_queue.jsonl`. Routing is internal — the caller does not specify destinations.

The SQLite schema stores individual queryable columns plus a `full_event_json` column containing the complete event dict as a JSON string. This ensures no data is lost regardless of what fields v3 adds — a schema migration is never required to access new event fields.

**What it does not do:** No separate `log_decision()` and `log_escalation()` functions — a single interface handles all cases. No filtering or transformation of the event dict.

---

## The Three-Path State Machine

The three-path structure is not an implementation detail. It is a deliberate architectural decision: the three paths have different regulatory stakes, different performance characteristics, and different audit trail requirements. Merging them would obscure those differences in conditional logic.

### Path 1 — Invalid Type Exit

**Where it fires:** API layer (Pydantic validation). The agent never receives an invalid type.

**Why it is a separate path:** Pydantic catches schema violations before the agent is instantiated. This is not a graph path — it is a validation layer that prevents the graph from running on malformed input.

### Path 2 — Mandatory Escalation Fast-Exit

**Where it fires:** `classify` node. If a keyword is detected in the description, the graph routes to `escalate_fast_exit` then `log_result`.

**Why it is a separate path:** Exceptions containing `sanctions`, `AML`, `regulatory hold`, `buy-in`, or `sell-out` have crossed from normal triage territory into legally sensitive territory. No confidence score from a retrieval-and-reasoning pipeline is sufficient to auto-resolve them. The fast-exit path ensures they never touch Mimir or the LLM — it is structurally impossible for the standard path to run on these exceptions.

### Path 3 — Standard Path

**Where it fires:** All exceptions that pass validation and contain no mandatory keywords.

`classify` → `retrieve` → `reason` → `decide` → `log_result`

The retrieve node calls Mimir. The reason node calls the Claude API with the retrieved chunks and the regulatory reasoning rubric. The decide node compares the confidence score against `ESCALATION_THRESHOLD = 0.75`. Both `auto_resolve` and `escalate` outcomes route to `log_result`.

### Component Interaction Diagram

```
HTTP Request
    ↓
[API Layer] — validates TradeException schema
    ↓
[Agent — classify node] — detects type and keywords
    ↓
    ├── keyword found → [Agent — escalate_fast_exit node] → [Logger]
    └── no keyword → [Mimir — retrieve()]
                          ↓
                     Pass 1: semantic search (top_k=3)
                          ↓
                     Cross-reference detection
                          ↓
                     Pass 2: targeted retrieval by document_id (top_k_cross_ref=2)
                          ↓
                     Deduplicated chunk list returned
                          ↓
                     [Agent — reason node] → [Agent — decide node]
                                                    ↓
                                         ┌──────────┴──────────┐
                                    auto_resolve            escalate
                                         └──────────┬──────────┘
                                                    ↓
                                               [Logger]
                                                    ↓
                                         audit.jsonl + SQLite
                                         + escalation_queue.jsonl (if escalated)
```

---

## Key Design Decisions

These are the eight decisions most worth understanding. The full decision log — with complete reasoning and all rejected alternatives — is in [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md).

### Decision 8 — Real Regulatory Documents Over Synthetic SOPs

V2's knowledge base replaces synthetic SOPs with six real regulatory documents from FINRA and the SEC. The documents are indexed in full rather than curated sections. A retriever that returns noise from an irrelevant section produces a low confidence score and escalates — the safe outcome. A retriever that silently excludes a relevant section produces a confidently wrong answer — the worse outcome. Curating requires predicting relevance in advance; full-text indexing does not.

### Decisions 30 & 49 — Section-Aware Chunking with False-Split Filter

Regulatory documents are divided into logical units by their authors — lettered subsections are the natural semantic boundaries. V2 splits on those boundaries rather than arbitrary character counts. The `_is_real_section()` filter rejects regex matches that are mid-sentence parentheticals rather than true section headers, by checking whether the character following the `(x)` marker is uppercase. Without this filter, FINRA-11810 produced a 292-character spurious fragment that would have passed the 200-char minimum threshold and been indexed as a real section.

### Decision 37 — Two-Pass Iterative Retrieval with Cross-Reference Resolution

Regulatory documents cross-reference each other heavily. A chunk saying "the remedy is provided for by Rules 11810 and 11820" without those rules' content leaves the LLM with incomplete regulatory context. After Pass 1 semantic search returns chunks, Pass 2 scans them for explicit rule references and fetches targeted chunks from each referenced rule using `document_id` metadata filtering. Pass 2 is deterministic — targeted by known rule identifier, not a second free semantic search.

### Decision 29 — Four-Factor Regulatory Reasoning Rubric

The LLM scoring rubric is built around how legal text actually works: (1) condition match — do the facts satisfy the rule's triggering conditions? (2) obligation clarity — does the rule specify a clear required action? (3) exception applicability — do any carve-outs apply? (4) cross-reference resolution — were all referenced rules retrieved? This replaced a v1 rubric calibrated for synthetic SOP documents with step-by-step procedural guidance. The two are not interchangeable.

### Decision 43 — Mandatory Escalation Keywords Expanded in V2

`buy-in` and `sell-out` were added to the three v1 keywords (`sanctions`, `AML`, `regulatory hold`). Both terms signal that a counterparty relationship has broken down to the point of formal FINRA Rule 11810/11820 close-out remedy — a stage at which automated confidence scoring is inappropriate regardless of retrieval quality.

### Decision 17 — Audit Log Full Fidelity

The audit log records the complete event: every retrieved chunk with `section_id` and `retrieved_via`, the raw LLM response before JSON parsing, the confidence score, the reasoning trace, the outcome, and the triggered keyword if applicable. The `full_event_json` column stores the entire event dict as JSON. This is compliance by design — every decision is fully reconstructible without needing to re-run the exception.

### Decision 28 — Claude API Failure Handling: Fail Fast and Escalate

If the Claude API call fails for any reason — network error, malformed response, JSON parse failure — the reason node returns null values for all LLM fields and sets `escalation_reason = "system_error: {error}"`. The exception escalates. No retries. The rationale: a system that silently retries and eventually produces a result has hidden its failure mode. A system that escalates on failure makes the failure visible and auditable.

### Decision 13 — Versioning Strategy: Code Is Disposable

Each version of Huginn is regenerated from scratch by Claude Code using a new masterplan. The v1 codebase was not the starting point for v2 — the design artifacts were. The interface contract, locked decisions, and methodology carried intent across versions; the code did not. V3 will be regenerated the same way. This decision is what makes the design artifacts the primary deliverable.

---

## What V2 Deliberately Excludes

The following are explicitly out of scope for v2 and deferred:

- Multiple exception types beyond settlement mismatches
- Per sub-type escalation thresholds (requires v2 audit log data for calibration)
- Severity field as a reasoning input (requires v2 audit log data for correlation analysis)
- Expanded mandatory escalation keyword list
- Frontend of any kind
- Asynchronous queue processing
- Evaluation harness with golden datasets
- Real notification system for escalations
- Multi-agent or distributed processing

This is not an incomplete list — it is a scope discipline record. V2's signal is settlement mismatch handled correctly against real regulations. V3 expands from there once that is proven.
