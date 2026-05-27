# Huginn

Huginn is a LangGraph-based AI agent that classifies financial trade exceptions and decides whether to auto-resolve them or escalate to a human reviewer. It was built design-first: the interface contract, architecture, and locked decision log all preceded the implementation. That sequence is the primary signal this repository is meant to convey.

---

## The Project Arc

| Version | What it is | What it advances |
|---|---|---|
| [**Huginn v1**](huginn_v1/README.md) | Full agentic pipeline — FastAPI, LangGraph, ChromaDB, Claude API, audit log | Proof of methodology. Three-path state machine, human-in-the-loop escalation, full-fidelity audit trail. Knowledge base is synthetic SOPs. |
| [**Huginn v2**](huginn_v2/README.md) | Rebuilt from a new masterplan against the same interface contract | Reasoning architecture upgrade. Synthetic SOPs replaced with six real FINRA and SEC regulatory documents. Scoring rubric rebuilt around the four cognitive tasks required to apply legal text. |
| [**Huginn v2 Demo**](huginn_v2_demo/README.md) | Interactive single-page demo — no local setup required | Live Claude API call via Cloudflare Worker. Five pre-built scenarios covering all three execution paths. Animated LangGraph state diagram. **[Open demo →](https://rlin25.github.io/HuginnsMessage/)** |

---

## Architecture

Huginn v2 control flow — from API ingress through the LangGraph state machine to the audit layer.

```mermaid
flowchart TD
    API(["POST /exceptions"]):::api --> VAL{Pydantic\nValidation}:::decision
    VAL -->|"422"| ERR(["Unprocessable Entity"]):::error
    VAL -->|valid| CLS

    CLS["classify\nKeyword scan on description"]:::proc
    CLS -->|"sanctions · AML\nbuy-in · sell-out"| FE["escalate_fast_exit\nRegulatory keyword bypass"]:::orange
    CLS -->|no keyword| RET

    subgraph MIMIR["Mimir  ·  ChromaDB"]
        RET["retrieve\nQuery knowledge base"]:::proc
        DB[("6 FINRA / SEC docs\nPass 1 · semantic · k=3\nPass 2 · cross-ref · k=2")]:::store
        RET -->|query| DB
    end

    subgraph CLAUDE_API["Claude API  ·  claude-sonnet-4-6"]
        RSN["reason\nFour-factor scoring rubric"]:::proc
        MODEL["Condition Match  ·  Obligation Clarity\nException Applicability  ·  Cross-ref Resolution"]:::llm
        RSN -->|prompt + chunks| MODEL
    end

    DB --> RSN
    MODEL --> DEC{"decide\nthreshold: 0.75"}:::decision

    DEC -->|"score ≥ 0.75"| AUTO["auto_resolve"]:::green
    DEC -->|"score < 0.75"| ESC["escalate"]:::orange

    FE & AUTO & ESC --> LOG["log_result\nAssembles AgentState"]:::proc

    subgraph AUDIT["Audit Layer"]
        direction LR
        SQLDB[("SQLite")]:::store
        AJ["audit.jsonl"]:::file
        EQ["escalation_queue.jsonl"]:::file
    end

    LOG --> AUDIT
    LOG --> RESP(["HTTP Response\njob_id · outcome · confidence_score"]):::api

    classDef proc fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#dbeafe
    classDef decision fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e0e7ff
    classDef green fill:#14532d,stroke:#4ade80,stroke-width:2px,color:#dcfce7
    classDef orange fill:#431407,stroke:#fb923c,stroke-width:2px,color:#ffedd5
    classDef error fill:#450a0a,stroke:#f87171,stroke-width:2px,color:#fee2e2
    classDef store fill:#0c1445,stroke:#60a5fa,stroke-width:2px,color:#bfdbfe
    classDef llm fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef api fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#d1fae5
    classDef file fill:#1c1c2e,stroke:#4b5563,stroke-width:1px,color:#9ca3af
```

---

## The Methodology

Every version followed the same six-phase sequence: domain learning, Socratic design, interface contract, masterplan, implementation, feedback loop. Phases one through four happened before Claude Code wrote a line of code. Claude acted as a design partner — pressing on reasoning, surfacing gaps, formalizing decisions. Every architectural judgment was the developer's.

The design artifacts — interface contracts, locked decision logs, masterplans — are version-stable. The code is intentionally disposable. V2 was regenerated from scratch against an updated masterplan. The documents carry intent across versions. The code does not.

The `prompts/` directory in each sub-project contains the structured prompts that governed the AI collaboration at each phase.
