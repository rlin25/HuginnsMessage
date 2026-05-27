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
    API["POST /exceptions"] --> VAL{"Pydantic\nValidation"}
    VAL -- "invalid type → 422" --> ERR["Unprocessable Entity"]
    VAL -- valid --> CLS
    CLS["classify\nKeyword scan on description\nSets: exception_type · triggered_keyword"]
    CLS -- "keyword detected\nsanctions · AML · buy-in · sell-out" --> FE
    CLS -- no keyword --> RET
    RET["retrieve\nSets: retrieved_chunks\nretrieved_document_ids"]
    RET -- query --> DB
    DB -- ranked chunks --> RSN
    subgraph MIMIR["Mimir — ChromaDB"]
        DB[("6 FINRA / SEC rules\nPass 1: semantic · k=3\nPass 2: cross-ref · k=2")]
    end
    RSN["reason\nSets: confidence_score · reasoning_trace\nresolution_steps · llm_raw_response"]
    RSN -- prompt + chunks --> CLAUDE
    CLAUDE -- scored JSON --> DEC
    subgraph CLAUDE_API["Claude API"]
        CLAUDE["claude-sonnet-4-6  ·  max_tokens=2048\nFour-factor rubric:\nCondition Match · Obligation Clarity\nException Applicability · Cross-ref Resolution"]
    end
    DEC["decide\nThreshold: 0.75\nSets: outcome · escalation_reason"]
    DEC -- "score ≥ 0.75" --> AUTO["auto_resolve"]
    DEC -- "score < 0.75 / LLM error" --> ESC["escalate"]
    FE["escalate_fast_exit\nSets: outcome = escalate · escalation_reason"]
    FE --> LOG
    AUTO --> LOG
    ESC --> LOG
    LOG["log_result\nAssembles full AgentState\ninto audit event"]
    subgraph AUDIT["Audit Layer"]
        direction LR
        SQLDB[("SQLite\naudit_log")]
        AJ["audit.jsonl"]
        EQ["escalation_queue.jsonl"]
    end
    LOG --> AUDIT
    LOG --> RESP["HTTP Response\njob_id · outcome · confidence_score\nreasoning_trace · resolution_steps"]
    style ERR fill:#922b21,color:#fff
    style AUTO fill:#1e8449,color:#fff
    style ESC fill:#935116,color:#fff
    style FE fill:#935116,color:#fff
```

---

## The Methodology

Every version followed the same six-phase sequence: domain learning, Socratic design, interface contract, masterplan, implementation, feedback loop. Phases one through four happened before Claude Code wrote a line of code. Claude acted as a design partner — pressing on reasoning, surfacing gaps, formalizing decisions. Every architectural judgment was the developer's.

The design artifacts — interface contracts, locked decision logs, masterplans — are version-stable. The code is intentionally disposable. V2 was regenerated from scratch against an updated masterplan. The documents carry intent across versions. The code does not.

The `prompts/` directory in each sub-project contains the structured prompts that governed the AI collaboration at each phase.
