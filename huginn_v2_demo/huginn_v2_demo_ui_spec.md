# Huginn v2 Demo — UI Specification

**Status:** Design phase complete. Ready for implementation.
**Last updated:** May 2026
**Location:** `HuginnsMessage/huginn_v2_demo/`
**Source of truth:** `huginn_v2_demo_design_decisions.md` and `huginn_v2_demo_interface_contract.md` — all visual decisions derive from locked decisions. If anything here conflicts with a locked decision, the locked decision governs.

---

## What This Document Is

The interface contract specifies component boundaries: inputs, outputs, state, and data shapes. This document specifies what the recruiter sees — layout, visual composition, interaction states, and the exact rendering of every element. A builder reading both documents should be able to implement the demo without making a visual judgment call.

This document does not re-specify anything already locked in the interface contract. It fills the gaps the contract explicitly deferred: SVG node geometry, component-level visual composition, shadcn/ui component selection, and element-level rendering detail.

---

## Implementation Stack Decision

**Component library:** shadcn/ui, imported from `@/components/ui/...` as available in Claude artifacts.

**Rationale:** The demo is a portfolio artifact. Generic AI-generated UI is a credibility liability in this context — a recruiter who recognizes the aesthetic loses signal about the candidate's design judgment. shadcn/ui provides polished, opinionated components (tabs, cards, badges, buttons, scroll areas) that read as deliberate choices. Color tokens from the interface contract override shadcn's defaults, so the Swagger-dark theme dominates while the component structure stays professional.

**shadcn components used:**

| Component | Used in |
|---|---|
| `Tabs` / `TabsList` / `TabsTrigger` | ScenarioSelector |
| `Card` / `CardHeader` / `CardContent` | RetrievalPanel chunk cards, ResponsePanel output cards |
| `Badge` | `retrieved_via` badges, outcome badges, HTTP status badge |
| `Button` | Execute button in RequestPanel |
| `ScrollArea` | Reasoning Trace card, Resolution Steps card (capped height) |
| `Separator` | Between FramingHeader and ScenarioSelector |

**Custom-built (not shadcn):**
- StateGraph (SVG)
- JSON syntax-highlighted block in RequestPanel
- POST badge (Swagger-specific chrome)
- Loading pulse indicator

---

## Typography

The interface contract specifies a system sans-serif stack. This document overrides that for the title only, to create visual hierarchy and avoid the AI-default look.

| Element | Font | Weight | Size |
|---|---|---|---|
| Demo title | `"IBM Plex Mono", monospace` | 600 | 1.5rem |
| Section headers | System sans-serif | 600 | 0.875rem, uppercase, letter-spacing 0.08em |
| Body / prose | System sans-serif | 400 | 0.9rem |
| JSON / code blocks | `"Fira Code", "SF Mono", monospace` | 400 | 0.8rem |
| Node labels (SVG) | System sans-serif | 500 | 11px |
| Badges | System sans-serif | 600 | 0.7rem, uppercase |

**Rationale for IBM Plex Mono on the title:** The demo is about a system that processes structured financial data. A monospace title reads as deliberate and technical without being decorative. It pairs cleanly with the Swagger aesthetic — monospace implies precision. The title is the only element using it; everything else stays in sans-serif to keep the interface readable.

---

## Component 1 — FramingHeader: Visual Composition

**Layout:** Single column. Title line, then framing paragraph, separated by 8px.

**Title line composition:**
- Demo title `Huginn — Triaging Trade Exceptions` in IBM Plex Mono, 1.5rem, color `--text-primary`.
- On the same line, flush right: a green `POST` badge (`--swagger-green` background, `--swagger-green-dark` text) followed by `/exceptions` in monospace, color `--text-secondary`.
- The title and badge share a flex row with `justify-content: space-between`.

**Framing paragraph:** Four sentences, `--text-secondary`, 0.9rem. Sits 8px below the title line.

**Bottom border:** A 1px `--panel-border` line (shadcn `Separator`) sits 24px below the framing paragraph and separates the header from the ScenarioSelector.

---

## Component 2 — ScenarioSelector: Visual Composition

**Implementation:** shadcn `Tabs` with `TabsList` rendered horizontally. Five `TabsTrigger` elements, all visible simultaneously — no overflow scroll.

**Tab trigger composition (each scenario):**
- **Line 1:** Scenario label text, `--text-primary`, 0.875rem.
- **Line 2:** Outcome hint in smaller text — `--text-secondary`, 0.75rem, italicized — e.g. *auto-resolved*, *escalated*, *rejected at validation*.
- Tabs are stacked two-line internally; the `TabsList` has `height: auto` to accommodate.

**Active tab visual state:**
- Background: `--panel-bg`.
- Left border: 2px solid `--swagger-green`.
- No underline (override shadcn default tab underline indicator).
- Text on active tab: `--text-primary`.

**Disabled state (during loading):**
- All tabs: opacity 0.5, `pointer-events: none`.
- The active tab retains its highlighted border at reduced opacity.

**Section header:** The label `Scenarios` appears above the `TabsList` in section-header style (uppercase, 0.875rem, `--text-secondary`, letter-spacing 0.08em).

---

## Component 3 — RequestPanel: Visual Composition

**Outer container:** A panel with `background: --panel-bg`, `border: 1px solid --panel-border`, `border-radius: 6px`, padding 16px.

**Section header row:** Two elements in a flex row, `align-items: center`, `justify-content: space-between`:
- Left: Label `Request Body` in section-header style.
- Right: HTTP method badge and endpoint. Green `POST` badge (pill shape, `--swagger-green` bg, `--swagger-green-dark` text, 0.7rem bold uppercase, horizontal padding 8px) followed by `/exceptions` in monospace `--text-secondary`.

**JSON block:**
- Background: `--swagger-bg` (one shade darker than panel).
- Border: 1px solid `--panel-border`.
- Border-radius: 4px.
- Padding: 12px.
- Font: Fira Code / SF Mono, 0.8rem, `--text-primary`.
- Syntax highlighting: property keys in `--swagger-green`, string values in `--text-secondary`, punctuation in `--text-primary`. Implemented via a lightweight custom tokenizer — no external library.
- Not editable. No cursor change on hover.

**Execute button:**
- shadcn `Button`, variant `default`, overridden to use `--swagger-green` background, `--swagger-green-dark` text.
- Label: `Execute` at rest. `Running agent…` when `isLoading` is true.
- Disabled state when `isLoading`: opacity 0.6, `cursor: not-allowed`.
- Positioned below the JSON block, flush right within the panel, margin-top 12px.
- Width: `auto` (fits label text with standard padding).

---

## Component 4 — StateGraph: SVG Specification

### Canvas

SVG element: `width="700" height="500"` (revised from the 700×650 canvas in the interface contract — the layout below fits in 500px height).
Viewbox: `0 0 700 500`.
Background: transparent (sits on `--swagger-bg` section background).
Section header `Agent — LangGraph State Machine` renders above the SVG in section-header style.

### Node Dimensions

All nodes: `width=140`, `height=40`, `rx=6` (rounded rectangle).
Node label: centered horizontally and vertically within the rect, font-size 11px, font-family system sans-serif, font-weight 500.

### Node Positions (cx, cy = center of node)

| Node ID | Label | cx | cy |
|---|---|---|---|
| `classify` | `classify` | 350 | 60 |
| `retrieve` | `retrieve` | 200 | 175 |
| `reason` | `reason` | 200 | 280 |
| `decide` | `decide` | 200 | 385 |
| `auto_resolve` | `auto_resolve` | 90 | 465 |
| `escalate` | `escalate` | 310 | 465 |
| `escalate_fast_exit` | `escalate_fast_exit` | 530 | 175 |

Node `x = cx - 70`, `y = cy - 20` (top-left corner derived from center).

### Edges

Edges are `<path>` elements with `marker-end` arrowhead. Stroke: `--panel-border` in neutral state, `--swagger-green` on active path segments.

**Arrowhead marker definition** (in SVG `<defs>`):
```
<marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
  <path d="M0,0 L0,6 L8,3 z" fill="currentColor"/>
</marker>
```

Two marker variants: `arrow-active` (fill `--swagger-green`) and `arrow-neutral` (fill `--panel-border`). Edges switch marker on activation.

**Edge paths** (all cubic bezier `<path d="M ... C ...">` — exact control points are implementation detail, but the routing rules below are required):

| Edge | Routing rule |
|---|---|
| `classify → retrieve` | Exits bottom-left of classify; enters top of retrieve. Slight leftward curve. |
| `classify → escalate_fast_exit` | Exits bottom-right of classify; enters top of escalate_fast_exit. Slight rightward curve. |
| `retrieve → reason` | Straight vertical line. |
| `reason → decide` | Straight vertical line. |
| `decide → auto_resolve` | Exits bottom-left of decide; enters top of auto_resolve. Diagonal left. |
| `decide → escalate` | Exits bottom-right of decide; enters top of escalate. Slight right curve. |

Edge stroke-width: 1.5px.

### Node Visual States

Three states per node. All transitions: `transition: all 400ms ease`.

**Neutral (pre-run / loading):**
- `fill`: `--panel-bg`
- `stroke`: `--panel-border`
- `stroke-width`: 1.5
- Label color: `--text-secondary`
- Opacity: 1

**Active:**
- `fill`: `--node-active-bg` (`#1a4a6b`)
- `stroke`: `--node-active-border` (`--swagger-green`)
- `stroke-width`: 2
- Label color: `--swagger-green`
- Opacity: 1

**Dimmed:**
- `fill`: `--panel-bg`
- `stroke`: `--panel-border`
- `stroke-width`: 1
- Label color: `--text-secondary`
- Opacity: `--node-dimmed-opacity` (0.3)

Nodes that are dimmed on fast-exit or rejection paths additionally render a small `skipped` label in 9px `--text-secondary` text, centered 14px below the node rect.

### Loading State Visual

When `status === "loading"`: all nodes render in neutral state. A pulsing ring animates around the `classify` node — a second `<circle>` centered on `classify`'s center, `r=36`, `stroke: --swagger-green`, `stroke-width: 1.5`, `fill: none`, animated with a CSS `@keyframes pulse` that cycles opacity 0.6→0→0.6 over 1.2s. Label above SVG: `Running agent…` in `--text-secondary`, 0.875rem.

### Animation Sequence

Nodes activate in path order, one per `NODE_STAGGER_MS` (300ms). Implementation constructs an ordered array of node IDs for the active path and steps through them with `setTimeout` chains. Edge segments activate when their destination node activates.

**Standard auto_resolve order:** classify → retrieve → reason → decide → auto_resolve
**Standard escalate order:** classify → retrieve → reason → decide → escalate
**Fast-exit order:** classify → escalate_fast_exit (then remaining nodes dim simultaneously)
**Rejection order:** classify (then all other nodes dim simultaneously)

---

## Component 5 — RetrievalPanel: Visual Composition

**Section header:** `Retrieved Regulatory Chunks — Mimir` in section-header style, with a small secondary label `Two-pass retrieval` in `--text-secondary` 0.75rem to the right.

**Chunk card** (shadcn `Card`):
- Background: `--panel-bg`, border: `--panel-border`.

**Card header row** (shadcn `CardHeader`):
- Left: `document_id — section_id` in bold, `--text-primary`, 0.875rem. Example: `FINRA-11810 — FINRA-11810-b`.
- Right: `retrieved_via` badge (shadcn `Badge`).
  - `primary`: neutral badge — background `--panel-border`, text `--text-secondary`, label `PRIMARY`.
  - `cross_reference`: purple badge — background `--cross-ref-badge` (`#8e44ad`), text white, label `CROSS-REF`.

**Card body** (shadcn `CardContent`):
- Truncated snippet text: `--text-secondary`, 0.85rem, line-height 1.5.
- Ellipsis at approximately 300 characters.
- Below snippet: a `Show full chunk` text button in `--swagger-green`, 0.8rem, no underline by default, underline on hover. On expand, the full chunk replaces the snippet and the button label becomes `Show less`. Each card manages its own expanded state independently.

**Card entry animation:** Cards fade in with `opacity: 0 → 1` over 300ms, staggered 150ms per card.

---

## Component 6 — ResponsePanel: Visual Composition

**Section header:** `Agent Response` in section-header style, with the HTTP status code badge to the right:
- Standard path: `200 OK` badge in `--swagger-green`.
- Fast-exit: `200 OK` badge in `--swagger-green` (still a valid response, just with escalation outcome).
- Rejection: `422 Unprocessable Entity` badge in `--red`.

### Standard Path — Three Cards

**Card 1: Confidence Score**

Layout: Two rows.

Row 1 (flex, `align-items: center`, `justify-content: space-between`):
- Left: Outcome label — `AUTO-RESOLVED` in `--swagger-green` bold uppercase 1rem, or `ESCALATED` in `--amber` bold uppercase 1rem.
- Right: Confidence score value — large numeric display, 2rem, `--text-primary`, monospace. Example: `0.83`.

Row 2 (flex, `align-items: center`, gap 8px):
- `HIGH` badge (shadcn `Badge`, `--swagger-green` background, dark text) if score ≥ 0.75.
- `LOW` badge (`--red` background, white text) if score < 0.75.
- Threshold label: `threshold: 0.75` in `--text-secondary`, 0.8rem.

**Card 2: Reasoning Trace**

- Card header label: `Reasoning Trace` bold, `--text-primary`.
- shadcn `ScrollArea` with `max-height: 300px`.
- Prose content: `--text-secondary`, 0.875rem, line-height 1.6.

**Card 3: Resolution Steps**

- Card header label: `Resolution Steps` bold, `--text-primary`.
- shadcn `ScrollArea` with `max-height: 300px`.
- Prose content: `--text-secondary`, 0.875rem, line-height 1.6.

### Fast-Exit Path — One Card

Single card with:
- Row 1: `ESCALATED` label in `--amber`, bold uppercase 1rem. Right: `Mandatory escalation` in `--text-secondary` 0.85rem.
- Row 2: `Keyword detected:` label followed by the triggered keyword in `--swagger-green` monospace bold.
- Row 3: Escalation reason prose in `--text-secondary`, 0.875rem.

### Rejection Path — One Card

Single card with:
- Row 1: `422 Unprocessable Entity` badge in `--red`. Right: `Rejected at validation — agent not reached` in `--text-secondary`.
- Pydantic error list: for each error object in the detail array, render three lines — `loc:` value, `msg:` value, `type:` value — in 0.8rem monospace `--text-secondary`, separated by a thin `--panel-border` line between error objects.

---

## Page-Level Layout

Single column, `max-width: 860px`, centered, `margin: 0 auto`.

**Vertical rhythm:**

| Section | Top margin |
|---|---|
| FramingHeader | 40px from top of page |
| ScenarioSelector | 32px below FramingHeader separator |
| RequestPanel | 24px below ScenarioSelector |
| StateGraph section | 32px below RequestPanel |
| RetrievalPanel | 32px below StateGraph |
| ResponsePanel | 32px below RetrievalPanel |

**Page background:** `--swagger-bg` (`#1a1a2e`). Full viewport height.

**Section background:** StateGraph, RetrievalPanel, and ResponsePanel sections each sit in a container with `background: #22223a` (1 shade lighter than page bg) and `border-radius: 8px`, `padding: 24px`. This creates a subtle panel grouping for the output sections without adding borders.

---

## Interaction States Summary

| State | ScenarioSelector | RequestPanel | StateGraph | RetrievalPanel | ResponsePanel |
|---|---|---|---|---|---|
| Initial load | Tab 1 active | Payload shown | Hidden | Hidden | Hidden |
| Loading | Disabled (0.5 opacity) | Button disabled, "Running agent…" | Visible, loading pulse on classify | Hidden | Hidden |
| Graph animating | Disabled | Button disabled | Animating | Hidden | Hidden |
| Standard — retrieval visible | Re-enabled | Button re-enabled | Complete | Fading in | Hidden |
| Standard — response visible | Re-enabled | Button re-enabled | Complete | Visible | Fading in |
| Fast-exit complete | Re-enabled | Button re-enabled | Complete (fast-exit path) | Hidden | Fading in |
| Rejection complete | Re-enabled | Button re-enabled | Complete (rejection path) | Hidden | Fading in |
| Error | Re-enabled | Button re-enabled | Error message shown | Hidden | Hidden |
| Scenario changed | New tab active | New payload shown | Hidden | Hidden | Hidden |

---

## Decisions Locked by This Document

The following were open in the interface contract and are now locked:

| Item | Decision |
|---|---|
| StateGraph implementation | SVG |
| Node canvas size | 700×500px |
| Node dimensions | 140×40px, rx=6 |
| All 7 node center coordinates | Specified in Node Positions table above |
| Edge geometry | Cubic bezier paths, routing rules specified |
| Component library | shadcn/ui |
| Title font | IBM Plex Mono |
| `primary` badge color | `--panel-border` background, `--text-secondary` text |
| Section containers | `#22223a` background panels with 8px radius |
| JSON syntax highlight implementation | Lightweight custom tokenizer, no external library |
| Confidence score display size | 2rem monospace |
| Card entry animation | Fade in 300ms, 150ms stagger |

---

## What This Document Does Not Specify

- Exact SVG bezier control point values — these are geometry to be calculated during implementation from the node center coordinates specified above.
- CSS class naming conventions.
- Internal variable naming.
- The exact 300-character truncation implementation (this is a guideline, not a hard boundary).
