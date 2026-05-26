# Huginn v1 — Glossary

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

**Compliance**
The requirement that every decision made by an automated system in a regulated industry be fully traceable and reconstructible. Huginn's full-fidelity audit log is designed from the start to satisfy compliance requirements — every input, every intermediate value, and every output is preserved.

**Counterparty**
The other party to a trade. In a stock purchase, the buyer and the seller are counterparties to each other. Settlement mismatches occur when the buyer's records and the seller's records disagree.

**Escalation**
The outcome when Huginn is not confident enough to handle a trade exception automatically, or when the exception contains a term that requires immediate human review regardless of confidence. Escalated exceptions are written to the escalation queue — the human reviewer's inbox.

**Escalation Queue**
A separate file (`logs/escalation_queue.jsonl`) that receives every exception Huginn escalates. It represents the human reviewer's inbox. Every record in this file is a complete copy of the audit log entry — the reviewer has full context without needing to look anywhere else. Accessible via the `GET /escalations` API endpoint.

**Exception**
See *Trade Exception*.

**FINRA (Financial Industry Regulatory Authority)**
The US self-regulatory body overseeing broker-dealers. Publishes publicly accessible rulebooks covering settlement, clearance, and compliance. FINRA regulatory documents are added to Huginn's knowledge base in v2.

**Human-in-the-Loop**
A design pattern where an automated system defers to a human when it lacks sufficient confidence or when the situation is too sensitive to handle automatically. Huginn implements this via the escalation queue — escalated exceptions wait for a human reviewer rather than being resolved automatically.

**Huginn**
The AI agent at the center of this system. Named after one of Odin's two ravens — Huginn representing thought. Receives flagged trade exceptions, classifies them, looks up relevant procedures, evaluates confidence, and decides to auto-resolve or escalate. Every decision is logged. See the README for a plain English description of the full flow.

**Knowledge Base**
The collection of Standard Operating Procedure documents Huginn consults when evaluating a trade exception. In v1, this consists of three synthetic documents — one per settlement mismatch sub-type — written for a fictional financial firm. Real regulatory documents are added in v2. The synthetic nature of the v1 knowledge base is disclosed in the README.

**Mimir**
The retrieval component that searches the knowledge base. Named after the Norse keeper of wisdom. When Huginn needs to look up a procedure, it queries Mimir with a description of the exception. Mimir returns the most relevant document chunks. Mimir knows nothing about escalation logic, confidence scoring, or trade operations — it only retrieves.

**Price Mismatch**
A type of settlement mismatch where the buyer's and seller's records disagree on the agreed price of a transaction. One of three sub-types handled by Huginn v1.

**Quantity Mismatch**
A type of settlement mismatch where the buyer's and seller's records disagree on the number of units transacted. One of three sub-types handled by Huginn v1.

**RAG (Retrieval-Augmented Generation)**
The technique underlying Mimir. Rather than relying solely on the AI model's training data, relevant document chunks are retrieved from a knowledge base and provided as context before the model reasons and generates a response. This makes the system's knowledge specific to the firm's actual procedures rather than generic.

**Regulatory Hold**
A restriction placed on a trade or position pending regulatory review. Any trade exception mentioning a regulatory hold is immediately escalated by Huginn — it cannot be auto-resolved while a regulator is actively reviewing the underlying transaction.

**Sanctions**
Restrictions imposed by governments or international bodies prohibiting or limiting transactions with specific entities, individuals, or countries. Any trade exception mentioning sanctions is immediately escalated by Huginn — sanctions compliance is a legal requirement that cannot be delegated to an automated confidence score.

**Settlement**
The actual completion of a trade — the physical exchange of cash for securities, or one currency for another. Settlement is a distinct event from the original trade agreement, typically occurring two business days later (T+2 convention). Trade exceptions in Huginn occur at the settlement stage.

**Settlement Fail**
When a trade does not complete on its scheduled settlement date. One party (or both) failed to deliver what they were supposed to. The exception system exists to catch and resolve these failures.

**Settlement Mismatch**
The only category of trade exception handled by Huginn v1. A flagged disagreement between buyer and seller records at the settlement stage — on price, quantity, or settlement date. All other exception types are rejected at the API boundary.

**SOP (Standard Operating Procedure)**
A documented step-by-step process for handling a specific type of situation. Huginn's knowledge base in v1 consists entirely of synthetic SOPs — one per settlement mismatch sub-type. When Huginn evaluates an exception, it retrieves the relevant SOP and uses it to reason about the appropriate resolution.

**Trade Exception**
A flagged problem in a financial transaction that cannot complete automatically and requires investigation or resolution. Huginn's input. In practice, exceptions are generated by back-office systems when internal records fail to reconcile with counterparty records at settlement.

**Wrong Settlement Date**
A type of settlement mismatch where the recorded settlement date in one party's system differs from the other's. One of three sub-types handled by Huginn v1.

---

## Part 2 — State Machine and Execution Paths

This section defines the logic layer of Huginn's agent. A reader familiar with the system overview who wants to understand how the agent makes decisions will encounter these terms before opening any source file.

---

**AgentState**
The data object that flows through every node in the LangGraph graph. Each node receives the full state and returns a partial update — only the fields it is responsible for. The state carries the original exception, every intermediate value produced by each node, and the final outcome. See `agent/state.py`.

**Auto-Resolve (outcome value)**
The string `"auto_resolve"` written to the `outcome` field of the agent state when the confidence score meets or exceeds the escalation threshold. Triggers the audit log write but does not write to the escalation queue.

**Classify Node**
The first node every exception passes through. Extracts the exception type and sub-type from the incoming payload and scans the description for mandatory escalation keywords. If a keyword is found, sets `triggered_keyword` and the graph routes to the fast-exit path. If no keyword is found, the graph routes to the standard path.

**Confidence Score**
A float between 0.0 and 1.0 produced by the Claude API during the reason node. Represents how clearly the retrieved SOP applies to the specific exception. Compared against the escalation threshold in the decide node to determine the outcome. Not produced on the fast-exit path — `confidence_score` is null for keyword-triggered escalations.

**Decide Node**
The node that converts the LLM's confidence score into a binary outcome. Compares `confidence_score` against `ESCALATION_THRESHOLD` (0.75). At or above threshold: `outcome = "auto_resolve"`. Below threshold: `outcome = "escalate"`. Also handles the API failure case where `confidence_score` is null — always escalates.

**Escalate Fast-Exit Node**
The node that fires when the classify node detects a mandatory escalation keyword. Sets `outcome = "escalate"` and records the triggered keyword as the escalation reason. Mimir is never called on this path; neither is the Claude API. All LLM and retrieval fields are set to null.

**Escalation Reason**
A string field populated in the agent state and audit log whenever an exception is escalated. On the standard path it contains a confidence explanation: `"confidence score 0.43 below threshold 0.75"`. On the fast-exit path it contains the keyword: `"mandatory escalation keyword detected: sanctions"`. On API failure it contains the error: `"system_error: ..."`. Null when the outcome is auto-resolve.

**Escalation Threshold**
The minimum confidence score required for auto-resolution. In v1 the value is `0.75`, applied uniformly to all sub-types. A single constant in `agent/nodes.py`. Per sub-type thresholds are a v2 feature, deferred until real audit log data exists to calibrate them against.

**Invalid Type Exit**
The first of three execution paths. Fires at the API layer, not inside the graph — Pydantic validation rejects any exception whose `type` field is not `settlement_mismatch`. The agent never receives an invalid type. No audit log entry is written.

**Log Result Node**
The terminal node. Assembles the full event dict from the agent state and calls the audit logger. Runs on every path — standard, fast-exit, and API failure. The only node with side effects beyond modifying state.

**Mandatory Escalation Keywords**
Three terms whose presence in an exception description triggers immediate escalation, bypassing Mimir and the LLM entirely: `sanctions`, `AML`, `regulatory hold`. Detection is case-insensitive. The list is exhaustive for v1.

**Mandatory Escalation Fast-Exit**
The second of three execution paths. Fires when the classify node detects a mandatory escalation keyword in the exception description. Sequence: `classify` → `escalate_fast_exit` → `log_result`. Skips retrieval and reasoning entirely.

**Reason Node**
The node that calls the Claude API. Constructs a prompt from the retrieved SOP chunks, the full exception payload, and a scoring rubric. Parses the structured JSON response to extract `confidence_score`, `reasoning_trace`, and `resolution_steps`. On API failure, returns null values for all three and sets an escalation reason.

**Resolution Steps**
A string produced by the Claude API in the reason node describing the specific steps to resolve the exception per the retrieved SOP. Populated on the standard path only — null on the fast-exit path.

**Reasoning Trace**
A string produced by the Claude API in the reason node explaining step-by-step how the confidence score was reached. Captured in both the audit log and the escalation queue entry. The primary artifact enabling a compliance reviewer or human escalation handler to understand the decision.

**Retrieve Node**
The node that queries Mimir. Constructs a query string from the exception's sub-type and description, calls `mimir.retrieve()`, and stores the returned chunks and the top result's document ID in the agent state. Standard path only.

**Scoring Rubric**
A set of instructions included in the LLM reasoning prompt that defines what constitutes a high versus low confidence score and how to weight the sub-type match, description clarity, and SOP completeness. Anchors confidence scores across runs, making them more consistent and defensible. The rubric text lives in `agent/nodes.py`.

**Standard Path**
The third of three execution paths. Followed when the exception passes classification and contains no mandatory escalation keywords. Sequence: `classify` → `retrieve` → `reason` → `decide` → `log_result`. Ends with either auto-resolve or escalate based on the confidence score.

**Triggered Keyword**
The specific keyword that caused the fast-exit to fire, stored in the agent state and audit log. Example: if the description contains "AML investigation", `triggered_keyword` is set to `"AML"`. Used in the escalation reason string and in the API response.

---

## Part 3 — Implementation Reference

Terms defined here are non-obvious to a developer reading the source for the first time. Self-explanatory names are skipped.

---

### `models/exception.py`

**`ExceptionType` (str, Enum)**
An enum with a single value: `settlement_mismatch`. The `str` mixin means instances serialize to their string value in JSON without a custom serializer. Adding new exception types in v2 means adding new values here and updating the model validator.

**`model_validator(mode="after")`**
A Pydantic v2 mechanism that runs after field-level validation. In v1 it is a stub — it returns `self` unchanged because there is only one exception type and all sub-types are valid for it. The validator exists now so v2 can add cross-field constraints (e.g. enforcing that a corporate action sub-type cannot appear under `settlement_mismatch`) without changing the validation architecture.

**`SettlementMismatchSubType` (str, Enum)**
Three values: `price_mismatch`, `quantity_mismatch`, `wrong_settlement_date`. Each has a corresponding SOP document in the knowledge base and a corresponding test fixture.

---

### `mimir/index.py`

**`_vectorstore` (module-level singleton)**
A module-level variable initialized to `None` and set on first call to `get_vectorstore()`. Python's module system ensures this is shared across all callers within a process. Avoids re-initializing the embedding model and re-connecting to the Chroma index on every query.

**`get_vectorstore()`**
Lazy initialization function. Loads the embedding model and connects to the Chroma index on first call; returns the cached instance on subsequent calls. Lazy rather than eager so the embedding model is not loaded on import — which would slow test collection and cause side effects in components that import from `mimir/` without intending to query it.

**`PERSIST_DIR`**
The path to the directory where `scripts/build_index.py` wrote the Chroma index. Must match the value in `scripts/build_index.py` — if they diverge, the server loads an empty or nonexistent index and all retrievals return empty results.

---

### `mimir/retriever.py`

**`similarity_search_with_score(query, k=top_k)`**
The Chroma method that performs the vector similarity search. Returns `(Document, score)` tuples — the score is the cosine distance from the query embedding to the chunk embedding. Lower distance = higher similarity in Chroma's scoring convention. The retriever exposes this as `similarity_score` in the returned dict.

**Empty list on failure**
The retriever catches all exceptions and returns `[]` rather than raising. The agent handles empty retrieval gracefully — the reason node receives an empty chunks list and the LLM prompt notes "No SOP documents retrieved," producing a low confidence score that routes to escalation.

---

### `logger/audit.py`

**`_db_initialized` (module-level flag)**
A boolean tracking whether `_init_db()` has already run. Guards against running `CREATE TABLE IF NOT EXISTS` on every log call. The guard condition is `_db_initialized and AUDIT_DB.exists()` — the `.exists()` check catches the case where a test deleted the database file between tests but the flag was still `True`, which would cause an insert into a nonexistent table.

**`INSERT OR REPLACE`**
The SQLite statement used for audit log rows. `job_id` is the primary key. If a job ID is somehow written twice, the second write replaces the first rather than raising a uniqueness error. In practice this does not occur in v1 — job IDs are UUIDs — but the statement is defensive.

**`full_event_json`**
A SQLite column storing the entire event dict serialized as a JSON string. Individual columns (`outcome`, `confidence_score`, etc.) support queries on common fields. `full_event_json` ensures no data is lost regardless of which columns exist — when v2 adds new fields to the event dict, they appear in `full_event_json` automatically without a schema migration.

---

### `agent/state.py`

**`TypedDict`**
The Python typing construct used to define `AgentState`. LangGraph's `StateGraph` expects a `TypedDict` as its state type. Each node receives and returns plain dicts; LangGraph merges the partial return into the full state.

**`llm_raw_response`**
The Claude API's raw text response before JSON parsing. Stored in state and written to the audit log for full fidelity. If the API returns malformed JSON, this field captures exactly what came back, enabling debugging without re-running the exception.

---

### `agent/nodes.py`

**`ESCALATION_THRESHOLD = 0.75`**
The module-level constant controlling the auto-resolve/escalate boundary. Placed at the top of the file so it is visible without reading node implementations. In v2 this becomes a per-sub-type dictionary keyed on sub-type string values.

**`LLM_MODEL = "claude-sonnet-4-6"`**
The Claude API model identifier. Defined as a module-level constant so it is easy to update when a new model is released. Changing the model may affect response formatting — the markdown fence stripping logic in the reason node exists because this model sometimes wraps JSON in code fences despite being instructed not to.

**Markdown fence stripping**
A defensive parsing step in the reason node. The Claude API is instructed to return raw JSON, but the model sometimes wraps the response in markdown code fences. The stripping logic checks for a leading ` ``` `, removes the fence and optional `json` language tag, and strips the trailing fence before calling `json.loads()`. Without this, the JSON parse fails and the exception auto-escalates with a `system_error`.

**`query = f"{exception['sub_type']}: {exception['description']}"`**
The Mimir query construction in `retrieve_node`. The sub-type prefix anchors the similarity search — in v1 with three documents, one per sub-type, including the sub-type makes it significantly harder to retrieve the wrong document.

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
An in-memory dict mapping `job_id` (str) to result dicts. Populated by `POST /exceptions` after the agent completes; read by `GET /exceptions/{job_id}`. Not persistent — cleared on server restart. V2 replaces this with a persistent store when async processing is added.

**`exception.model_dump_json()` + `json.loads()`**
The pattern for converting a Pydantic model to a plain dict with fully serializable values. `model_dump()` alone preserves Python types (UUID objects, datetime objects) that are not JSON-serializable. The JSON round-trip converts them to strings. Necessary because the agent state and audit logger expect plain dicts with string values throughout.

**Fake async job ID pattern**
`POST /exceptions` returns a job ID immediately; `GET /exceptions/{job_id}` retrieves the result. In v1 the agent runs synchronously before the POST response is sent — the result is always ready. The two-endpoint pattern keeps the interface forward-compatible with v2 async processing, where the result may not be ready when the POST returns.

---

### `scripts/build_index.py`

**`DOCUMENT_METADATA`**
A dict mapping SOP filename stems to their `document_id` and `sub_type` metadata. Attached to every chunk at index time so each chunk is self-describing when retrieved — the retriever can return `document_id` and `sub_type` without any additional lookup. Files not present in this dict are skipped with a warning.

**`chunk_overlap=50`**
The number of characters shared between adjacent chunks. Prevents a relevant sentence from being split across two chunks where neither has enough context alone. The 50-character overlap is a v1 baseline chosen to handle typical SOP sentence lengths.

**`sys.path.insert(0, ...)`**
Ensures the project root (`huginn_v1/`) is on the Python path when the script is run directly. Without this, Python adds the script's directory (`scripts/`) to the path, not the project root, and imports from project modules would fail.
