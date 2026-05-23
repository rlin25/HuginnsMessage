# Huginn v1 — Masterplan

**Phase:** 4 — Masterplan + Atomic Subplans
**Status:** Ready for Claude Code implementation
**Last updated:** May 2026
**Source of truth:** `huginn_v1_interface_contract.md`, `huginn_v1_design_decisions.md` (Decisions 1–28)

---

## The Completed System — Plain English Description

Huginn is a FastAPI service that accepts flagged financial trade exceptions over HTTP, classifies them, and decides whether to resolve them automatically or escalate them to a human reviewer. When an exception arrives, it is first validated against a strict schema — only `settlement_mismatch` exceptions with a valid sub-type are accepted. Inside the agent, two fast exits fire before any expensive operations: exceptions with an invalid type return a structured error, and exceptions whose description contains a mandatory escalation keyword (`sanctions`, `AML`, `regulatory hold`) are immediately escalated without touching the knowledge base or the LLM. All other exceptions follow the standard path: the agent queries Mimir — a Chroma-backed RAG retrieval layer — for the most relevant SOP document chunks, passes those chunks along with the exception and a scoring rubric to the Claude API, and uses the returned confidence score to decide whether to auto-resolve (≥ 0.75) or escalate (< 0.75). Every decision — on every path — is written in full fidelity to `logs/audit.jsonl`, a local SQLite database, and, if escalated, to `logs/escalation_queue.jsonl`. Three FastAPI endpoints expose the full system: `POST /exceptions` to submit an exception and receive a job ID, `GET /exceptions/{job_id}` to retrieve the full decision, and `GET /escalations` to inspect the human reviewer's inbox. The auto-generated `/docs` page at `http://127.0.0.1:8000/docs` is the v1 demo surface.

---

## Atomic Subplans

The build is divided into six atomic subplans, executed strictly in order. No subplan begins until the previous subplan's gate is confirmed passing.

| Subplan | Component | Gate |
|---|---|---|
| [Subplan 1](huginn_v1_subplan_1.md) | Exception Schema | Pydantic model instantiates and validates correctly for all test cases |
| [Subplan 2](huginn_v1_subplan_2.md) | Knowledge Base + Mimir | `retrieve()` returns relevant chunks for all three sub-types |
| [Subplan 3](huginn_v1_subplan_3.md) | Audit Logger | Log entries appear correctly in `.jsonl`, SQLite, and escalation queue |
| [Subplan 4](huginn_v1_subplan_4.md) | LangGraph Agent | All three state machine paths produce correct structured output |
| [Subplan 5](huginn_v1_subplan_5.md) | FastAPI Layer | All three endpoints return correct responses against the running agent |
| [Subplan 6](huginn_v1_subplan_6.md) | Integration Tests | End-to-end tests pass for all three paths; audit log and SQLite state verified |

---

## Folder Structure

```
huginn/
├── api/
│   └── main.py
├── agent/
│   ├── graph.py
│   ├── nodes.py
│   └── state.py
├── mimir/
│   ├── retriever.py
│   └── index.py
├── knowledge_base/
│   ├── raw/
│   └── processed/
├── logger/
│   └── audit.py
├── models/
│   └── exception.py
├── scripts/
│   └── build_index.py
├── tests/
│   ├── test_agent.py
│   ├── test_mimir.py
│   └── test_api.py
├── logs/
├── .env
├── requirements.txt
└── README.md
```

---

## Library Stack

| Library | Role |
|---|---|
| FastAPI | API layer |
| Pydantic | Schema validation |
| LangGraph | Agent orchestration |
| Anthropic SDK | LLM reasoning (Claude API) |
| LangChain | Document preprocessing only |
| Chroma (`langchain-chroma`) | Vector store |
| sentence-transformers | Local embeddings |
| PyMuPDF | PDF parsing during preprocessing |
| sqlite3 | Audit log database (stdlib) |
| pytest | Unit and integration tests |
| python-dotenv | API key loading |
| uvicorn | ASGI server for FastAPI |

Install command:
```bash
pip install langchain langchain-anthropic langchain-huggingface langchain-chroma langgraph fastapi uvicorn python-dotenv sentence-transformers pymupdf pytest
```

---

## Hard-Coded Values (V1)

These values are explicitly defined for v1. They are listed here so they are easy to locate and update.

| Value | Location | V1 Setting |
|---|---|---|
| Escalation threshold | `agent/nodes.py` — decide node | `0.75` |
| Mandatory escalation keywords | `agent/nodes.py` — classify node | `["sanctions", "AML", "regulatory hold"]` |
| Valid exception types | `models/exception.py` — ExceptionType enum | `["settlement_mismatch"]` |
| Valid sub-types | `models/exception.py` — SettlementMismatchSubType enum | `["price_mismatch", "quantity_mismatch", "wrong_settlement_date"]` |
| Mimir top_k default | `mimir/retriever.py` | `3` |
| LLM model | `agent/nodes.py` — reason node | `claude-sonnet-4-20250514` |
| Audit log paths | `logger/audit.py` | `logs/audit.jsonl`, `logs/audit.db`, `logs/escalation_queue.jsonl` |

---

## Environment Variables

`.env` file must contain:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Loaded via `python-dotenv` in any module that calls the Claude API.

---

## The One Rule

**Every component must be independently testable before it touches any other component.**

If you find yourself unable to test a component in isolation, that is a signal that separation of concerns has broken down. Refactor before proceeding.
