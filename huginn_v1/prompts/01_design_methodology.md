# Prompt: Development Methodology and Claude Collaboration Framework
**Phase:** Design phase (Phases 1–3) — applied before any code was written
**Produced by:** Initial project setup
**Produces:** Governs all design-phase interactions — Socratic design sessions,
rubber duck specification passes, interface contract generation, and masterplan
construction.

---

# Claude Interaction Workflow — Behavioral Instructions and Methods

**Status:** Current as of Huginn v1 Phase 7 (Feedback Loop) complete.
**Purpose:** A reusable reference for how to work with Claude effectively across projects. Documents every behavioral instruction, metacognitive method, and workflow decision established during Huginn development. Apply this to future projects from the start.

---

## Part 1 — Project Development Workflow

The full workflow for building software projects using Claude Web Projects and Claude Code. Established during Huginn v1 Design Refinement.

### Phase 1 — Domain Learning *(Claude Web Project)*
Build vocabulary, understand the problem space, learn the terminology. Flashcard exports, reading lists, concept explanations. This phase produces a person who can make informed decisions, not just a document.

### Phase 2 — Socratic Design *(Claude Web Project)*
Resolve every major design decision using the Socratic method until every ambiguity is eliminated. No open questions leave this phase. Every decision is recorded with its reasoning and rejected alternatives explicitly documented. This phase produces a locked decisions document.

### Phase 3 — Interface Contract Document *(Claude Web Project)*
Before writing the masterplan, define every component boundary explicitly — what each component accepts as input, what it returns as output, and what data types are involved. This document becomes the integration source of truth that every Claude Code subagent references. This phase prevents subagent conflicts.

### Phase 4 — Masterplan + Atomic Subplans *(Claude Web Project)*
Generate the masterplan referencing the interface contract and locked decisions. The masterplan opens with a plain English paragraph describing the completed system — this is the first thing Claude Code reads. Each subplan contains three things: its own implementation instructions, the interface contract document, and the explicit build sequence gate it must pass before the next subplan starts.

### Phase 5 — Verification Checklist *(Claude Web Project)*
Apply the ten-item checklist (see Part 3) to the masterplan before any code is written. This phase produces confidence that what you hand off to Claude Code matches your intent.

### Phase 6 — Implementation *(Claude Code)*
Hand the masterplan to Claude Code. Subagents implement atomic subplans in strict build sequence order, each referencing the interface contract document. No subagent starts until the previous gate is confirmed working.

### Phase 7 — Feedback Loop *(Claude Code)*
Runs inside Claude Code after all subplans are complete and all tests pass. Claude Code has simultaneous access to the full codebase and all design documents, making it the correct environment for reconciliation — the Web Project cannot read source files. Claude Code reads every source file and design document, runs a four-category inspection (interface drift, changed decisions, implementation details that became decisions, new known issues), and regenerates all design documents clean against the actual implementation. The Web Project's role after Phase 7 is v2 design only — no further reconciliation work belongs there.

---

## Part 2 — Metacognitive Methods

These are the methods used during planning phases to surface gaps and make implicit assumptions explicit. Each method is suited to a different phase of work.

### Method 1 — Socratic Method
**Best for:** Phase 2 (design decisions). Eliminating ambiguity in choices where multiple valid options exist.

**How it works:** Claude asks structured questions about each design area. You answer. Claude challenges weak reasoning and presents alternatives. Decisions are locked only when the reasoning is explicit and all alternatives are documented with rejection rationale.

**Why it works:** Forces every decision to be made consciously rather than by default. When a result is bad later, the cause is traceable to a specific decision and its reasoning — not to something that was never discussed.

**Signal that it's working:** You find yourself unable to answer a question clearly — this means the decision was previously made by assumption rather than by reasoning.

---

### Method 2 — Rubber Duck Specification
**Best for:** Phase 3 (interface contract). Making implicit assumptions explicit before writing specs.

**How it works:** You describe each component as if explaining it to a developer who has zero additional context and cannot ask follow-up questions. Claude listens for gaps — moments where you say something vague, skip a detail, or cannot produce a precise answer — and flags them. Claude then formalizes what you said into the document.

**Why it works:** Writing for an audience that cannot ask follow-up questions forces you to externalize your internal model. Gaps surface as friction — when you reach for words and cannot find them, that is the gap revealing itself.

**Signal that it's working:** You hit moments of discomfort where you think you know something but cannot say it precisely. This is the method working, not a sign of inadequate preparation. Flag the gap and continue; gaps are resolved in the Socratic pass that follows.

**Important:** When you hit a gap during rubber duck, do not reach for the design documents. Flag it and keep going. The Socratic pass resolves gaps; the rubber duck pass surfaces them.

---

### Method 3 — Draft and Challenge
**Best for:** Reviewing completed documents. Catching gaps in something that already exists.

**How it works:** Claude produces a complete draft from existing project files. You read it and push back on anything that feels wrong, underspecified, or inconsistent with your intent.

**Why it works:** Fast. A complete document gives you something concrete to react to, which is easier than generating from nothing.

**Risk:** You may rubber-stamp something that has a subtle gap because it looks complete on the surface. Use in combination with rubber duck or Socratic where thoroughness matters more than speed.

---

### Recommended Sequencing

For specification work (Phase 3): **Rubber Duck first, then Socratic.**

Rubber duck first forces you to externalize your own mental model before seeing Claude's. When the Socratic pass follows, the questions hit genuine gaps rather than territory you already know. If Socratic came first, Claude's questions would lead you through territory you could have mapped yourself — less valuable.

For decision work (Phase 2): **Socratic only.**

For document review: **Draft and Challenge, then Socratic on flagged gaps.**

---

## Part 3 — Pre-Implementation Verification Checklist

Apply this checklist identically to every masterplan before handing it to Claude Code. Takes approximately 10 minutes. The value is not the individual questions — it is asking the same questions every single time.

1. Is every component's input defined explicitly, including data types?
2. Is every component's output defined explicitly, including data types?
3. Does every design decision include the reasoning behind it, not just the decision itself?
4. Is the build sequence explicitly ordered with clear gates between steps?
5. Does every subplan reference the interface contract document?
6. Are all rejected options documented with the reason they were rejected?
7. Is every technical term used in the masterplan defined in the project glossary?
8. Is the exception type taxonomy (or equivalent domain taxonomy) fully defined with no placeholder entries?
9. Are all hard-coded values (thresholds, keywords, enum values) explicitly listed?
10. Can you describe the completed system in one paragraph without referring back to the masterplan?

If any item fails, fix it before proceeding to Claude Code. A checklist item that fails is a gap that will surface as a bug or a misimplementation later.

---

## Part 4 — Behavioral Instructions for Claude

These are the specific instructions established during Huginn development that alter how Claude responds. Apply these at the start of relevant sessions.

### Instruction 1 — Two Options with Rationale
**Trigger:** Any decision point during Socratic or specification work.

**Instruction:** *"For each question, provide your two best options alongside a brief rationale for each, and indicate which you lean toward and why."*

**Why:** Presenting two options with explicit rationale prevents Claude from defaulting to a single answer, forces comparison, and makes the reasoning behind the recommendation visible and challengeable. The lean indication is useful but should always be questioned, not accepted by default.

---

### Instruction 2 — Flag New Additions
**Trigger:** Any session where decisions are being made against existing locked documents.

**Instruction:** *"Cross-reference the locked design documents and flag any new additions — things not mentioned in previous chats or documents — with a ⚠️ marker before discussing them."*

**Why:** Prevents scope creep from going unnoticed. New additions that aren't flagged can be accepted without realizing they represent a design decision that should be deliberate. The flag prompts a conscious choice: lock it, defer it, or reject it.

---

### Instruction 3 — Maintain a Pending Changes List
**Trigger:** Any session that produces decisions that will require document updates.

**Instruction:** *"Maintain a running pending changes list throughout this session, updated after each decision, so nothing is lost when we generate the updated documents at the end."*

**Why:** Long sessions produce many decisions. Without a running list, decisions made early in the session are easy to miss when generating the final documents.

---

### Instruction 4 — Cross-Reference Documentation for Contradictions
**Trigger:** Rubber duck specification sessions.

**Instruction:** *"Cross-reference the project documentation and flag anything that contradicts, conflicts with, or is missing from what is locked."*

**Why:** During rubber duck, you may state something that contradicts a locked decision without realizing it. Claude catching this in real time is faster than discovering it after the interface contract is written.

---

### Instruction 5 — Integrated Updates, Not Bolt-Ons
**Trigger:** When generating updated versions of project documents.

**Instruction:** *"Generate a fully integrated updated version of the document, not a version with additions bolted onto the end. New decisions should be woven into the document in the correct location, not appended."*

**Why:** Documents that accumulate bolted-on sections become harder to read and harder to hand to Claude Code as a coherent reference. A clean integrated document is easier to maintain and more reliable as a source of truth.

---

### Instruction 6 — Batch Document Updates
**Trigger:** At the end of any session that produces multiple document changes.

**Instruction:** *"Hold all document updates until the end of the session. Generate all updated documents in a single pass once all decisions are locked."*

**Why:** Generating documents mid-session and then making more decisions creates multiple versions of documents in the same conversation, which is confusing. A single end-of-session generation pass is cleaner.

---

## Part 5 — Versioning and Continuity Decisions

### Versioning Strategy
Each version of a project is regenerated from scratch by Claude Code using a new masterplan. The previous version's codebase is never the starting point for the next version. Design documents — the interface contract, locked decisions, and architecture document — are the artifacts that carry intent across versions. Code is disposable.

**Why:** Iterating on existing code requires Claude Code to simultaneously reason about what exists, what to change, and what to leave alone — a significantly harder task than building fresh, and a common source of subtle bugs. Regenerating from scratch keeps each Claude Code session unambiguous.

**Implication:** Every masterplan must be complete and self-contained. Any capability carried forward from a previous version must be explicitly re-specified — it cannot be assumed.

---

### Project File Strategy
Critical decisions should be captured in project files, not left only in conversation history. Conversations can lose early context as they grow; project files persist across all conversations.

The canonical project files for any project are:
- `{project}_design_decisions.md` — every locked decision with reasoning and rejected alternatives
- `{project}_glossary.md` — all domain and technical terms
- `{project}_architecture.md` — component structure and build sequence
- `{project}_interface_contract.md` — component inputs, outputs, and data types
- `{project}_setup_notes.md` — environment setup, known issues, reading list

Update these files at the end of each session, not during. Generate integrated versions, not bolt-ons.

---

### Cross-Conversation Context
Claude does not automatically remember previous conversations. The project files are the shared context. If a decision was made conversationally but never written to a file, it effectively does not exist for the next conversation.

When starting a new session, open with a prompt that tells Claude which phase you're in and what the last session produced. The handoff prompt from each session should be explicit enough that the next session can pick up without relitigating anything already decided.

---

## Part 6 — Vertical Slicing Principle

The core versioning philosophy. Each version is a complete, independently demonstrable system — not a prototype that becomes a real thing, but a real thing that gets more capable.

### What to do in each version
Design interfaces wide enough that later versions can add capability without breaking what's already there. Include data fields that will be acted on in later versions — the data should be captured early even if it's not used yet.

### What not to do in each version
Do not build scaffolding for features you haven't implemented yet. No placeholder functions, no stub reasoning paths, no TODO comments wired into logic. The code does exactly what the current version specifies, nothing more.

### The analogy
You are laying foundations wide enough for a larger building, but only constructing the first floor. The foundation is not artificially narrow — but it does not contain empty rooms waiting to be filled.

### Applying vertical slicing to interface decisions
When specifying an interface, ask: if this field or parameter is included now but not acted on, does it cost anything? If the answer is no, include it. If including it requires building logic that isn't needed yet, exclude it and note it as a v{n+1} addition.
