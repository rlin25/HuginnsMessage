# Huginn v2 — Glossary

---

## Part 1 — Domain and System Overview

Terms in this section are readable without any technical background. If you have already read the README, this section fills in the domain vocabulary behind it.

---

**AML (Anti-Money Laundering)**
A regulatory and legal framework requiring financial firms to detect and report activity that may be used to disguise illegally obtained funds. Any trade exception whose description mentions AML is immediately escalated by Huginn without further analysis — it is too sensitive to be handled automatically.

**Audit Log**
A complete, tamper-evident record of every decision Huginn makes. For every trade exception processed, the audit log records what the exception was, what reasoning was applied, what the outcome was, and why. Exists in two forms simultaneously: a human-readable flat file (`logs/audit.jsonl`) and a queryable database (`logs/audit.db`). The dual format serves two different audiences — a compliance officer reading the file and a developer running queries against the database.

**Auto-Resolve**
The outcome when Huginn is confident enough to close out a trade exception without human involvement. The decision is recorded in the audit log, but no human reviewer is notified. The exception is considered handled.

**Buy-In**
A formal close-out procedure governed by FINRA Rule 11810. When a seller fails to deliver securities by the contractually required date, the buyer may — after providing written notice and waiting the required period — purchase replacement securities in the open market and charge the cost to the defaulting seller. Any trade exception whose description mentions a buy-in is immediately escalated by Huginn — the exception has already progressed past normal triage into formal regulatory remedy, requiring human oversight regardless of confidence score. Added as a mandatory escalation keyword in v2.

**Compliance**
The requirement that every decision made by an automated system in a regulated industry be fully traceable and reconstructible. Huginn's full-fidelity audit log is designed from the start to satisfy compliance requirements — every input, every intermediate value, and every output is preserved.

**Condition Match**
One of the four factors in Huginn v2's regulatory reasoning scoring rubric. Measures whether the exception facts satisfy the triggering conditions specified in the retrieved regulatory rule — does the described scenario meet the threshold or criteria the rule requires for a specific obligation or remedy to apply. A clear condition match is necessary for a high confidence score.

**Counterparty**
The other party to a trade. In a stock purchase, the buyer and the seller are counterparties to each other. Settlement mismatches occur when the buyer's records and the seller's records disagree.

**Cross-Reference Resolution**
One of the four factors in Huginn v2's regulatory reasoning scoring rubric. Measures whether all rules referenced within the retrieved chunks were also retrieved and considered. Regulatory documents cross-reference each other heavily — a retrieved chunk may say "the remedy is provided for by Rules 11810 and 11820" without those rules' content. Unresolved cross-references lower the confidence score because the complete regulatory picture is not available. Resolved by Mimir's two-pass retrieval.

**eCFR (Electronic Code of Federal Regulations)**
The official, continuously updated online publication of US federal regulations. Huginn's knowledge base uses the eCFR as the source for SEC Rules 15c6-1 and 15c6-2 — the rule text is current and authoritative. Available at `ecfr.gov`.

**Escalation**
The outcome when Huginn is not confident enough to handle a trade exception automatically, or when the exception contains a term that requires immediate human review regardless of confidence. Escalated exceptions are written to the escalation queue — the human reviewer's inbox.

**Escalation Queue**
A separate file (`logs/escalation_queue.jsonl`) that receives every exception Huginn escalates. It represents the human reviewer's inbox. Every record in this file is a complete copy of the audit log entry — the reviewer has full context without needing to look anywhere else. Accessible via the `GET /escalations` API endpoint.

**Exception**
See *Trade Exception*.

**Exception Applicability**
One of the four factors in Huginn v2's regulatory reasoning scoring rubric. Measures whether any of the rule's carve-outs, exceptions, or exclusions apply to the described exception. For example: does Rule 15c6-1's T+1 requirement apply, or does the late-pricing T+2 exception apply? Does Rule 11810 apply, or is the contract subject to a registered clearing agency's buy-in requirements instead? Applicable exceptions lower the confidence score because they change the regulatory obligation.

**FINRA (Financial Industry Regulatory Authority)**
The US self-regulatory body overseeing broker-dealers. Publishes publicly accessible rulebooks covering settlement, clearance, and compliance. Huginn v2's knowledge base includes four FINRA rules: 11100 (Uniform Practice Code scope), 11710 (General Provisions), 11810 (Buy-In Procedures), and 11820 (Selling-Out).

**FINRA Rule 11100**
The scope and definitions rule of FINRA's Uniform Practice Code. Establishes which over-the-counter transactions between members are governed by the UPC, defines key terms including "delivery date" (used interchangeably with "settlement date"), and specifies that failure to deliver does not cancel the contract — the remedy is provided by Rules 11810 and 11820. Included in Huginn's v2 knowledge base as the foundational regulatory context for settlement mismatch exceptions.

**FINRA Rule 11710**
The General Provisions rule governing reclamations — a claim for the right to return or demand the return of a security that has been previously delivered. Included in Huginn's v2 knowledge base as a dependency of Rule 11820: the sell-out rule references the Uniform Reclamation Form defined in 11710, and an exception involving a disputed reclamation cannot be reasoned against 11820 without it.

**FINRA Rule 11810**
The Buy-In Procedures and Requirements rule. Governs the formal close-out procedure when a seller fails to deliver securities. Specifies the timing, notice requirements, and execution procedures for a buyer to purchase replacement securities and charge the cost to the defaulting seller. One of the most structurally complex rules in Huginn's knowledge base — seven pages with fifteen lettered subsections, including sample buy-in forms that produce duplicate section markers handled by sequential suffixing in `build_index.py`.

**FINRA Rule 11820**
The Selling-Out rule. The mirror image of Rule 11810 — governs the formal close-out procedure when a buyer fails to accept delivery. The seller may sell the securities in the best available market and charge any losses to the defaulting buyer. References Rule 11710 for the Uniform Reclamation Form requirements.

**Human-in-the-Loop**
A design pattern where an automated system defers to a human when it lacks sufficient confidence or when the situation is too sensitive to handle automatically. Huginn implements this via the escalation queue — escalated exceptions wait for a human reviewer rather than being resolved automatically.

**Huginn**
The AI agent at the center of this system. Named after one of Odin's two ravens — Huginn representing thought. Receives flagged trade exceptions, classifies them, retrieves relevant regulatory document chunks from the knowledge base, evaluates confidence using a regulatory reasoning rubric, and decides to auto-resolve or escalate. Every decision is logged.

**Knowledge Base**
The collection of regulatory documents Huginn consults when evaluating a trade exception. In v2, this consists of six real regulatory documents sourced from FINRA and the SEC: Rules 11100, 11710, 11810, 11820 (FINRA) and Rules 15c6-1 and 15c6-2 (SEC). V1 used synthetic Standard Operating Procedure documents — v2 replaces them entirely with real regulatory text.

**Mandatory Escalation Keyword**
A term in a trade exception description that triggers immediate escalation without consulting the knowledge base or the LLM. In v2, five keywords are defined: `sanctions`, `AML`, `regulatory hold`, `buy-in`, `sell-out`. Each represents a scenario where automated confidence scoring is inappropriate regardless of retrieval quality — the stakes are too high or the situation has already progressed beyond normal triage.

**Mimir**
The retrieval component that searches the knowledge base. Named after the Norse keeper of wisdom. When Huginn needs to look up regulatory context, it queries Mimir with a description of the exception. In v2, Mimir performs two-pass retrieval: a semantic search pass followed by a targeted cross-reference resolution pass. Mimir knows nothing about escalation logic, confidence scoring, or trade operations — it only retrieves.

**Obligation Clarity**
One of the four factors in Huginn v2's regulatory reasoning scoring rubric. Measures whether the retrieved rule specifies a clear required action given the exception facts, or whether the rule leaves the required response ambiguous or conditional on additional facts not present in the exception description. High obligation clarity is required for a high confidence score.

**Price Mismatch**
A type of settlement mismatch where the buyer's and seller's records disagree on the agreed price of a transaction. One of three sub-types handled by Huginn v1 and v2.

**Quantity Mismatch**
A type of settlement mismatch where the buyer's and seller's records disagree on the number of units transacted. One of three sub-types handled by Huginn v1 and v2.

**RAG (Retrieval-Augmented Generation)**
The technique underlying Mimir. Rather than relying solely on the AI model's training data, relevant document chunks are retrieved from a knowledge base and provided as context before the model reasons and generates a response. This makes the system's knowledge grounded in real regulatory documents rather than the model's general training.

**Reclamation**
A claim for the right to return or demand the return of a security that has been previously delivered. Governed by FINRA Rule 11710. Relevant to Huginn's knowledge base because Rule 11820's sell-out procedure requires a properly executed Uniform Reclamation Form before the seller may sell out — an exception involving a reclamation dispute is governed by both 11710 and 11820.

**Regulatory Hold**
A restriction placed on a trade or position pending regulatory review. Any trade exception mentioning a regulatory hold is immediately escalated by Huginn — it cannot be auto-resolved while a regulator is actively reviewing the underlying transaction.

**Regulatory Reasoning Rubric**
The scoring framework used by Huginn v2's LLM reasoning node. Replaces the SOP-oriented rubric from v1. Built around four factors specific to reasoning against legal text: condition match, obligation clarity, exception applicability, and cross-reference resolution. Each factor reflects a distinct cognitive task the LLM performs when evaluating whether a regulatory rule applies to an exception and what it requires.

**Sanctions**
Restrictions imposed by governments or international bodies prohibiting or limiting transactions with specific entities, individuals, or countries. Any trade exception mentioning sanctions is immediately escalated by Huginn — sanctions compliance is a legal requirement that cannot be delegated to an automated confidence score.

**SEC Rule 15c6-1**
The SEC rule governing the standard settlement cycle for most broker-dealer securities transactions. Amended in 2023 to shorten the cycle from T+2 to T+1 (effective May 28, 2024). Paragraph (a) prohibits broker-dealers from entering into contracts that provide for settlement later than T+1, unless otherwise agreed at the time of the transaction. Contains exceptions for certain security types and for firm commitment offerings priced after 4:30 p.m. ET (which default to T+2). The primary regulatory source for Huginn's `wrong_settlement_date` sub-type.

**SEC Rule 15c6-2**
The SEC rule requiring broker-dealers to complete trade allocations, confirmations, and affirmations by the end of trade date to support T+1 settlement. Either written agreements or written policies and procedures must be in place. Included in Huginn's knowledge base as a companion to Rule 15c6-1 — together they define the full regulatory framework for T+1 settlement obligations.

**Section-Aware Chunking**
Huginn v2's document chunking strategy. Rather than splitting regulatory documents at arbitrary character boundaries (v1's approach), v2 splits on structural boundaries defined by the documents' own authors — lettered subsections `(a)`, `(b)`, `(c)` etc. Each subsection becomes one chunk, with the parent rule identifier and section header prepended as context. Implemented in `scripts/build_index.py` using a regex parser with a minimum chunk length threshold.

**Section ID**
A metadata field attached to every chunk in Huginn's v2 knowledge base. Identifies the specific rule subsection a chunk came from — e.g. `FINRA-11810-b-1`. Composed of the document ID, the lettered section marker, and a sequential suffix to handle documents where the same letter appears multiple times (as in FINRA-11810's sample form appendix). Enables targeted retrieval in the cross-reference pass and full auditability of which specific rule subsections were consulted.

**Sell-Out**
A formal close-out procedure governed by FINRA Rule 11820. When a buyer fails to accept delivery of securities, the seller may sell the securities in the best available market and charge any losses to the defaulting buyer. Any trade exception whose description mentions a sell-out is immediately escalated by Huginn — the exception has already progressed into formal regulatory remedy. Added as a mandatory escalation keyword in v2.

**Settlement**
The actual completion of a trade — the physical exchange of cash for securities, or one currency for another. Under SEC Rule 15c6-1 (as amended in 2024), settlement for most US securities transactions must occur by T+1 — the business day following the trade date. Trade exceptions in Huginn occur at the settlement stage.

**Settlement Fail**
When a trade does not complete on its scheduled settlement date. One party (or both) failed to deliver what they were supposed to. The exception system exists to catch and resolve these failures. Settlement fails that are not resolved through normal triage are subject to formal close-out procedures under FINRA Rules 11810 and 11820.

**Settlement Mismatch**
The only category of trade exception handled by Huginn v1 and v2. A flagged disagreement between buyer and seller records at the settlement stage — on price, quantity, or settlement date. All other exception types are rejected at the API boundary.

**SOP (Standard Operating Procedure)**
A documented step-by-step process for handling a specific type of situation. Huginn's v1 knowledge base consisted entirely of synthetic SOPs — one per settlement mismatch sub-type — written for a fictional financial firm. V2 replaces synthetic SOPs entirely with real regulatory documents. The term SOP no longer describes Huginn's knowledge base after v1.

**T+1**
The standard settlement cycle for most US broker-dealer securities transactions, as required by SEC Rule 15c6-1 since May 28, 2024. Means settlement must occur by the first business day after the trade date. Replaced the previous T+2 standard. The `wrong_settlement_date` exception sub-type in Huginn frequently involves disputes about whether T+1 or a legitimate exception (late-pricing T+2, or a mutually agreed alternative) applies.

**T+2**
The settlement cycle standard prior to May 2024, and still applicable in specific circumstances under SEC Rule 15c6-1(c): firm commitment underwritten offerings priced after 4:30 p.m. ET default to T+2 rather than T+1. The distinction between T+1 and T+2 applicability is a key exception applicability question in Huginn's regulatory reasoning rubric.

**Trade Exception**
A flagged problem in a financial transaction that cannot complete automatically and requires investigation or resolution. Huginn's input. In practice, exceptions are generated by back-office systems when internal records fail to reconcile with counterparty records at settlement.

**Two-Pass Retrieval**
Huginn v2's retrieval strategy, implemented in `mimir/retriever.py`. Pass 1 performs a standard semantic similarity search against the full regulatory knowledge base and returns the most relevant chunks. Pass 2 scans those chunks for explicit references to other rules in the knowledge base and fetches targeted chunks from each referenced rule. The two passes are combined and deduplicated before being handed to the LLM. Addresses the heavy cross-referencing in regulatory text that single-pass retrieval cannot resolve.

**Uniform Practice Code (UPC)**
The body of FINRA rules (the 11000 series) governing operational and settlement practices for over-the-counter securities transactions between members. Establishes uniform standards for trade terms, deliveries, payments, and close-out procedures. FINRA Rules 11100, 11710, 11810, and 11820 — all part of Huginn's v2 knowledge base — are sections of the Uniform Practice Code.

**Uniform Reclamation Form**
A standardized form specified in FINRA Rule 11710, required when a receiving broker returns a security that has been previously delivered. Rule 11820 requires a properly executed Uniform Reclamation Form (or equivalent depository-generated advice) before a sell-out can proceed. Its absence is one of the triggering conditions for a sell-out.

**Wrong Settlement Date**
A type of settlement mismatch where the recorded settlement date in one party's system differs from the other's. One of three sub-types handled by Huginn v1 and v2. The primary regulatory source is SEC Rule 15c6-1, which defines what the correct settlement date should be and what exceptions apply.

---

## Part 2 — State Machine and Execution Paths

This section defines the logic layer of Huginn's agent. A reader familiar with the system overview who wants to understand how the agent makes decisions will encounter these terms before opening any source file.

---

**AgentState**
The data object that flows through every node in the LangGraph graph. Each node receives the full state and returns a partial update — only the fields it is responsible for. The state carries the original exception, every intermediate value produced by each node, and the final outcome. See `agent/state.py`. In v2, carries `retrieved_document_ids` (list of strings) instead of `retrieved_document_id` (single string).

**Auto-Resolve (outcome value)**
The string `"auto_resolve"` written to the `outcome` field of the agent state when the confidence score meets or exceeds the escalation threshold (0.75). Triggers the audit log write but does not write to the escalation queue.

**Classify Node**
The first node every exception passes through. Extracts the exception type and sub-type from the incoming payload and scans the description for mandatory escalation keywords. If a keyword is found, sets `triggered_keyword` and the graph routes to the fast-exit path. If no keyword is found, the graph routes to the standard path.

**Confidence Score**
A float between 0.0 and 1.0 produced by the Claude API during the reason node. Represents how confident the LLM is that the exception can be resolved given the retrieved regulatory context. Scores at or above 0.75 produce auto-resolve outcomes; scores below 0.75 produce escalation. Produced by the v2 regulatory reasoning rubric — not directly comparable to v1 scores, which used a different rubric against synthetic SOP documents.

**Cross-Reference Pass**
The second pass in Mimir's two-pass retrieval. After the primary semantic search returns chunks, the cross-reference pass scans those chunks for explicit mentions of other rules in the knowledge base and fetches targeted chunks from each referenced rule using `document_id` metadata filtering. Tagged `retrieved_via: "cross_reference"` in the returned chunk dicts.

**Decide Node**
The node that translates the confidence score into a binary outcome. Compares `state["confidence_score"]` against `ESCALATION_THRESHOLD = 0.75`. If the score is at or above the threshold, sets `outcome = "auto_resolve"`. If below the threshold, or if `confidence_score` is null (system error), sets `outcome = "escalate"`. Does not call the LLM — the decision is deterministic code.

**Escalate (outcome value)**
The string `"escalate"` written to the `outcome` field of the agent state. Triggers both the audit log write and the escalation queue write.

**Escalate Fast-Exit Node**
The terminal node on the mandatory escalation fast-exit path. Sets `outcome = "escalate"` and writes the triggered keyword into `escalation_reason`. Mimir and the LLM are never called on this path — `retrieved_chunks` and `retrieved_document_ids` remain empty lists.

**Fast-Exit Path**
The execution path taken when the classify node detects a mandatory escalation keyword. Bypasses Mimir retrieval and LLM reasoning entirely. Routes directly to `escalate_fast_exit` then `log_result`. In v2, five keywords trigger this path: `sanctions`, `AML`, `regulatory hold`, `buy-in`, `sell-out`.

**Log Result Node**
The terminal node on all paths. Constructs the full audit log event dict from all state fields and calls `logger.log()`. Has no state output — it is a side-effect-only node. Every execution path terminates here, ensuring every exception is logged regardless of which path was taken.

**Primary Pass**
The first pass in Mimir's two-pass retrieval. A standard semantic similarity search against the full Chroma index using the query string constructed by the retrieve node. Returns the top-k chunks by cosine similarity. Tagged `retrieved_via: "primary"` in the returned chunk dicts.

**Reason Node**
The node that calls the Claude API. Constructs a prompt containing the regulatory reasoning rubric, the retrieved chunks (with `section_id` and `retrieved_via` fields visible), and the exception payload. Parses the JSON response into `confidence_score`, `reasoning_trace`, and `resolution_steps`. On any failure, returns null values for all LLM fields and sets `escalation_reason = "system_error: ..."`.

**Retrieve Node**
The node that calls Mimir. Constructs the query string as `"{sub_type}: {description}"`, calls `mimir.retrieve()`, and stores the returned chunks in `retrieved_chunks`. Derives `retrieved_document_ids` by collecting unique `document_id` values across all returned chunks from both retrieval passes.

**Standard Path**
The execution path taken when no mandatory escalation keyword is detected. Runs the full pipeline: classify → retrieve → reason → decide → log_result. The only path that calls Mimir and the Claude API.

**Triggered Keyword**
The specific keyword that caused the fast-exit path to fire, stored in `state["triggered_keyword"]`. Written to the audit log and to `escalation_reason` in the API response. Null on the standard path.

---

## Part 3 — Implementation Details

This section defines terms a developer will encounter when reading or modifying the source code. Organized by source file.

---

### `models/exception.py`

**`ExceptionType`**
A Pydantic string enum with a single value: `settlement_mismatch`. All other values are rejected at the API boundary. Defined as a separate enum rather than a literal so v3 can add new exception types by extending the enum without modifying the model structure.

**`SettlementMismatchSubType`**
A Pydantic string enum with three values: `price_mismatch`, `quantity_mismatch`, `wrong_settlement_date`. Scoped to the `settlement_mismatch` parent type and enforced by the model validator.

**`Severity`**
A Pydantic string enum with three values: `low`, `medium`, `high`. Present in the schema and captured in the audit log, but not passed to the LLM in v2. Activation as a reasoning input is deferred to v3.

**`model_validator`**
A Pydantic v2 decorator applied to `TradeException` to enforce sub-type scoping. Validates that the `sub_type` value is appropriate for the `type` value. Exists as a separate validator (rather than collapsing into the enum definition) so v3 can add new type/sub-type pairs without modifying the enum structure.

---

### `scripts/build_index.py`

**`DOCUMENT_METADATA`**
A dict mapping PDF filename stems to their `document_id` values. Explicit mapping rather than dynamic derivation — if a file is present but not in the map, it is skipped with a warning. Ensures `document_id` values are always predictable and match the interface contract's Knowledge Base Reference table.

**Section boundary parser**
The custom text processing logic in `build_index.py` that splits regulatory document text into semantically correct chunks. Uses regex pattern `^\([a-z]\)` with `re.MULTILINE` to detect lettered subsection headers, combined with a 200-character minimum chunk length threshold to prevent false splits on incidental parenthetical references. Replaces v1's `RecursiveCharacterTextSplitter`.

**Sequential suffixing**
The `section_id` disambiguation strategy used when a document produces duplicate lettered section markers. The first occurrence of `(b)` in a document produces `section_id = "FINRA-11810-b-1"`, the second produces `"FINRA-11810-b-2"`. Applied to all documents for consistency — documents with no duplicates use the `-1` suffix throughout. Handles the known case of FINRA-11810's sample buy-in forms, which restart the lettered section labeling after the main rule text.

**Preamble chunk**
A chunk produced from pre-section text in eCFR-sourced PDFs (SEC-15c6-1 and SEC-15c6-2). The eCFR page includes a header before the first lettered section — this text is captured as a separate chunk with `section_id = "{document_id}-preamble"`. It is indexed but has low semantic similarity to settlement mismatch queries and will rarely be retrieved.

**Chunk inspection log**
A stdout summary printed by `build_index.py` before the Chroma index is built. Lists each document with its chunk count and each chunk's `section_id` and character count. The gate for Subplan 2 — must be inspected manually to confirm section boundaries are semantically correct before proceeding.

---

### `mimir/index.py`

**`PERSIST_DIR`**
The path to the directory where `build_index.py` writes the Chroma index. Shared constant between `build_index.py` and `mimir/retriever.py`. If they diverge, the retriever loads an empty or nonexistent index and all retrievals return empty results.

**`EMBEDDING_MODEL`**
The HuggingFace sentence transformer model used to generate vector embeddings. `"sentence-transformers/all-mpnet-base-v2"`. Shared constant between `build_index.py` and `mimir/retriever.py`. If they diverge, the retriever cannot query the index — embeddings must be generated by the same model that built the index.

---

### `mimir/retriever.py`

**`TOP_K_CROSS_REF = 2`**
The number of chunks fetched per referenced rule in the cross-reference pass (Pass 2). Independent of the `top_k` parameter passed by the caller, which controls Pass 1 only. Smaller than `top_k` because Pass 2 fetches for specific context on a known reference, not a broad relevance search. Defined as a module-level constant so it is visible and tunable without reading the retrieval logic.

**`KNOWN_DOCUMENT_IDS`**
The set of rule number substrings used for cross-reference detection: `{"15c6-1", "15c6-2", "11100", "11710", "11810", "11820"}`. String matching checks whether any of these substrings appear in a chunk's text. Kept as a module-level constant so adding a new document in v3 requires updating only this set and `SUBSTRING_TO_DOCUMENT_ID`.

**`SUBSTRING_TO_DOCUMENT_ID`**
A dict mapping the rule number substrings in `KNOWN_DOCUMENT_IDS` to their full `document_id` values used in Chroma metadata filtering. E.g. `"11810" → "FINRA-11810"`. Required because cross-reference detection finds the substring `"11810"` in chunk text, but the Chroma `where` filter needs the full `document_id` string `"FINRA-11810"`.

**`retrieved_via`**
A field in every returned chunk dict indicating which retrieval pass produced it. Value is either `"primary"` (Pass 1 semantic search) or `"cross_reference"` (Pass 2 targeted retrieval). Enables the audit log to record which chunks came from each pass without exposing pass internals through the public interface.

**`similarity_search_with_score(query, k=top_k)`**
The Chroma method used for Pass 1. Returns `(Document, score)` tuples. The score is cosine distance — lower distance means higher similarity. The retriever exposes this as `similarity_score` in the returned chunk dict.

**Deduplication**
The step that combines Pass 1 and Pass 2 results and removes duplicate chunks. Deduplication is keyed on `section_id`. When a chunk appears in both passes, the `"primary"` tagged version is retained and the `"cross_reference"` duplicate is discarded.

---

### `logger/audit.py`

**`INSERT OR REPLACE`**
The SQLite statement used for audit log rows. `job_id` is the primary key. If a job ID is somehow written twice, the second write replaces the first rather than raising a uniqueness error. In practice this does not occur — job IDs are UUIDs.

**`full_event_json`**
A SQLite column storing the entire event dict serialized as a JSON string. Individual columns (`outcome`, `confidence_score`, etc.) support queries on common fields. `full_event_json` ensures no data is lost regardless of which columns exist — when v3 adds new fields to the event dict, they appear in `full_event_json` automatically without a schema migration.

**`retrieved_document_ids`**
Stored in the SQLite `audit_log` table as a JSON-serialized string (e.g. `'["FINRA-11810", "FINRA-11710"]'`). Queryable by parsing the JSON string. The `full_event_json` column always contains the authoritative copy.

---

### `agent/state.py`

**`TypedDict`**
The Python typing construct used to define `AgentState`. LangGraph's `StateGraph` expects a `TypedDict` as its state type. Each node receives and returns plain dicts; LangGraph merges the partial return into the full state.

**`retrieved_document_ids`**
A `list[str]` field in `AgentState` carrying the unique `document_id` values across all chunks returned by Mimir. Populated by the retrieve node. Empty list on the fast-exit path. Replaces v1's `retrieved_document_id: str | None` (single string).

**`llm_raw_response`**
The Claude API's raw text response before JSON parsing. Stored in state and written to the audit log for full fidelity. If the API returns malformed JSON, this field captures exactly what came back, enabling debugging without re-running the exception.

---

### `agent/nodes.py`

**`ESCALATION_THRESHOLD = 0.75`**
The module-level constant controlling the auto-resolve/escalate boundary. Applies to all sub-types in v2. Carried forward from v1 as a provisional value — recalibrate after v2 audit log data accumulates against real regulatory documents. Per sub-type thresholds are a v3 feature.

**`LLM_MODEL = "claude-sonnet-4-6"`**
The Claude API model identifier. Defined as a module-level constant so it is easy to update when a new model is released. The model string must match an available Anthropic model at runtime.

**`ESCALATION_KEYWORDS`**
The module-level list of mandatory escalation keywords. In v2: `["sanctions", "AML", "regulatory hold", "buy-in", "sell-out"]`. Detection is case-insensitive. Expanded from v1's three keywords to include `"buy-in"` and `"sell-out"` following Phase 1 regulatory document review.

**Markdown fence stripping**
A defensive parsing step in the reason node. The Claude API is instructed to return raw JSON, but the model sometimes wraps the response in markdown code fences. The stripping logic checks for a leading ` ``` `, removes the fence and optional `json` language tag, and strips the trailing fence before calling `json.loads()`. Without this, the JSON parse fails and the exception auto-escalates with a `system_error`.

**Chunk formatting in the LLM prompt**
Each retrieved chunk is formatted in the prompt as:
```
[{section_id}] ({retrieved_via})
{text}
---
```
The `section_id` and `retrieved_via` fields are included so the LLM can reason about which specific regulatory subsections were consulted and whether they came from the primary search or cross-reference resolution.

---

### `agent/graph.py`

**`should_fast_exit(state)`**
A LangGraph routing function. Not a node — it produces no state update. Reads `triggered_keyword` and returns a routing key: `"fast_exit"` or `"standard"`. Used as the condition for the conditional edge after the classify node.

**`should_escalate(state)`**
A LangGraph routing function. Reads `outcome` and returns `"escalate"` or `"resolve"`. Both keys route to `log_result` — the conditional edge exists to make the branching explicit and extensible, not to route to different terminal nodes.

**`huginn_graph = build_graph()`**
The module-level compiled graph instance. Compiled once at import time and shared across all callers in the process. The API layer imports this name directly: `from agent.graph import huginn_graph`.

---

### `api/main.py`

**`_result_store`**
An in-memory dict mapping `job_id` (str) to result dicts. Populated by `POST /exceptions` after the agent completes; read by `GET /exceptions/{job_id}`. Not persistent — cleared on server restart. V3 replaces this with a persistent store when async processing is added.

**`exception.model_dump_json()` + `json.loads()`**
The pattern for converting a Pydantic model to a plain dict with fully serializable values. `model_dump()` alone preserves Python types (UUID objects, datetime objects) that are not JSON-serializable. The JSON round-trip converts them to strings. Necessary because the agent state and audit logger expect plain dicts with string values throughout.

**Fake async job ID pattern**
`POST /exceptions` returns a job ID immediately; `GET /exceptions/{job_id}` retrieves the result. In v2 the agent runs synchronously before the POST response is sent — the result is always ready. The two-endpoint pattern keeps the interface forward-compatible with v3 async processing, where the result may not be ready when the POST returns.
