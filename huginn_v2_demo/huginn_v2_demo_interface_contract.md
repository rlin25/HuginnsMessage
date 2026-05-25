# Huginn v2 Demo — Interface Contract

**Status:** Design phase complete. Ready for implementation.
**Last updated:** May 2026
**Location:** `HuginnsMessage/huginn_v2_demo/`
**Source of truth:** `huginn_v2_demo_design_decisions.md` — all component specifications derive from locked decisions. If a specification here conflicts with a locked decision, the locked decision governs.

---

## What This Document Is

An interface contract defines every component's inputs, outputs, and boundaries before any code is written. A developer reading this document should be able to build the demo without asking a follow-up question. A specification that cannot be written precisely is a gap — gaps are resolved here, not during implementation.

This contract specifies a single React artifact. There is no backend, no database, and no local API. The only external call is to the Anthropic Claude API at runtime.

---

## Plain English Description

The Huginn v2 demo is a single-page React artifact styled to resemble a Swagger UI. It opens with a short framing paragraph and a title. Below that, the recruiter sees a scenario selector showing five named scenarios simultaneously. The selected scenario's JSON request body is displayed in a read-only request panel beneath the selector. An Execute button submits the scenario.

On Execute, a loading state appears and a live Claude API call is made. When the response returns, three sections reveal sequentially: the LangGraph state diagram (nodes animate to show which path fired), the retrieval cards (one card per regulatory chunk retrieved, with metadata and a snippet), and the response cards (confidence score, reasoning trace, resolution steps). Selecting a new scenario collapses all output sections and resets to the pre-run state.

---

## Component Map

The demo consists of six components rendered top to bottom in a single column:

1. `FramingHeader`
2. `ScenarioSelector`
3. `RequestPanel`
4. `StateGraph`
5. `RetrievalPanel`
6. `ResponsePanel`

Components 4, 5, and 6 are hidden on load and appear sequentially after Execute is clicked.

---

## Shared Data — Scenario Definitions

All five scenarios are defined as a static constant. No scenario data is fetched at runtime.

```
SCENARIOS = [
  {
    id: "price_mismatch",
    label: "Price mismatch — AAPL, 500 shares",
    outcome_hint: "auto-resolved",
    path: "standard",
    payload: {
      exception_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      trade_id: "TRD-2026-00142",
      type: "settlement_mismatch",
      sub_type: "price_mismatch",
      description: "Counterparty confirms 142.50, we show 141.75 for 500 AAPL shares settled 2026-05-20. Discrepancy of $375.00 total. Counterparty has not responded to our query.",
      timestamp: "2026-05-20T09:30:00",
      severity: "high"
    }
  },
  {
    id: "quantity_mismatch",
    label: "Quantity mismatch — TSLA, 200 shares",
    outcome_hint: "escalated",
    path: "standard",
    payload: {
      exception_id: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      trade_id: "TRD-2026-00198",
      type: "settlement_mismatch",
      sub_type: "quantity_mismatch",
      description: "We delivered 200 TSLA shares, counterparty confirms receipt of 150 only. Settlement date 2026-05-21. Shortfall of 50 shares unresolved after two business days.",
      timestamp: "2026-05-21T10:15:00",
      severity: "high"
    }
  },
  {
    id: "wrong_settlement_date",
    label: "Wrong settlement date — MSFT bond",
    outcome_hint: "auto-resolved",
    path: "standard",
    payload: {
      exception_id: "c3d4e5f6-a7b8-9012-cdef-123456789012",
      trade_id: "TRD-2026-00231",
      type: "settlement_mismatch",
      sub_type: "wrong_settlement_date",
      description: "MSFT 3.75% bond due 2031. We show settlement date 2026-05-22, counterparty confirms 2026-05-23. T+1 affirmation was submitted same-day per SEC Rule 15c6-2.",
      timestamp: "2026-05-22T08:45:00",
      severity: "medium"
    }
  },
  {
    id: "fast_exit",
    label: "Buy-in notice received",
    outcome_hint: "escalated",
    path: "fast_exit",
    payload: {
      exception_id: "d4e5f6a7-b8c9-0123-defa-234567890123",
      trade_id: "TRD-2026-00089",
      type: "settlement_mismatch",
      sub_type: "price_mismatch",
      description: "Counterparty has issued a formal buy-in notice for 300 shares of GE undelivered as of 2026-05-19. Buy-in execution scheduled for 2026-05-22 per FINRA Rule 11810.",
      timestamp: "2026-05-20T14:00:00",
      severity: "high"
    }
  },
  {
    id: "invalid_type",
    label: "Invalid exception type",
    outcome_hint: "rejected at validation",
    path: "rejection",
    payload: {
      exception_id: "e5f6a7b8-c9d0-1234-efab-345678901234",
      trade_id: "TRD-2026-00310",
      type: "trade_reporting_violation",
      sub_type: "late_report",
      description: "FINRA Rule 7270 late reporting violation. Trade executed 2026-05-20, reported 2026-05-22.",
      timestamp: "2026-05-22T11:00:00",
      severity: "medium"
    }
  }
]
```

**Notes:**
- `outcome_hint` is display-only — it appears in the scenario label, not in the payload.
- `path` drives which visualization behavior fires: `standard`, `fast_exit`, or `rejection`.
- Payloads are static. They do not change between runs.

---

## Shared Data — Node Graph Definition

The state graph is a static constant matching `agent/graph.py` exactly.

```
NODES = [
  { id: "classify",          label: "classify",          x: 400, y: 80  },
  { id: "retrieve",          label: "retrieve",          x: 250, y: 200 },
  { id: "reason",            label: "reason",            x: 250, y: 320 },
  { id: "decide",            label: "decide",            x: 250, y: 440 },
  { id: "auto_resolve",      label: "auto_resolve",      x: 100, y: 560 },
  { id: "escalate",          label: "escalate",          x: 400, y: 560 },
  { id: "escalate_fast_exit",label: "escalate_fast_exit",x: 550, y: 200 },
]

EDGES = [
  { from: "classify",   to: "retrieve"           },  // standard path
  { from: "classify",   to: "escalate_fast_exit" },  // fast-exit path
  { from: "retrieve",   to: "reason"             },
  { from: "reason",     to: "decide"             },
  { from: "decide",     to: "auto_resolve"       },
  { from: "decide",     to: "escalate"           },
]
```

**Active nodes per path:**

| Path | Active nodes | Dimmed nodes |
|---|---|---|
| Standard — auto_resolve | classify → retrieve → reason → decide → auto_resolve | escalate, escalate_fast_exit |
| Standard — escalate | classify → retrieve → reason → decide → escalate | auto_resolve, escalate_fast_exit |
| Fast-exit | classify → escalate_fast_exit | retrieve, reason, decide, auto_resolve, escalate |
| Rejection | classify only | all others |

---

## Shared Data — API Call Specification

**Endpoint:** `POST https://api.anthropic.com/v1/messages`

**Headers:**
```
Content-Type: application/json
x-api-key: <embedded key>
anthropic-version: 2023-06-01
```

**Model:** `claude-sonnet-4-20250514`

**Max tokens:** `1000`

**System prompt:**
```
You are simulating the Huginn v2 trade exception triage agent for a portfolio demo.
Huginn is a LangGraph-based AI agent that classifies financial trade exceptions,
retrieves relevant regulatory document chunks from a Chroma vector store (Mimir),
and reasons over them using a four-factor regulatory rubric to produce a confidence
score, reasoning trace, and resolution steps.

You will receive a trade exception payload. Respond ONLY with a JSON object.
No preamble. No explanation outside the JSON.

For standard path exceptions, respond with:
{
  "path": "standard",
  "retrieved_chunks": [
    {
      "document_id": "<e.g. FINRA-11810>",
      "section_id": "<e.g. FINRA-11810-b>",
      "retrieved_via": "<primary or cross_reference>",
      "text": "<full text of the retrieved regulatory chunk — minimum 3 sentences>"
    }
  ],
  "confidence_score": <float 0.0–1.0>,
  "outcome": "<auto_resolve or escalate>",
  "reasoning_trace": "<step-by-step explanation referencing the retrieved chunks>",
  "resolution_steps": "<specific steps to resolve this exception>"
}

For fast-exit exceptions (description contains: sanctions, AML, regulatory hold, buy-in, sell-out):
{
  "path": "fast_exit",
  "triggered_keyword": "<the keyword detected>",
  "outcome": "escalate",
  "escalation_reason": "mandatory escalation keyword detected: <keyword>"
}

For invalid type exceptions (type is not settlement_mismatch):
{
  "path": "rejection",
  "error": {
    "status": 422,
    "detail": [
      {
        "loc": ["body", "type"],
        "msg": "value is not a valid settlement_mismatch type",
        "type": "value_error.enum"
      }
    ]
  }
}

The confidence threshold is 0.75. auto_resolve when score >= 0.75, escalate when < 0.75.
Regulatory documents in scope: SEC-15c6-1, SEC-15c6-2, FINRA-11100, FINRA-11710,
FINRA-11810, FINRA-11820. Always retrieve 2–5 chunks across 1–3 documents for standard
path exceptions. Include at least one cross_reference chunk where a rule references another.
```

**User message:** The full JSON payload of the selected scenario, serialized as a string.

**Response handling:**
- Parse `data.content[0].text` as JSON.
- Strip any markdown code fences before parsing.
- On JSON parse failure, treat as API error and show error state.
- On HTTP error (non-200 status), show error state.

---

## Component 1 — FramingHeader

**Responsibility:** Renders the demo title and framing paragraph. Static. No inputs, no outputs, no interaction.

**Renders:**
- Title: `Huginn — Triaging Trade Exceptions` — large, prominent.
- Swagger-style endpoint badge: green `POST` badge followed by `/exceptions`.
- Framing paragraph: four sentences maximum. Content:
  - What Huginn does (trade exception triage agent, auto-resolve or escalate).
  - That it was built design-first using structured human-AI collaboration.
  - That the knowledge base is real FINRA and SEC regulatory documents.
  - What the recruiter is about to do (select a scenario, run the agent, watch it reason).

**Boundaries:**
- Does not render any interactive elements.
- Does not conditionally render based on application state.
- Framing copy is hardcoded — it is not derived from scenario data.

---

## Component 2 — ScenarioSelector

**Responsibility:** Displays all five scenarios simultaneously. Tracks the selected scenario. On selection change, notifies the parent and clears all output sections.

**Inputs:**
- `selectedScenarioId: string` — the id of the currently selected scenario.
- `onSelect: (scenarioId: string) => void` — callback fired when the recruiter selects a scenario.
- `disabled: boolean` — true while the API call is in flight. Selection is blocked during loading.

**Renders:**
- Five scenario options displayed simultaneously as a radio group or tab strip.
- Each option shows: scenario label (e.g. "Price mismatch — AAPL, 500 shares") and outcome hint (e.g. "auto-resolved") as a subordinate label beneath the scenario name.
- The active scenario is visually highlighted.
- When `disabled` is true, the selector is non-interactive but remains visible.

**Outputs:**
- Fires `onSelect(scenarioId)` when a scenario is clicked and `disabled` is false.

**Boundaries:**
- Does not own scenario data — reads from `SCENARIOS` constant.
- Does not clear output sections directly — parent handles that on `onSelect`.
- Does not render the payload — that is `RequestPanel`'s responsibility.

---

## Component 3 — RequestPanel

**Responsibility:** Displays the selected scenario's JSON payload in a read-only, Swagger-styled request body panel. Contains the Execute button.

**Inputs:**
- `scenario: Scenario` — the full scenario object for the currently selected scenario.
- `onExecute: () => void` — callback fired when Execute is clicked.
- `isLoading: boolean` — true while the API call is in flight.

**Renders:**
- Section header: `Request Body` in Swagger style.
- Read-only JSON block displaying the selected scenario's payload, pretty-printed with syntax highlighting. Not editable.
- Execute button labeled `Execute`. When `isLoading` is true, the button is disabled and its label changes to `Running agent…`.

**Outputs:**
- Fires `onExecute()` when Execute is clicked and `isLoading` is false.

**Boundaries:**
- Payload is always read-only. No input elements, no contentEditable.
- Does not make the API call — parent handles that on `onExecute`.
- Does not show the response — that is `ResponsePanel`'s responsibility.

---

## Component 4 — StateGraph

**Responsibility:** Renders the LangGraph node graph. Hidden on load. Appears when Execute is clicked. Animates nodes sequentially to show which path fired. Renders loading state and error state.

**Inputs:**
- `visible: boolean` — false on load, true after Execute is clicked.
- `status: "loading" | "animating" | "complete" | "error"` — drives rendering behavior.
- `activePath: "standard_auto_resolve" | "standard_escalate" | "fast_exit" | "rejection" | null` — determines which nodes activate and which dim. Null during loading.
- `errorMessage: string | null` — shown when status is "error".

**Renders:**

*When `visible` is false:* Nothing. Component is not mounted.

*When `status` is "loading":* The full node graph renders with all nodes in a neutral (unactivated) state. A pulsing loading indicator appears above the graph labeled `Running agent…`.

*When `status` is "animating" or "complete":* The node graph renders with nodes colored according to `activePath`. Nodes animate to their final state sequentially — each node transitions from neutral to active or dimmed with a 400ms transition, staggered 300ms apart in path order. Active nodes: highlighted border, colored background. Dimmed nodes: reduced opacity (0.3), grayed fill, labeled "skipped" where applicable (fast-exit and rejection paths only).

*When `status` is "error":* The node graph is hidden. An error message renders: `The API call failed — please try again.`

**Node coloring by path:**

| Node | Standard auto_resolve | Standard escalate | Fast-exit | Rejection |
|---|---|---|---|---|
| classify | active | active | active | active |
| retrieve | active | active | dimmed | dimmed |
| reason | active | active | dimmed | dimmed |
| decide | active | active | dimmed | dimmed |
| auto_resolve | active | dimmed | dimmed | dimmed |
| escalate | dimmed | active | dimmed | dimmed |
| escalate_fast_exit | dimmed | dimmed | active | dimmed |

**Boundaries:**
- Does not make the API call.
- Does not read scenario data directly — receives `activePath` from parent.
- Node positions are defined by `NODES` constant. Layout is fixed, not dynamic.
- Animation is CSS transition-based. No animation library required.
- The graph is rendered as SVG or as absolutely positioned divs — either is acceptable. The node positions in `NODES` are specified in pixels relative to a 700×650px canvas.

---

## Component 5 — RetrievalPanel

**Responsibility:** Renders one card per retrieved chunk. Hidden on load and on fast-exit and rejection paths. Appears after StateGraph animation completes on the standard path.

**Inputs:**
- `visible: boolean` — false on load, false on fast-exit and rejection paths, true after StateGraph animation completes on standard path.
- `chunks: Chunk[]` — array of retrieved chunk objects from the API response.

**Chunk shape:**
```
{
  document_id: string,       // e.g. "FINRA-11810"
  section_id: string,        // e.g. "FINRA-11810-b"
  retrieved_via: "primary" | "cross_reference",
  text: string               // full chunk text from API response
}
```

**Renders:**

*When `visible` is false:* Nothing. Component is not mounted.

*When `visible` is true:* A section header labeled `Retrieved Regulatory Chunks — Mimir` followed by one card per chunk in the order returned by the API.

Each chunk card renders:
- **Header:** `document_id` — `section_id` (e.g. `FINRA-11810 — FINRA-11810-b`), bold.
- **Badge:** `retrieved_via` value. `primary` renders as a neutral badge. `cross_reference` renders as a distinct badge (different color) to signal two-pass retrieval.
- **Body:** Truncated snippet — first two to three sentences of `chunk.text`. Truncation is applied by character count (approximately 300 characters) with an ellipsis if truncated.
- **Expand control:** A `Show full chunk` toggle below the snippet. On click, the full `chunk.text` replaces the truncated snippet. Toggle label changes to `Show less`. State is per-card and independent.

**Boundaries:**
- Does not make the API call.
- Does not determine its own visibility — parent controls `visible`.
- Truncation is presentational only — the full text is always available in the component's data.
- Card order matches the order of `chunks` array — no re-sorting.

---

## Component 6 — ResponsePanel

**Responsibility:** Renders the agent's decision as three cards on the standard path, or a single outcome card on fast-exit and rejection paths. Hidden on load. Appears after RetrievalPanel on standard path, or after StateGraph on fast-exit and rejection paths.

**Inputs:**
- `visible: boolean` — false on load, true after the appropriate prior section has appeared.
- `path: "standard" | "fast_exit" | "rejection"` — determines which cards render.
- `response: StandardResponse | FastExitResponse | RejectionResponse | null`

**Response shapes:**

Standard path:
```
{
  confidence_score: float,      // 0.0–1.0
  outcome: "auto_resolve" | "escalate",
  reasoning_trace: string,
  resolution_steps: string
}
```

Fast-exit path:
```
{
  triggered_keyword: string,
  outcome: "escalate",
  escalation_reason: string
}
```

Rejection path:
```
{
  error: {
    status: 422,
    detail: Array<{ loc: string[], msg: string, type: string }>
  }
}
```

**Renders:**

*When `visible` is false:* Nothing. Component is not mounted.

*Standard path — three cards:*

1. **Confidence Score card:**
   - Prominent outcome label: `AUTO-RESOLVED` (green) or `ESCALATED` (amber).
   - Numeric confidence score (e.g. `0.83`).
   - Color-coded badge: `HIGH` in green if score ≥ 0.75, `LOW` in red if score < 0.75.
   - Threshold label: `threshold: 0.75`.

2. **Reasoning Trace card:**
   - Header: `Reasoning Trace`.
   - Full prose reasoning trace. Scrollable if long (max height: 300px, overflow scroll).

3. **Resolution Steps card:**
   - Header: `Resolution Steps`.
   - Full prose resolution steps. Scrollable if long (max height: 300px, overflow scroll).

*Fast-exit path — one card:*
- Outcome label: `ESCALATED` (amber).
- Label: `Mandatory escalation — no model call`.
- Triggered keyword displayed: `Keyword detected: <triggered_keyword>`.
- Escalation reason prose.

*Rejection path — one card:*
- HTTP status badge: `422 Unprocessable Entity` in red.
- Label: `Rejected at validation — agent not reached`.
- Pydantic error detail rendered as a structured list: `loc`, `msg`, `type` for each error object.

**Boundaries:**
- Does not make the API call.
- Does not determine its own visibility — parent controls `visible`.
- Scrollable containers are per-card — the page itself does not scroll lock.
- Cards render in fixed order: Confidence Score, Reasoning Trace, Resolution Steps. Order is not configurable.

---

## Parent Component — App (Root)

**Responsibility:** Owns all application state. Orchestrates the API call. Controls visibility and timing of all child components. Renders all six components in a single column.

**State:**
```
selectedScenarioId: string          // default: SCENARIOS[0].id
isLoading: boolean                  // default: false
graphStatus: "hidden" | "loading" | "animating" | "complete" | "error"
retrievalVisible: boolean           // default: false
responseVisible: boolean            // default: false
apiResponse: ParsedResponse | null  // default: null
errorMessage: string | null         // default: null
```

**Interaction sequence — Execute clicked:**

1. Set `isLoading: true`, `graphStatus: "loading"`, collapse retrieval and response sections to hidden, clear `apiResponse`.
2. Make API call with selected scenario payload.
3. On API success:
   a. Parse response JSON.
   b. Set `isLoading: false`, `apiResponse: parsedResponse`.
   c. Set `graphStatus: "animating"`. StateGraph begins node animation.
   d. After StateGraph animation completes (duration: number of active nodes × 300ms + 400ms):
      - Set `graphStatus: "complete"`.
      - If path is `standard`: set `retrievalVisible: true`. After 1500ms: set `responseVisible: true`.
      - If path is `fast_exit` or `rejection`: set `responseVisible: true` immediately.
4. On API error:
   a. Set `isLoading: false`, `graphStatus: "error"`, `errorMessage: "The API call failed — please try again."`.

**Interaction sequence — Scenario selected:**

1. Set `selectedScenarioId: newId`.
2. Set `graphStatus: "hidden"`, `retrievalVisible: false`, `responseVisible: false`, `apiResponse: null`, `errorMessage: null`.
3. `isLoading` is always false at this point — selection is blocked during loading.

**Boundaries:**
- All API calls originate here. No child component makes API calls.
- All visibility state lives here. No child component controls its own visibility independently.
- The embedded API key is defined here as a module-level constant. It is not passed as a prop.
- Timing constants (animation durations, inter-section delays) are defined here as named constants, not inline magic numbers.

---

## Timing Constants

| Constant | Value | Purpose |
|---|---|---|
| `NODE_TRANSITION_MS` | 400 | CSS transition duration per node |
| `NODE_STAGGER_MS` | 300 | Delay between each node activation |
| `POST_GRAPH_DELAY_MS` | 1500 | Delay between graph complete and retrieval panel appearing |
| `POST_RETRIEVAL_DELAY_MS` | 1500 | Delay between retrieval panel appearing and response panel appearing |

---

## Visual Specification

**Color palette — Swagger-inspired:**

| Token | Value | Usage |
|---|---|---|
| `--swagger-green` | `#49cc90` | POST badge, active node fill, HIGH badge, AUTO-RESOLVED label |
| `--swagger-green-dark` | `#1a7a4a` | POST badge text |
| `--swagger-bg` | `#1a1a2e` | Page background |
| `--panel-bg` | `#2d2d44` | Panel and card backgrounds |
| `--panel-border` | `#3d3d5c` | Panel borders |
| `--text-primary` | `#f0f0f0` | Primary text |
| `--text-secondary` | `#a0a0b8` | Secondary text, labels |
| `--red` | `#e74c3c` | LOW badge, ESCALATED label, 422 badge |
| `--amber` | `#f39c12` | ESCALATED label on fast-exit |
| `--node-active-bg` | `#1a4a6b` | Active node fill |
| `--node-active-border` | `#49cc90` | Active node border |
| `--node-dimmed-opacity` | `0.3` | Dimmed node opacity |
| `--cross-ref-badge` | `#8e44ad` | cross_reference badge color |

**Typography:**
- Font: system sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`).
- Code/JSON blocks: monospace (`"SF Mono", "Fira Code", monospace`).

**Layout:**
- Single column, centered, max-width 860px.
- Sections separated by 32px vertical gap.
- Cards within a section separated by 16px vertical gap.

---

## What This Document Does Not Specify

The following are implementation details resolved during build, not contract items:

- Internal variable names within any component
- CSS class naming conventions
- Exact SVG path geometry for node graph edges
- The exact character count used for snippet truncation (approximately 300 is a guideline)
- Whether the node graph is implemented as SVG or positioned divs
EOF