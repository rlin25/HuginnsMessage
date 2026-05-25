# Prompt: README and Documentation Generation
**Phase:** Post-implementation documentation
**Produced by:** Rubber duck specification pass → Socratic pass → locked decisions
**Produces:** README.md, DESIGN.md, INTERFACE_CONTRACT.md, DESIGN_DECISIONS.md,
prompts/README.md

---

## Inputs

The following project files must be available and cross-referenced when generating all documents:

- `docs/huginn_v2_interface_contract.md`
- `docs/huginn_v2_design_decisions.md`
- `docs/huginn_v2_masterplan.md`
- `docs/huginn_v2_glossary.md`
- `docs/huginn_v2_setup_notes.md`
- `prompts/01_design_methodology.md`

Do not invent details not present in the source documents. Flag any gap where the source documents are insufficient to complete a section.

---

## Context and Audience

You are generating documentation artifacts for a portfolio project called Huginn, targeting recruiters — both technical and nontechnical — for a junior AI engineer role at a financial services firm. The job listing emphasizes agentic workflows, RAG pipelines, LangGraph, FastAPI, human-in-the-loop design, audit trails, and financial operations domain knowledge.

The core argument this documentation must make is this: **in the age of AI, code is disposable — design principles are not.** This project was built design-first. The interface contract, architecture document, and locked design decisions all preceded the code. That methodology is the primary signal this documentation should convey, above the technical stack.

The development methodology involved structured human-AI collaboration throughout the design phase — Claude was used as a Socratic design partner to stress-test decisions, surface gaps, and formalize specifications. All architectural judgment and design choices belonged to the developer. This should be stated transparently and framed as a demonstration of AI fluency, not apologized for.

V2 is specifically significant because it replaces synthetic knowledge with real regulatory documents and introduces a reasoning rubric built around how legal text actually works — condition match, obligation clarity, exception applicability, cross-reference resolution. This is not a tech stack upgrade. It is a reasoning architecture upgrade.

---

## Document 1 — README.md

**Audience:** both technical and nontechnical recruiters. Nontechnical readers should get full value from the first third and be able to stop. Technical readers should be pulled deeper.

**Structure:**

### 1. Opening statement
Direct and opinionated, not a generic project description. Lead with the design-first philosophy and what it means for how this project was built. This is the candidate's voice and point of view, not a neutral description. Do not open with "Huginn is a FastAPI service that..." or any equivalent generic opener.

### 2. What Huginn does
Plain English, no jargon. What problem it solves, what happens when an exception comes in, what the two possible outcomes are. Two to three short paragraphs maximum.

### 3. Why the design matters
Briefly surface the three-path state machine, the audit trail design, and the human-in-the-loop escalation pattern as deliberate architectural choices, not implementation details. Connect each to the financial operations context. Surface v2's specific advance: the knowledge base is now six real regulatory documents (FINRA and SEC rules), and the reasoning rubric is built around the cognitive tasks required to apply legal text — not a generic scoring framework.

### 4. How it was built
Describe the six-phase development methodology: domain learning, Socratic design, interface contract, masterplan, implementation, feedback loop. Frame the AI collaboration explicitly and offensively — Claude as Socratic partner, all design judgment belonging to the developer. Note that the design artifacts are version-stable while the code is intentionally disposable.

### 5. Companion documents
Link all three companion documents with one-line descriptions framing who should read each and why. Use the following as a starting point but write them in the voice of the rest of the README:

- **DESIGN.md** — architecture, state machine, and the three execution paths. Start here if you want to understand how the system thinks.
- **INTERFACE_CONTRACT.md** — every component's inputs, outputs, and data types. The stable contract the code was built against.
- **DESIGN_DECISIONS.md** — every major decision with its reasoning and rejected alternatives documented. The clearest signal of how design tradeoffs were evaluated.

### 6. Tech stack
Clean table, no commentary needed.

### 7. Setup and demo
Instructions to get the system running and the three API calls that tell the full demo story: standard path submission, result retrieval, escalation queue inspection.

**Tone:** direct, confident, opinionated. This README opens with a position.

---

## Document 2 — DESIGN.md

**Audience:** technical recruiters and hiring managers who want architectural depth.

**Structure:**

### 1. System overview
Use the plain English paragraph from `docs/huginn_v2_masterplan.md` verbatim as the opening.

### 2. The five components
Each component described with its responsibility, its boundaries, and what it explicitly does not do. Draw from `docs/huginn_v2_interface_contract.md`. Components are:
- Exception schema (`models/exception.py`)
- API layer (`api/main.py`)
- LangGraph agent (`agent/`)
- Mimir retriever (`mimir/`)
- Audit logger (`logger/audit.py`)

### 3. The three-path state machine
Describe each path (invalid type exit, mandatory escalation fast-exit, standard path) with the reasoning for why each exists as a distinct path rather than inline logic. Include the Component Interaction Summary diagram from `docs/huginn_v2_interface_contract.md` verbatim.

### 4. Key design decisions
Surface the eight most interview-worthy decisions from `docs/huginn_v2_design_decisions.md` with their reasoning and rejected alternatives. Prioritize:
- Real regulatory documents over synthetic SOPs (Decision 8)
- Section-aware chunking with false-split filter (Decisions 30, 49)
- Two-pass iterative retrieval with cross-reference resolution (Decision 37)
- Four-factor regulatory reasoning rubric (Decision 29)
- Mandatory escalation keywords — buy-in and sell-out added in v2 (Decision 43)
- Audit log full fidelity (Decision 17)
- Claude API failure handling — fail fast and escalate (Decision 28)
- Versioning strategy — code is disposable (Decision 13)

### 5. What v2 deliberately excludes
The explicit out-of-scope list from `docs/huginn_v2_design_decisions.md` (the "What V2 Is Not" section), framed as evidence of scope discipline rather than incompleteness.

---

## Document 3 — INTERFACE_CONTRACT.md

Use `docs/huginn_v2_interface_contract.md` as the source. Reproduce it with the following additions only:

- A one-paragraph introduction at the top explaining what an interface contract is, why it was written before the code, and how to use it as a reader.
- A one-line note at the top of each component section indicating which subplan implemented it and which design decisions govern it.

Do not alter any existing specifications. The contract is locked.

---

## Document 4 — DESIGN_DECISIONS.md

Use `docs/huginn_v2_design_decisions.md` as the source. Reproduce it with the following addition only:

- A one-paragraph introduction explaining the Socratic design methodology, why rejected alternatives are documented, and how this document relates to the interface contract.

Do not rewrite or alter any existing decisions. They are locked.

---

## Document 5 — prompts/README.md

Generate a one-page index for the `prompts/` folder explaining:
- What this folder is and why it exists
- The core argument: in AI-assisted development, the prompts and methodology that produce the code are as significant as the code itself
- How to read the folder — each prompt file listed with a one-line description of what phase it belongs to and what it produced

Frame this around the design-first philosophy established throughout the project. The prompts folder is evidence that the thinking happened before the code.

**Prompt file index to document:**

| File | Phase | Produced |
|---|---|---|
| `01_design_methodology.md` | Design phase (Phases 1–3) | Behavioral instructions and methods governing human-AI collaboration throughout design |
| `02_readme_generation.md` | Post-implementation (Phase 7+) | README.md, DESIGN.md, INTERFACE_CONTRACT.md, DESIGN_DECISIONS.md, prompts/README.md |
| `03_generate_walkthrough.md` | Post-implementation (Phase 7+) | `walkthrough/` directory of annotated design rationale for every source file |
| `04_rewrite_glossary.md` | Post-implementation (Phase 7+) | Polished `docs/huginn_v2_glossary.md` written for two audiences: recruiter and returning developer |
| `05_feedback_loop.md` | Phase 7 | Updated design documents reconciled against the implemented codebase |

---

## Output Checklist

Before finishing, verify:

- [ ] README opens with a position statement, not a system description
- [ ] README serves nontechnical readers in the first third without requiring technical knowledge
- [ ] AI collaboration is framed transparently and offensively in the README
- [ ] README surfaces v2's regulatory reasoning advance specifically, not just the tech stack
- [ ] DESIGN.md includes the Component Interaction Summary diagram verbatim from the interface contract
- [ ] DESIGN.md key decisions are drawn from v2 decisions, not v1
- [ ] INTERFACE_CONTRACT.md specifications are unaltered
- [ ] DESIGN_DECISIONS.md decisions are unaltered
- [ ] All companion documents are linked from the README with one-line descriptions
- [ ] prompts/README.md indexes all five prompt files with phase and output noted
- [ ] No details invented that are not present in the source documents
- [ ] Any gaps where source documents are insufficient are flagged explicitly
