# Huginn v2 — Code Walkthrough

Nine files. Browse the directory above to open any walkthrough.

```mermaid
flowchart TD
    REQ(["HTTP Request"]):::io --> API["api/main.py\nHTTP entry point"]:::entry

    API -->|validates| MDL["models/exception.py\nInput schema"]:::schema
    API -->|invokes| GRP["agent/graph.py\nNode wiring · routing"]:::agent

    GRP -.->|defines| STA["agent/state.py\nShared pipeline state"]:::schema
    GRP -->|executes| NOD["agent/nodes.py\nclassify · retrieve · reason\ndecide · escalate · log_result"]:::agent
    NOD -.->|reads & writes| STA

    NOD -->|retrieval query| RET["mimir/retriever.py\nTwo-pass retrieval"]:::mimir
    NOD --> AUD["logger/audit.py\nAudit writer"]:::agent

    RET -.->|imports| IDX["mimir/index.py\nPERSIST_DIR · EMBEDDING_MODEL"]:::mimir
    RET --> CDB[("ChromaDB\nvector index")]:::store

    BLD["scripts/build_index.py\nOffline index build"]:::build
    BLD -.->|imports| IDX
    BLD -->|populates| CDB

    AUD --> RESP(["HTTP Response"]):::io

    classDef entry fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#d1fae5
    classDef agent fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#dbeafe
    classDef schema fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e0e7ff
    classDef mimir fill:#2e1065,stroke:#a78bfa,stroke-width:2px,color:#ede9fe
    classDef store fill:#0c1445,stroke:#60a5fa,stroke-width:2px,color:#bfdbfe
    classDef build fill:#431407,stroke:#fb923c,stroke-width:2px,color:#ffedd5
    classDef io fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#d1fae5
```

Solid arrows are runtime execution flow. Dotted arrows are import/structural dependencies. `scripts/build_index.py` runs offline once before the server starts.
