# Prompt: Rewrite Glossary

**Purpose:** Rewrite the design-phase glossary as a post-implementation reference organized for two audiences: non-technical and technical recruiters reading the repo, and the developer returning to the codebase.  
**When to use:** After all subplans are implemented and the codebase is complete.  
**Reusability:** Adapt the three-part structure and source file list for each new project.

---

## Prompt

Rewrite `glossary.md` from scratch. The original was written during the design phase and does not reflect the implemented codebase. The new glossary serves two audiences: recruiters (technical and non-technical) reading the repository, and the developer returning to the codebase after time away.

Organize the glossary into three parts:

---

### Part 1 — Domain and System Overview

Define all financial domain terms and high-level system concepts. This section should be readable by a non-technical recruiter with no prior knowledge of trade operations or compliance. Assume the reader has already read the README.

Include:
- Financial domain terms (settlement, trade exception, counterparty, escalation, compliance, etc.)
- High-level system concepts (what Huginn does, what Mimir is, what the audit log is for)
- Any acronyms used in the codebase or documentation

Do not reference specific files, functions, or implementation details in this section.

---

### Part 2 — State Machine and Execution Paths

Define the agent's logic layer. This section bridges the domain overview and the implementation reference — a recruiter reading the architecture diagram or the README's flow description will encounter these terms before opening any source file.

Include:
- The three execution paths and when each fires (invalid type exit, mandatory escalation fast-exit, standard path)
- Every node in the state machine (`classify`, `retrieve`, `reason`, `decide`, `escalate`, `auto_resolve`)
- `AgentState` and what it carries across nodes
- Confidence scoring and the threshold decision
- Mandatory escalation keywords and their role

---

### Part 3 — Implementation Reference

File-by-file breakdown of implementation-specific terms. Organize by source file. For terms that span multiple files, define them at their source file and note where else they appear.

Cover these files in order:
- `models/exception.py`
- `mimir/index.py`
- `mimir/retriever.py`
- `logger/audit.py`
- `agent/state.py`
- `agent/nodes.py`
- `agent/graph.py`
- `api/main.py`
- `scripts/build_index.py`

For each file, define only the terms that are non-obvious to a developer reading it for the first time. Skip terms that are self-explanatory from the code.

---

## Constraints

- Do not carry over definitions from the original glossary without verifying them against the implementation.
- Do not define terms that are fully explained in the README — reference the README instead.
- Write Part 1 for a non-technical reader. Write Parts 2 and 3 for a technical reader.
- Output the full glossary as a single `glossary.md` file.

Reference documents: `architecture.md`, `design_decisions.md`, `interface_contract.md`.
