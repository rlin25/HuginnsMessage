# Huginn v2 Demo — Locked Design Decisions

**Status:** Implementation complete. Phase 7 feedback loop complete.
**Last updated:** May 2026
**Location:** `HuginnsMessage/huginn_v2_demo/` (monorepo subdirectory — see Decision 16 addendum)
**Relationship:** Standalone static web application. Referenced from Huginn v2 README via a single link. Does not live inside the `huginn_v2/` repository. The demo lives as a subdirectory of the `HuginnsMessage/` monorepo.

---

## Project Summary

The Huginn v2 demo is an interactive single-page web application that allows recruiters to experience the Huginn v2 trade exception triage system without cloning the repository or running the API locally. It presents a Swagger-inspired UI with pre-built scenarios covering all three of Huginn's execution paths. The recruiter selects a named scenario from a simultaneously visible tab strip, clicks Execute, and watches a sequential animated visualization of the agent's LangGraph state machine — nodes lighting up as each stage completes — rendered in real time via a live Claude API call. The demo is built as a self-contained HTML file, deployed to GitHub Pages, and implemented via Claude Code. The demo is a portfolio artifact, not a system component. It demonstrates the system's behavior and architecture to an external audience.

---

## Decision 1 — API Key

**Decision:** The Claude API key is embedded in the source file. The recruiter interacts with the demo without any setup step.

**Reasoning:** The demo's audience is recruiters, not adversaries. The exposure surface is a GitHub Pages link shared via a portfolio README — a low-traffic, low-risk surface. Friction at the start of the demo — requiring a recruiter to obtain and paste their own API key — causes meaningful drop-off, particularly among non-technical recruiters. A demo that does not run is worse than a demo with a key in the source. The key can be rotated after the portfolio push if needed. Using a separate key scoped to this demo (not the primary development key) limits blast radius further.

**Rejected option:** Recruiter pastes their own key. Rejected because it requires the recruiter to have an Anthropic account, locate their API key, and complete a setup step before seeing any output. A meaningful percentage of non-technical recruiters will not complete this step.

**Rejected option:** Server-side proxy to hide the key. Rejected because it introduces backend infrastructure for a portfolio demo with no meaningful security requirement — the audience is recruiters, not adversaries, and the complexity cost is not justified.

**Implementation note [May 2026]:** This decision was reversed during implementation. A Cloudflare Worker proxy (`worker/index.js`) was built and deployed to inject the API key server-side. The key does not appear anywhere in `index.html`. The `WORKER_URL` constant in `index.html` points to the deployed Worker at `https://huginn-demo.richard-lin2025.workers.dev`. The security reasoning in the original decision ("the complexity cost is not justified") was overridden by a practical consideration: GitHub Pages serves the HTML publicly, and an embedded key in a public repository is automatically flagged by secret-scanning tools and revoked by Anthropic. The Worker proxy resolves this without meaningful additional complexity. The key lives in the Worker's environment variable binding `ANTHROPIC_API_KEY`, not in any committed file.

---

## Decision 2 — Scenario Selection

**Decision:** Five named scenarios are available via a simultaneously visible tab strip or radio group — all options visible without clicking to open. Labels include an expected outcome suffix to prime recruiter attention on the pipeline rather than the outcome. All fields are auto-populated on selection. The payload is read-only — the recruiter cannot modify it.

The five scenarios are:

| Label | Path | Sub-type | Expected outcome |
|---|---|---|---|
| Price mismatch — AAPL, 500 shares | Standard | `price_mismatch` | auto-resolved |
| Quantity mismatch — TSLA, 200 shares | Standard | `quantity_mismatch` | escalated |
| Wrong settlement date — MSFT bond | Standard | `wrong_settlement_date` | auto-resolved |
| Buy-in notice received | Fast-exit | n/a — keyword detected | escalated |
| Invalid exception type | Rejection | n/a — validation error | rejected at validation |

**Reasoning:** Named scenarios serve the demo goal better than free-form input. The pre-filled payload makes the exception schema visible to technical recruiters without requiring them to construct valid input. Read-only payloads guarantee consistent, representative outputs on every run. A simultaneously visible tab strip ensures the fast-exit and rejection scenarios — which carry the most architectural signal — are not buried in a dropdown. Expected outcome suffixes focus recruiter attention on how the system reached the outcome, not on what the outcome is.

**Rejected option:** Dropdown selector. Rejected because it buries all options behind a click and makes the fast-exit and rejection scenarios easy to overlook.

**Rejected option:** Editable payload. Rejected because a poorly constructed description may produce a low-confidence result or a confusing reasoning trace that cannot be anticipated or explained.

**Rejected option:** Single standard-path scenario only. Rejected because showing one sub-type understates the RAG layer — different exceptions retrieve different regulatory documents, which is a meaningful demonstration of the retrieval architecture.

---

## Decision 3 — Paths Represented

**Decision:** All three of Huginn's execution paths are represented in the scenario selector: standard path (three sub-types), mandatory escalation fast-exit, and invalid type rejection (422).

**Reasoning:** The three-path state machine is one of the most interview-worthy architectural decisions in the project. Each path exists for an explicit reason — fast exits before expensive operations, keyword detection before Mimir is called, validation before the agent runs. A recruiter who sees all three paths understands the design philosophy without requiring an explanation. The 422 is framed as intentional validation behavior ("Invalid exception type — rejected at validation"), not as a failure.

**Rejected option:** Standard path only. Rejected because it shows the interesting output but obscures the architecture that produces it.

**Rejected option:** Standard path and fast-exit only, omitting the 422. Rejected because the validation boundary is itself a design decision worth demonstrating — the agent never touches invalid input.

---

## Decision 4 — State Diagram Structure and Animation

**Decision:** The state diagram is an accurate representation of the LangGraph node graph, not a simplified three-stage abstraction. All nodes are rendered: `classify`, `retrieve`, `reason`, `decide`, `escalate`, `auto_resolve`, and `escalate_fast_exit`, with correct edges between them matching `agent/graph.py`. The diagram animates sequentially as each stage of the reveal progresses — nodes light up in order as they activate. On fast-exit, skipped nodes animate to a grayed-out state rather than appearing pre-grayed. Active path highlights; inactive path grays out.

**Reasoning:** The demo's audience includes technical recruiters who will read the codebase afterward. A diagram that misrepresents the graph is a credibility liability — a recruiter who checks `agent/graph.py` and finds a discrepancy loses trust in the demo and by extension the project. Accuracy costs nothing extra given that the node graph is well-defined. Animation makes the state machine feel alive — the recruiter watches the agent move through nodes rather than seeing a finished diagram.

**Rejected option:** Simplified three-stage representation (retrieval → reasoning → decision). Rejected because it misrepresents the architecture to technical recruiters and loses the fast-exit node structure that makes the three-path design visible.

**Rejected option:** Static diagram appearing after the full response is received. Rejected because it reduces the diagram to an explanation rather than a demonstration — the recruiter sees a result rather than watching a process.

---

## Decision 5 — Fast-Exit and Rejection Visualization

**Decision:** The full node graph is always rendered. On the fast-exit path, the `retrieve`, `reason`, and `decide` nodes are visibly dimmed and labeled "skipped — keyword detected" as the animation progresses. On the invalid type rejection path, all nodes after `classify` are dimmed and the response panel shows the 422 error body. The `escalate_fast_exit` node highlights on the fast-exit path.

**Reasoning:** A grayed-out node graph is more informative than a collapsed one. The recruiter sees the full architecture on every run — the nodes that ran, and the nodes that did not. The fast-exit path becomes more explanatory than a standard path run: the recruiter immediately understands that the system deliberately bypassed expensive operations. The absence of retrieval and reasoning is the point, and the animation makes it visible.

**Rejected option:** Nodes collapse or disappear on fast-exit. Rejected because the absence of nodes is less legible than nodes that are visibly present but skipped.

---

## Decision 6 — Reveal Trigger

**Decision:** The sequential reveal is automatic. The recruiter clicks Execute, sees a loading state while the API call completes, then the stages animate in one by one — state diagram first, retrieval cards second, response cards third — with approximately one to two seconds between stages. No step-through interaction required.

**Reasoning:** The demo's job is to show the system reasoning, not to require the recruiter to advance through it. Automatic reveal with readable timing keeps momentum without rushing. A recruiter who wants to linger can read during the delay between stages.

**Rejected option:** Step-through reveal requiring the recruiter to click Next at each stage. Rejected because it adds friction and requires multiple clicks to reach the output.

---

## Decision 7 — Animation Timing and API Call Relationship

**Decision:** The animation waits for the full API response before beginning. The recruiter clicks Execute and sees a loading state ("Running agent…") until the response is received. The sequential stage reveal then begins with the complete data in hand. The animation is purely presentational — it reveals data that already exists.

**Reasoning:** Animating optimistically while the API call is in flight introduces synchronization complexity — the animation must stall if the API is slow, which produces a broken visual experience. A loading state followed by a clean sequential reveal is simpler to build and more reliable.

**Rejected option:** Optimistic animation while the API call is in flight. Rejected because it requires the animation to stall on slow responses and introduces a synchronization variable that cannot be controlled.

---

## Decision 8 — Load State

**Decision:** The demo opens with the first scenario pre-selected and the payload pre-filled. Sections below the request panel are hidden. The recruiter lands in a ready state — one click to see the system run.

**Reasoning:** A recruiter who opens the link and sees something ready to run is more likely to engage than one who sees an empty panel. Hiding lower sections on load keeps the initial view clean and prevents empty panels from reading as broken or incomplete.

**Rejected option:** Empty state on load with all sections visible.

---

## Decision 9 — API Simulation Fidelity

**Decision:** The Claude API call simulates the full Huginn v2 reasoning pipeline. The system prompt instructs the model to produce output matching the structure of what the real Huginn agent would produce — retrieved regulatory chunks with document and section IDs, a four-factor confidence score, a regulatory reasoning trace, and resolution steps. The model is not constrained to use the exact chunks the real Chroma index would return, but the document IDs and section IDs it references must be drawn from the real Huginn v2 knowledge base (SEC Rules 15c6-1 and 15c6-2, FINRA Rules 11100, 11710, 11810, and 11820).

**Reasoning:** The demo's signal is behavioral and architectural, not a ground-truth replay. A recruiter cannot verify whether the retrieved chunks are exactly what the real Mimir would return. What they can verify — if they inspect the codebase — is that the document IDs match the real knowledge base. Constraining document IDs preserves credibility with technical recruiters while keeping the simulation tractable.

**Rejected option:** Fully hardcoded responses per scenario. Rejected because it removes the live API call, which is a demonstrable signal that the system is actively running reasoning, not replaying a recording.

---

## Decision 10 — Re-Run Behavior

**Decision:** When the recruiter selects a new scenario, all output sections clear immediately and collapse back to hidden. The new scenario's payload populates the request panel. The recruiter clicks Execute to run the new scenario.

**Reasoning:** A blank output area during loading is less confusing than a mismatched state where the previous scenario's output is visible while a new scenario's input is shown. Collapsing sections on selection resets the page to its pre-run state, which is coherent and expected.

**Rejected option:** Previous output persists until new result arrives, then replaces. Rejected because the transient mismatch between old output and new input reads as inconsistent.

---

## Decision 11 — Error Handling

**Decision:** If the API call fails, the state diagram section appears with an error state and a visible message: "The API call failed — please try again." The recruiter can retry by clicking Execute again. No silent fallback to pre-baked output.

**Reasoning:** The demo claims to be live. Silently serving canned output on failure is inconsistent with that claim. A clean, recoverable error state is more defensible. The failure case is rare and a retry resolves most cases.

**Rejected option:** Silent fallback to hardcoded representative output on API failure. Rejected because it misrepresents the demo as live when it is not.

---

## Decision 12 — Retrieval Stage Display

**Decision:** Retrieved chunks are displayed as cards, one per chunk. Each card shows `document_id` and `section_id` as a header, `retrieved_via` as a badge (`primary` or `cross_reference`), and a truncated snippet of the chunk text — approximately two to three sentences — as the card body. An expand control reveals the full chunk text. On fast-exit and rejection paths, this section does not appear.

**Reasoning:** Cards accommodate both chunk metadata and snippet text more naturally than a table with subordinate rows. The truncated snippet establishes that the right documents were retrieved without requiring the recruiter to read regulatory text. The `retrieved_via` badge surfaces the two-pass retrieval architecture — primary versus cross-reference — which is one of the most technically substantive signals the demo can show. The expand control satisfies technical recruiters who want the full chunk without imposing it on everyone.

**Rejected option:** Table with snippet below each row. Rejected because cards are more visually consistent with the response panel layout and give snippet text room to breathe.

**Rejected option:** Full chunk text always visible. Rejected because it overwhelms the visualization and redirects attention from the architecture to the regulatory content.

**Rejected option:** Metadata only, no snippet. Rejected because document and section IDs alone do not establish that the retrieved content is relevant — the snippet makes the retrieval meaningful.

---

## Decision 13 — Response Panel Display

**Decision:** The response panel renders three labeled cards: Confidence Score, Reasoning Trace, and Resolution Steps.

- **Confidence Score card:** Numeric score (e.g. `0.83`) plus a color-coded badge (`HIGH` in green above threshold, `LOW` in red below threshold) plus an explicit threshold label ("threshold: 0.75"). The outcome — `auto_resolve` or `escalate` — is displayed as a prominent label on the card.
- **Reasoning Trace card:** Full prose reasoning trace, scrollable.
- **Resolution Steps card:** Full prose resolution steps.

On fast-exit and rejection paths, the Confidence Score card shows the escalation reason. The Reasoning Trace and Resolution Steps cards do not appear.

**Reasoning:** Three separate cards make the response readable to non-technical recruiters without hiding anything from technical ones. The confidence score deserves visual treatment — a numeric value alone undersells the threshold logic that governs the outcome. Naming the threshold explicitly ("threshold: 0.75") tells a complete story: this score, this threshold, this outcome. The Swagger aesthetic is preserved in the request panel; the response panel is more expressive.

**Rejected option:** Single Swagger-style response panel with field names as labels. Rejected because it treats the confidence score as a plain value rather than a decision point, losing the threshold logic that makes the score meaningful.

---

## Decision 14 — Framing Copy

**Decision:** The demo opens with a short paragraph above the interface. It states what Huginn does, that it was built design-first with structured human-AI collaboration, and what the recruiter is about to see — including an explicit statement that the responses are generated live by Claude simulating Huginn's reasoning pipeline. Four sentences maximum. The methodology signal is retained but compressed. The title is "Huginn — Triaging Trade Exceptions."

The simulation disclosure must name three things: (1) that the responses are generated live by a Claude API call, not by the running Huginn backend; (2) that the architecture, execution paths, and regulatory document references are accurate to the real system; and (3) that the specific retrieved chunks and reasoning traces are illustrative. This framing is not a disclaimer — it is a signal that the candidate understands exactly what the demo is and is not doing.

**Reasoning:** The demo is a standalone artifact — a recruiter may arrive via the README link without having read the full documentation. The methodology framing is the differentiating argument that separates this from a generic RAG demo. The simulation disclosure is necessary for full honesty and interview defensibility: the real Huginn backend cannot be hosted cost-effectively for a portfolio (a persistent AWS deployment was used during development and cleared due to cost — see Decision 16), and the simulation preserves every signal a recruiter can meaningfully evaluate. A technical recruiter who runs the real system and compares outputs should already know what to expect. Burying this distinction is worse than stating it clearly — the disclosure converts a potential credibility gap into a demonstration of engineering judgment.

**Rejected option:** Two sentences maximum, methodology and simulation disclosure omitted. Rejected because it removes the signal that distinguishes this project from a generic agentic demo and leaves the simulation nature implicit rather than stated.

**Rejected option:** Prominent disclaimer framing ("Note: this demo does not run the real backend"). Rejected because disclaimer language frames the simulation as a limitation rather than a deliberate design choice. The framing copy states it as fact, not apology.

**Implementation note [May 2026]:** The sentence referencing a previous AWS deployment — `"A previous version was deployed on AWS; this demo uses a live Claude API call to simulate Huginn's reasoning pipeline..."` — was removed from the final framing copy. The deployed framing paragraph reads: `"Huginn is a LangGraph-based AI agent that classifies financial trade exceptions and decides whether to auto-resolve them or escalate to a human reviewer — built design-first using a structured human-AI collaboration methodology. This demo uses a live Claude API call to simulate Huginn's reasoning pipeline, with architecture, execution paths, and regulatory document references accurate to the real system. Select a scenario below and click Execute to watch the agent work."` The AWS reference was judged to add backstory clutter rather than signal. The simulation disclosure and methodology signal are preserved.

---

## Decision 15 — Swagger Fidelity

**Decision:** The demo uses a Swagger-inspired visual aesthetic — the green POST badge, sans-serif type, endpoint label (`POST /exceptions`), request body panel, HTTP status code in the response — but the interaction layer is custom-built. The recruiter does not interact with actual Swagger UI.

**Reasoning:** Full Swagger fidelity cannot support the sequential reveal animation, the node graph visualization, or the card-based response panel. The aesthetic signal — "this is what the running API looks like" — is achievable with the visual language alone. Non-technical recruiters will not know the difference. Technical recruiters will recognize the Swagger language and find it credible.

**Rejected option:** Full Swagger fidelity, actual Swagger UI rendered in the page. Rejected because it cannot support the demo's primary visualization.

---

## Decision 16 — Deployment

**Decision:** The demo is a self-contained HTML file deployed to GitHub Pages under its own repository (`HuginnsMessage/huginn_v2_demo`). It is referenced from the Huginn v2 README with a single line. It does not live inside the `huginn_v2/` repository. The demo repository also contains the design documents (`design_decisions.md`, `interface_contract.md`, `ui_spec.md`).

**Reasoning:** The Huginn v2 repo's signal is the backend architecture. A separate repository keeps the demo and its design documents together without conflating the portfolio presentation layer with the system. GitHub Pages provides free static hosting with no infrastructure to manage, a stable public URL, and zero friction for a recruiter opening the link. The design documents in the same repository make the methodology visible to technical recruiters who inspect the repo directly.

A prior version of Huginn was deployed on AWS with a production-grade hosted backend. That experience — provisioning infrastructure, managing costs, operating the system end to end — informed both the v2 architecture decisions and the decision not to host v2 as a persistent service for portfolio purposes. A persistent server for a portfolio project introduces cold-start latency on free tiers and ongoing cost on paid tiers, both of which produce a worse recruiter experience than a simulation. The AWS deployment experience is surfaced in the v2 README as a portfolio signal in its own right.

**Rejected option:** Demo lives in a `demo/` subdirectory of `huginn_v2/`. Rejected because it embeds a portfolio presentation layer inside a system repository, weakening both signals.

**Rejected option:** Claude artifact shared via claude.ai link. Rejected because Claude artifacts run in a sandboxed environment that blocks outbound HTTP requests, making the live Claude API call impossible.

**Rejected option:** Hosted Huginn v2 backend on a persistent server. Rejected because free-tier hosting introduces cold-start latency that degrades recruiter experience, and paid hosting is disproportionate for a portfolio project. The simulation approach preserves every signal a recruiter can meaningfully evaluate.

**Implementation note [May 2026]:** The demo was not deployed as a standalone repository. It lives as a subdirectory (`huginn_v2_demo/`) inside the existing `HuginnsMessage/` monorepo alongside `huginn_v1/` and `huginn_v2/`. GitHub Pages is configured at the monorepo level via a GitHub Actions workflow (`.github/workflows/deploy-demo.yml`) that deploys the `huginn_v2_demo/` subdirectory on pushes to `master` that touch `huginn_v2_demo/**`. The live URL is `https://rlin25.github.io/HuginnsMessage/`, not `https://huginnsmessage.github.io/huginn_v2_demo/` as originally planned. The design documents were placed in a `docs/` subdirectory (`huginn_v2_demo/docs/`) rather than at the repo root as shown in the masterplan structure diagram.

---

## Decision 17 — Implementation Environment

**Decision:** The demo is implemented via Claude Code from the locked design documents. The same design-first methodology used for Huginn v2 applies: masterplan with atomic subplans, strict build sequence with visual gates, Claude Code reads the interface contract and design decisions before implementing anything. The output is a single self-contained HTML file.

**Reasoning:** Consistent with the project's methodology signal. Using Claude Code on a locked spec demonstrates that the design artifacts are complete and implementation-ready, not aspirational. A single HTML file with no build step is the simplest possible delivery format for a self-hosted static demo — no Node.js, no bundler, no deployment pipeline.

**Rejected option:** Manual implementation without Claude Code. Rejected because it bypasses the methodology signal the project is designed to demonstrate.

---

## Decision 18 — JSON Syntax Highlighter Implementation

**Decision:** The JSON syntax highlighter is a lightweight custom character-by-character tokenizer written directly in the `index.html` script block. No external library is used.

**Reasoning:** The UI spec locked the requirement for syntax highlighting of property keys and values but deferred the implementation approach. A full tokenizer library (e.g. Prism.js) is unnecessary for a single static JSON block with a predictable structure. The custom tokenizer is approximately 40 lines and handles the three cases required: property keys (colored `--swagger-green`), string values (colored `--text-secondary`), and structural punctuation (`{}[],:.`) colored `--text-primary`. Numbers, booleans, and null are tokenized as a catch-all and colored `--text-secondary`.

**Key implementation detail:** Property key detection works by scanning past the closing `"` and any whitespace to check whether the next non-whitespace character is `:`. If so, the quoted string is a property key; otherwise it is a value.

**Rejected option:** Prism.js or similar library via CDN. Rejected because it introduces a CDN dependency and significant bundle weight for functionality achievable in a small custom implementation.

---

## Decision 19 — SVG Edge Geometry

**Decision:** Edges are implemented as cubic bezier `<path>` elements with the following control point formulas, derived from node center coordinates at implementation time:

- `classify → retrieve`: `M (cx-30, cy+20) C (cx-30, cy+65) (t.cx, t.cy-65) (t.cx, t.cy-20)` — exits bottom-left of classify, slight leftward curve to top of retrieve.
- `classify → escalate_fast_exit`: `M (cx+30, cy+20) C (cx+30, cy+65) (t.cx, t.cy-65) (t.cx, t.cy-20)` — exits bottom-right of classify, rightward curve to top of escalate_fast_exit.
- `retrieve → reason`: `M (f.cx, f.cy+20) L (t.cx, t.cy-20)` — straight vertical line.
- `reason → decide`: `M (f.cx, f.cy+20) L (t.cx, t.cy-20)` — straight vertical line.
- `decide → auto_resolve`: `M (cx-40, cy+20) C (cx-40, cy+55) (t.cx, t.cy-55) (t.cx, t.cy-20)` — exits bottom-left of decide, diagonal left curve to top of auto_resolve.
- `decide → escalate`: `M (cx+20, cy+20) C (cx+20, cy+55) (t.cx, t.cy-55) (t.cx, t.cy-20)` — exits bottom-right of decide, slight rightward curve to top of escalate.

**Reasoning:** The UI spec specified routing rules and stated that control point values were implementation details. These formulas produce clean, non-overlapping curves that clearly indicate directionality within the 700×500 canvas.

---

## Decision 20 — ScenarioSelector Active Tab Indicator

**Decision:** The active tab indicator is implemented as `boxShadow: 'inset 2px 0 0 var(--swagger-green)'` rather than a `border-left` property.

**Reasoning:** The tab strip uses `overflow: hidden` on the wrapping container, which clips any `border-left` added to a tab element (because the tab itself has no overflow). An inset box-shadow achieves the visual equivalent — a 2px left-side green bar — without being clipped. Adjacent tabs are separated by `borderRight: '1px solid var(--panel-border)'` on all tabs except the last. The outer container has `border: '1px solid var(--panel-border)'` and `borderRadius: 6`.

---

## Decision 21 — isLoading Timing

**Decision:** `isLoading` is set to `false` after the node animation completes, not at the moment of API response receipt.

**Reasoning:** The interface contract (Step 3b) specified `isLoading: false` at API success. The UI spec Interaction States Summary table showed the scenario selector and Execute button remaining disabled during the "Graph animating" state. These were contradictory. The implementation follows the UI spec table: `isLoading` stays `true` through the entire animation sequence and is set to `false` only after the last active node has animated and `NODE_TRANSITION_MS` (400ms) has elapsed. This prevents the recruiter from launching a second API call while the first run's animation is still in progress.

---

## Decision 22 — revealedNodes State Semantics

**Decision:** The animation state is tracked via a `revealedNodes: Set<string>` React state variable. Nodes are added to this set one by one as their stagger timer fires. After the last active node's timer, `revealedNodes` is set to the full set of all node IDs — this triggers the dimming of non-active nodes simultaneously.

**Reasoning:** The UI spec's animation sequence required two distinct phases: (1) active nodes appearing one by one, and (2) all remaining nodes dimming simultaneously at the end. A `revealedNodes` set naturally implements this: `getNodeState()` returns `neutral` for nodes not yet in the set, `active` for nodes in the set that are on the active path, and `dimmed` for nodes in the set that are not on the active path. Setting `revealedNodes = allNodeIds` at the end causes all non-active nodes to transition from neutral to dimmed in a single render.

---

## Decision 23 — Timer Cleanup

**Decision:** All `setTimeout` calls are registered through a `later()` wrapper that stores their IDs in a `useRef` array. A `clearTimers()` function cancels all pending timers by calling `clearTimeout` on each stored ID.

**Reasoning:** Without cleanup, timers from a previous run can fire after the user has selected a new scenario or started a new run, causing state mutations that produce visual glitches (e.g., nodes activating for a scenario that is no longer selected). `clearTimers()` is called at the start of every `handleExecute()` call and inside `resetOutput()` (which fires on scenario selection). This guarantees that no timer from a prior run can outlive its run.

---

## Decision 24 — Cloudflare Worker Format

**Decision:** The Cloudflare Worker is implemented using the service worker `addEventListener('fetch', ...)` format, not the ES module `export default { fetch }` format specified in the masterplan.

**Reasoning:** The masterplan's ES module example used `env.ANTHROPIC_API_KEY` to access the environment variable binding. In the deployed Worker, the API key binding is accessed as a global variable `ANTHROPIC_API_KEY` (not `env.ANTHROPIC_API_KEY`), which is the behavior of the service worker format. Both formats are supported by Cloudflare Workers; the service worker format was used because it matched the runtime behavior observed during deployment. Functionally the Worker is identical: OPTIONS requests return CORS headers; POST requests are forwarded to `https://api.anthropic.com/v1/messages` with the injected API key and CORS headers appended to the response.

---

## Decision 25 — GitHub Actions Deployment Workflow

**Decision:** Deployment to GitHub Pages is automated via a GitHub Actions workflow at `.github/workflows/deploy-demo.yml`. The workflow triggers on pushes to `master` that match the path filter `huginn_v2_demo/**`, and on `workflow_dispatch`. It uses `actions/checkout@v4`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3`, and `actions/deploy-pages@v4`. The entire `huginn_v2_demo` directory is uploaded as the Pages artifact.

**Reasoning:** A path-filtered workflow means unrelated changes to `huginn_v1/` or `huginn_v2/` do not trigger a demo deployment. Uploading the full `huginn_v2_demo/` directory means the design documents in `docs/` are also served at the Pages URL, which is acceptable for a portfolio artifact where source transparency is valued. The workflow requires no Node.js or build steps — the artifact is the directory as-is.

---

## What the Demo Is Not

The following are explicitly out of scope:

- A general-purpose Huginn interface — the recruiter cannot construct arbitrary inputs
- A replacement for the README or the documentation — it demonstrates behavior, not architecture
- A test harness — outputs are illustrative, not validated against the real Huginn codebase
- A v3 preview — it demonstrates v2 exactly as built
- A multi-file application — it is a single self-contained HTML file with no build step required
