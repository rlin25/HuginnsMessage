# Prompt: Generate Walkthrough Directory

**Purpose:** Generate a `walkthrough/` directory of annotated design rationale documents for every source file in the project.  
**When to use:** After all subplans are implemented and the codebase is complete.  
**Reusability:** Lightly edit the source file list and reference document names for each new project.

---

## Prompt

Create a `walkthrough/` directory in the project root. For each source file in the project, create a corresponding markdown file explaining it to someone who understands the overall system design but is reading the implementation for the first time.

Each walkthrough file should cover:

1. **Purpose** — what this file does and why it exists as a separate component. Reference the specific design decisions that created it.
2. **Relationships** — what it imports from, what imports it, and what it deliberately does not touch.
3. **Decision rationale** — for non-obvious implementation choices, explain why the code is written that way rather than what it is doing. Reference design decision numbers where relevant.
4. **What it does not do** — responsibilities explicitly excluded from this file and where those responsibilities live instead.
5. **V2 touch points** — which parts of this file are intentionally minimal in v1 and what will change.

Do not explain syntax. Do not describe what lines of code do — describe why they exist. If a section of code is self-explanatory, skip it.

Name each walkthrough file to match its source file: `walkthrough/agent_nodes.md` for `agent/nodes.py`, `walkthrough/logger_audit.md` for `logger/audit.py`, and so on.

Source files to cover:
- `models/exception.py`
- `mimir/retriever.py`
- `mimir/index.py`
- `logger/audit.py`
- `agent/state.py`
- `agent/nodes.py`
- `agent/graph.py`
- `api/main.py`
- `scripts/build_index.py`

Reference documents available in the project root: `interface_contract.md`, `design_decisions.md`, `architecture.md`.

---

## Notes

- Run this after Subplan 6 is complete — the walkthrough is only useful once the source files exist.
- The goal is decision rationale, not documentation. If a walkthrough file reads like a comment block, it's too shallow.
- Update the source file list and reference document names when reusing on a new project.
