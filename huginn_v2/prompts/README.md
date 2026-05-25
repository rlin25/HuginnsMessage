# prompts/

This folder contains the prompts that governed every phase of Huginn's design and documentation. It exists because in AI-assisted development, the prompts and methodology that produce the code are as significant as the code itself.

## Why This Folder Exists

Software built with AI assistance has a provenance problem: the artifact (the code) is visible, but the thinking that produced it (the design sessions, the design decisions, the rejected alternatives, the iteration) is invisible. This folder is the answer to that problem for Huginn.

Every document in `docs/` was produced by a prompt in this folder. Every design decision that was made before the code was written was made using the methodology in `01_design_methodology.md`. The prompts are the evidence that the thinking happened before the code — not after, not during, not never.

This is also a demonstration of AI fluency as a design skill. Producing a useful output from a language model requires understanding what it does well, what it does badly, how to structure a prompt to surface gaps rather than paper over them, and how to govern a human-AI collaboration so that design judgment stays with the human. These prompts are artifacts of that skill.

## How to Read This Folder

Read the prompts in order. Each one is labeled with the phase it belongs to and what it produced. The early prompts (01, 02) were the most consequential — they governed the design methodology and the documentation standard before any code was written. The later prompts (03–05) were applied post-implementation to reconcile, document, and present the completed system.

| File | Phase | Produced |
|---|---|---|
| `01_design_methodology.md` | Design phase (Phases 1–3) | Behavioral instructions and methods governing human-AI collaboration throughout design |
| `02_readme_generation.md` | Post-implementation (Phase 7+) | README.md, DESIGN.md, INTERFACE_CONTRACT.md, DESIGN_DECISIONS.md, prompts/README.md |
| `03_generate_walkthrough.md` | Post-implementation (Phase 7+) | `walkthrough/` directory of annotated design rationale for every source file |
| `04_rewrite_glossary.md` | Post-implementation (Phase 7+) | Polished `docs/huginn_v2_glossary.md` written for two audiences: recruiter and returning developer |
| `05_feedback_loop.md` | Phase 7 | Updated design documents reconciled against the implemented codebase |

## The Core Argument

In the age of AI, code is disposable. Huginn v3 will be regenerated from scratch using an updated masterplan. What carries forward is not the code — it is the design principles, the locked decisions, and the methodology that produced them.

The prompts in this folder are part of what carries forward.
