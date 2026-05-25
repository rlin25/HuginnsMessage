# Huginn v2 Demo — Interface Contract

**Status:** Implementation complete.
**Last updated:** May 2026
**Location:** `HuginnsMessage/huginn_v2_demo/` (monorepo subdirectory)
**Source of truth:** `huginn_v2_demo_design_decisions.md` — all component specifications derive from locked decisions. If a specification here conflicts with a locked decision, the locked decision governs.

---

## What This Document Is

An interface contract defines every component's inputs, outputs, and boundaries before any code is written. A developer reading this document should be able to build the demo without asking a follow-up question. A specification that cannot be written precisely is a gap — gaps are resolved here, not during implementation.

This contract specifies a single React artifact. There is no backend, no database, and no local API. The only external call is to the Anthropic Claude API at runtime, proxied through a Cloudflare Worker.

[Updated post-implementation: The original contract stated "the only external call is to the Anthropic Claude API at runtime" with no proxy. The actual implementation routes through a Cloudflare Worker at `https://huginn-demo.richard-lin2025.workers.dev`. The Worker injects the API key server-side. `index.html` does not contain the API key. See Decision 1 addendum in design_decisions.md.]

---

## Plain English Description

The Huginn v2 demo is a single-page React artifact styled to resemble a Swagger UI. It opens with a short framing paragraph and a title. Below that, the recruiter sees a scenario selector showing five named scenarios simultaneously. The selected scenario's JSON request body is displayed in a read-only request panel beneath the selector. An Execute button submits the scenario.

On Execute, a loading state appears and a live Claude API call is made (via the Cloudflare Worker proxy). When the response returns, three sections reveal sequentially: the LangGraph state diagram (nodes animate to show which path fired), the retrieval cards (one card per regulatory chunk retrieved, with metadata and a snippet), and the response cards (confidence score, reasoning trace, resolution steps). Selecting a new scenario collapses all output sections and resets to the pre-run state.

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
      description: "We delivered 200 TSLA shares; counterparty acknowledges receipt of 150 only and has formally rejected responsibility for the 50-share shortfall, asserting our delivery records are erroneous. Settlement date 2026-05-21. Three business days elapsed, two resolution attempts rejected by counterparty. Their compliance team is now involved and has indicated a formal FINRA arbitration filing if the discrepancy is not resolved by end of day.",
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

[Updated post-implementation: The `quantity_mismatch` description was extended after initial implementation. The original spec read: `"We delivered 200 TSLA shares, counterparty confirms receipt of 150 only. Settlement date 2026-05-21. Shortfall of 50 shares unresolved after two business days."` The deployed description is more confrontational — counterparty formal rejection, two resolution attempts, compliance team involvement, FINRA arbitration threat — to increase the likelihood that the model reliably returns `escalate` outcome for this scenario. The scenario's `outcome_hint` of `"escalated"` is meant to be descriptive, and the longer description makes the model's escalation decision more deterministic.]

**Notes:**
- `outcome_hint` is display-only — it appears in the scenario label, not in the payload.
- `path` drives which visualization behavior fires: `standard`, `fast_exit`, or `rejection`.
- Payloads are static. They do not change between runs.

---

## Shared Data — Node Graph Definition

The state graph is a static constant matching `agent/graph.py` exactly.

```
NODES = [
  { id: "classify",           label: "classify",           cx: 350, cy: 60  },
  { id: "retrieve",           label: "retrieve",           cx: 200, cy: 175 },
  { id: "reason",             label: "reason",             cx: 200, cy: 280 },
  { id: "decide",             label: "decide",             cx: 200, cy: 385 },
  { id: "auto_resolve",       label: "auto_resolve",       cx: 90,  cy: 465 },
  { id: "escalate",           label: "escalate",           cx: 310, cy: 465 },
  { id: "escalate_fast_exit", label: "escalate_fast_exit", cx: 530, cy: 175 },
]

EDGES = [
  { from: "classify",  to: "retrieve"           },
  { from: "classify",  to: "escalate_fast_exit" },
  { from: "retrieve",  to: "reason"             },
  { from: "reason",    to: "decide"             },
  { from: "decide",    to: "auto_resolve"       },
  { from: "decide",    to: "escalate"           },
]
```

[Updated post-implementation: The original interface contract specified node positions using `x`/`y` keys with different values (e.g. classify at `x: 400, y: 80`). The UI spec updated the canvas to 700×500px and recalculated all positions using `cx`/`cy` center-of-node keys. The implementation uses the UI spec coordinates exactly as shown above. The interface contract's original node position table is superseded by the UI spec and this corrected entry.]

**Active nodes per path:**

| Path | Active nodes | Dimmed nodes |
|---|---|---|
| Standard — auto_resolve | classify → retrieve → reason → decide → auto_resolve | escalate, escalate_fast_exit |
| Standard — escalate | classify → retrieve → reason → decide → escalate | auto_resolve, escalate_fast_exit |
| Fast-exit | classify → escalate_fast_exit | retrieve, reason, decide, auto_resolve, escalate |
| Rejection | classify only | all others |

**Active edges per path:**

[Updated post-implementation: `PATH_ACTIVE_EDGES` was not specified in any design document. It was introduced during implementation to drive edge coloring (green stroke and active arrowhead marker on edges along the active path). Each edge activates when its destination node is revealed.]

```
PATH_ACTIVE_EDGES = {
  standard_auto_resolve: [
    { from: "classify", to: "retrieve"      },
    { from: "retrieve", to: "reason"        },
    { from: "reason",   to: "decide"        },
    { from: "decide",   to: "auto_resolve"  },
  ],
  standard_escalate: [
    { from: "classify", to: "retrieve"  },
    { from: "retrieve", to: "reason"    },
    { from: "reason",   to: "decide"    },
    { from: "decide",   to: "escalate"  },
  ],
  fast_exit:  [{ from: "classify", to: "escalate_fast_exit" }],
  rejection:  [],
}
```

---

## Shared Data — API Call Specification

**Endpoint:** `POST https://huginn-demo.richard-lin2025.workers.dev`

[Updated post-implementation: The original spec listed the endpoint as `POST https://api.anthropic.com/v1/messages` with an embedded API key header. The implementation calls the Cloudflare Worker proxy instead. The Worker forwards the request body to the Anthropic endpoint and injects the API key server-side. `index.html` sends no `x-api-key` header — that is handled by the Worker.]

**Headers sent from index.html to Worker:**
```
Content-Type: application/json
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

**User message:** The full JSON payload of the selected scenario, serialized as a string, wrapped in `{ "exception": <payload> }`.

**Response handling:**
- Parse `data.content[0].text` as JSON.
- Strip any markdown code fences before parsing.
- On JSON parse failure, treat as API error and show error state.
- On HTTP error (non-200 status from Worker), show error state.

---

## Component 1 — FramingHeader

**Responsibility:** Renders the demo title and framing paragraph. Static. No inputs, no outputs, no interaction.

**Renders:**
- Title: `Huginn — Triaging Trade Exceptions` — large, prominent, IBM Plex Mono.
- Swagger-style endpoint badge: green `POST` badge followed by `/exceptions`, flush right on the same line as the title.
- Framing paragraph below. Content as implemented:
  - What Huginn does and that it was built design-first.
  - That this demo uses a live Claude API call to simulate Huginn's pipeline.
  - That architecture, execution paths, and regulatory document references are accurate to the real system.
  - Instruction to select a scenario and click Execute.

[Updated post-implementation: The framing copy specified in the masterplan included a sentence about a previous AWS deployment. That sentence was removed. The deployed framing paragraph is three sentences, not four. See Decision 14 addendum in design_decisions.md for the exact deployed copy.]

**Boundaries:**
- Does not render any interactive elements.
- Does not conditionally render based on application state.
- Framing copy is hardcoded — it is not derived from scenario data.

---

## Component 2 — ScenarioSelector

**Responsibility:** Displays all five scenarios simultaneously. Tracks the selected scenario. On selection change, notifies the parent and clears all output sections.

**Inputs:**
- `selectedId: string` — the id of the currently selected scenario.
- `onSelect: (scenarioId: string) => void` — callback fired when the recruiter selects a scenario.
- `disabled: boolean` — true while the API call is in flight and during animation. Selection is blocked during loading.

[Updated post-implementation: The prop is named `selectedId`, not `selectedScenarioId`. The `disabled` prop is `true` for the entire duration of `isLoading`, which includes the animation phase (see Decision 21 in design_decisions.md).]

**Renders:**
- Five scenario options displayed simultaneously as a tab strip inside a bordered container.
- Each option shows: scenario label and outcome hint as a subordinate italic label beneath the scenario name.
- The active scenario is visually highlighted with an inset box-shadow left indicator and `--panel-bg` background.
- When `disabled` is true, the selector is non-interactive (opacity 0.5, cursor not-allowed) but remains visible.

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
- `isLoading: boolean` — true while the API call is in flight and during animation.

**Renders:**
- Section header row: `Request Body` label left, POST badge + `/exceptions` right.
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
- `status: "loading" | "animating" | "complete" | "error"` — drives rendering behavior.
- `activePath: "standard_auto_resolve" | "standard_escalate" | "fast_exit" | "rejection" | null` — determines which nodes activate and which dim. Null during loading.
- `revealedNodes: Set<string>` — the set of node IDs that have been revealed by the animation so far. Drives per-node state calculation.
- `errorMessage: string | null` — shown when status is "error".

[Updated post-implementation: The original spec listed a `visible: boolean` prop. The implementation does not pass a `visible` prop to `StateGraph`. Visibility is controlled by the parent with conditional rendering: `{graphStatus !== 'hidden' && <StateGraph ... />}`. The `revealedNodes` prop was not in the original spec — it was introduced as an implementation detail to drive per-node animation state without the component managing its own timers. The original spec listed `animatedNodes` as a possible name; the implemented name is `revealedNodes`.]

**Renders:**

*When not mounted (graphStatus === 'hidden' in parent):* Nothing.

*When `status` is "loading":* The full node graph renders with all nodes in neutral state. A pulsing SVG ring animates around the classify node. Label `Running agent…` in `--text-secondary`.

*When `status` is "animating" or "complete":* The node graph renders with nodes colored according to `activePath` and `revealedNodes`. Nodes not in `revealedNodes` remain neutral. Nodes in `revealedNodes` and in the active path list are active. Nodes in `revealedNodes` but not in the active path list are dimmed.

*When `status` is "error":* The SVG is not rendered. An error message renders: `The API call failed — please try again.`

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
- The graph is rendered as SVG on a 700×500px canvas.

---

## Component 5 — RetrievalPanel

**Responsibility:** Renders one card per retrieved chunk. Hidden on load and on fast-exit and rejection paths. Appears after StateGraph animation completes on the standard path.

**Inputs:**
- `chunks: Chunk[]` — array of retrieved chunk objects from the API response.

[Updated post-implementation: The original spec listed a `visible: boolean` prop. The implementation does not pass a `visible` prop to `RetrievalPanel`. Visibility is controlled by the parent with conditional rendering: `{retrievalVisible && apiResponse?.retrieved_chunks && <RetrievalPanel chunks={...} />}`.]

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

*When not mounted:* Nothing.

*When mounted:* A section header labeled `Retrieved Regulatory Chunks — Mimir` followed by one card per chunk in the order returned by the API.

Each chunk card renders:
- **Header:** `document_id — section_id`, bold.
- **Badge:** `retrieved_via` value. `primary` renders as a neutral badge. `cross_reference` renders as a purple badge labeled `CROSS-REF`.
- **Body:** Truncated snippet — first approximately 300 characters of `chunk.text` with ellipsis if truncated.
- **Expand control:** A `Show full chunk` toggle below the snippet. On click, the full `chunk.text` replaces the truncated snippet. Toggle label changes to `Show less`. State is per-card and independent.

**Boundaries:**
- Does not make the API call.
- Truncation is presentational only — the full text is always available in the component's data.
- Card order matches the order of `chunks` array — no re-sorting.

---

## Component 6 — ResponsePanel

**Responsibility:** Renders the agent's decision as three cards on the standard path, or a single outcome card on fast-exit and rejection paths. Hidden on load. Appears after RetrievalPanel on standard path, or after StateGraph on fast-exit and rejection paths.

**Inputs:**
- `path: "standard" | "fast_exit" | "rejection"` — determines which cards render.
- `response: StandardResponse | FastExitResponse | RejectionResponse` — the parsed API response object.

[Updated post-implementation: The original spec listed a `visible: boolean` prop. The implementation does not pass a `visible` prop to `ResponsePanel`. Visibility is controlled by the parent with conditional rendering: `{responseVisible && apiResponse && <ResponsePanel path={apiResponse.path} response={apiResponse} />}`.]

**Response shapes:**

Standard path:
```
{
  path: "standard",
  confidence_score: float,      // 0.0–1.0
  outcome: "auto_resolve" | "escalate",
  reasoning_trace: string,
  resolution_steps: string,
  retrieved_chunks: Chunk[]
}
```

Fast-exit path:
```
{
  path: "fast_exit",
  triggered_keyword: string,
  outcome: "escalate",
  escalation_reason: string
}
```

Rejection path:
```
{
  path: "rejection",
  error: {
    status: 422,
    detail: Array<{ loc: string[], msg: string, type: string }>
  }
}
```

**Renders:**

*When not mounted:* Nothing.

*Standard path — three cards:*

1. **Confidence Score card:**
   - Prominent outcome label: `AUTO-RESOLVED` (green) or `ESCALATED` (amber).
   - Numeric confidence score (e.g. `0.83`) at 2rem monospace, flush right.
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
- Secondary label: `Mandatory escalation — no model call`.
- Triggered keyword: `Keyword detected: <triggered_keyword>` in monospace green.
- Escalation reason prose.

*Rejection path — one card:*
- HTTP status badge: `422 Unprocessable Entity` in red.
- Secondary label: `Rejected at validation — agent not reached`.
- Pydantic error detail rendered as structured lines: `loc`, `msg`, `type` for each error object.

**Boundaries:**
- Does not make the API call.
- Scrollable containers are per-card — the page itself does not scroll lock.
- Cards render in fixed order: Confidence Score, Reasoning Trace, Resolution Steps. Order is not configurable.

---

## Parent Component — App (Root)

**Responsibility:** Owns all application state. Orchestrates the API call. Controls visibility and timing of all child components. Renders all six components in a single column.

**State:**
```
selectedId: string              // default: SCENARIOS[0].id
isLoading: boolean              // default: false
graphStatus: "hidden" | "loading" | "animating" | "complete" | "error"
activePath: string | null       // default: null
revealedNodes: Set<string>      // default: new Set()
retrievalVisible: boolean       // default: false
responseVisible: boolean        // default: false
apiResponse: ParsedResponse | null  // default: null
errorMessage: string | null     // default: null
```

[Updated post-implementation: The original spec listed 7 state fields. The implementation has 9. `activePath` and `revealedNodes` were added during implementation to drive StateGraph rendering. The original spec used `selectedScenarioId`; the implementation uses `selectedId`.]

**Interaction sequence — Execute clicked:**

1. Set `isLoading: true`, `graphStatus: "loading"`, clear `activePath`, clear `revealedNodes`, collapse retrieval and response sections to hidden, clear `apiResponse` and `errorMessage`.
2. Make API call (via `callHuginn`) with selected scenario payload.
3. On API success:
   a. Parse response JSON.
   b. Set `apiResponse: parsedResponse`, `activePath: deriveActivePath(parsed)`, `graphStatus: "animating"`.
   c. Step through `PATH_ACTIVE_NODES[activePath]` in order, adding each node ID to `revealedNodes` with `NODE_STAGGER_MS` (300ms) stagger between each.
   d. After last active node's stagger timer, wait `NODE_TRANSITION_MS` (400ms), then set `revealedNodes` to the full set of all node IDs (triggers dimming of non-active nodes).
   e. Wait another `NODE_TRANSITION_MS` (400ms), then set `graphStatus: "complete"` and `isLoading: false`.
   f. If path is `standard`: wait `POST_GRAPH_DELAY_MS` (1500ms), set `retrievalVisible: true`. Wait `POST_RETRIEVAL_DELAY_MS` (1500ms), set `responseVisible: true`.
   g. If path is `fast_exit` or `rejection`: set `responseVisible: true` immediately (no delay after graph completes).
4. On API error:
   a. Set `isLoading: false`, `graphStatus: "error"`, `errorMessage: "The API call failed — please try again."`.

[Updated post-implementation: The original spec Step 3b set `isLoading: false` at API success. The implementation sets `isLoading: false` after animation completes (Step 3e above). This is consistent with the UI spec Interaction States table, which shows the selector and Execute button disabled during "Graph animating" state. See Decision 21 in design_decisions.md.]

**Interaction sequence — Scenario selected:**

1. Cancel all pending timers.
2. Set `selectedId: newId`.
3. Set `graphStatus: "hidden"`, `activePath: null`, `revealedNodes: new Set()`, `retrievalVisible: false`, `responseVisible: false`, `apiResponse: null`, `errorMessage: null`.
4. `isLoading` is always false at this point — selection is blocked during loading.

**Boundaries:**
- All API calls originate here. No child component makes API calls.
- All visibility state lives here. No child component controls its own visibility independently.
- The API key is not in `index.html` — it lives in the Cloudflare Worker environment variable.
- Timing constants are defined as named constants, not inline magic numbers.
- A `timers` ref tracks all pending `setTimeout` IDs. A `clearTimers()` function cancels all pending timers. All `setTimeout` calls go through a `later()` wrapper that registers the ID.

---

## Timing Constants

| Constant | Value | Purpose |
|---|---|---|
| `NODE_TRANSITION_MS` | 400 | CSS transition duration per node; also used as post-animation settle delay |
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
| `--red` | `#e74c3c` | LOW badge, 422 badge |
| `--amber` | `#f39c12` | ESCALATED label on fast-exit |
| `--node-active-bg` | `#1a4a6b` | Active node fill |
| `--node-active-border` | `#49cc90` | Active node border (same value as `--swagger-green`) |
| `--cross-ref-badge` | `#8e44ad` | cross_reference badge color |

[Updated post-implementation: The original spec listed `--node-dimmed-opacity: 0.3` as a CSS custom property in the color palette. This token is not defined as a CSS custom property in the implemented `:root` block. The value `0.3` is applied inline in the component logic. All other tokens are defined in `:root` and match their specified values exactly.]

**Typography:**
- Font: system sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`).
- Code/JSON blocks: monospace (`"Fira Code", "SF Mono", monospace`).
- Title: IBM Plex Mono 600, loaded via Google Fonts.

**Layout:**
- Single column, centered, max-width 860px.
- Sections separated by 32px vertical gap.
- Cards within a section separated by 12px vertical gap (implemented as `gap: 12` in flex column).

[Updated post-implementation: The original spec listed 16px card gap. The implementation uses 12px (`gap: 12` in the flex column containing RetrievalPanel chunk cards and ResponsePanel output cards).]

---

## What This Document Does Not Specify

The following are implementation details resolved during build, not contract items:

- Internal variable names within any component (beyond those documented in the App state section above)
- CSS class naming conventions
- Exact SVG path geometry for node graph edges (see Decision 19 in design_decisions.md for the implemented formulas)
- Whether the node graph is implemented as SVG or positioned divs (implemented as SVG)
EOF