# Huginn — System Design

---

## System Overview

Huginn is a FastAPI service that accepts flagged financial trade exceptions over HTTP, classifies them, and decides whether to resolve them automatically or escalate them to a human reviewer. When an exception arrives, it is first validated against a strict schema — only `settlement_mismatch` exceptions with a valid sub-type are accepted. Inside the agent, two fast exits fire before any expensive operations: exceptions with an invalid type return a structured error, and exceptions whose description contains a mandatory escalation keyword (`sanctions`, `AML`, `regulatory hold`) are immediately escalated without touching the knowledge base or the LLM. All other exceptions follow the standard path: the agent queries Mimir — a Chroma-backed RAG retrieval layer — for the most relevant SOP document chunks, passes those chunks along with the exception and a scoring rubric to the Claude API, and uses the returned confidence score to decide whether to auto-resolve (≥ 0.75) or escalate (< 0.75). Every decision — on every path — is written in full fidelity to `logs/audit.jsonl`, a local SQLite database, and, if escalated, to `logs/escalation_queue.jsonl`. Three FastAPI endpoints expose the full system: `POST /exceptions` to submit an exception and receive a job ID, `GET /exceptions/{job_id}` to retrieve the full decision, and `GET /escalations` to inspect the human reviewer's inbox. The auto-generated `/docs` page at `http://127.0.0.1:8000/docs` is the v1 demo surface.

---

## The Five Components

### 1. API Layer (`api/main.py`)

The front door to the system. Validates all incoming exceptions against the Pydantic schema before anything else runs. Enforces the exception type taxonomy at the boundary — all non-`settlement_mismatch` types are rejected here with a structured validation error before reaching the agent. Issues job IDs and exposes the three endpoints.

**What it does not do:** The API layer does not make any decisions about exceptions. It validates, routes, and returns. All reasoning belongs to the agent.

### 2. The Agent (`agent/`)

Huginn's reasoning brain. Receives a validated exception from the API layer and orchestrates the full triage process as a three-path state machine. Calls Mimir when information retrieval is needed, evaluates confidence against the threshold, applies escalation rules, and produces a structured decision. The Claude API performs all LLM reasoning at runtime — there is no hardcoded rule-based scoring.

Each node is a pure function: state in, updated state out. This design makes every node independently testable without running the full graph.

**What it does not do:** The agent does not write to the audit log directly. It calls the logger at the terminal node. It does not validate schema — that happens at the API layer.

### 3. Mimir (`mimir/`)

The knowledge library. Exposes a single public function that accepts a query string and returns the most relevant document chunks from the knowledge base. Knows nothing about exceptions, decisions, or escalation logic — it only answers retrieval queries.

Backed by a Chroma vector store that persists to disk, requiring no re-indexing on restart. In v1, retrieval is single-pass only.

**What it does not do:** Mimir does not interpret results, make decisions, or know what Huginn will do with what it returns. It retrieves. Nothing more.

### 4. The Knowledge Base (`knowledge_base/`)

Mimir's filing cabinet. Three synthetic SOP documents — one per settlement mismatch sub-type — written for a fictional financial firm. A one-time preprocessing script chunks these documents, converts them to vector embeddings, and loads them into the Chroma index.

The synthetic nature of the knowledge base is disclosed here explicitly. Real FINRA/SEC regulatory documents are added in v2.

**What it does not do:** The knowledge base is inert. It is searched by Mimir; it does not initiate anything.

### 5. The Audit Logger (`logger/audit.py`)

The paper trail. A dedicated, isolated module with a single public function. Writes every decision to two destinations simultaneously: `logs/audit.jsonl` (human-readable, append-only flat file) and a local SQLite database (queryable by exception type, outcome, confidence score, and date range). Escalated exceptions are additionally written to `logs/escalation_queue.jsonl`, the human reviewer's inbox.

**What it does not do:** The logger does not decide where to write. Routing is internal — callers pass a structured event dict and the logger handles the rest. Nothing in the codebase touches the logger's internals directly.

---

## The Three-Path State Machine

Huginn's agent is a directed graph with three distinct execution paths. The branching structure exists for reasons that are each individually defensible.

### Path 1 — Invalid Type Exit

Fires at the API layer, not inside the agent. Pydantic validation rejects any exception whose `type` field is not in the approved taxonomy (`settlement_mismatch` in v1). A structured 422 error is returned. The agent never receives an invalid type. Nothing else runs — Mimir is not called, no audit log entry is written.

**Why it exists as a distinct path:** The agent is not the right place to handle schema violations. Enforcing the taxonomy at the API boundary means invalid inputs are caught as early as possible, before any resources are consumed. The Pydantic enum on the `type` field enforces this in three lines of code.

### Path 2 — Mandatory Escalation Fast-Exit

Fires immediately after classification if a trigger keyword (`sanctions`, `AML`, `regulatory hold`) is detected in the exception description. Skips Mimir retrieval and LLM reasoning entirely. Routes directly to escalation. The audit log records the specific keyword that triggered it. `retrieved_document_id` is null in the API response — confirming Mimir was never called.

**Why it exists as a distinct path:** Mandatory escalation keywords are properties of the exception itself, not of the SOP documents. No retrieval is needed to recognize a sanctions flag. Running a Mimir query and an LLM call before escalating an exception that contains "sanctions" would incur unnecessary cost and produce a misleading audit trail — a log entry that references a retrieved document that played no role in the decision. The fast-exit is also more defensible from a compliance perspective: fewer moving parts between a red-flag term and an escalation decision.

### Path 3 — Standard Path

Followed when the exception passes classification and contains no mandatory escalation keywords. Full sequence: classify → retrieve (Mimir) → reason (Claude API) → decide → log. Ends with a single branch point: auto-resolve if confidence ≥ 0.75, escalate if it does not.

```
Incoming HTTP Request
        ↓
   [FastAPI]
   - Validates exception schema
   - Enforces exception type taxonomy
   - Issues job ID
        ↓
   [LangGraph Agent]
        ↓
   Classification Node
        ↓
   ┌────────────────────────────────────────┐
   │                                        │
   ▼                                        ▼
Invalid Type?                   Mandatory Escalation Keyword?
(sanctions, AML,                (price/quantity/date mismatch
 regulatory hold)                with no keyword flags)
   │                                        │
   ▼                                        ▼
[ERROR EXIT]              ┌─────────────────┴──────────────────┐
Return structured         │                                    │
validation error.    Keyword found                      No keyword found
Nothing else runs.        │                                    │
                          ▼                                    ▼
                   [FAST-EXIT]                         [STANDARD PATH]
                   Skip Mimir.                    Retrieve → Reason → Decide
                   Skip LLM.                               │
                   Route directly                          ▼
                   to escalation.              Confidence ≥ threshold?
                          │                       │              │
                          │                      YES             NO
                          │                       │              │
                          │                       ▼              ▼
                          │               [AUTO-RESOLVE]   [ESCALATE]
                          │                       │              │
                          └───────────────────────┴──────────────┘
                                                  │
                                                  ▼
                                         [Audit Logger]
                                    - Writes to audit.jsonl
                                    - Writes to SQLite
                                    - If escalated: writes to
                                      escalation_queue.jsonl
```

---

## Key Design Decisions

The following decisions are the most interview-worthy from the full set of 28 locked decisions. Full documentation including all rejected alternatives is in [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md).

### LLM Reasoning at Runtime vs. Rules Engine (Decision 4)

**Decision:** The Claude API reasons over the retrieved SOP at runtime to produce the confidence score, reasoning trace, and resolution steps. This is non-negotiable across all versions.

**Why:** The entire point of Huginn as a portfolio piece is demonstrating agentic AI reasoning. Hardcoded rule-based scoring with no LLM in the loop produces a rules engine with a vector store attached, not an AI agent. The LLM reasoning step is what makes the system interesting and what makes the decisions defensible to a compliance reviewer.

**Rejected:** Rule-based scoring with no runtime LLM call.

### Keyword Scan Pre-Retrieval (Decision 10)

**Decision:** The mandatory escalation keyword scan runs immediately after classification, before Mimir retrieval.

**Why:** Mandatory escalation keywords are properties of the exception itself, not of the SOP documents. No retrieval is needed. Running Mimir before the keyword scan incurs unnecessary cost and produces a misleading audit trail — a log entry that references a retrieved document that played no role in the decision.

**Rejected:** Keyword scan after retrieval.

### Audit Log Full Fidelity (Decision 17)

**Decision:** Every audit log record contains: the complete original exception, all retrieved document chunks, the LLM's raw response before parsing, the confidence score, the reasoning trace, the resolution steps, the outcome, the escalation reason, the triggered keyword, the retrieved document ID, and all timestamps.

**Why:** The audit log serves two purposes: compliance trail and v2 evaluation harness. Full fidelity satisfies both. For compliance, every decision is fully reconstructible. For the evaluation harness, full fidelity means exceptions can be replayed against known good outcomes without any missing context.

**Rejected:** Decision-focused records omitting raw retrieved chunks and raw LLM response.

### Single Logger Interface (Decision 27)

**Decision:** The audit logger exposes one function: `log(event: dict) -> None`. Routing to all destinations — `audit.jsonl`, SQLite, and conditionally `escalation_queue.jsonl` — is handled internally.

**Why:** Routing logic belongs inside the logger, not at call sites. A single entry point means callers cannot accidentally write to the wrong destination or forget to write to one. The logger remains a fully isolated, testable component with a single mock target.

**Rejected:** Separate `log_decision()` and `log_escalation()` functions.

### Fake Async Job ID Pattern (Decisions 7, 19)

**Decision:** `POST /exceptions` returns a job ID immediately; the caller retrieves the result via `GET /exceptions/{job_id}`. In v1, processing is synchronous — the result is always ready by the time the ID is returned. The interface is designed for async so v2 can slot in a real queue without changing the API contract.

**Why:** The job ID pattern makes the API forward-compatible. V2 async processing requires no changes to the client-facing interface. Three lines of code in v1 prevent a breaking interface change in v2.

**Rejected:** `POST /exceptions` blocking until processing completes and returning the full result directly.

### Chroma Over FAISS (Decision 12)

**Decision:** Chroma is the vector store for Mimir. It persists to disk, runs locally with no external service, and supports metadata filtering.

**Why:** FAISS was the original recommendation. Chroma replaced it because FAISS does not persist to disk — the index must be rebuilt on every restart — and does not support metadata filtering natively. Chroma provides both at no additional complexity cost.

**Rejected:** FAISS.

### Code is Disposable — Versioning Strategy (Decision 13)

**Decision:** Each version of Huginn is regenerated from scratch by Claude Code using a new masterplan. The previous version's codebase is never the starting point for the next version. Design documents carry intent across versions. Code does not.

**Why:** Iterating on existing code requires Claude Code to simultaneously reason about what exists, what to change, and what to leave alone — a harder task with more opportunities for subtle drift from the interface contract. Regenerating from scratch keeps each implementation session unambiguous: build this spec, nothing more.

**Rejected:** Iterating on the v1 codebase for v2 and beyond.

### Claude API Failure Handling (Decision 28)

**Decision:** If the Claude API call fails during the reasoning node, Huginn auto-escalates the exception. The audit log receives a full-fidelity record with `outcome = "escalate"`, `escalation_reason = "system_error: {error}"`, and null values for confidence score, reasoning trace, and resolution steps.

**Why:** An exception that entered the pipeline but received no decision is a worse outcome than a conservative escalation. Silent failures produce audit log gaps — a compliance problem — and leave real trade exceptions unresolved with no human reviewer aware of them. Auto-escalating on failure ensures every exception that enters the pipeline gets a disposition.

**Rejected:** Return a structured error to the caller with no audit log entry written.

---

## What V1 Deliberately Excludes

The following are explicitly out of scope. This is evidence of scope discipline, not incompleteness.

**Deferred to v2:**
- Multiple exception types beyond settlement mismatches
- Real FINRA/SEC regulatory documents in the knowledge base
- Iterative retrieval in Mimir
- Principled confidence scoring replacing hardcoded thresholds
- Per sub-type escalation thresholds
- Severity as a reasoning input
- Expanded mandatory escalation keyword list

**Deferred to v3:**
- Frontend of any kind
- Asynchronous queue processing
- Evaluation harness with golden datasets
- Real notification system for escalations
- Multi-agent or distributed processing

The v1 demo surface is FastAPI's auto-generated `/docs` interface. This is a deliberate choice: the `/docs` page exposes the API contract directly — request schema, response schema, and all three endpoints — which is a better signal to technical reviewers than a barebones HTML wrapper.
