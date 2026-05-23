# Huginn v1 — Architecture Document

**Status:** Design locked. Phase 3 — Interface Contract Document.
**Last updated:** May 2026
**Source of truth:** `huginn_v1_design_decisions.md` (Decisions 1–12)

---

## Project Summary

Huginn is an AI agent that receives flagged financial trade exceptions, classifies them, retrieves relevant resolution procedures from Mimir (its internal RAG knowledge base), reasons over them using the Claude API, and decides whether to auto-resolve the exception or escalate it to a human reviewer. Every decision is recorded in a structured audit log. V1 handles settlement mismatches only and is demonstrated entirely through a FastAPI interface.

---

## The Five Components

### 1. API Layer (FastAPI)
The front door to the system. Exposes exactly three endpoints, validates all incoming exceptions against the Pydantic schema before anything else runs, and returns structured responses. Nothing in the system is reachable except through this layer. Enforces the exception type taxonomy at the boundary — all non-`settlement_mismatch` types are rejected here with a structured validation error before reaching the agent.

**Endpoints:**
- `POST /exceptions` — accepts an exception payload, returns a job ID
- `GET /exceptions/{job_id}` — retrieves the full result for a given job ID
- `GET /escalations` — returns the current escalation queue as a JSON list

### 2. The Agent (LangGraph)
Huginn's reasoning brain. Receives a validated exception from the API layer and orchestrates the full triage process as a three-path state machine. Calls Mimir when information retrieval is needed, evaluates confidence, applies escalation rules, produces a structured decision, and emits a structured log event at every node transition. The Claude API performs all LLM reasoning at runtime — there is no hardcoded rule-based scoring.

### 3. The Retrieval Layer (Mimir)
The knowledge library. Exposes a single clean function that accepts a query string and returns the most relevant document chunks from the knowledge base. Knows nothing about exceptions, decisions, or escalation logic — it only answers retrieval queries. Backed by a Chroma vector store that persists to disk, requiring no re-indexing on restart. In v1, retrieval is single-pass only.

### 4. The Knowledge Base
Mimir's filing cabinet. A folder of three to four synthetic SOP documents — one per settlement mismatch sub-type — written for a fictional financial firm. A one-time preprocessing script chunks these documents, converts them to vector embeddings, and loads them into the Chroma index. The synthetic nature of the knowledge base is disclosed in the project README. Real FINRA/SEC regulatory documents are added in v2.

### 5. The Audit Logger
The paper trail. A dedicated, isolated module that every other component calls to emit structured log events. Writes every decision to two destinations simultaneously: `logs/audit.jsonl` (human-readable, append-only flat file for compliance inspection) and a local SQLite database (queryable by exception type, outcome, confidence score, and date range). Escalated exceptions are additionally written to `logs/escalation_queue.jsonl`, which represents the human reviewer's inbox. Nothing in the codebase touches the logger's internals directly — it is a fully isolated component.

---

## Component Communication

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

**Mimir is called only on the Standard Path, after the keyword scan clears.** It is never called on the invalid type exit or the mandatory escalation fast-exit.

---

## Folder Structure

```
huginn/
├── api/
│   └── main.py                  # FastAPI endpoints and routing
├── agent/
│   ├── graph.py                 # LangGraph state machine definition
│   ├── nodes.py                 # Individual node logic (one function per node)
│   └── state.py                 # Shared state object definition
├── mimir/
│   ├── retriever.py             # Single query function — the only public interface
│   └── index.py                 # Chroma loading and initialization logic
├── knowledge_base/
│   ├── raw/                     # Source SOP documents (.txt or .pdf)
│   └── processed/               # Chroma persistent index (auto-generated)
├── logger/
│   └── audit.py                 # Structured logger — writes JSONL and SQLite
├── models/
│   └── exception.py             # Pydantic exception schema and type enums
├── scripts/
│   └── build_index.py           # One-time preprocessing — chunk, embed, load to Chroma
├── tests/
│   ├── test_agent.py            # Agent node unit tests
│   ├── test_mimir.py            # Retriever unit tests
│   └── test_api.py              # API integration tests
├── logs/
│   ├── audit.jsonl              # Append-only human-readable compliance log
│   ├── audit.db                 # SQLite database for queryable log history
│   └── escalation_queue.jsonl   # Human reviewer inbox
├── .env                         # API keys (Claude API key)
├── requirements.txt
└── README.md                    # Discloses synthetic knowledge base
```

---

## Library Stack

| Library | Role | Justification |
|---|---|---|
| **FastAPI** | API layer | Python-native, minimal boilerplate, auto-generates `/docs` demo interface, industry standard for Python AI services |
| **Pydantic** | Schema validation | Native to FastAPI, enforces exception type enum at the API boundary, three lines of code for full type safety |
| **LangGraph** | Agent orchestration | Models the three-path state machine explicitly as a graph — branching logic is inspectable and debuggable, not hidden in callbacks |
| **Anthropic SDK** | LLM reasoning | Claude API called at runtime for confidence scoring, reasoning trace, and resolution steps — the core of what makes Huginn an AI agent |
| **LangChain** | Document preprocessing only | Used minimally for its document loaders and text splitters during knowledge base indexing — not used in the runtime agent path |
| **Chroma** | Vector store | Persists to disk (no re-indexing on restart), runs locally with no external service, supports metadata filtering, most common local vector store in LangChain projects. Supersedes FAISS. |
| **sentence-transformers** | Embedding model | Converts text to vector embeddings for Chroma — runs entirely locally with no API key required |
| **PyMuPDF** | PDF parsing | Extracts text from SOP documents during the one-time preprocessing step |
| **sqlite3** | Audit log database | Built into Python's standard library — zero additional dependency, queryable by exception type/outcome/confidence/date, sets up v2 evaluation harness naturally |
| **pytest** | Testing | Standard Python testing framework — used for unit tests on individual nodes and integration tests on the full API |
| **python-dotenv** | Environment config | Loads Claude API key from `.env` without hardcoding credentials |

---

## Build Sequence

Each step must be fully working and independently tested before the next step begins. Never wire two components together before both work in isolation.

### Step 1 — Exception Schema and Models
Define the Pydantic exception model in `models/exception.py`. Lock the exception type enum (`settlement_mismatch` only), the sub-type enum (`price_mismatch`, `quantity_mismatch`, `wrong_settlement_date`), the severity tiers, and all required fields. Write a set of sample exception JSON fixtures that you will reuse as test inputs throughout every subsequent step. This is the foundation everything else is built on.

### Step 2 — Knowledge Base and Mimir
Write the three to four synthetic SOP documents in `knowledge_base/raw/`. Build and run `scripts/build_index.py` to chunk, embed, and load them into the Chroma index. Then build `mimir/retriever.py` and test it in complete isolation — at the end of this step you must be able to call a single Python function with a query string and receive relevant document chunks back. Nothing else in the system exists yet.

### Step 3 — Audit Logger
Build `logger/audit.py` in complete isolation. It must accept a structured dictionary and write it correctly to both `logs/audit.jsonl` and the SQLite database. Additionally test the escalation path — escalated entries must also appear in `logs/escalation_queue.jsonl`. This step should take two to three hours at most, but doing it now means every subsequent component can log from day one.

### Step 4 — LangGraph Agent
Build the state machine in `agent/graph.py` and `agent/nodes.py`. Implement and test nodes one at a time in this order: classify → keyword scan → Mimir retrieval → LLM reasoning → confidence evaluation → escalate/resolve → log. Wire the three-path branching structure only after each individual node passes its unit tests. Every node must be a pure function — state in, updated state out — which makes them independently testable without running the full graph.

### Step 5 — FastAPI Layer
Wrap the working agent in `api/main.py`. Implement the three endpoints. Add the job ID pattern — `POST /exceptions` returns a job ID synchronously in v1, `GET /exceptions/{job_id}` returns the completed result, `GET /escalations` reads from the escalation queue. Add error handling for malformed requests. At this point the agent already works — this step is purely plumbing.

### Step 6 — Integration Tests
Write end-to-end tests in `tests/test_api.py` that submit sample exceptions through the full HTTP stack and assert on: response structure, audit log entry structure, SQLite record presence, and escalation queue state. Use the sample exception fixtures created in Step 1. Run one test case for each of the three state machine paths — standard resolution, mandatory escalation fast-exit, and invalid type rejection.

---

## Exception Type Taxonomy (V1)

Valid exception types:
- `settlement_mismatch`

All other values are rejected at the API layer with a structured Pydantic validation error.

## Settlement Mismatch Sub-Types (V1)

- `price_mismatch`
- `quantity_mismatch`
- `wrong_settlement_date`

Each has a corresponding synthetic SOP document in the knowledge base.

## Mandatory Escalation Keywords (V1)

The following keywords trigger an immediate fast-exit to escalation, bypassing Mimir and the LLM entirely:
- `sanctions`
- `AML`
- `regulatory hold`

This list is exhaustive for v1. Additional keywords are added in v2.

---

## What V1 Is Not

The following are explicitly out of scope and deferred:

**V2:**
- Multiple exception types beyond settlement mismatches
- Real FINRA/SEC regulatory documents in the knowledge base
- Iterative retrieval in Mimir
- Principled confidence scoring replacing hardcoded thresholds
- Expanded mandatory escalation keyword list

**V3:**
- Frontend of any kind
- Asynchronous queue processing
- Evaluation harness with golden datasets
- Real notification system for escalations
- Multi-agent or distributed processing

---

## The One Rule

**Every component must be independently testable before it touches any other component.**

If you find yourself unable to test a component in isolation, that is a signal that your separation of concerns has broken down and you must refactor before proceeding. This discipline is the difference between a portfolio project that holds up under interview questioning and one that only works when nothing goes wrong.
