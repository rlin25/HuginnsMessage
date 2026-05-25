# Prompt: README and Documentation Generation
**Phase:** Post-implementation documentation
**Produced by:** Rubber duck specification pass → Socratic pass → locked decisions
**Produces:** README.md, DESIGN.md, INTERFACE_CONTRACT.md, DESIGN_DECISIONS.md,
prompts/README.md

---

## Inputs

The following project files must be available and cross-referenced when generating all documents:

- `huginn_v1_architecture.md`
- `huginn_v1_interface_contract.md`
- `huginn_v1_design_decisions.md`
- `huginn_v1_masterplan.md`
- `huginn_v1_claude_workflow.md`
- `huginn_v1_glossary.md`

Do not invent details not present in the source documents. Flag any gap where the source documents are insufficient to complete a section.

---

## Context and Audience

You are generating documentation artifacts for a portfolio project called Huginn, targeting recruiters — both technical and nontechnical — for a junior AI engineer role at a financial services firm. The job listing emphasizes agentic workflows, RAG pipelines, LangGraph, FastAPI, human-in-the-loop design, audit trails, and financial operations domain knowledge.

The core argument this documentation must make is this: **in the age of AI, code is disposable — design principles are not.** This project was built design-first. The interface contract, architecture document, and locked design decisions all preceded the code. That methodology is the primary signal this documentation should convey, above the technical stack.

The development methodology involved structured human-AI collaboration throughout the design phase — Claude was used as a Socratic design partner to stress-test decisions, surface gaps, and formalize specifications. All architectural judgment and design choices belonged to the developer. This should be stated transparently and framed as a demonstration of AI fluency, not apologized for.

---

## Document 1 — README.md

**Audience:** both technical and nontechnical recruiters. Nontechnical readers should get full value from the first third and be able to stop. Technical readers should be pulled deeper.

**Structure:**

### 1. Opening statement
Direct and opinionated, not a generic project description. Lead with the design-first philosophy and what it means for how this project was built. This is the candidate's voice and point of view, not a neutral description. Do not open with "Huginn is a FastAPI service that..." or any equivalent generic opener.

### 2. What Huginn does
Plain English, no jargon. What problem it solves, what happens when an exception comes in, what the two possible outcomes are. Two to three short paragraphs maximum.

### 3. Why the design matters
Briefly surface the three-path state machine, the audit trail design, and the human-in-the-loop escalation pattern as deliberate architectural choices, not implementation details. Connect each to the financial operations context.

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
Use the plain English paragraph from `huginn_v1_masterplan.md` verbatim as the opening.

### 2. The five components
Each component described with its responsibility, its boundaries, and what it explicitly does not do. Draw from `huginn_v1_architecture.md`.

### 3. The three-path state machine
Describe each path (invalid type exit, mandatory escalation fast-exit, standard path) with the reasoning for why each exists as a distinct path rather than inline logic. Include the ASCII flow diagram from `huginn_v1_architecture.md` verbatim.

### 4. Key design decisions
Surface the six to eight most interview-worthy decisions from `huginn_v1_design_decisions.md` with their reasoning and rejected alternatives. Prioritize the following:
- LLM reasoning at runtime vs rules engine (Decision 4)
- Keyword scan timing — pre-retrieval (Decision 10)
- Audit log full fidelity (Decision 17)
- Single logger interface (Decision 27)
- Fake async job ID pattern (Decision 7 / Decision 19)
- Chroma over FAISS (Decision 12)
- Versioning strategy — code is disposable (Decision 13)
- Claude API failure handling (Decision 28)

### 5. What v1 deliberately excludes
The explicit out-of-scope list from the architecture document, framed as evidence of scope discipline rather than incompleteness.

---

## Document 3 — INTERFACE_CONTRACT.md

Use `huginn_v1_interface_contract.md` as the source. Reproduce it with the following additions only:

- A one-paragraph introduction at the top explaining what an interface contract is, why it was written before the code, and how to use it as a reader.
- A one-line note at the top of each component section indicating which subplan implemented it and which design decisions govern it.

Do not alter any existing specifications. The contract is locked.

---

## Document 4 — DESIGN_DECISIONS.md

Use `huginn_v1_design_decisions.md` as the source. Reproduce it with the following addition only:

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
| `01_design_methodology.md` | Design phase (Phases 1–3) | The behavioral instructions and methods governing human-AI collaboration throughout design |
| `02_readme_generation.md` | Post-implementation (Phase 4+) | This document — the README and all companion documentation |

Note that additional prompt files will be added as the project progresses through the feedback loop phase. The naming convention is two-digit prefix reflecting phase sequence.

---

## Document 6 — prompts/01_design_methodology.md

Source from `huginn_v1_claude_workflow.md`. Reproduce it in full as a prompt artifact with the following addition at the top:

```
# Prompt: Development Methodology and Claude Collaboration Framework
**Phase:** Design phase (Phases 1–3) — applied before any code was written
**Produced by:** Initial project setup
**Produces:** Governs all design-phase interactions — Socratic design sessions,
rubber duck specification passes, interface contract generation, and masterplan
construction.
```

Do not summarize or paraphrase the source document. Reproduce it in full. The methodology document is the artifact.

---

## Document 7 — prompts/02_readme_generation.md

This file is the prompt you are currently reading. Reproduce it in full as a prompt artifact with the following header at the top:

```
# Prompt: README and Documentation Generation
**Phase:** Post-implementation documentation
**Produced by:** Rubber duck specification pass → Socratic pass → locked decisions
**Produces:** README.md, DESIGN.md, INTERFACE_CONTRACT.md, DESIGN_DECISIONS.md,
prompts/README.md
```

Do not summarize or paraphrase. Reproduce verbatim.

---

## Output Checklist

Before finishing, verify:

- [ ] README opens with a position statement, not a system description
- [ ] README serves nontechnical readers in the first third without requiring technical knowledge
- [ ] AI collaboration is framed transparently and offensively in the README
- [ ] DESIGN.md includes the ASCII flow diagram verbatim from the architecture document
- [ ] INTERFACE_CONTRACT.md specifications are unaltered
- [ ] DESIGN_DECISIONS.md decisions are unaltered
- [ ] All companion documents are linked from the README with one-line descriptions
- [ ] prompts/README.md indexes all prompt files with phase and output noted
- [ ] No details invented that are not present in the source documents
- [ ] Any gaps where source documents are insufficient are flagged explicitly
