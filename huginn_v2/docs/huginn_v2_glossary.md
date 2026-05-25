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
The official, continuously updated online publication of US federal regulations. Huginn's knowledge base uses the eCFR as the source for SEC Rules 15c6-1 and 15c6-2 — the rule text is current and authoritative.

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
The Buy-In Procedures and Requirements rule. Governs the formal close-out procedure when a seller fails to deliver securities. Specifies the timing, notice requirements, and execution procedures for a buyer to purchase replacement securities and charge the cost to the defaulting seller. One of the most structurally complex rules in Huginn's knowledge base — seven pages with multiple lettered subsections, including sample buy-in forms that produce duplicate section markers handled by sequential suffixing in `build_index.py`.

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
Huginn v2's document chunking strategy. Rather than splitting regulatory documents at arbitrary character boundaries (v1's approach), v2 splits on structural boundaries defined by the documents' own authors — lettered subsections `(a)`, `(b)`, `(c)` etc. Each subsection becomes one chunk, with the parent rule identifier and section header prepended as context. Implemented in `scripts/build_index.py` using a regex parser with a false-split filter and a 200-character minimum length threshold.

**Section ID**
A metadata field attached to every chunk in Huginn's v2 knowledge base. Identifies the specific rule subsection a chunk came from — e.g. `FINRA-11810-b-1`. Composed of the document ID, the lettered section marker, and a sequential suffix to handle documents where the same letter appears multiple times. Enables targeted retrieval in the cross-reference pass and full auditability of which specific rule subsections were consulted.

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
The standard settlement cycle for most US broker-dealer securities transactions, as required by SEC Rule 15c6-1 since May 28, 2024. Means settlement must occur by the first business day after the trade date. Replaced the previous T+2 standard. The `wrong_settlement_date` exception sub-type in Huginn frequently involves disputes about whether T+1 or a legitimate exception applies.

**T+2**
The settlement cycle standard prior to May 2024, and still applicable in specific circumstances under SEC Rule 15c6-1(c): firm commitment underwritten offerings priced after 4:30 p.m. ET default to T+2 rather than T+1. The distinction between T+1 and T+2 applicability is a key exception applicability question in Huginn's regulatory reasoning rubric.

**Trade Exception**
A flagged problem in a financial transaction that cannot complete automatically and requires investigation or resolution. Huginn's input. In practice, exceptions are generated by back-office systems when internal records fail to reconcile with counterparty records at settlement.

**Two-Pass Retrieval**
Huginn v2's retrieval strategy, implemented in `mimir/retriever.py`. Pass 1 performs a standard semantic similarity search against the full regulatory knowledge base and returns the most relevant chunks. Pass 2 scans those chunks for explicit references to other rules in the knowledge base and fetches targeted chunks from each referenced rule using metadata filtering. The two passes are combined and deduplicated before being handed to the LLM. Addresses the heavy cross-referencing in regulatory text that single-pass retrieval cannot resolve.

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
The `TypedDict` that flows through every node in the LangGraph graph. Each node receives the full state and returns a partial update — only the fields it is responsible for. The state carries the original exception, every intermediate value produced by each node, and the final outcome. See `agent/state.py`. In v2, carries `retrieved_document_ids` (list of strings) instead of the v1 `retrieved_document_id` (single string).

**Auto-Resolve (outcome value)**
The string `"auto_resolve"` written to the `outcome` field of the agent state when the confidence score meets or exceeds the escalation threshold (0.75). Triggers the audit log write but does not write to the escalation queue.

**Classify Node**
The first node every exception passes through. Extracts the exception type and sub-type from the incoming payload and scans the description for mandatory escalation keywords. If a keyword is found, sets `triggered_keyword` and the graph routes to the fast-exit path. If no keyword is found, the graph routes to the standard path.

**Confidence Score**
A float between 0.0 and 1.0 produced by the Claude API during the reason node. Represents how confident the LLM is that the exception can be resolved given the retrieved regulatory context. Scores at or above 0.75 produce auto-resolve outcomes; scores below 0.75 produce escalation. Produced by the v2 regulatory reasoning rubric — not directly comparable to v1 scores, which used a different rubric against synthetic SOP documents.

**Cross-Reference Pass**
The second pass in Mimir's two-pass retrieval. After the primary semantic search returns chunks, the cross-reference pass scans those chunks for explicit mentions of other rules in the knowledge base and fetches targeted chunks from each referenced rule using `document_id` metadata filtering. Tagged `retrieved_via: "cross_reference"` in the returned chunk dicts.

**Decide Node**
The node that translates the confidence score into a binary outcome. Compares `state["confidence_score"]` against `ESCALATION_THRESHOLD = 0.75`. If the score is at or above the threshold, sets `outcome = "auto_resolve"`. If below the threshold, or if `confidence_score` is null (system error or fast-exit), sets `outcome = "escalate"`. Does not call the LLM — the decision is deterministic code.

**Escalate (outcome value)**
The string `"escalate"` written to the `outcome` field of the agent state. Triggers both the audit log write and the escalation queue write.

**Escalate Fast-Exit Node**
The terminal node on the mandatory escalation fast-exit path. Sets `outcome = "escalate"` and writes the triggered keyword into `escalation_reason`. Mimir and the LLM are never called on this path — `retrieved_chunks` and `retrieved_document_ids` remain empty lists.

**Fast-Exit Path**
The execution path taken when the classify node detects a mandatory escalation keyword. Bypasses Mimir retrieval and LLM reasoning entirely. Routes directly to `escalate_fast_exit` then `log_result`. In v2, five keywords trigger this path: `sanctions`, `AML`, `regulatory hold`, `buy-in`, `sell-out`.

**Log Result Node**
The terminal node on all paths. Constructs the full audit log event dict from all state fields and calls `logger.log()`. Every execution path terminates here, ensuring every exception is logged regardless of which path was taken. Returns `{"current_node": "log_result"}` — consistent with all other nodes — rather than an empty dict.

**Primary Pass**
The first pass in Mimir's two-pass retrieval. A standard semantic similarity search against the full Chroma index using the query string constructed by the retrieve node. Returns the top-k chunks by cosine similarity score. Tagged `retrieved_via: "primary"` in the returned chunk dicts.

**Reason Node**
The node that calls the Claude API. Constructs a prompt containing the regulatory reasoning rubric (the `SCORING_RUBRIC` constant), the retrieved chunks formatted with `section_id` and `retrieved_via` visible, and the exception payload. Parses the JSON response into `confidence_score`, `reasoning_trace`, and `resolution_steps`. On any failure, returns null values for all LLM fields and sets `escalation_reason = "system_error: ..."`.

**Retrieve Node**
The node that calls Mimir. Constructs the query string as `"{sub_type}: {description}"`, calls `mimir.retrieve()`, and stores the returned chunks in `retrieved_chunks`. Derives `retrieved_document_ids` by collecting unique `document_id` values across all returned chunks from both retrieval passes, preserving insertion order.

**Standard Path**
The execution path taken when no mandatory escalation keyword is detected. Runs the full pipeline: classify → retrieve → reason → decide → log_result. The only path that calls Mimir and the Claude API.

**Triggered Keyword**
The specific keyword that caused the fast-exit path to fire, stored in `state["triggered_keyword"]`. Written to the audit log and to `escalation_reason` in the API response. Null on the standard path.

---

## Part 3 — Implementation Reference

File-by-file breakdown of implementation-specific terms. Organized by source file. For terms that span multiple files, they are defined at their source file and noted where else they appear.

---

### `models/exception.py`

**`ExceptionType`**
A Pydantic string enum with a single value: `settlement_mismatch`. All other values are rejected at the API boundary with a structured 422 error. Defined as a separate enum rather than a literal so v3 can add new exception types by extending the enum without modifying the `TradeException` model structure.

**`SettlementMismatchSubType`**
A Pydantic string enum with three values: `price_mismatch`, `quantity_mismatch`, `wrong_settlement_date`. Scoped to the `settlement_mismatch` parent type and enforced by the model validator.

**`Severity`**
A Pydantic string enum with three values: `low`, `medium`, `high`. Present in the schema and captured in the audit log on every record, but not passed to the LLM in v2. Activation as a reasoning input is deferred to v3, but capturing it now means v3 can analyze severity-outcome correlation from real v2 audit data.

**`model_validator`**
A Pydantic v2 decorator applied to `TradeException` to enforce sub-type scoping. Validates that the `sub_type` value is appropriate for the `type` value. Exists as a separate validator function — not collapsed into the enum definition — so v3 can add new type/sub-type pairs by extending the validator's mapping without modifying the enum structure.

---

### `mimir/index.py`

**`PERSIST_DIR`**
The path string (`"knowledge_base/processed"`) where `build_index.py` writes the Chroma index and from which `mimir/retriever.py` loads it. The single shared constant prevents silent drift: if the two files disagreed on this path, the retriever would load from a nonexistent or empty directory and return no results without raising an error.

**`EMBEDDING_MODEL`**
The HuggingFace sentence transformer model identifier (`"sentence-transformers/all-mpnet-base-v2"`) shared between `build_index.py` and `mimir/retriever.py`. The index and the retriever must use the same embedding model — querying an index with a different model produces meaningless similarity scores without raising any error.

---

### `mimir/retriever.py`

**`TOP_K_CROSS_REF = 2`**
The number of chunks fetched per referenced rule in the cross-reference pass (Pass 2). Independent of the `top_k` parameter passed by the caller, which controls Pass 1 only. Smaller than `top_k` because Pass 2 fetches targeted context for a known reference, not a broad relevance search.

**`SUBSTRING_TO_DOCUMENT_ID`**
A dict mapping rule number substrings to their full `document_id` values: `{"15c6-1": "SEC-15c6-1", "15c6-2": "SEC-15c6-2", "11100": "FINRA-11100", ...}`. Serves a dual purpose: the keys are used for cross-reference detection (substring search against chunk text), and the values are used to construct the `document_id` filter for Pass 2 queries. The design document specified two separate constants (`KNOWN_DOCUMENT_IDS` and a mapping); the implementation collapses them into one dict because iterating `items()` provides both in a single pass. Adding a new regulatory document requires one entry here.

**`_vectorstore`**
A module-level singleton holding the loaded Chroma index. Initialized lazily on the first `retrieve()` call via `_get_vectorstore()`. Loading the HuggingFace embedding model and the persisted Chroma index is expensive — doing it once at module level means all subsequent requests reuse the same in-memory store.

**`retrieved_via`**
A field in every returned chunk dict indicating which retrieval pass produced it. Value is `"primary"` (Pass 1 semantic search) or `"cross_reference"` (Pass 2 targeted retrieval). Enables the audit log to record which chunks came from each pass without exposing retrieval internals through the public interface. Visible to the LLM in the reasoning prompt.

**Deduplication**
The step that combines Pass 1 and Pass 2 results and removes chunks that appear in both. Keyed on `section_id`. When a chunk appears in both passes, the `"primary"` tagged version is retained — it was most relevant in the semantic search, and preserving that tag is more accurate for audit purposes than replacing it with `"cross_reference"`.

---

### `logger/audit.py`

**`_db_initialized`**
A module-level boolean flag that prevents `_init_db()` from opening a new SQLite connection and running `CREATE TABLE IF NOT EXISTS` on every call to `log()`. Set to `True` after the first successful initialization. The additional `AUDIT_DB.exists()` check in `_init_db()` handles process restarts — the in-memory flag resets to `False`, but if the database file already exists it need not be recreated.

**`INSERT OR REPLACE`**
The SQLite statement used for audit log rows. `job_id` is the primary key. If a job ID is somehow written twice, the second write replaces the first rather than raising a uniqueness error. In practice this does not occur — job IDs are UUIDs generated per request.

**`full_event_json`**
A SQLite column storing the entire event dict serialized as a JSON string. Individual columns (`outcome`, `confidence_score`, etc.) support efficient queries on common fields. `full_event_json` ensures no data is lost regardless of which columns exist — when v3 adds new fields to the event dict, they appear in `full_event_json` automatically without a schema migration. The `GET /exceptions/{job_id}` and `GET /escalations` endpoints read this column directly.

**`decision_timestamp`**
A field in the audit log event dict set by the `log_result` node using `datetime.now(timezone.utc).isoformat()`. Distinguished from `timestamp` (the original exception timestamp from the incoming payload). Uses UTC explicitly — naive datetimes in a financial audit log are a compliance liability because there is no way to determine the timezone from the value alone.

**`retrieved_document_ids` (SQLite column)**
Stored as a JSON-serialized string (e.g. `'["FINRA-11810", "FINRA-11710"]'`). The `full_event_json` column always contains the authoritative copy; this column supports direct SQL queries on document ID membership without parsing the full JSON.

---

### `agent/state.py`

**`TypedDict`**
The Python typing construct used to define `AgentState`. LangGraph's `StateGraph` expects a `TypedDict` as its state type. Nodes receive and return plain dicts; LangGraph merges the partial return into the full state. Using Pydantic here would require conversion to and from dicts at every node boundary.

**`retrieved_document_ids`**
A `list[str]` field in `AgentState` carrying the unique `document_id` values across all chunks returned by Mimir, in the order they first appeared in the combined chunk list. Populated by the retrieve node. Empty list on the fast-exit path. Replaces v1's `retrieved_document_id: str | None` (single string or null). Stored separately from `retrieved_chunks` so the API response and audit log can include the flat list without recomputing it from the chunk list on every access.

**`llm_raw_response`**
The Claude API's raw text response before JSON parsing. Stored in state and written to the audit log for full fidelity. If the API returns malformed JSON or wraps the response in markdown fences, this field captures exactly what came back — enabling debugging without re-running the exception.

**`current_node`**
A string field updated by every node to record the name of the last node that executed. LangGraph does not natively expose the currently executing node as a readable value. This field is the workaround, updated as a convention by every node including `log_result`.

---

### `agent/nodes.py`

**`SCORING_RUBRIC`**
A module-level string constant containing the full text of the four-factor regulatory reasoning rubric passed to the Claude API in the reason node. Defined at module level — not assembled inside the `reason()` function — because it is the primary artifact for v3 prompt engineering. Every confidence score in the v2 audit log was produced by this exact text against `LLM_MODEL`. Changes to this constant change the system's scoring behavior.

**`ESCALATION_THRESHOLD = 0.75`**
The module-level constant controlling the auto-resolve/escalate boundary. Applies to all sub-types in v2. Carried forward from v1 as a provisional value — recalibrate after v2 audit log data accumulates against real regulatory documents and the new rubric. Per sub-type thresholds are a v3 feature.

**`LLM_MODEL = "claude-sonnet-4-6"`**
The Claude API model identifier. Defined as a module-level constant so the model string is easy to locate and update when a new model is released. Every confidence score in the v2 audit log was produced by this model against `SCORING_RUBRIC`.

**`ESCALATION_KEYWORDS`**
The module-level list of mandatory escalation keywords. In v2: `["sanctions", "AML", "regulatory hold", "buy-in", "sell-out"]`. A list (not a set) because list iteration preserves order — the first matching keyword is recorded in `triggered_keyword`. Detection is case-insensitive.

**Markdown fence stripping**
A defensive parsing step in the reason node. The Claude API is instructed to return raw JSON, but the model sometimes wraps the response in triple-backtick code fences. The stripping logic checks for a leading ` ``` `, removes the fence and optional `json` language tag, and strips the trailing fence before calling `json.loads()`. Without this, the JSON parse fails and the exception auto-escalates with a `system_error`.

**`dict.fromkeys()` for `retrieved_document_ids`**
Used in the `retrieve` node as `list(dict.fromkeys(c["document_id"] for c in chunks))`. Deduplicates while preserving insertion order, which `set()` does not. The ordering reflects which documents appeared first in the combined chunk list (Pass 1 results before Pass 2 results), producing a more meaningful ID list than arbitrary set ordering.

---

### `agent/graph.py`

**`_route_after_classify(state)`**
A LangGraph routing function — not a node. Produces no state update. Reads `triggered_keyword` via `state.get()` (not direct key access) and returns `"fast_exit"` if truthy, `"standard"` if falsy or absent. Used as the conditional function for the edge after the classify node.

**`_route_after_decide(state)`**
A LangGraph routing function — not a node. Reads `outcome` and returns `"auto_resolve"` or `"escalate"`. Both values map to `log_result` in the edge definition — the conditional edge makes the branching explicit in the graph structure without routing to different terminal nodes.

**`huginn_graph = build_graph()`**
The module-level compiled graph instance. Compiled once at import time and reused across all requests in the process. The API layer imports this name directly: `from agent.graph import huginn_graph`. Compilation validates node registrations and compiles edge routing; doing this once avoids the cost on every request.

**`build_graph()`**
The function that constructs and compiles the graph. A separate function (rather than just module-level code) because the test suite imports `build_graph()` to verify the graph structure independently of the `huginn_graph` singleton.

---

### `api/main.py`

**`payload: dict` parameter in `submit_exception`**
`POST /exceptions` accepts a raw dict rather than a typed `TradeException` parameter. If `TradeException` were the FastAPI parameter type, FastAPI would perform automatic validation and return its own 422 format. By accepting a dict and catching `ValidationError` explicitly, the endpoint controls the 422 response body — returning `e.errors()`, which is the Pydantic structured error format.

**`exc.model_dump(mode="json")`**
Converts the validated `TradeException` Pydantic model to a plain dict with JSON-serializable values. `mode="json"` serializes UUID as a hyphenated string and datetime as ISO 8601 — necessary because the agent state, audit logger, and JSON responses all require plain serializable dicts. The design documents described a `model_dump_json() + json.loads()` round-trip; the implementation uses `model_dump(mode="json")` directly, which produces the same result without the intermediate JSON string.

**Deferred imports in GET endpoints**
`sqlite3`, `json`, and `AUDIT_DB` are imported inside `get_result()` and `get_escalations()` rather than at module level. This keeps the module-level namespace focused on FastAPI and the project components that are needed for every request, not just GET requests.

**`full_event_json` as the GET response source**
Both `GET /exceptions/{job_id}` and `GET /escalations` read `full_event_json` from SQLite and return `json.loads(row[0])` directly. This means the GET response always reflects exactly what the audit logger wrote — no field mapping or reconstruction required.

---

### `scripts/build_index.py`

**`DOCUMENT_MAP`**
A dict mapping PDF filename stems to their `document_id` values. Explicit rather than dynamically derived — a file present in `knowledge_base/raw/` but absent from this dict is skipped with a warning rather than auto-included. The explicit mapping makes the filename-to-ID relationship auditable and prevents unknown files from entering the knowledge base silently.

**`_is_real_section(text, match)`**
A filter function applied to every regex match of `^\([a-z]\)`. Returns `True` only if the text following the match begins with an uppercase character (after stripping leading whitespace and optional quote/parenthesis characters). The purpose: FINRA-11810 contains `(b) through (g) of this Rule shall apply` as a mid-sentence phrase that appears at the start of a line in the extracted PDF text, triggering the section regex. Without this filter, that phrase produces a spurious 292-character chunk that passes the 200-character minimum threshold and is indexed as a real section.

**Section boundary parser**
The custom text processing logic in `build_index.py` that splits regulatory document text into semantically correct chunks. Uses `SECTION_PATTERN = re.compile(r"^\([a-z]\)", re.MULTILINE)` combined with `_is_real_section()` to detect real section headers. Replaces v1's `RecursiveCharacterTextSplitter`. The section header line (`"{document_id} Section ({letter}):\n"`) is prepended to every chunk body, so each chunk is self-contained as a retrievable unit.

**Sequential suffixing**
The `section_id` disambiguation strategy used when a document produces duplicate lettered section markers. The first occurrence of `(b)` in a document produces `section_id = "FINRA-11810-b-1"`, the second produces `"FINRA-11810-b-2"`. Applied to all documents for consistency — documents with no duplicates use the `-1` suffix throughout. Handles the known case of FINRA-11810's sample buy-in forms, which restart the lettered section labeling after the main rule text.

**Preamble chunk**
A chunk produced from text that appears before the first lettered section in a document. For eCFR-sourced PDFs (SEC-15c6-1 and SEC-15c6-2), this includes the regulatory header and scope language. Assigned `section_id = "{document_id}-preamble"`. Short preambles (under 200 characters) are prepended to the first section rather than indexed as standalone chunks.

**Duplicate `section_id` gate check**
A validation step that runs after all chunks are assembled but before `Chroma.from_documents()` is called. If any two chunks share a `section_id`, the script prints an error and exits. This prevents a silent data quality problem: the deduplication logic in `mimir/retriever.py` uses `section_id` as its key — a collision would cause one chunk to be silently dropped on every retrieval.

**Chunk inspection log**
A stdout summary printed before the Chroma index is built. Lists each document with its chunk count, and each chunk with its `section_id` and character count. The gate for Subplan 2 — must be inspected manually to confirm section boundaries are semantically correct before proceeding. The log prints before building so a misconfigured parser can be fixed without having written a broken index.
