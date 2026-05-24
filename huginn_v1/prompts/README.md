# prompts/

This folder contains the prompts and methodology documents that governed Huginn's development. It exists because in AI-assisted development, the prompts that produce the code are as significant as the code itself.

The core argument: a well-structured prompt reflects well-structured thinking. A system built against a precise interface contract, preceded by locked design decisions, preceded by a Socratic design phase, preceded by domain learning — that chain of thinking is what the prompts folder preserves. Anyone can generate code. The methodology that produces good code is the harder thing to demonstrate.

The `prompts/` folder is evidence that the thinking happened before the code.

---

## How to Read This Folder

Each file documents a phase of the project's development. They are ordered by phase sequence using a two-digit prefix. New prompt files will be added as the project progresses through the feedback loop phase and into v2 development.

| File | Phase | Produced |
|---|---|---|
| [`01_design_methodology.md`](01_design_methodology.md) | Design phase (Phases 1–3) — applied before any code was written | The behavioral instructions and methods governing human-AI collaboration throughout design: Socratic design sessions, rubber duck specification passes, interface contract generation, and masterplan construction |
| [`02_readme_generation.md`](02_readme_generation.md) | Post-implementation (Phase 4+) | The README and all companion documentation — README.md, DESIGN.md, INTERFACE_CONTRACT.md, DESIGN_DECISIONS.md, and this file |

---

## What These Files Are

These are not scripts or configuration. They are design artifacts — the specifications that governed what Claude was asked to do and how it was asked to do it.

`01_design_methodology.md` documents the framework for human-AI collaboration during design: which metacognitive methods were used and when, what behavioral instructions were applied to Claude during each phase, and the principles governing versioning and continuity across versions. This file was applied before Huginn's design phase began.

`02_readme_generation.md` is the prompt used to generate this project's README and companion documentation. It specifies the audience, the core argument, the structure of each document, and what sources to draw from. Reproducing it here makes the documentation generation process auditable.

---

## The Design-First Philosophy

This folder reflects the same principle that governs the rest of the project: design comes first, and the quality of a system is determined before a single line of code is written.

Code is disposable. When Huginn v2 is built, the codebase will be regenerated from scratch by Claude Code using a new masterplan. The design documents — including these prompts — are the artifacts that carry intent across versions.
