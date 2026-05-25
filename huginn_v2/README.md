# Huginn v2

**Design principles outlast code. This project was built to prove that.**

The architecture was designed before a single line of code was written. The interface contract, locked decision log, and state machine specification all preceded the implementation. When Claude Code wrote the code, it was building against a stable specification — not discovering requirements as it went. That sequence is the thesis.

Huginn is a portfolio project demonstrating agentic workflow design, RAG pipeline architecture, and human-in-the-loop system design for a financial operations context. The primary signal this project is meant to convey is not the tech stack — it is the methodology. In the age of AI, code is disposable. Design principles are not.

---

## What Huginn Does

Financial firms generate thousands of trade exceptions every day — flagged mismatches where a buyer's records and a seller's records disagree at settlement. Left unresolved, they become regulatory and operational problems. Huginn accepts these exceptions over HTTP and makes a decision: resolve automatically, or escalate to a human reviewer.

When an exception arrives, two fast checks fire before anything expensive happens. If the exception type is invalid, it is rejected immediately. If the description contains a sensitive term — sanctions, AML, regulatory hold, buy-in, sell-out — it is escalated immediately, without consulting the knowledge base or calling the AI. Both checks protect the system from doing expensive reasoning on cases where the answer is already known.

For everything else, Huginn retrieves the most relevant regulatory document chunks from a knowledge base of six real FINRA and SEC rules, passes them to Claude along with a four-factor reasoning rubric, and receives a confidence score in return. Scores at or above 0.75 produce an auto-resolve outcome. Scores below 0.75 escalate to the human reviewer queue. Either way, the full decision — every retrieved chunk, the raw LLM response, the reasoning trace, the outcome, and why — is written to the audit log.

---

## Why the Design Matters

**The three-path state machine** is not an implementation convenience. It is a deliberate architectural choice rooted in financial operations. Invalid types, mandatory escalations, and standard-path exceptions have completely different regulatory stakes. They should not share the same logic path. The graph's branching structure makes that separation visible and auditable — not buried in conditional logic.

**The audit trail** records full fidelity on every decision: every retrieved document chunk with its section ID, the raw LLM response before parsing, the confidence score, the reasoning trace, the outcome, and the reason. This is not for debugging. It is for compliance. Every automated decision in a regulated environment must be reconstructible. The audit log is designed from the start to satisfy that requirement — `full_event_json` captures the complete event dict so no data is lost regardless of what fields v3 adds.

**The human-in-the-loop escalation pattern** exists because the design team made a deliberate choice not to trust any automated system with every case. When the system lacks confidence, or when the exception is too sensitive to auto-resolve, it goes to the escalation queue — the human reviewer's inbox. That is not a fallback. It is designed behavior.

**V2's specific advance is a reasoning architecture upgrade, not a tech stack upgrade.** V1's knowledge base was synthetic SOPs. V2 replaces them with six real regulatory documents sourced from FINRA and the SEC, and replaces the v1 scoring rubric with one built around the cognitive tasks required to apply legal text: condition match, obligation clarity, exception applicability, and cross-reference resolution. These four factors reflect how a compliance analyst actually reads a regulation. V2 teaches the LLM to reason that way.

---

## How It Was Built

The project followed a six-phase methodology: domain learning, Socratic design, interface contract, masterplan, implementation, feedback loop.

Phases 1 through 4 happened in Claude's web interface. Claude acted as a Socratic design partner — asking structured questions, challenging weak reasoning, surfacing gaps in specifications, and formalizing decisions. Every major architectural decision was argued to completion with rejected alternatives documented alongside the accepted choice. All design judgment belonged to the developer. Claude pressed on the reasoning; the developer made the calls.

This is stated transparently because it is the point, not a caveat. Using AI as a Socratic partner to stress-test design decisions is a skill. The design artifacts produced in Phases 1 through 4 — the interface contract, the locked decision log, the masterplan — are the evidence that the thinking happened before the code. The prompts that governed the AI collaboration are in the `prompts/` directory.

The implementation happened in Claude Code, building against the complete interface contract. The Phase 7 feedback loop reconciled all design documents against the implemented codebase. Every discrepancy was corrected or recorded as a known issue with an explicit deferral note. The design artifacts are now stable. The code is intentionally disposable — v3 will be regenerated from scratch using an updated masterplan.

---

## Companion Documents

- **[DESIGN.md](DESIGN.md)** — Architecture, state machine, and the three execution paths. Start here if you want to understand how the system thinks.
- **[INTERFACE_CONTRACT.md](INTERFACE_CONTRACT.md)** — Every component's inputs, outputs, and data types. The stable contract the code was built against.
- **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)** — Every major decision with its reasoning and rejected alternatives documented. The clearest signal of how design tradeoffs were evaluated.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Agent orchestration | LangGraph |
| LLM | Claude API (Anthropic) — `claude-sonnet-4-6` |
| Vector store | ChromaDB |
| Embeddings | `sentence-transformers/all-mpnet-base-v2` |
| PDF extraction | pypdf |
| Schema validation | Pydantic v2 |
| Audit log | JSONL flat file + SQLite |
| Server | Uvicorn |
| Language | Python 3.10 |

---

## Setup and Demo

### Prerequisites

- Python 3.10+
- `ANTHROPIC_API_KEY` (Anthropic API access required for standard-path processing)
- Six regulatory PDFs in `knowledge_base/raw/` (see table below)

### Setup

```bash
# From huginn_v2/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (parent of `huginn_v2/`) with your API key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

**Place these six PDFs in `knowledge_base/raw/`:**

| Filename | Source |
|---|---|
| `FINRA-11100.pdf` | FINRA Rulebook — Rule 11100 |
| `FINRA-11710.pdf` | FINRA Rulebook — Rule 11710 |
| `FINRA-11810.pdf` | FINRA Rulebook — Rule 11810 |
| `FINRA-11820.pdf` | FINRA Rulebook — Rule 11820 |
| `SEC-15c6-1.pdf` | eCFR — 17 CFR § 240.15c6-1 |
| `SEC-15c6-2.pdf` | eCFR — 17 CFR § 240.15c6-2 |

```bash
# Build the knowledge base index — inspect the chunk log printed to stdout before proceeding
python scripts/build_index.py

# Run unit tests (no API key required)
python -m pytest tests/test_models.py tests/test_retriever.py -v

# Start the server
uvicorn api.main:app --reload
```

API docs at `http://127.0.0.1:8000/docs`.

### Demo — Three Calls That Tell the Full Story

**1. Standard path — submit an exception and receive the full result:**
```bash
curl -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "550e8400-e29b-41d4-a716-446655440000",
    "trade_id": "TRD-DEMO-001",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Counterparty confirms 142.50, we show 141.75 for 500 shares settled 2026-05-01.",
    "timestamp": "2026-05-01T09:30:00",
    "severity": "high"
  }'
```
Returns the full result immediately: outcome, confidence score, reasoning trace, resolution steps, and the list of regulatory document IDs that were retrieved.

**2. Result retrieval — look up a previous decision by job ID:**
```bash
curl http://127.0.0.1:8000/exceptions/{job_id}
```
Reads from the SQLite audit log. Persistent across server restarts — the decision is always retrievable regardless of when the server was last restarted.

**3. Escalation queue — inspect the human reviewer's inbox:**
```bash
curl http://127.0.0.1:8000/escalations
```
Returns all escalated exceptions with full context. To populate it before running this call, submit an exception containing `"sanctions"` in the description — it will fast-exit to the escalation queue without calling Mimir or the LLM.
