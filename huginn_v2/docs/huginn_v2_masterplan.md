# Huginn v2 — Masterplan

**Phase:** 4 — Masterplan + Atomic Subplans
**Status:** Ready for Claude Code implementation
**Last updated:** May 2026
**Source of truth:** `huginn_v2_interface_contract.md`, `huginn_v2_design_decisions.md` (Decisions 1–46)

---

## The Completed System — Plain English Description

Huginn is a FastAPI service that accepts flagged financial trade exceptions over HTTP, classifies them, and decides whether to resolve them automatically or escalate them to a human reviewer. When an exception arrives, it is validated against a strict schema — only settlement_mismatch exceptions with a valid sub-type are accepted. Inside the agent, two fast exits fire before any expensive operations: exceptions with an invalid type return a structured error, and exceptions whose description contains a mandatory escalation keyword (sanctions, AML, regulatory hold, buy-in, sell-out) are immediately escalated without touching the knowledge base or the LLM. All other exceptions follow the standard path: the agent queries Mimir — a Chroma-backed RAG retrieval layer — for the most relevant chunks from a real regulatory document knowledge base (SEC Rules 15c6-1 and 15c6-2, FINRA Rules 11100, 11710, 11810, and 11820). Mimir performs two-pass retrieval: a semantic search pass followed by a targeted cross-reference resolution pass that fetches additional chunks from any regulatory rules explicitly referenced in the first-pass results. The combined chunks are passed along with the exception and a regulatory reasoning scoring rubric to the Claude API, which returns a confidence score used to decide whether to auto-resolve (≥ 0.75) or escalate (< 0.75). Every decision — on every path — is written in full fidelity to logs/audit.jsonl, a local SQLite database, and, if escalated, to logs/escalation_queue.jsonl. Three FastAPI endpoints expose the full system: POST /exceptions to submit an exception and receive a job ID, GET /exceptions/{job_id} to retrieve the full decision, and GET /escalations to inspect the human reviewer's inbox.

---

## Reference Documents

Every subplan references these documents. Claude Code must read both before implementing any subplan.

- `huginn_v2_interface_contract.md` — component inputs, outputs, and data types
- `huginn_v2_design_decisions.md` — all locked decisions with reasoning

---

## Build Sequence

Subplans are executed in strict order. No subplan begins until the previous subplan's gate is confirmed passing. Gates are not advisory — they are hard stops.

| Subplan | Component | Gate |
|---|---|---|
| 1 | Models and schema | Pydantic validation smoke test passes |
| 2 | Knowledge base indexing | Chroma index built, chunk inspection passes |
| 3 | Mimir retriever | Retriever smoke test passes against live index |
| 4 | Agent state and graph structure | Graph compiles, all nodes registered |
| 5 | LangGraph nodes | Full agent trace produces valid output on test input |
| 6 | API layer | All three endpoints return correct responses |
| 7 | Integration and smoke test | Full end-to-end test suite passes |

---

## Subplan 1 — Models and Schema

### What to build
`models/exception.py` — the Pydantic model that defines the exception schema and validates all incoming requests.

### Interface contract reference
Component 1 — Exception Schema (`models/exception.py`)

### Implementation instructions

Create `models/exception.py` with the following:

**Enums:**
- `ExceptionType` — string enum with single value: `settlement_mismatch`
- `SettlementMismatchSubType` — string enum with three values: `price_mismatch`, `quantity_mismatch`, `wrong_settlement_date`
- `Severity` — string enum with three values: `low`, `medium`, `high`

**TradeException model:**
Fields exactly as specified in the interface contract. All fields required. Types exactly as specified — `UUID` for `exception_id`, `datetime` for `timestamp`, enums for `type`, `sub_type`, `severity`, `str` for `trade_id` and `description`.

**Model validator:**
A `@model_validator(mode="after")` that enforces sub-type scope against parent type. In v2 only `settlement_mismatch` is valid, so the validator confirms that `sub_type` is a `SettlementMismatchSubType` when `type` is `settlement_mismatch`. This validator exists to be extended in v3 when new exception types are added — do not collapse it into the enum definition.

**What NOT to build:**
- No helper methods on the model
- No custom JSON serializers
- No default values on any field — all fields are required

### Gate — Subplan 1

Create a file `tests/test_models.py` and confirm all of the following pass before proceeding:

```python
# 1. Valid exception passes validation
valid = TradeException(
    exception_id="550e8400-e29b-41d4-a716-446655440000",
    trade_id="TRD-001",
    type="settlement_mismatch",
    sub_type="price_mismatch",
    description="Counterparty confirms 142.50, we show 141.75 for 500 AAPL shares.",
    timestamp="2026-05-01T09:30:00",
    severity="high"
)
assert valid.type == ExceptionType.settlement_mismatch

# 2. Invalid type raises ValidationError
with pytest.raises(ValidationError):
    TradeException(..., type="unknown_type", ...)

# 3. Invalid sub_type raises ValidationError
with pytest.raises(ValidationError):
    TradeException(..., sub_type="unknown_sub_type", ...)

# 4. Missing required field raises ValidationError
with pytest.raises(ValidationError):
    TradeException(trade_id="TRD-001", ...)  # missing exception_id
```

All four assertions must pass. If any fail, fix the model before proceeding to Subplan 2.

---

## Subplan 2 — Knowledge Base Indexing

### What to build
- `scripts/build_index.py` — one-time script that extracts, chunks, and indexes all regulatory documents
- `mimir/index.py` — Chroma index configuration and persistence settings used by both the indexer and the retriever

### Interface contract reference
Component 4 — Mimir Retriever, Knowledge Base Reference section
Design Decisions 30, 35, 36, 46

### Source documents

The following PDFs must be present in `knowledge_base/raw/` before running `build_index.py`:

| Filename | Document ID | Rule |
|---|---|---|
| `FINRA-11100.pdf` | `FINRA-11100` | FINRA Rule 11100 — Scope of Uniform Practice Code |
| `FINRA-11710.pdf` | `FINRA-11710` | FINRA Rule 11710 — General Provisions |
| `FINRA-11810.pdf` | `FINRA-11810` | FINRA Rule 11810 — Buy-In Procedures and Requirements |
| `FINRA-11820.pdf` | `FINRA-11820` | FINRA Rule 11820 — Selling-Out |
| `SEC-15c6-1.pdf` | `SEC-15c6-1` | SEC Rule 15c6-1 — Standard Settlement Cycle |
| `SEC-15c6-2.pdf` | `SEC-15c6-2` | SEC Rule 15c6-2 — Same-Day Affirmation |

The `document_id` is derived from the filename stem. The filename-to-document_id mapping must be explicit in `build_index.py` — do not derive it dynamically from the filename.

### Implementation instructions

**`mimir/index.py`:**
Define two module-level constants used by both `build_index.py` and `mimir/retriever.py`:
```python
PERSIST_DIR = "knowledge_base/processed"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
```
No other logic in this file. It is a shared configuration module.

**`scripts/build_index.py`:**

The script runs once from the project root: `python scripts/build_index.py`

Step 1 — PDF text extraction:
Use `pypdf.PdfReader` to extract text from each PDF. Concatenate text across all pages. Both `.pdf` and `.txt` source files are supported — detect by file extension. For `.txt` files, read directly.

Step 2 — Section boundary parsing:
Apply the section parser to the full extracted text. The parser uses:
- Regex pattern: `^\([a-z]\)` with `re.MULTILINE` flag
- Minimum chunk length: 200 characters (chunks below this threshold are merged with the preceding chunk rather than treated as independent sections)

The parser splits on detected boundaries and constructs chunks. Each chunk consists of:
- The section content (text between two boundaries)
- A prepended header: `"{document_id} Section ({letter}):\n"` — e.g. `"FINRA-11810 Section (b):\n"`

Step 3 — Sequential suffixing for duplicate section IDs:
When a document produces duplicate lettered section markers (known to occur in FINRA-11810 due to the sample buy-in forms at the end of the rule), assign sequential suffixes to disambiguate:
- First occurrence of `(b)`: `section_id = "FINRA-11810-b-1"`
- Second occurrence of `(b)`: `section_id = "FINRA-11810-b-2"`

Apply sequential suffixing to all documents, not just FINRA-11810. For documents with no duplicates, the suffix `-1` is still appended for consistency: `"FINRA-11820-a-1"`, `"FINRA-11820-b-1"`. This ensures `section_id` values are always unique within a document.

Step 4 — Chunk metadata:
Attach to every chunk:
```python
{
    "document_id": "FINRA-11810",
    "section_id": "FINRA-11810-b-1"
}
```

Step 5 — Chunk inspection log:
Before building the Chroma index, print a chunk inspection summary to stdout:
```
FINRA-11810: 15 chunks
  FINRA-11810-a-1: 1287 chars
  FINRA-11810-b-1: 2833 chars
  ...
```
This is the gate validation artifact. Do not suppress this output.

Step 6 — Chroma index build:
Use `HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)` from `mimir/index.py`.
Persist to `PERSIST_DIR` from `mimir/index.py`.
Use `Chroma.from_documents()` to build the index from all chunks across all documents.

**Known issues to handle:**
- eCFR pages (SEC-15c6-1, SEC-15c6-2) include a preamble before the first lettered section. Pre-section text (before the first `(a)` match) is captured as a preamble chunk with `section_id = "{document_id}-preamble"`. It is indexed but will have low similarity scores on settlement mismatch queries.
- FINRA-11810 produces duplicate section letters due to sample form templates appended after the main rule text. Sequential suffixing (Step 3) handles this.

**What NOT to build:**
- No `sub_type` metadata on chunks — this was explicitly rejected in Decision 36
- No `applicable_sub_types` field
- No logic that filters or excludes any section based on content

### Gate — Subplan 2

Run `python scripts/build_index.py` and confirm:

1. Script completes without errors
2. Chunk inspection log prints to stdout showing all six documents with chunk counts matching approximately: FINRA-11100 (~4), FINRA-11710 (~5), FINRA-11810 (~15), FINRA-11820 (~2), SEC-15c6-1 (~4), SEC-15c6-2 (~2)
3. `knowledge_base/processed/` directory exists and is non-empty after the run
4. No two chunks share the same `section_id`

Manually inspect the chunk inspection log before proceeding. Confirm that section boundaries are semantically correct — each chunk should begin at the start of a logical rule subsection, not mid-sentence. If any chunk appears to split incorrectly, adjust the parser before proceeding to Subplan 3.

---

## Subplan 3 — Mimir Retriever

### What to build
`mimir/retriever.py` — the two-pass retrieval function. The only public interface is `retrieve(query, top_k)`.

### Interface contract reference
Component 4 — Mimir Retriever (full specification including two-pass behavior)
Design Decisions 37, 38

### Prerequisites
Subplan 2 gate must be confirmed passing. The Chroma index at `knowledge_base/processed/` must exist.

### Implementation instructions

**Module-level constants:**
```python
TOP_K_CROSS_REF = 2

KNOWN_DOCUMENT_IDS = {
    "15c6-1", "15c6-2", "11100", "11710", "11810", "11820"
}
```

`KNOWN_DOCUMENT_IDS` contains the identifying substrings used for cross-reference detection. These are the rule number portions of the full document IDs. String matching checks whether any of these substrings appear in a chunk's text.

**`retrieve(query: str, top_k: int = 3) -> list[dict]`:**

Load the persisted Chroma index using `PERSIST_DIR` and `EMBEDDING_MODEL` from `mimir/index.py`. The index is loaded once at module level, not on every `retrieve()` call.

**Pass 1 — Semantic search:**
```python
results = vectorstore.similarity_search_with_score(query, k=top_k)
```
Convert each result to the chunk dict format specified in the interface contract:
```python
{
    "text": doc.page_content,
    "document_id": doc.metadata["document_id"],
    "section_id": doc.metadata["section_id"],
    "similarity_score": float(score),
    "retrieved_via": "primary"
}
```

**Cross-reference detection:**
Scan the `text` field of every Pass 1 chunk. For each entry in `KNOWN_DOCUMENT_IDS`, check whether it appears as a substring in the text (case-insensitive). Collect the set of referenced document IDs that are not already fully represented in Pass 1 results.

"Fully represented" means: at least one Pass 1 chunk has a `document_id` matching the referenced rule. If Pass 1 already returned chunks from `FINRA-11710`, do not queue a Pass 2 fetch for `FINRA-11710`.

**Pass 2 — Targeted retrieval:**
For each referenced rule not already represented in Pass 1:
```python
results = vectorstore.similarity_search_with_score(
    query,
    k=TOP_K_CROSS_REF,
    filter={"document_id": f"FINRA-{rule_number}"}  # or "SEC-{rule_number}"
)
```

Reconstruct the full `document_id` from the matched substring before filtering. The mapping is:
```python
SUBSTRING_TO_DOCUMENT_ID = {
    "15c6-1": "SEC-15c6-1",
    "15c6-2": "SEC-15c6-2",
    "11100": "FINRA-11100",
    "11710": "FINRA-11710",
    "11810": "FINRA-11810",
    "11820": "FINRA-11820",
}
```

Tag each Pass 2 chunk `retrieved_via: "cross_reference"`.

**Deduplication:**
Combine Pass 1 and Pass 2 results. If a chunk appears in both (matched by `section_id`), retain the `"primary"` tagged version and discard the duplicate.

**Return:**
Return the combined deduplicated list. Do not sort or re-rank — return in the order: Pass 1 results first, Pass 2 results appended.

**Error handling:**
If the Chroma index is unavailable or empty, return an empty list. Do not raise exceptions.

**What NOT to build:**
- No public functions other than `retrieve()`
- No pass count or cross-reference metadata exposed through the public interface
- No re-ranking or score normalization

### Gate — Subplan 3

Create `tests/test_retriever.py` and confirm all of the following pass:

```python
# 1. Basic retrieval returns correctly structured chunks
chunks = retrieve("price_mismatch: counterparty confirms different price than recorded")
assert len(chunks) > 0
for chunk in chunks:
    assert "text" in chunk
    assert "document_id" in chunk
    assert "section_id" in chunk
    assert "similarity_score" in chunk
    assert chunk["retrieved_via"] in ("primary", "cross_reference")

# 2. Two-pass behavior fires — a query about settlement failure
# should retrieve from 11100 (which references 11810 and 11820)
# and trigger cross-reference retrieval
chunks = retrieve("settlement_mismatch: seller failed to deliver securities on settlement date")
doc_ids = [c["document_id"] for c in chunks]
# At minimum, multiple document IDs should be represented
assert len(set(doc_ids)) > 1

# 3. No duplicate section_ids in results
section_ids = [c["section_id"] for c in chunks]
assert len(section_ids) == len(set(section_ids))

# 4. Empty query returns gracefully
chunks = retrieve("")
assert isinstance(chunks, list)
```

All four assertions must pass. Print the full chunk list from test 2 to stdout and inspect manually — confirm that cross-reference retrieval is fetching semantically relevant content, not noise.

---

## Subplan 4 — Agent State and Graph Structure

### What to build
- `agent/state.py` — the `AgentState` TypedDict
- `agent/graph.py` — the LangGraph graph definition, node registration, and edge routing

### Interface contract reference
Component 3 — LangGraph Agent, Agent State Object and Graph Paths sections

### Prerequisites
Subplan 3 gate must be confirmed passing.

### Implementation instructions

**`agent/state.py`:**
Implement `AgentState` exactly as specified in the interface contract. All fields typed as specified. No additional fields. No default values — state fields are populated by nodes, not initialized with defaults.

**`agent/graph.py`:**

Define the graph using LangGraph's `StateGraph(AgentState)`.

Register all nodes. Node functions are imported from `agent/nodes.py` — stubs are acceptable at this subplan stage. Each stub must accept `AgentState` and return a dict:
```python
def classify(state: AgentState) -> dict:
    return {"current_node": "classify"}
```

Define edges implementing the three-path structure:

**Path 2 — Mandatory escalation fast-exit:**
After `classify`: conditional edge. If `state["triggered_keyword"]` is not None, route to `escalate_fast_exit`. Otherwise route to `retrieve`.

**Path 3 — Standard path:**
`retrieve` → `reason` → `decide` → conditional edge on `state["outcome"]`:
- `"auto_resolve"` → `log_result`
- `"escalate"` → `log_result`

Both paths terminate at `log_result`.

Set entry point to `classify`. Set finish point to `log_result`.

`build_graph()` is called at module level in `agent/graph.py` and the compiled graph assigned to `huginn_graph`. The API layer imports `huginn_graph` directly:
```python
huginn_graph = build_graph()
```

**What NOT to build:**
- No node logic in `graph.py` — only graph structure and edge routing
- No error handling at the graph level — error handling is inside individual nodes

### Gate — Subplan 4

```python
# Graph compiles without errors
from agent.graph import build_graph
graph = build_graph()
assert graph is not None

# Graph has correct entry point
# Graph reaches log_result on both fast-exit and standard path
# (stub nodes return minimal valid state updates)
```

Run the graph with a minimal state dict and confirm it completes without errors on both paths. Stub node output is acceptable at this stage — the gate is graph structure only, not output correctness.

---

## Subplan 5 — LangGraph Nodes

### What to build
`agent/nodes.py` — all node functions. Replaces the stubs from Subplan 4.

### Interface contract reference
Component 3 — LangGraph Agent, Node Specifications section
Component 4 — Mimir Retriever (called by retrieve node)
Component 5 — LLM Reasoning
Design Decisions 23, 24, 25, 26, 28, 29, 43

### Prerequisites
Subplan 4 gate must be confirmed passing.

### Implementation instructions

**Module-level constants:**
```python
ESCALATION_THRESHOLD = 0.75
LLM_MODEL = "claude-sonnet-4-6"

ESCALATION_KEYWORDS = [
    "sanctions",
    "AML",
    "regulatory hold",
    "buy-in",
    "sell-out",
]
```

**`classify(state: AgentState) -> dict`:**
Extract `type` and `sub_type` from `state["exception"]`. Perform case-insensitive keyword scan over `state["exception"]["description"]` against `ESCALATION_KEYWORDS`. If a keyword is found, set `triggered_keyword` to the matched keyword. Otherwise set `triggered_keyword` to None.

**`retrieve(state: AgentState) -> dict`:**
Construct query: `f"{state['exception_sub_type']}: {state['exception']['description']}"`.
Call `mimir.retrieve(query)`.
Derive `retrieved_document_ids` as the list of unique `document_id` values across all returned chunks.
Return `retrieved_chunks` and `retrieved_document_ids`.

**`reason(state: AgentState) -> dict`:**
Construct the LLM prompt with three sections in order:
1. The regulatory reasoning scoring rubric (see Decision 29 — full rubric text)
2. The retrieved chunks — formatted as labeled regulatory context. For each chunk:
   ```
   [{section_id}] ({retrieved_via})
   {text}
   ---
   ```
3. The exception payload — formatted as labeled input

Instruct the LLM to respond with structured JSON only, matching the schema in the interface contract (Component 5).

Call the Claude API:
```python
response = anthropic.Anthropic().messages.create(
    model=LLM_MODEL,
    max_tokens=1000,
    messages=[{"role": "user", "content": prompt}]
)
```

Parse the JSON response. On any exception (API failure, JSON parse error, missing fields), return:
```python
{
    "confidence_score": None,
    "reasoning_trace": None,
    "resolution_steps": None,
    "llm_raw_response": None,
    "escalation_reason": f"system_error: {str(e)}"
}
```

**`decide(state: AgentState) -> dict`:**
If `state["confidence_score"]` is None or below `ESCALATION_THRESHOLD`:
```python
{"outcome": "escalate", "escalation_reason": f"confidence score {score} below threshold {ESCALATION_THRESHOLD}"}
```
Otherwise:
```python
{"outcome": "auto_resolve", "escalation_reason": None}
```

**`escalate_fast_exit(state: AgentState) -> dict`:**
```python
{
    "outcome": "escalate",
    "escalation_reason": f"mandatory escalation keyword detected: {state['triggered_keyword']}"
}
```

**`log_result(state: AgentState) -> dict`:**
Construct the full event dict from all state fields as specified in Component 6 (Audit Logger). Call `logger.log(event)`. Return empty dict — this node has no state output.

**Scoring rubric — full text for Decision 29:**

The following rubric text is hardcoded in the `reason` node's prompt construction. It must be reproduced exactly:

```
You are a financial trade exception triage agent. Your task is to assess whether a settlement mismatch exception can be auto-resolved based on the retrieved regulatory document context.

Score the exception on a scale of 0.0 to 1.0 using the following four factors:

1. CONDITION MATCH (0.0–1.0)
Do the exception facts satisfy the triggering conditions specified in the retrieved regulatory rule? Does the scenario described meet the threshold or criteria the rule requires for a specific obligation or remedy to apply?

2. OBLIGATION CLARITY (0.0–1.0)
Does the retrieved rule specify a clear required action given the exception facts? Or does the rule leave the required response ambiguous, conditional on additional facts not present in the exception description?

3. EXCEPTION APPLICABILITY (0.0–1.0)
Do any of the rule's carve-outs, exceptions, or exclusions apply to this exception? Consider whether any exception provisions (e.g. T+2 late-pricing exception in Rule 15c6-1, clearing agency carve-outs in Rule 11810) apply to the described scenario.

4. CROSS-REFERENCE RESOLUTION (0.0–1.0)
Were all rules referenced within the retrieved chunks also retrieved and considered? Unresolved cross-references lower confidence because the complete regulatory picture is not available.

Scoring guidance:
- 0.85–1.00: Condition match is clear, obligation is unambiguous, no exceptions apply, all cross-references resolved.
- 0.75–0.84: Condition match is probable, obligation is mostly clear, minor ambiguity exists but resolution path is defensible.
- 0.50–0.74: Condition match is uncertain, or an exception may apply but cannot be determined from available facts, or cross-references are unresolved.
- 0.00–0.49: Condition match cannot be established, or the rule explicitly requires human judgment, or critical cross-references are missing.

Respond with a JSON object only. No preamble. No explanation outside the JSON. Exactly three fields:
{
  "confidence_score": <float between 0.0 and 1.0>,
  "reasoning_trace": "<step-by-step explanation of how you reached this score>",
  "resolution_steps": "<specific steps to resolve this exception per the retrieved regulatory guidance>"
}
```

**What NOT to build:**
- No severity input to the LLM prompt — severity is metadata only in v2 (Decision 42)
- No retry logic on Claude API failures — fail fast and escalate (Decision 28)
- No caching of LLM responses

### Gate — Subplan 5

Create a test exception and run the full agent graph end-to-end:

```python
test_exception = {
    "exception_id": "550e8400-e29b-41d4-a716-446655440000",
    "trade_id": "TRD-001",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Counterparty confirms price of 142.50, we show 141.75 for 500 AAPL shares settled on 2026-05-01.",
    "timestamp": "2026-05-01T09:30:00",
    "severity": "high"
}
```

Confirm:
1. Agent runs to completion without errors
2. `outcome` is either `"auto_resolve"` or `"escalate"`
3. `confidence_score` is a float between 0.0 and 1.0
4. `reasoning_trace` is a non-empty string
5. `retrieved_document_ids` is a non-empty list
6. `logs/audit.jsonl` contains one entry after the run

Also run the fast-exit path:
```python
fast_exit_exception = {
    ...same fields...,
    "description": "Counterparty flagged for sanctions review — settlement on hold."
}
```

Confirm:
1. Agent completes without calling Mimir or the Claude API
2. `outcome` is `"escalate"`
3. `triggered_keyword` is `"sanctions"`
4. `retrieved_document_ids` is an empty list
5. `logs/escalation_queue.jsonl` contains one entry

---

## Subplan 6 — API Layer

### What to build
`api/main.py` — the FastAPI application with all three endpoints.

### Interface contract reference
Component 2 — API Layer (all three endpoints, full request/response schemas)
Design Decisions 7, 19, 20, 21

### Prerequisites
Subplan 5 gate must be confirmed passing.

### Implementation instructions

**Application setup:**
```python
app = FastAPI(title="Huginn v2", version="2.0.0")
```

**In-memory result store:**
```python
results: dict[str, dict] = {}
```
Keyed by `job_id`. Populated synchronously after agent run. This is the v2 fake-async pattern — the interface is forward-compatible with v3 async processing.

**`POST /exceptions`:**
1. Validate request body as `TradeException` (Pydantic handles this automatically)
2. Generate a new `job_id` UUID
3. Initialize the `AgentState` with the exception dict and job_id
4. Run the compiled LangGraph graph synchronously
5. Store the final state in `results[job_id]`
6. Return the POST response schema (job_id, status, exception_id, timestamp)

**`GET /exceptions/{job_id}`:**
Look up `job_id` in `results`. If not found, return HTTP 404. Otherwise return the GET response schema — map from `AgentState` fields to response fields exactly as specified in Component 2.

`retrieved_document_ids` in the response comes directly from `state["retrieved_document_ids"]` — it is a list of strings, empty list on fast-exit path.

**`GET /escalations`:**
Filter `results` for entries where `state["outcome"] == "escalate"`. Return the escalations response schema. Return `{"escalations": []}` when no escalations exist.

**Pydantic validation errors:**
Do not add a custom exception handler. FastAPI's default 422 response is used as specified in Decision 34.

**What NOT to build:**
- No authentication
- No rate limiting
- No background task processing — synchronous only in v2
- No custom exception handlers

### Gate — Subplan 6

Start the server: `uvicorn api.main:app --reload`

Using the `/docs` interface at `http://127.0.0.1:8000/docs`, confirm:

1. `POST /exceptions` with a valid exception body returns HTTP 200 with correct schema
2. `GET /exceptions/{job_id}` with the returned job_id returns HTTP 200 with outcome, confidence_score, reasoning_trace, and `retrieved_document_ids` as a list
3. `GET /exceptions/{job_id}` with an unknown job_id returns HTTP 404
4. `POST /exceptions` with an invalid `type` value returns HTTP 422
5. `GET /escalations` returns `{"escalations": [...]}` — submit a sanctions exception first if needed to populate it

---

## Subplan 7 — Integration and Smoke Test

### What to build
`tests/test_integration.py` — full end-to-end integration test suite covering all three agent paths.

### Interface contract reference
All components.

### Prerequisites
Subplan 6 gate must be confirmed passing.

### Test cases

**Test 1 — Standard path, auto-resolve:**
Submit a well-formed `price_mismatch` exception with a specific, actionable description. Assert:
- HTTP 200 from POST
- HTTP 200 from GET with matching job_id
- `outcome` is `"auto_resolve"` (may be `"escalate"` if confidence < 0.75 — accept either, but log the score)
- `confidence_score` is a float
- `reasoning_trace` is non-empty
- `retrieved_document_ids` is a non-empty list of strings
- `logs/audit.jsonl` contains the entry

**Test 2 — Standard path, low confidence escalation:**
Submit a `quantity_mismatch` exception with a vague description (e.g. `"quantity issue"`). Assert:
- `outcome` is `"escalate"`
- `escalation_reason` contains `"confidence score"`
- `confidence_score` is below 0.75
- `retrieved_document_ids` is non-empty (Mimir ran)

**Test 3 — Mandatory escalation fast-exit:**
Submit a `price_mismatch` exception with `"sanctions"` in the description. Assert:
- `outcome` is `"escalate"`
- `escalation_reason` contains `"mandatory escalation keyword detected: sanctions"`
- `confidence_score` is null
- `retrieved_document_ids` is empty list
- Entry appears in `logs/escalation_queue.jsonl`

**Test 4 — Fast-exit with new v2 keywords:**
Submit exceptions containing `"buy-in"` and `"sell-out"` in descriptions separately. Assert both trigger fast-exit escalation with the correct keyword in `escalation_reason`.

**Test 5 — Pydantic validation rejection:**
Submit a request with `type` set to `"invalid_type"`. Assert HTTP 422 response.

**Test 6 — wrong_settlement_date sub-type:**
Submit a `wrong_settlement_date` exception with a description referencing T+1 settlement. Assert:
- Agent completes without errors
- `retrieved_document_ids` contains `"SEC-15c6-1"` (the primary source for T+1 settlement)

**Test 7 — GET /escalations:**
After Tests 2 and 3, assert `GET /escalations` returns at least two entries, each with correct schema including `retrieved_document_ids`.

### Final verification checklist

Before declaring v2 complete:

- [ ] All seven test cases pass
- [ ] `logs/audit.jsonl` contains entries from all test runs
- [ ] `logs/audit.db` is queryable — run `SELECT sub_type, outcome, confidence_score FROM audit_log` and confirm rows exist
- [ ] `logs/escalation_queue.jsonl` contains entries from Tests 2, 3, and 4
- [ ] `knowledge_base/processed/` is non-empty and contains the persisted Chroma index
- [ ] `http://127.0.0.1:8000/docs` loads and all three endpoints are visible
- [ ] No open TODOs or stub functions remain in any source file

---

## What This Masterplan Does Not Specify

- Internal variable names within any component
- Import organization and file header comments
- The exact format of print/log statements within `build_index.py`
- Whether to use `pytest` fixtures or plain functions in test files

These are implementation details resolved by Claude Code. Discoveries that contradict a locked decision must be flagged and returned to the project via the Phase 7 feedback loop before implementation continues.
