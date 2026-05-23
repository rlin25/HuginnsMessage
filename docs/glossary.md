# Huginn v1 — Consolidated Glossary

**Status:** Current as of Phase 3 (Interface Contract) complete.
**Sources:** Initial Conceptualization · Design Refinement · Basic Terminology · Locked Design Decisions · Interface Contract Session (authoritative)
**Note:** Terms marked ⚠️ evolved across conversations. The definition given reflects the most recent locked decision.

---

## Section 1 — Huginn System Terms

**Agent (Huginn)**
The LangGraph-based reasoning component that receives a trade exception, classifies it, queries Mimir, evaluates the retrieved SOP, produces a confidence score and reasoning trace, and decides whether to auto-resolve or escalate. Huginn is the decision-maker; Mimir is the knowledge source it consults.

**Audit Log**
A dual-format record written for every exception Huginn processes. Writes to both `logs/audit.jsonl` (human-readable, append-only) and a local SQLite database (queryable). Captures full fidelity — the complete original exception payload, all retrieved document chunks, the LLM's raw response before parsing, the confidence score, reasoning trace, resolution steps, outcome, escalation reason, triggered keyword, and all timestamps. ⚠️ *Evolved: initial design considered a flat file only; SQLite was added in Socratic Design; full fidelity requirement locked in Interface Contract.*

**Auto-Resolve**
The outcome when Huginn's confidence score meets or exceeds the escalation threshold — the exception is processed without human involvement and the decision is written to the audit log.

**Confidence Score**
A float between 0.0 and 1.0 produced by the LLM at runtime representing how certain Huginn is about its resolution decision. Determines whether the exception is auto-resolved or escalated by comparison against the escalation threshold. In v1 a single hardcoded threshold of 0.75 applies to all sub_types; per sub_type thresholds replace this in v2. ⚠️ *Evolved: threshold structure clarified in Interface Contract session.*

**Escalation**
The outcome when Huginn's confidence score falls below the required threshold, or when a mandatory escalation keyword is detected. The full exception and reasoning trace are written to both the audit log and the escalation queue.

**Escalation Queue**
A separate file — `logs/escalation_queue.jsonl` — that receives every escalated exception and its full fidelity record. Represents the human reviewer's inbox. Physically distinct from the audit log so the escalation pathway is visible without parsing the full log. Exposed via the `GET /escalations` endpoint. Records are identical in schema to audit log records.

**Escalation Reason**
A string field populated in the API response and audit log explaining why an exception was escalated. On the standard path it contains a low confidence explanation (e.g. `"confidence score 0.43 below threshold 0.75"`). On the mandatory escalation fast-exit it contains the specific keyword detected (e.g. `"mandatory escalation keyword detected: sanctions"`). Null when the outcome is auto-resolve.

**Escalation Threshold**
The minimum confidence score required for Huginn to auto-resolve an exception. In v1 the value is 0.75, hardcoded and applied uniformly across all sub_types. Calibrated per sub_type against real audit log data in v2.

**Evaluation Harness**
A testing framework that measures agent decision quality over time, distinct from code correctness tests. In v2, the evaluation harness replays a set of golden examples through the agent and measures what percentage are classified correctly, whether confidence scores are well-calibrated, and whether prompt changes improve or hurt decision quality. Requires full fidelity audit log records to function — exceptions must be replayable with all inputs intact.

**Exception Payload**
The complete set of fields submitted to Huginn when a trade exception is reported. In v1: `exception_id` (UUID), `trade_id` (str), `type` (Enum), `sub_type` (Enum), `description` (str), `timestamp` (datetime), `severity` (Enum: low/medium/high). The payload is validated at the API layer before reaching the agent and is captured in full in the audit log.

**Full Fidelity**
A record-keeping standard where every input the agent received and every output it produced is captured in the log — including the raw exception payload, raw retrieved chunks, raw LLM response before parsing, and all intermediate values. Contrasted with decision-focused logging which captures only the final outcome. Full fidelity is required for the v2 evaluation harness and for debugging incorrect decisions.

**Golden Examples**
A curated set of trade exceptions with known correct outcomes — pre-labeled as auto-resolve or escalate, with the correct sub_type and reasoning. Used by the v2 evaluation harness to measure agent performance. The quality of the evaluation harness depends on the quality and coverage of the golden example set.

**Huginn**
The overall AI agent system. Named after one of Odin's two ravens — Huginn representing thought, Muninn representing memory. Receives flagged financial trade exceptions, classifies them, consults Mimir, reasons over the retrieved procedure, and decides to auto-resolve or escalate. Every decision is recorded in the audit log.

**Interface Contract Document**
The Phase 3 deliverable following locked design decisions. A formal document specifying every component's inputs, outputs, and data types — the stable contract that Claude Code builds against. Prevents Claude Code from making implementation decisions that conflict with design intent. Along with the design decisions document, it is the primary artifact carried across versions.

**Invalid Type Exit**
The first branch in Huginn's LangGraph state machine. Fires immediately at classification if the exception's `type` field is not in the approved taxonomy. Returns a structured error. Nothing else runs — Mimir is never called, no audit log entry is written.

**Mandatory Escalation Fast-Exit**
The second branch in Huginn's LangGraph state machine. Fires immediately after classification if a trigger keyword (`sanctions`, `AML`, `regulatory hold`) is detected in the exception text. Skips Mimir retrieval and LLM reasoning entirely. Routes directly to escalation. The audit log records the specific keyword that triggered it. `retrieved_document_id` is null in the API response for this path — confirming Mimir was never called. ⚠️ *Evolved: early design had keyword scanning as part of the confidence scoring logic; Socratic Design locked it as a pre-retrieval fast-exit.*

**Mandatory Escalation Keywords (V1)**
The exhaustive list of trigger terms for the mandatory escalation fast-exit in v1: `sanctions`, `AML`, `regulatory hold`. Any of these present in an exception triggers immediate escalation regardless of confidence score. Additional keywords are added in v2.

**Mimir**
The RAG retrieval component. Named after the Norse keeper of wisdom — a figure separate from Huginn and Muninn in Norse mythology. Stores synthetic SOP documents in a Chroma vector store, accepts a structured query from Huginn, performs similarity search, and returns the most relevant document chunks with metadata. In v1 retrieval is single-pass only; iterative retrieval is a v2 feature. ⚠️ *Evolved: FAISS was the originally recommended vector store; Chroma replaced it in Socratic Design.*

**Regression Test**
A test that confirms previously working behavior has not broken after a change. In the context of Huginn, regression tests run the golden example set through the agent after any prompt or logic change and assert that outcomes match the expected labels. Distinct from unit tests (which test individual components in isolation) and integration tests (which test the full pipeline end-to-end).

**Standard Path**
The third and primary branch in Huginn's LangGraph state machine. Followed when the exception passes classification and contains no mandatory escalation keywords. Sequence: classify → retrieve (Mimir) → reason (LLM) → decide → log. Ends with a single branch point: auto-resolve if confidence meets threshold, escalate if it does not.

**Vertical Slicing**
The versioning strategy for Huginn. Each version (v1, v2, v3) is a fully working end-to-end system with increasing sophistication — not a prototype that becomes a real thing, but a real thing that gets more capable. Interfaces defined in v1 are stable contracts that later versions build on rather than replace. Each version is regenerated from scratch by Claude Code — the design documents carry intent across versions, not the code.

---

## Section 2 — Financial Domain Terms

**AML**
Anti-Money Laundering. A mandatory escalation keyword in v1 — any exception containing this term is immediately escalated without LLM reasoning, regardless of confidence score.

**Counterparty**
One of the two parties on either side of a trade.

**Counterparty Credit Risk**
The risk that the other party to a trade will fail to meet its obligations — e.g. failing to deliver securities or payment at settlement.

**DTCC**
The Depository Trust & Clearing Corporation. The central US clearinghouse that processes and guarantees trades. When a settlement fails, DTCC is the entity flagging it.

**Delivery-versus-Payment (DVP)**
A settlement method where securities and payment are exchanged simultaneously — neither side delivers unless the other does.

**FINRA**
Financial Industry Regulatory Authority. Publishes publicly accessible rulebooks and regulatory guidance covering settlement, clearance, and compliance — used as Mimir's regulatory document layer in v2.

**Free-of-Payment (FOP)**
A settlement method where securities delivery and payment occur separately — risky for whichever party delivers first.

**Price Mismatch**
A settlement mismatch sub-type where the buyer's and seller's records disagree on the agreed price of the transaction. One of three sub-types handled by Huginn v1.

**Quantity Mismatch**
A settlement mismatch sub-type where the buyer's and seller's records disagree on the number of units transacted. One of three sub-types handled by Huginn v1.

**Regulatory Hold**
A mandatory escalation keyword in v1 — any exception flagged with a regulatory hold is immediately escalated without LLM reasoning.

**Sanctions**
A mandatory escalation keyword in v1 — any exception involving sanctions is immediately escalated without LLM reasoning.

**Settlement**
The actual completion of a trade — the physical exchange of cash for securities or one currency for another.

**Settlement Date**
The date the counterparties actually exchange assets. May differ from the value date if a settlement fail occurs.

**Settlement Fail**
When a trade does not settle on its contractually scheduled date — the buyer and seller's exchange did not complete as agreed.

**Settlement Mismatch**
The only exception type handled by Huginn v1. A flagged disagreement between buyer and seller records at the settlement stage — on price, quantity, or settlement date. All other exception types are rejected at the API validation layer.

**SOP (Standard Operating Procedure)**
A documented step-by-step process for handling a specific type of situation. Mimir's knowledge base in v1 consists entirely of synthetic SOPs — one per settlement mismatch sub-type — written for a fictional financial firm.

**Trade Date**
The date the counterparties agree to trade. The actual exchange of assets does not occur on this date.

**Trade Exception**
A flagged problem in a financial transaction that cannot complete automatically and requires investigation or resolution. Huginn's input.

**Trade Life Cycle**
The full sequence of events from pre-trade preparation through settlement and ongoing position management. Huginn operates at the settlement stage.

**Trade Reconciliation**
Comparing internal records against external records to identify and resolve discrepancies — one of the ongoing position management activities.

**Value Date**
The date counterparties are contractually obligated to exchange assets. They may fail to do so in practice, producing a settlement fail.

**Wrong Settlement Date**
A settlement mismatch sub-type where the recorded settlement date in one party's system differs from the other's. One of three sub-types handled by Huginn v1.

---

## Section 3 — Technical Implementation Terms

**Agentic Workflow**
A multi-step AI process where the agent makes decisions between steps and can invoke tools — not a single question-and-answer exchange. Huginn's full processing sequence is: receive exception → classify → query Mimir → evaluate confidence → auto-resolve or escalate → write audit log.

**Async def**
A Python function definition that can pause and wait without blocking other requests from being handled simultaneously. Used in FastAPI path operation functions.

**Chroma**
The vector store used by Mimir in v1. Persists to disk (no re-indexing on restart), runs locally with no external service, supports metadata filtering. ⚠️ *Evolved: FAISS was originally recommended; Chroma replaced it in Socratic Design.*

**Compliance-Ready**
Every decision is recorded and fully traceable so a compliance officer can verify it without developer involvement. Huginn's audit log is designed for this from v1.

**Decorator**
The `@something` syntax in Python that wraps a function and adds behavior — e.g. `@app.get("/")` registers a function as a FastAPI route handler.

**Embeddings**
A representation of text as a list of numbers where similar meanings produce numerically similar vectors — the mechanism that enables Mimir's similarity search.

**Exception Schema**
A blueprint defining the required fields and data types for every trade exception submitted to Huginn. In v1 this is a flat Pydantic model with strict typing throughout, a `type` field constrained to the approved taxonomy via enum, and sub_type scoped to its parent type via a model validator.

**Exception Type Taxonomy**
The controlled vocabulary of valid exception types. In v1 the only valid value is `settlement_mismatch`. All other values are rejected at the API layer before reaching the agent.

**FAISS**
A local vector store library considered during initial design. Replaced by Chroma in Socratic Design due to Chroma's disk persistence and metadata filtering support. ⚠️ *Superseded: no longer used in v1.*

**FastAPI**
The Python framework providing Huginn's API layer. Exposes three endpoints in v1: `POST /exceptions`, `GET /exceptions/{job_id}`, and `GET /escalations`. The auto-generated `/docs` interface is Huginn v1's demo surface.

**Fake Async Job ID Pattern**
The API design pattern where `POST /exceptions` returns a job ID immediately and the caller retrieves the result via `GET /exceptions/{job_id}`. In v1 processing is synchronous so the result is always ready by the time the ID is returned — but the interface is designed for asynchronous processing so v2 can slot in a real queue without changing the API contract.

**Flat Schema**
A schema where all fields sit at the same level with no nesting. Huginn v1's exception schema is flat — simple to build and validate while anticipating the richer nested schema of v2.

**Human-in-the-Loop**
A design pattern where the agent hands off to a human when confidence falls below threshold or when a mandatory escalation keyword is detected. In Huginn v1 this is implemented via the escalation queue.

**Integration Test**
A test that sends a complete exception through the full system end-to-end and asserts on the output, audit log entry, and escalation queue state.

**Interface Contract Document**
See Section 1. The Phase 3 document specifying every component's inputs, outputs, and data types.

**Knowledge Base**
The collection of documents Mimir searches. In v1: three to four synthetic SOP documents, one per settlement mismatch sub-type. Real FINRA/SEC documents are added in v2.

**LangGraph**
The Python library used to build Huginn's agent as a directed graph — nodes are reasoning steps, edges are transitions, conditional edges implement branching.

**LangSmith**
A debugging and monitoring tool that records every node execution, state transition, and LLM call inside a LangGraph agent — used to trace incorrect decisions back to their source.

**LLM Reasoning at Runtime**
The non-negotiable design decision that Claude API reasons over the retrieved SOP at runtime to produce the confidence score, reasoning trace, and resolution steps. Rule-based scoring without a live LLM call is explicitly rejected as it produces a rules engine, not an agent.

**Mandatory Escalation Keyword Scan**
Runs immediately after classification, before Mimir retrieval. If a trigger keyword is found, the graph exits directly to escalation. Runs pre-retrieval to avoid paying for a Mimir call that would be discarded, and to produce a cleaner audit trail.

**Model Validator**
A Pydantic v2 mechanism for enforcing constraints that span multiple fields — used in Huginn to enforce that `sub_type` values are valid for their parent `type`. Fires at validation time before the data reaches the agent.

**Pydantic**
The Python library FastAPI uses under the hood for data validation and parsing. Huginn uses Pydantic models to enforce the exception schema, the exception type enum, and the sub_type scoping constraint at the API layer.

**Pure Function**
A function that takes inputs and returns outputs without modifying anything outside itself — the design target for each LangGraph node so they can be tested in isolation.

**RAG (Retrieval Augmented Generation)**
The technique underlying Mimir — relevant SOP document chunks are retrieved from the vector store and provided as context to the LLM before it reasons and generates a decision.

**Reasoning Trace**
The LLM's step-by-step explanation of how it arrived at its confidence score and resolution decision. Captured in both the audit log and the escalation queue entry. The primary artifact enabling compliance review.

**Regression Test**
See Section 1.

**Scoring Rubric**
An explicit set of instructions included in the LLM reasoning prompt that defines what constitutes a high versus low confidence decision and how to weight the sub_type, description, and SOP content. Anchors confidence scores across runs, making them more consistent and defensible. The rubric text lives in `agent/nodes.py` and is iterated during the feedback loop phase.

**sentence-transformers**
The local library that converts SOP document text into vector embeddings for storage in Chroma. Runs without an API key.

**Similarity Score**
A numeric value returned by Chroma alongside each retrieved chunk indicating how semantically close the chunk is to the query. Included in Mimir's structured return dict and available as an additional signal for the LLM reasoning prompt.

**Similarity Search**
The mechanism Mimir uses to find the SOP chunks most relevant to the current exception — finds by meaning not by keyword.

**SQLite**
The local database used alongside `audit.jsonl` for queryable audit log storage. Built into Python's standard library, requires no external service. ⚠️ *Evolved: added in Socratic Design; initial design used flat file only.*

**State Machine**
The model of Huginn's agent execution — a system that moves through defined states (classification, retrieval, reasoning, decision, logging) via conditional transitions. Implemented in LangGraph.

**Structured Output**
A response formatted to a defined schema. Huginn's LLM call is prompted to return a structured JSON object containing exactly three fields: `confidence_score`, `reasoning_trace`, and `resolution_steps`.

**Sub-Type Scoping**
The constraint that valid `sub_type` values are determined by the parent `type` value. Enforced at the Pydantic layer via a model validator. Prevents logically invalid combinations (e.g. a `corporate_action_failure` sub_type on a `settlement_mismatch` exception). Sets up v2 expansion cleanly — new exception types bring their own scoped sub_type sets.

**Synchronous Processing**
Huginn v1 handles one exception completely before starting the next. Designed behind a fake async API boundary so v2 can add a real queue without changing the API contract.

**Unit Test**
A test that checks a single LangGraph node or Mimir function in complete isolation — enabled by the pure function design target for each component.

**Vector Store**
A database that stores embeddings and supports similarity search. Huginn uses Chroma as its vector store for Mimir in v1.

**Vertical Slicing**
See Section 1.
