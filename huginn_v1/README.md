# Huginn

Most AI engineering portfolios demonstrate that you can wire together a framework. This one demonstrates something different: that design comes first, and that the quality of a system is determined before a single line of code is written.

Huginn was built design-first. The interface contract, architecture document, and all 28 locked design decisions preceded the implementation. Claude was used as a Socratic design partner throughout — to stress-test decisions, surface assumptions, and formalize specifications. Every architectural judgment belonged to the developer. The result is a system where every choice has a documented reason and every rejected alternative has a documented reason for its rejection.

That methodology is the primary signal this project is meant to convey. The code is demonstrably secondary. By design.

---

## What Huginn Does

Financial firms generate trade exceptions constantly — flagged discrepancies between internal records and counterparty records at the moment a trade is meant to settle. A price is wrong. A quantity doesn't match. A settlement date has shifted. These exceptions require human investigation, but the volume means not all of them can go to a human reviewer. Someone — or something — has to decide which ones can be handled automatically and which ones require human eyes.

Huginn is that decision-maker. When a trade exception arrives, Huginn classifies it, looks up the relevant Standard Operating Procedure, reasons over it using the Claude API, and produces a confidence score. If the score is high enough, the exception is auto-resolved and the decision is logged. If it isn't — or if the exception contains a red-flag term like "sanctions" or "AML" — the exception is escalated to a human reviewer and written to the escalation queue.

Every decision Huginn makes, on every path, is written in full to an audit log: what the exception was, which SOP was retrieved, what the Claude API said, what confidence score resulted, and why the final outcome was what it was. Nothing is opaque.

---

## Why the Design Matters

Three architectural choices are worth naming explicitly.

**The three-path state machine.** Huginn's agent is not a linear pipeline — it branches at two points before any expensive operations run. Exceptions with mandatory red-flag terms are routed directly to escalation without touching the knowledge base or the LLM. This isn't just an optimization; it's more defensible from a compliance perspective. Fewer moving parts between a sanctions flag and an escalation decision means fewer opportunities for something to go wrong. The state machine makes this explicit rather than burying it in conditional logic.

**The audit trail design.** Every log entry captures full fidelity: the complete original exception, all retrieved document chunks, the LLM's raw response before parsing, the confidence score, the reasoning trace, and the escalation reason if applicable. This is deliberately more than needed for v1. The full fidelity design means every decision is reconstructible without contacting the developer, satisfying compliance requirements and enabling the v2 evaluation harness without requiring schema migration.

**Human-in-the-loop escalation.** Escalated exceptions don't just set a flag — they write a complete record to a physically separate escalation queue that represents the human reviewer's inbox. A dedicated `GET /escalations` endpoint makes this queue inspectable via API with no file parsing required. The escalation pathway is a first-class feature, not a fallback.

---

## How It Was Built

Huginn was built through a six-phase methodology, all of it before Claude Code wrote a line of implementation:

1. **Domain learning** — building vocabulary in trade settlement, exception types, and financial operations compliance before making any design decisions.
2. **Socratic design** — resolving every major architectural question through structured challenge-and-response until all alternatives were documented and all reasoning was explicit. The result was a locked decisions document with 28 entries.
3. **Interface contract** — specifying every component's inputs, outputs, and data types before any component was built. This document became the integration source of truth that prevented interface conflicts during implementation.
4. **Masterplan and atomic subplans** — breaking the build into six independently testable stages, each with an explicit gate the implementation must pass before the next stage begins.
5. **Implementation** — Claude Code built each subplan against the interface contract, with no subplan starting until the previous gate was confirmed passing.
6. **Feedback loop** — implementation discoveries fed back into the design documents to keep the design artifacts and the codebase synchronized.

The AI collaboration in this project is stated transparently and without apology. Claude served as a Socratic partner during design — asking questions, challenging weak reasoning, presenting alternatives, and formalizing specifications. Every design judgment was the developer's. The methodology is itself a demonstration of AI fluency: knowing what to delegate, when to push back, and how to keep architectural ownership while moving faster.

The design documents are intentionally version-stable. The code is intentionally disposable. When v2 is built, Claude Code will regenerate the codebase from a new masterplan referencing the same interface contract. The design artifacts carry intent across versions. The code does not.

---

## Companion Documents

Three documents accompany this README for readers who want more depth:

- **[DESIGN.md](DESIGN.md)** — architecture, state machine, and the three execution paths. Start here if you want to understand how the system thinks.
- **[INTERFACE_CONTRACT.md](INTERFACE_CONTRACT.md)** — every component's inputs, outputs, and data types. The stable contract the code was built against, written before the code existed.
- **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)** — every major decision with its reasoning and rejected alternatives documented. The clearest signal of how design tradeoffs were evaluated.

The `prompts/` folder contains the design methodology and documentation generation prompts used to build this project. See [prompts/README.md](prompts/README.md).

---

## Tech Stack

| Library | Role |
|---|---|
| **FastAPI** | API layer — three endpoints, auto-generated `/docs` demo surface |
| **Pydantic** | Schema validation — exception type enum enforced at API boundary |
| **LangGraph** | Agent orchestration — three-path state machine as an inspectable graph |
| **Anthropic SDK** | LLM reasoning — Claude API called at runtime for confidence scoring and resolution steps |
| **Chroma** | Vector store — persists to disk, runs locally, supports metadata filtering |
| **sentence-transformers** | Embedding model — converts SOP text to vectors, no API key required |
| **LangChain** | Document preprocessing only — text splitting during knowledge base indexing |
| **sqlite3** | Audit log database — Python standard library, queryable without external services |
| **pytest** | Testing — unit tests on individual nodes, integration tests on the full API |
| **python-dotenv** | Environment config — loads Claude API key from `.env` |

---

## Setup and Demo

**Prerequisites:** Python 3.11+, a Claude API key.

```bash
# 1. Clone and install dependencies
git clone git@github.com:rlin25/HuginnsMessage.git
cd HuginnsMessage/huginn_v1
pip install -r requirements.txt

# 2. Set your API key
echo "ANTHROPIC_API_KEY=your_key_here" > ../.env

# 3. Build the knowledge base index (one-time)
python scripts/build_index.py

# 4. Start the server
uvicorn api.main:app --reload
```

The FastAPI auto-generated interface is available at `http://127.0.0.1:8000/docs`.

**The three API calls that tell the full story:**

```bash
# Submit a trade exception
curl -s -X POST http://127.0.0.1:8000/exceptions \
  -H "Content-Type: application/json" \
  -d '{
    "exception_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "trade_id": "TRD-20260523-001",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Counterparty confirms different price at settlement.",
    "timestamp": "2026-05-23T09:00:00Z",
    "severity": "high"
  }'
# Returns: {"job_id": "...", "status": "received", "exception_id": "...", "timestamp": "..."}

# Retrieve the decision
curl -s http://127.0.0.1:8000/exceptions/{job_id}
# Returns: outcome, confidence_score, reasoning_trace, resolution_steps, retrieved_document_id

# Inspect the human reviewer inbox
curl -s http://127.0.0.1:8000/escalations
# Returns: all escalated exceptions with full context
```

**To run the test suite:**

```bash
cd huginn_v1
pytest tests/ -v
```

**Knowledge base disclosure:** The SOP documents in `knowledge_base/raw/` are synthetic documents written for a fictional financial firm (Arcturus Capital Management). They are designed to give the retrieval pipeline a meaningful job to do while keeping debugging unambiguous. Real FINRA/SEC regulatory documents are added in v2.
