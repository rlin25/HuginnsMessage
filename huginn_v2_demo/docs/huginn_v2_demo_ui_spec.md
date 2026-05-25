# Huginn v2 Demo — UI Specification

**Status:** Implementation complete.
**Last updated:** May 2026
**Location:** `HuginnsMessage/huginn_v2_demo/` (monorepo subdirectory)
**Source of truth:** `huginn_v2_demo_design_decisions.md` and `huginn_v2_demo_interface_contract.md` — all visual decisions derive from locked decisions. If anything here conflicts with a locked decision, the locked decision governs.

---

## What This Document Is

The interface contract specifies component boundaries: inputs, outputs, state, and data shapes. This document specifies what the recruiter sees — layout, visual composition, interaction states, and the exact rendering of every element. A builder reading both documents should be able to implement the demo without making a visual judgment call.

This document does not re-specify anything already locked in the interface contract. It fills the gaps the contract explicitly deferred: SVG node geometry, component-level visual composition, and element-level rendering detail.

---

## Implementation Stack

**Component library:** No external component library was used. The UI spec originally planned shadcn/ui, but all components — tab strip, cards, badges, buttons, scroll areas — are implemented as lightweight inline React components with direct inline styles and minimal CSS classes defined in the `<style>` block.

[Updated post-implementation: The original UI spec specified shadcn/ui (`Tabs`, `Card`, `Badge`, `Button`, `ScrollArea`, `Separator`) imported from CDN. These components were not used. All visual output matches the shadcn-inspired aesthetic specified here; only the underlying implementation differs. See Decision 20 (tab strip), Decision 18 (JSON highlighter), and the implementation notes throughout this document.]

**Custom-built components (all components in the implementation):**
- StateGraph (SVG)
- ScenarioSelector (flex row tab strip with inline styles)
- RequestPanel with HighlightedJSON (custom character-by-character tokenizer)
- ChunkCard / RetrievalPanel (inline-styled divs)
- ResponsePanel (inline-styled divs)
- POST badge (Swagger-specific chrome)
- Loading pulse indicator (SVG `<circle>` with CSS `@keyframes`)

---

## Typography

| Element | Font | Weight | Size |
|---|---|---|---|
| Demo title | `"IBM Plex Mono", monospace` | 600 | 1.5rem |
| Section headers | System sans-serif | 600 | 0.875rem, uppercase, letter-spacing 0.08em |
| Body / prose | System sans-serif | 400 | 0.9rem |
| JSON / code blocks | `"Fira Code", "SF Mono", monospace` | 400 | 0.8rem |
| Node labels (SVG) | System sans-serif | 500 | 11px |
| Badges | System sans-serif | 700 | 0.7rem, uppercase |

IBM Plex Mono is loaded via Google Fonts (`wght@600`). It is applied only to the title element via the `.ibm-plex` CSS class.

---

## Component 1 — FramingHeader: Visual Composition

**Layout:** Flex row for the title line (title left, POST badge right). Framing paragraph 8px below. 1px separator line 24px below the paragraph.

**Title line composition:**
- Demo title `Huginn — Triaging Trade Exceptions` in IBM Plex Mono, 1.5rem, color `--text-primary`.
- On the same line, flush right: a green `POST` badge (`--swagger-green` background, `--swagger-green-dark` text) followed by `/exceptions` in `.code-font` `--text-secondary`, 0.875rem.
- The title and badge share a flex row with `justify-content: space-between`.

**Framing paragraph:** `--text-secondary`, 0.9rem, line-height 1.65. Sits 8px below the title line. Three sentences as deployed (see Decision 14 addendum in design_decisions.md).

**Bottom border:** A 1px `--panel-border` div (height: 1) sits 24px below the framing paragraph.

---

## Component 2 — ScenarioSelector: Visual Composition

**Implementation:** A flex row of `<button>` elements inside a wrapping `<div>`. The outer container has `border: '1px solid var(--panel-border)'`, `borderRadius: 6`, `overflow: 'hidden'`. Each button has `flex: 1`.

**Tab trigger composition (each scenario):**
- **Line 1:** Scenario label text, `--text-primary`, 0.875rem, `lineHeight: 1.4`.
- **Line 2:** Outcome hint — `--text-secondary`, 0.75rem, italic — e.g. *auto-resolved*, *escalated*, *rejected at validation*.
- Padding: `10px 12px` per tab.

**Active tab visual state:**
- Background: `--panel-bg`.
- Active indicator: `boxShadow: 'inset 2px 0 0 var(--swagger-green)'` (inset box-shadow, not border-left).
- Text on active tab: `--text-primary`, font-weight 600.
- Inactive tabs: transparent background, font-weight 400, `boxShadow: 'inset 2px 0 0 transparent'`.

[Updated post-implementation: The original spec required a `border-left: 2px solid var(--swagger-green)` active indicator and specified overriding the shadcn default underline indicator. The implementation uses an inset box-shadow instead, because the outer container uses `overflow: hidden` which clips any actual border-left. The visual result is identical — a 2px green bar on the left edge of the active tab. See Decision 20 in design_decisions.md.]

**Tab separator:** `borderRight: '1px solid var(--panel-border)'` on all tabs except the last, creating a visible separator line between adjacent tabs.

**Disabled state (during loading):**
- All tabs: `opacity: 0.5`, `cursor: 'not-allowed'`.
- Clicks are ignored (`!disabled && onSelect(s.id)` guard in click handler).

**Section header:** The label `Scenarios` appears above the tab container in section-header style (uppercase, 0.875rem, `--text-secondary`, letter-spacing 0.08em), with `marginBottom: 12`.

---

## Component 3 — RequestPanel: Visual Composition

**Outer container:** `background: var(--panel-bg)`, `border: 1px solid var(--panel-border)`, `borderRadius: 6`, `padding: 16`.

**Section header row:** Flex row, `justify-content: space-between`, `align-items: center`, `marginBottom: 12`:
- Left: Label `Request Body` in section-header style.
- Right: POST badge (same `PostBadge` component as FramingHeader).

**JSON block:**
- Background: `--swagger-bg` (one shade darker than panel).
- Border: 1px solid `--panel-border`, border-radius 4px.
- Padding: 12px.
- Font: Fira Code / SF Mono, 0.8rem, line-height 1.5.
- `userSelect: 'none'`, `cursor: 'default'` — not editable, no text selection.
- `whiteSpace: 'pre'`, `overflowX: 'auto'`.
- Syntax highlighting: property keys in `--swagger-green`, string values in `--text-secondary`, punctuation (`{}[],:.`) in `--text-primary`, numbers/booleans/null in `--text-secondary`. Implemented via a custom character-by-character tokenizer (see Decision 18 in design_decisions.md).

**Execute button:**
- At rest: `background: var(--swagger-green)`, `color: var(--swagger-green-dark)`, `fontWeight: 700`, `fontSize: 0.875rem`, `border: none`, `borderRadius: 4`, `padding: 8px 20px`.
- `isLoading` state: `background: var(--panel-border)`, `color: var(--text-secondary)`, `cursor: not-allowed`, `opacity: 0.6`.
- Label: `Execute` at rest. `Running agent…` when `isLoading`.
- Positioned flush right below the JSON block with `marginTop: 12`.

---

## Component 4 — StateGraph: SVG Specification

### Canvas

SVG element: `width="700" height="500"`, `viewBox="0 0 700 500"`.
Background: transparent (sits on `#22223a` section container background).
Section header `Agent — LangGraph State Machine` renders above the SVG in section-header style, with `Running agent…` in `--text-secondary` 0.875rem shown to the right only when `status === 'loading'`.

### Node Dimensions

All nodes: `width=140`, `height=40`, `rx=6` (rounded rectangle).
Node rect top-left: `x = cx - 70`, `y = cy - 20`.
Node label: centered at `(cx, cy + 4)`, `textAnchor="middle"`, `fontSize="11"`, `fontFamily="system-ui, sans-serif"`, `fontWeight="500"`.

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

### Edges

Edges are `<path>` elements with `marker-end` arrowhead. `strokeWidth: 1.5`. CSS class `edge-path` with `transition: stroke 400ms ease`.

**Arrowhead markers** (in SVG `<defs>`):
- `arrow-neutral`: `fill: var(--panel-border)`
- `arrow-active`: `fill: var(--swagger-green)`

Each edge uses `url(#arrow-active)` or `url(#arrow-neutral)` based on whether the edge is active (determined by `PATH_ACTIVE_EDGES` and `revealedNodes`).

**Marker geometry:** `markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"`, path `M0,0 L0,6 L8,3 z`.

[Updated post-implementation: The original spec defined a single arrowhead marker with `refX="6"` and `fill="currentColor"`. The implementation uses two separate markers (`arrow-neutral` and `arrow-active`) with `refX="7"` and explicit fill colors. The visual result is equivalent.]

**Edge paths** (cubic bezier formulas as implemented, where `f` = from node, `t` = to node):

| Edge | Path formula |
|---|---|
| `classify → retrieve` | `M (f.cx-30, f.cy+20) C (f.cx-30, f.cy+65) (t.cx, t.cy-65) (t.cx, t.cy-20)` |
| `classify → escalate_fast_exit` | `M (f.cx+30, f.cy+20) C (f.cx+30, f.cy+65) (t.cx, t.cy-65) (t.cx, t.cy-20)` |
| `retrieve → reason` | `M (f.cx, f.cy+20) L (t.cx, t.cy-20)` |
| `reason → decide` | `M (f.cx, f.cy+20) L (t.cx, t.cy-20)` |
| `decide → auto_resolve` | `M (f.cx-40, f.cy+20) C (f.cx-40, f.cy+55) (t.cx, t.cy-55) (t.cx, t.cy-20)` |
| `decide → escalate` | `M (f.cx+20, f.cy+20) C (f.cx+20, f.cy+55) (t.cx, t.cy-55) (t.cx, t.cy-20)` |

[Updated post-implementation: The original spec stated "exact control points are implementation detail." The implemented formulas are recorded above. `retrieve → reason` and `reason → decide` are straight lines (`L`), not curves. See Decision 19 in design_decisions.md.]

**Edge routing rules (unchanged from spec):**
- `classify → retrieve`: exits bottom-left of classify, enters top of retrieve, leftward curve.
- `classify → escalate_fast_exit`: exits bottom-right of classify, enters top of escalate_fast_exit, rightward curve.
- `retrieve → reason`, `reason → decide`: straight vertical lines.
- `decide → auto_resolve`: exits bottom-left of decide, enters top of auto_resolve, diagonal left.
- `decide → escalate`: exits bottom-right of decide, enters top of escalate, slight right curve.

### Node Visual States

Three states per node. CSS classes `node-rect` and `node-text` each have `transition` properties.

`node-rect` transitions: `fill 400ms ease, stroke 400ms ease, stroke-width 400ms ease, opacity 400ms ease`.
`node-text` transitions: `fill 400ms ease, opacity 400ms ease`.

**Neutral (pre-run / loading):**
- `fill`: `var(--panel-bg)`
- `stroke`: `var(--panel-border)`
- `stroke-width`: 1.5
- Label color: `var(--text-secondary)`
- Opacity: 1

**Active:**
- `fill`: `var(--node-active-bg)` (`#1a4a6b`)
- `stroke`: `var(--swagger-green)`
- `stroke-width`: 2
- Label color: `var(--swagger-green)`
- Opacity: 1

**Dimmed:**
- `fill`: `var(--panel-bg)`
- `stroke`: `var(--panel-border)`
- `stroke-width`: 1.5 (unchanged from neutral in implementation)
- Label color: `var(--text-secondary)`
- Opacity: 0.3

[Updated post-implementation: The original spec specified `stroke-width: 1` for dimmed nodes. The implementation leaves dimmed nodes at the default `stroke-width: 1.5`. The visual difference at 0.3 opacity is negligible.]

Dimmed nodes on fast-exit and rejection paths additionally render a `skipped` text element: `x={node.cx}`, `y={node.cy + 34}`, `textAnchor="middle"`, `fontSize="9"`, `fill="var(--text-secondary)"`, `opacity={0.3}`.

[Updated post-implementation: The original spec stated `skipped` renders "14px below the node rect." The implementation positions the text at `cy + 34`, which is 14px below the bottom edge of the node rect (`cy + 20`). This matches the spec intention but the coordinate is `cy + 34`, not an offset from rect bottom.]

### Loading State Visual

When `status === "loading"`: all nodes render in neutral state. A pulsing `<circle>` is rendered with `className="pulse-ring"`, `cx={350}`, `cy={60}`, `r={36}`, `stroke="var(--swagger-green)"`, `strokeWidth="1.5"`, `fill="none"`.

CSS animation `pulse-ring`: `@keyframes pulse-ring { 0%, 100% { opacity: 0.6; } 50% { opacity: 0; } }` over `1.2s ease-in-out infinite`.

### Animation Sequence

Nodes activate in path order, one per `NODE_STAGGER_MS` (300ms). After last active node: all non-active nodes dim simultaneously by setting `revealedNodes` to the full set of all node IDs. See Decision 22 in design_decisions.md for `revealedNodes` semantics.

**Standard auto_resolve order:** classify → retrieve → reason → decide → auto_resolve (5 nodes, 1.2s total stagger)
**Standard escalate order:** classify → retrieve → reason → decide → escalate (5 nodes, 1.2s total stagger)
**Fast-exit order:** classify → escalate_fast_exit (2 nodes, 300ms total stagger)
**Rejection order:** classify (1 node, 0ms stagger)

Edges activate when their destination node is added to `revealedNodes`.

---

## Component 5 — RetrievalPanel: Visual Composition

**Section container:** `background: #22223a`, `borderRadius: 8`, `padding: 24`. Mounted with `marginTop: 32` from the StateGraph section.

**Section header row:** Flex row, `justify-content: space-between`, `align-items: center`, `marginBottom: 16`:
- Left: `Retrieved Regulatory Chunks — Mimir` in section-header style.
- Right: `Two-pass retrieval` in `--text-secondary`, 0.75rem.

**Chunk cards container:** `display: flex, flexDirection: column, gap: 12`.

**Chunk card:**
- `background: var(--panel-bg)`, `border: 1px solid var(--panel-border)`, `borderRadius: 6`, `padding: 16`.
- CSS class `fade-in-card` with `animationDelay: idx * 150ms`.

**Card header row:** Flex, `justify-content: space-between`, `align-items: center`, `marginBottom: 10`:
- Left: `document_id — section_id` bold, `--text-primary`, 0.875rem.
- Right: `retrieved_via` badge.
  - `primary`: `background: var(--panel-border)`, `color: var(--text-secondary)`, label `PRIMARY`.
  - `cross_reference`: `background: var(--cross-ref-badge)` (`#8e44ad`), `color: white`, label `CROSS-REF`.
  - Badge style: `fontSize: 0.7rem`, `fontWeight: 700`, `textTransform: uppercase`, `padding: 2px 8px`, `borderRadius: 4`, `letterSpacing: 0.05em`.

**Card body:**
- Snippet text: `--text-secondary`, 0.85rem, `lineHeight: 1.5`, `marginBottom: 8`.
- Truncation: `chunk.text.length > 300 ? chunk.text.slice(0, 300) + '…' : chunk.text`.
- Expand toggle: `background: none`, `border: none`, `color: var(--swagger-green)`, `fontSize: 0.8rem`, `cursor: pointer`, `padding: 0`. Underline on hover via `onMouseEnter`/`onMouseLeave`. Label `Show full chunk` / `Show less`. Per-card independent state via `useState(false)`.

**Card entry animation:** CSS `@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }` over 300ms, staggered 150ms per card.

---

## Component 6 — ResponsePanel: Visual Composition

**Section container:** `background: #22223a`, `borderRadius: 8`, `padding: 24`. Mounted with `marginTop: 32`.

**Section header row:** Flex, `justify-content: space-between`, `align-items: center`, `marginBottom: 16`:
- Left: `Agent Response` in section-header style.
- Right: HTTP status badge.
  - Standard path: `200 OK` in `--swagger-green` / `--swagger-green-dark`.
  - Fast-exit: `200 OK` in `--swagger-green` / `--swagger-green-dark`.
  - Rejection: `422 Unprocessable Entity` in `--red` / white.

### Standard Path — Three Cards

Cards container: `display: flex, flexDirection: column, gap: 12`.

**Card 1: Confidence Score**

Container: `background: var(--panel-bg)`, `border: 1px solid var(--panel-border)`, `borderRadius: 6`, `padding: 16`.

Row 1 (flex, `justify-content: space-between`, `align-items: center`, `marginBottom: 8`):
- Left: Outcome label — `AUTO-RESOLVED` in `var(--swagger-green)` bold uppercase 1rem, or `ESCALATED` in `var(--amber)` bold uppercase 1rem. Driven by `response.outcome`.
- Right: Confidence score — `response.confidence_score.toFixed(2)` (or raw value if not a number), 2rem, `.code-font`, `--text-primary`.

Row 2 (flex, `align-items: center`, `gap: 8`):
- Score badge: `HIGH` (`--swagger-green` bg, `--swagger-green-dark` text) if score ≥ 0.75; `LOW` (`--red` bg, white text) if score < 0.75. `fontSize: 0.7rem`, `fontWeight: 700`, `padding: 2px 8px`, `borderRadius: 4`.
- Threshold label: `threshold: 0.75` in `--text-secondary`, 0.8rem.

**Card 2: Reasoning Trace**

Container: `background: var(--panel-bg)`, `border: 1px solid var(--panel-border)`, `borderRadius: 6`, `padding: 16`.
Header: `Reasoning Trace` bold, `--text-primary`, 0.875rem, `marginBottom: 10`.
Content: `className="scroll-area"` div with `color: var(--text-secondary)`, `fontSize: 0.875rem`, `lineHeight: 1.6`.

**Card 3: Resolution Steps**

Container: same as Reasoning Trace card.
Header: `Resolution Steps` bold.
Content: same scroll-area style.

**Scroll area implementation:** CSS class `.scroll-area` with `max-height: 300px`, `overflow-y: auto`. Custom scrollbar: `width: 4px`, track `--panel-bg`, thumb `--panel-border`, `borderRadius: 2px`.

### Fast-Exit Path — One Card

Container: `background: var(--panel-bg)`, `border: 1px solid var(--panel-border)`, `borderRadius: 6`, `padding: 16`.

Row 1 (flex, `justify-content: space-between`, `align-items: center`, `marginBottom: 8`):
- Left: `ESCALATED` in `--amber`, bold uppercase 1rem.
- Right: `Mandatory escalation — no model call` in `--text-secondary`, 0.85rem.

Row 2: `Keyword detected:` in `--text-secondary` + triggered keyword in `--swagger-green` bold, `.code-font`, 0.875rem, `marginBottom: 8`.

Row 3: `escalation_reason` prose in `--text-secondary`, 0.875rem, `lineHeight: 1.6`.

### Rejection Path — One Card

Container: `background: var(--panel-bg)`, `border: 1px solid var(--panel-border)`, `borderRadius: 6`, `padding: 16`.

Row 1 (flex, `justify-content: space-between`, `align-items: center`, `marginBottom: 12`):
- Left: `422 Unprocessable Entity` badge in `--red` / white.
- Right: `Rejected at validation — agent not reached` in `--text-secondary`, 0.85rem.

Error detail list: for each error in `response.error.detail`, render three lines (`loc`, `msg`, `type`) in `--text-secondary`, 0.8rem, `.code-font`. Error objects separated by `borderBottom: '1px solid var(--panel-border)'` and `paddingBottom: 8px` between items (last item has no border).

---

## Page-Level Layout

Single column, `maxWidth: 860`, centered, `margin: 0 auto`, `padding: 40px 24px 80px`.

**Vertical rhythm:**

| Section | Top margin |
|---|---|
| FramingHeader | 40px from top (via container padding) |
| ScenarioSelector | 32px below FramingHeader |
| RequestPanel | 24px below ScenarioSelector |
| StateGraph section | 32px below RequestPanel |
| RetrievalPanel | 32px below StateGraph |
| ResponsePanel | 32px below RetrievalPanel |

**Page background:** `--swagger-bg` (`#1a1a2e`). Full viewport via `min-height: 100vh` on `body`.

**Section background:** StateGraph, RetrievalPanel, and ResponsePanel each sit in a `<div>` with `background: #22223a`, `borderRadius: 8`, `padding: 24`. FramingHeader, ScenarioSelector, and RequestPanel have no section container.

---

## Interaction States Summary

| State | ScenarioSelector | RequestPanel | StateGraph | RetrievalPanel | ResponsePanel |
|---|---|---|---|---|---|
| Initial load | Tab 1 active | Payload shown | Hidden | Hidden | Hidden |
| Loading (API in flight) | Disabled (0.5 opacity) | Button disabled, "Running agent…" | Visible, loading pulse on classify | Hidden | Hidden |
| Graph animating | Disabled | Button disabled | Animating | Hidden | Hidden |
| Standard — retrieval visible | Re-enabled | Button re-enabled | Complete | Fading in | Hidden |
| Standard — response visible | Re-enabled | Button re-enabled | Complete | Visible | Fading in |
| Fast-exit complete | Re-enabled | Button re-enabled | Complete (fast-exit path) | Hidden | Fading in |
| Rejection complete | Re-enabled | Button re-enabled | Complete (rejection path) | Hidden | Fading in |
| Error | Re-enabled | Button re-enabled | Error message shown | Hidden | Hidden |
| Scenario changed | New tab active | New payload shown | Hidden | Hidden | Hidden |

[Updated post-implementation: The ScenarioSelector and RequestPanel button remain disabled ("Re-enabled" column shows "Disabled") during the "Graph animating" state. `isLoading` is set to `false` only after animation completes. This is consistent with this table but differs from the interface contract's original Step 3b which set `isLoading: false` at API success. See Decision 21 in design_decisions.md.]

---

## Decisions Locked by This Document

The following were open in the interface contract and are now locked:

| Item | Decision |
|---|---|
| StateGraph implementation | SVG |
| Node canvas size | 700×500px |
| Node dimensions | 140×40px, rx=6 |
| All 7 node center coordinates | Specified in Node Positions table above |
| Edge geometry | Cubic bezier paths — formulas recorded in Edge paths table above |
| Component library | None — all inline implementations |
| Title font | IBM Plex Mono |
| `primary` badge color | `--panel-border` background, `--text-secondary` text |
| Section containers | `#22223a` background panels with 8px radius |
| JSON syntax highlight implementation | Lightweight custom character-by-character tokenizer |
| Confidence score display size | 2rem monospace |
| Card entry animation | Fade in 300ms, 150ms stagger |
| Active tab indicator | `boxShadow: inset 2px 0 0 var(--swagger-green)` (not border-left) |
| Tab separator | `borderRight: 1px solid var(--panel-border)` between tabs |
| Scroll area implementation | CSS `.scroll-area` class, max-height 300px, custom webkit scrollbar |
| Card gap within sections | 12px flex gap |

---

## What This Document Does Not Specify

- CSS class naming conventions.
- Internal variable naming.
- The exact 300-character truncation implementation (implemented as `text.length > 300 ? text.slice(0, 300) + '…' : text`).
