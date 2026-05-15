# Phase 11: Frontend - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

A static, three-deliverable frontend for the Inside Bar Pattern Scanner project, reading the live `data.json` / `stats.json` / `charts/` files already produced by Phase 10's nightly GHA pipeline. Concretely:

1. **`docs/projects/patterns/index.html`** — pattern scanner screener. Sortable / filterable table of current detections (44 rows today, will vary 5–100 night to night). Columns: ticker, company, sector, confirmation date, confirmation type, **Pattern Quality** badge, current price, **Status** badge. An **always-visible 5-bar diagram band** sits above the controls so first-time visitors understand the structure without any prior knowledge. Status filter chips (All / Open / Target / Stop / Pending) sit above the table for one-click outcome isolation. Default sort: `confirmation_date` desc (most recent first). Clicking a row navigates to `stock.html?ticker=<SYMBOL>`. Theme: GitHub-blue (`#0d1117`), mirroring the existing DCF screener index for portfolio-wide table consistency.

2. **`docs/projects/patterns/stock.html`** — per-stock drilldown. Hero is the **annotated YOLO PNG** from `/charts/{TICKER}_{DATE}.png` (the rule frozen at confirmation), with **TradingView embed below** as live-price context (`interval: 'D'`, daily bars to match Phase 7 methodology). Below those: a 5-bar OHLC anatomy table (one row per bar with date / O / H / L / C), the per-row `simulate_trade` resolution block (status, entry/exit dates and prices, R, hold_days), and backtest stat cards (win rate with N, avg return R, median hold days) pulled from `stats.json` via the by_type_x_spring → by_confirmation_type → all fallback chain. Cross-link to the DCF drilldown when the ticker exists in `docs/projects/screener/data.json` (100% coverage today, but check defensively). Theme: analytical-dark (`#080c12`, Syne display + DM Sans body + DM Mono numbers, dot-grid background), mirroring DCF `stock.html` for drilldown consistency.

3. **A new card on `docs/index.html`** — pattern scanner project card added to the existing card grid (currently: Screener, Calculator). Links via `#patterns` hash to `docs/projects/patterns/index.html` through the same on-demand-iframe pattern the other two cards use (`docs/index.html` lines 401–497). The `projects` registry needs a new `patterns: 'projects/patterns/index.html'` entry.

**Explicitly out of scope:**
- Generating, mutating, or extending `data.json` / `stats.json` / chart PNGs — Phase 10 owns the data layer; Phase 11 is read-only.
- Tier stratification of `stats.json` by `yolo_conf` (the "score post-cutoff filtered slice with ONNX, ~5 min" follow-up Phase 9 SUMMARY flagged) — a Phase 11.x or later enrichment if pursued.
- YOLO output bbox overlay on the annotated chart — the algorithmic bbox is the deliverable (Phase 10 D-13).
- New backend API — site stays static; calculator is the only project with a live backend.
- Confidence threshold slider, historical detection accumulation, additional confirmation bar types — explicitly deferred to PAT2-* in REQUIREMENTS.md.

</domain>

<decisions>
## Implementation Decisions

### Pattern Quality Badge (D-01 — D-03)

- **D-01 — Column label = "Pattern Quality"** (NOT "Confidence"). The yolo_conf score is what the YOLOv8 model gives a detection, but per Phase 10 D-05 / D-12 the model was trained on chart-shape mimicry of the algorithmic detector (Phase 8 D-10 hard-negative strategy) — it judges "how textbook does this look on a chart," NOT trade success. "Confidence" in a finance UI invites the inference "the AI thinks this trade will work," which is the exact wrong mental model. "Pattern Quality" frames the score as a grade of the visual structure itself. REQ UI-01 says "confidence badge" but that wording predates the empirical understanding of what the model actually measures; the spec's intent (a quality indicator) is preserved.

- **D-02 — Tier cutoffs = 0.50 / 0.25 absolute (NOT percentile, NOT 0.75/0.25):**
  - Green ("clean"): `yolo_conf ≥ 0.50`
  - Yellow ("standard"): `0.25 ≤ yolo_conf < 0.50`
  - Red ("loose"): `yolo_conf < 0.25`
  - Grey/dash: `yolo_conf == null` (D-08-from-Phase-10 fallback when ONNX missing)
  - Today's distribution (44 detections): 10 green / 19 yellow / 15 red — visually balanced. The user considered 0.75/0.25 but that would put 0 detections in green today (model max is 0.726). Cutoffs are absolute (lock once in code) — NOT percentile-based — so a row's badge doesn't drift colour night to night as the population changes. Reasoning: visitors need a stable, comparable signal, not a relative ranking that re-weights every cron.
  - **Researcher knob:** flag a TODO to revisit cutoffs after ~30 nightly runs once an empirical histogram exists. One-line constant change.

- **D-03 — Badge palette reuses existing valuation badge colours from `docs/projects/screener/index.html`:** green `#3fb950` / yellow `#e3b341` / red `#f85149` with the matching 0.15-alpha background pattern (lines 222–256 of DCF index). Visual cohesion across the portfolio's screeners — visitors recognise the green/yellow/red language instantly.

### Pattern Legend / UI-02 (D-04 — D-05)

- **D-04 — Format = always-visible diagram band** above the controls. NOT collapsible, NOT a tooltip-only solution. Visitors should grasp the rule on first scroll without clicking. Reasoning: the requirement UI-02 explicitly says "explains the 5-bar structure in plain language so a first-time visitor understands what they are looking at without prior knowledge" — collapse / tooltip patterns fail visitors who don't click.
  - Layout: a horizontal band ~140–180px tall containing a labelled 5-bar mini-chart (SVG preferred for crispness; inline so no extra HTTP request) with short labels under each bar (Mother / Inside / Break / Confirm / Continuation OR similar — exact wording is planner's call). Plain-language caption below the diagram in one sentence (suggested: "Inside bar spring — a brief break-below after a tight pullback, recovered by the next bar"). Sits between the page header and the controls strip.

- **D-05 — Diagram scope = 5-bar structure ONLY.** Confirmation types (Pin / Mark Up / Ice-cream) and trend filters (HH/HL, above 50-SMA, SMA cluster) are NOT in the legend band — they surface via column-header tooltips (Confirmation Type column) and the drilldown page. Reasoning: the legend's job is the first-impression "what is this?" — three layers of pedagogy at once turns it into a textbook page and crowds the table out of the viewport on smaller screens. Type/filter context for visitors who want to go deeper is one click away.

### Visual Theme (D-06)

- **D-06 — Mirror the DCF project's theme split:**
  - `docs/projects/patterns/index.html` → **GitHub-blue theme** (`#0d1117` bg, `#161b22` surface, `#58a6ff` accent, system fonts, 8px radius) — same as `docs/projects/screener/index.html`.
  - `docs/projects/patterns/stock.html` → **Analytical-dark theme** (`#080c12` bg, layered `#0f1520`/`#161e2e`/`#1e2840` surfaces, Syne display + DM Sans body + DM Mono numbers, dot-grid radial-gradient background, 12px radius) — same as `docs/projects/screener/stock.html` and `docs/projects/moat/index.html`.
  - Reasoning: portfolio-wide rhythm. Tables = scan = familiar GitHub-style; drilldowns = focused study = "analytical studio" feel. Visitors who already navigated the DCF screener feel oriented in patterns immediately. NOT a third theme — the portfolio has only three projects; three themes would be visual fragmentation.
  - **Researcher / planner: copy CSS variable blocks verbatim from the DCF analogs.** Do NOT redefine palette tokens. Anything pattern-specific (badge variants, legend diagram styling, status pills) extends the existing token set, doesn't replace it.

### Drilldown Layout (D-07 — D-09)

- **D-07 — Hero = annotated PNG; TradingView below.** The static YOLO-annotated chart from `/charts/{TICKER}_{DATE}.png` is the largest visual element on the page (suggested 640px max-width to match the source aspect; centered or left-aligned per design judgement). Beneath it, the TradingView Advanced Chart embed (height ~340–420px) shows "what's happened on this ticker since." Reasoning: the project's pitch is "I encoded a domain rule into code — here are its decisions." The PNG IS that rule made visual. Putting TradingView first would relegate the project's actual deliverable to a supporting role. The audit-the-rule narrative wins by leading with the rule artefact.

- **D-08 — TradingView config = daily bars (`interval: 'D'`), dark theme, advanced-chart widget**, mirroring the DCF `stock.html` setup at `docs/projects/screener/stock.html` lines 1535–1580 BUT with `interval` flipped from `'W'` to `'D'`. Reasoning: Phase 7 / 8 / 10 operate on daily bars; the live chart should match that timeframe so visitors can see the actual 5 bars of the detection on the live chart too. Reuse the existing `script.onerror` "Chart unavailable offline" fallback verbatim — that pattern already handles graceful degradation.

- **D-09 — Drilldown information stack (top to bottom):**
  1. Top nav (sticky) — logo / breadcrumb (Patterns › TICKER) / Back to scanner
  2. Hero band — Ticker badge, company name, sector / industry breadcrumb, status pill, Pattern Quality pill, current price
  3. Annotated PNG (the rule) — large, centered or left-justified
  4. TradingView (the live chart) — full width, daily bars
  5. **5-bar anatomy table** — 5 rows × 5 cols (Date / Open / High / Low / Close) reading from `detection.bars[]` in `data.json`. Mono font for OHLC; tabular-nums.
  6. **Resolution card** — `status` headline + entry_date, entry_price, stop_price, target_price, exit_date, exit_price, exit_reason, hold_days, R. Coloured outline matching status (green target / red stop / blue open / grey pending).
  7. **Backtest stat cards (3-up)** — Win rate (with N denominator), Avg return (R-multiples), Median hold days. Sourced from `stats.json` via the `by_type_x_spring` → `by_confirmation_type` → `all` fallback chain (Phase 10 D-11). Show the actual cut used and N somewhere ("Based on N=293 out-of-sample ice_cream_spring detections") for transparency.
  8. **DCF cross-link card** — "View DCF analysis for {TICKER} →" linking to `../screener/stock.html?ticker={TICKER}` when the ticker exists in DCF `data.json`. Silent absence (no card shown) when the ticker isn't present. Today: 44/44 present; defensive check is for future-proofing.

### Status Surfacing on Screener (D-10 — D-12)

- **D-10 — Dedicated coloured Status column** in the screener table. Pill style: green=target, red=stop, blue=open, grey=pending. Reuses the badge geometry from D-03 (12px radius, 2px 10px padding, 12px font, alpha background) but with a different colour mapping. Column sortable. Reasoning: Phase 10 D-02 carried the full simulate_trade payload per row specifically so the frontend could expose outcomes; relegating it to drilldown only (the rejected option) would waste that data and weaken the "audit accuracy" framing.

- **D-11 — Status filter chips above the table.** Five clickable chips: `All (44)` `Open (10)` `Target (4)` `Stop (29)` `Pending (1)` — counts computed dynamically from the loaded `data.json`. Click toggles a single-active filter (radio-style, not multi-select). Sits in the existing controls strip alongside the search input and sector dropdown — design judgement on exact placement. Reasoning: visitors who want "show me only the live trades" or "show me only what stopped out" get there in one click; without chips, they have to learn to use the column sort + visually scan.

- **D-12 — Default sort = `confirmation_date` desc (newest first).** NOT sorted by status. Reasoning: the table tells a chronological story (these are the most recent 20 trading days of detections); sorting by status would scramble the recency story and confuse a visitor expecting "what just happened." Status visibility comes from the column + chips, not the default sort. Status sort is one column-header click away if a visitor wants it.

### Stats Loader & Fallback Chain (D-13)

- **D-13 — `stats.json` fallback per detection = `by_type_x_spring` → `by_confirmation_type` → `all`** (Phase 10 D-11 contract — Phase 11 IS the consumer). Lookup key: `f"{confirmation_type}_{is_spring ? 'spring' : 'extended'}"`. Show the actual cut used in the stat-card subtitle ("Based on N=293 ice_cream_spring detections" / "...N=713 ice_cream detections" / "...N=1325 all-type detections") so visitors see whether they're getting the granular cell or a fallback. Hide / dash any individual metric whose n is below the floor — better to show "—" than mislead with N=2 stats.

### Cross-Link to DCF (D-14)

- **D-14 — DCF cross-link via on-demand fetch of `docs/projects/screener/data.json`** on drilldown page load. If the page's `ticker` query param appears in the screener's `stocks[].ticker` list, render the cross-link card; otherwise omit it. Today's reality: 100% of pattern tickers are in DCF data (all 44/44), so the card will always render in practice — the check is defensive. The fetched DCF data.json is large (~503 stocks) but loads in <50 ms from GitHub Pages and only happens on the drilldown page (not the index). Cache via standard browser behaviour; no service worker needed.

### Empty / Error / Stale States (D-15 — D-16)

- **D-15 — Stale data banner driven by `pipeline_status.completed`** (Phase 10 D-16: completed=true when success_rate ≥ 95%). When `data.json.pipeline_status.completed === false`, render a yellow banner above the controls: "Data may be stale — last nightly pipeline run reported {failed_count} ticker failures." When true, render the standard "Last updated: {as_of_date}" subtitle (matches DCF screener pattern). No banner spam during normal operation.

- **D-16 — Empty detections array** (zero current setups — possible during low-volatility periods): render an empty-state card in place of the table: "No active inside-bar-spring setups in the last 20 trading days." The legend band stays visible (visitors still learn what they'd be looking at). This is rare — Phase 10's filtered detector on S&P 500 over 20 days routinely produces double-digit counts — but the path needs handling.

### Home-Page Card (UI-05) (D-17)

- **D-17 — Card structure mirrors the existing DCF screener card** in `docs/index.html` lines 357–369:
  - Anchor: `<a href="#patterns" class="card" data-project="patterns" aria-label="Open Inside Bar Pattern Scanner project">`
  - Thumbnail: `card-thumbnail-placeholder` div initially (matching the current DCF card pattern) with a TODO to swap in a real thumbnail PNG. Suggested real thumbnail: a cropped, polished version of one of the annotated `/charts/` PNGs (the most visually striking textbook example).
  - Title: "Inside Bar Pattern Scanner"
  - Benefit copy (one short line, blue accent — matches `card-benefit` class): suggested "AI-curated chart setups, updated every trading day"
  - Description: one sentence on what it does, suggested "Computer-vision-graded inside-bar-spring detections across the S&P 500, with backtested outcomes per setup type."
  - Tags: `Python`, `ONNX`, `Computer Vision`, `Finance` — four tags matching the card density of the other two cards.
  - Registry update: add `patterns: 'projects/patterns/index.html'` to the `projects` object at `docs/index.html` line 406–409.
  - Card ORDER on the home page is planner's call — suggest patterns first (newest), then DCF screener, then calculator (oldest), to emphasise current work to recruiters scanning the page.

### SEO & Marketing (D-18)

- **D-18 — Both pattern pages need the full SEO/OG/Twitter meta stack** that DCF screener / portfolio index already have (canonical, og:type, og:url, og:title, og:description, og:image, twitter:card, twitter:title, twitter:description, twitter:image, theme-color, meta description). Mirror the structure of `docs/projects/screener/index.html` lines 6–17. og:image: reuse a striking annotated chart PNG (export a high-res version as `docs/projects/patterns/og-image.png` — planner's call on which detection to use). Pages also need a single `<h1>` (REQ PERF-/marketing inheritance from Phase 6). Update `docs/sitemap.xml` and verify nothing in `docs/robots.txt` blocks the new directory.

### Accessibility (D-19)

- **D-19 — Match Phase 6 accessibility baseline:** keyboard-navigable controls with visible focus rings (`:focus-visible` box-shadow pattern from existing pages), `<a>` elements for navigable cards (not click handlers on `<div>`), explicit form labels (`<label class="sr-only">` for search/sector inputs), badge text accessible to screen readers (no colour-only meaning — pair colour with text label inside every pill), skip-nav link to the table. All existing pages already do this; pattern pages must not regress.

### Performance (D-20)

- **D-20 — Performance budget = match Phase 6 / DCF screener:**
  - Lazy-load the TradingView script on drilldown (it's already async per the existing pattern).
  - Lazy-load the annotated PNG via `loading="lazy"` and explicit width/height to prevent CLS.
  - Inline critical CSS (current convention — all DCF pages have a single `<style>` block, no external CSS files).
  - `data.json` for the screener: typical 44 detections × ~700 bytes/row ≈ 30 KB — fetches in a single round-trip, no progressive loading needed.
  - `data.json` for DCF cross-link check (on drilldown): ~503 stocks × ~1.5 KB ≈ 800 KB — fetch only on drilldown, NOT on screener index. Browser caches across views.
  - Lighthouse target: LCP under 2.5s (REQ PERF-03). The annotated PNG is the LCP candidate on the drilldown; size-optimise it (PNG quality already set by the publication style in Phase 10; reconsider WebP conversion only if Lighthouse flags it).

### Claude's Discretion

- **Exact diagram artwork for the legend band** — SVG hand-drawn vs generated from a fixture `Detection` via mplfinance and committed as a static PNG. Suggest SVG: vector-crisp at any zoom, no extra HTTP request, easy to tweak labels. Planner's call.
- **Mobile breakpoint behaviour for the legend band** — collapse to a smaller vertical layout or hide entirely below 480px? Suggest collapse-with-text-fallback. Planner's call.
- **Exact column hide order on mobile** for the screener table — at 640px the DCF screener hides sector/method/moat. Suggest hiding sector + status counts on the chips collapse to dropdown. Planner's call.
- **Whether to show `filters` (the three booleans per detection) on the drilldown** — `data.json` carries `filters: {above_50sma, hh_hl, sma_cluster}`. Suggest a small 3-pill filter strip in the drilldown ("Trend ✓ · Above 50-SMA ✓ · Cluster ✓") so visitors see ALL filters passed for this detection (today they always do — D-04 is filtered-only — but transparency is on-brand). Planner's call.
- **Whether to show `simulate_trade.exit_reason` verbosely** — strings like "target_hit" vs nice-language "Hit target at $310.70 on 2026-05-14". Suggest the nice version. Planner's call.
- **R-multiple rendering format** — `+0.53R` vs `+0.53` vs `0.53R`. Suggest `+0.53R` (signed, suffixed) to align with backtest convention. Planner's call.
- **Whether to surface `as_of_date` from `data.json` in the page header or in a tooltip** — suggest the header subtitle ("Last updated: 2026-05-15"), matching DCF screener.
- **Whether the DCF cross-link card has an icon** — suggest a small DCF-screener glyph or chart icon for visual recognition. Planner's call.

### Folded Todos

None — no pending todos matched Phase 11.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level
- `.planning/PROJECT.md` — Milestone v2.0 vision; "Out of Scope" list (no buy/sell signals, no P&L sim, no editable parameters in UI, no live model inference API, no separate tabs/windows for projects).
- `.planning/REQUIREMENTS.md` §"Frontend" — UI-01 through UI-05 acceptance criteria (this is the contract).
- `.planning/ROADMAP.md` §"Phase 11: Frontend" — Goal, dependency on Phase 10, the four success criteria.

### Upstream phase contracts (Phase 11 is a pure consumer of these)
- `.planning/phases/10-batch-pipeline/10-CONTEXT.md` — **MOST CRITICAL.** D-01 (20-day window), D-02 (full simulate_trade payload per row including the new `pending` status), D-05/D-07/D-12 (yolo_conf semantics and tier-decision deferral to Phase 11), D-09/D-10/D-11 (stats.json shape and fallback chain), D-13 (algorithmic bbox in the annotated PNG), D-15 (PNG filename convention `{TICKER}_{DATE}.png`), D-16 (`pipeline_status.completed` semantics), D-17 (atomic-write data contract Phase 11 reads).
- `.planning/phases/09-backtesting-engine/09-CONTEXT.md` — Filter ablation surprise context (filtered marginally underperforms unfiltered on the small post-cutoff slice) — informs the drilldown narrative framing ("filters tighten selectivity at small cost, not a clear edge"). DO NOT expose unfiltered numbers on the public screener (Phase 10 D-04).
- `.planning/phases/09-backtesting-engine/09-SUMMARY.md` — Empirical N counts (pin=295, mark_up=317, ice_cream=713 out-of-sample filtered); the "score post-cutoff filtered slice with ONNX, ~5 min" follow-up flagged for Phase 11 enrichment (NOT a Phase 11 blocker — Phase 10 ships without it per D-12).
- `.planning/phases/07-detection-engine/07-CONTEXT.md` — Detection record schema and confirmation-type definitions (Pin / Mark Up / Ice-cream / Spring case). Phase 11 reads this purely to write the legend / type-tooltip copy.

### Live data contracts (the only files Phase 11 actually reads at runtime)
- `docs/projects/patterns/data.json` — per-detection rows. Fields Phase 11 consumes per row: `ticker`, `company_name`, `sector`, `confirmation_date`, `confirmation_type` (pin/mark_up/ice_cream), `is_spring` (bool), `current_price`, `bars[]` (5 OHLC bars), `chart_path` ("charts/AAPL_2026-04-22.png"), `yolo_conf` (float or null), `filters` ({above_50sma, hh_hl, sma_cluster}), and the full simulate_trade block (`status`, `entry_date`, `entry_price`, `stop_price`, `target_price`, `risk`, `exit_date`, `exit_price`, `exit_reason`, `hold_days`, `R`). Top-level: `as_of_date`, `detections[]`, `pipeline_status`.
- `docs/projects/patterns/stats.json` — backtest aggregates. Top-level: `schema_version`, `generated_at`, `source`, `fallback_order`, `n_floor`, `rule`, `stats: { by_type_x_spring, by_confirmation_type, all }`. Each leaf has `n`, `n_resolved`, `win_rate`, `avg_return_r`, `median_hold_days`, `open_count`, `stop_count`, `target_count`.
- `docs/projects/patterns/charts/{TICKER}_{DATE}.png` — annotated 5-bar chart per detection. Referenced by row.chart_path; loaded with `loading="lazy"` and explicit dimensions for CLS prevention.
- `docs/projects/screener/data.json` — fetched ONLY on drilldown to check DCF cross-link availability (UI-04). Phase 11 reads `stocks[].ticker` and nothing else.

### Codebase pattern references (Phase 11 MUST mirror, not reinvent)
- `docs/projects/screener/index.html` — **Closest analog for the patterns screener index.** Copy: page structure (header / controls / table-scroll / table), sticky-thead styling, sortable column-header `data-col` pattern, search-input + sector-dropdown layout, sort indicator (`th[data-sort='asc'/'desc']::after`), badge variants (badge-highly-undervalued etc. — adapt to status pills), responsive mobile breakpoint at 640px, skip-nav link, error/empty/loading state divs, CSS variable token set (`--bg #0d1117`, `--surface #161b22`, `--border #30363d`, `--accent #58a6ff`, etc.).
- `docs/projects/screener/stock.html` — **Closest analog for the patterns drilldown.** Copy: top-nav with sticky logo + breadcrumb, hero glow variants pattern (adapt to status colours), badge stack, TradingView embed (`initChart(sym)` function at lines 1535–1580 — flip `interval: 'W'` to `'D'`), `script.onerror` fallback, dark-theme CSS variable token set (`--bg #080c12`, `--surface #0f1520`, etc.), Syne + DM Sans + DM Mono font import, dot-grid radial-gradient background, `.stat-td-*` table styling, `chart-fallback` empty state.
- `docs/projects/moat/index.html` — Secondary analytical-dark reference for confirming colour usage and component density.
- `docs/index.html` — **The only file modified outside `docs/projects/patterns/`.** Add a third card to the `<div class="projects">` grid (lines 357–391); add `patterns: 'projects/patterns/index.html'` to the `projects` registry (lines 406–409). NO other changes to this file. The postMessage navigation pattern (lines 480–493) already supports the pattern card without modification.
- `docs/sitemap.xml` — Add `<url>` entries for both new pages (`/projects/patterns/` and `/projects/patterns/stock.html`).

### Marketing / Accessibility baseline (Phase 6 inheritance)
- `.planning/phases/05-*/` and `.planning/phases/06-*/` (if archived: their summaries) — Phase 6 set the bar for SEO meta, OG tags, accessibility patterns. Pattern pages MUST match this bar — that means OG image, canonical URL, theme-color, JSON-LD where appropriate, focus rings, semantic HTML, accessible labels.

### Configuration files
- `.gitignore` — verify `docs/projects/patterns/charts/` is NOT ignored (it must commit — Phase 10's nightly pipeline relies on it). Currently fine, but check before assuming.

### Out-of-scope-but-related (do not implement in Phase 11)
- ONNX re-scoring of Phase 9 backtest cache — Phase 11 enrichment / Phase 11.x or later.
- Confidence threshold slider, historical-detection accumulation per ticker, additional confirmation bar types — PAT2-* in REQUIREMENTS.md (Pattern Scanner Iteration 2).
- Editing pattern parameters in the UI — explicitly out of scope per REQUIREMENTS.md ("the encoded ruleset IS the demonstration of domain knowledge").

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`docs/projects/screener/index.html` structure (707 lines)** — page layout, sticky thead, sortable columns, search + filter controls, badge variants, mobile breakpoint, error/empty/loading states. Pattern screener clones this skeleton and replaces the column set + filter dropdowns. Same CSS variable tokens, same accessibility patterns.
- **`docs/projects/screener/stock.html` structure (1809 lines)** — analytical-dark theme variables, top-nav sticky + breadcrumb, hero band, badge stack, TradingView embed pattern (`initChart` function with config object + onerror fallback), stat-card grid, dot-grid background, Syne/DM Sans/DM Mono font imports. Pattern drilldown clones the skeleton and replaces: financial snapshot → 5-bar OHLC anatomy + resolution card; spider chart → annotated PNG hero; DCF summary → backtest stat cards; (TradingView stays, but `interval: 'W'` → `'D'`).
- **`docs/index.html` `projects` registry pattern (lines 401–497)** — `projects[hash] = 'path'` lookup plus on-demand iframe creation, hash routing, fade transitions, postMessage support for sub-page back-navigation. Pattern card slots in with a one-line registry addition.
- **DCF screener's badge component pattern (lines 213–276)** — `.badge` base + `.badge-{label}` variants with `rgba(R,G,B,0.15)` background + matching colored text + `rgba(R,G,B,0.3)` border. Pattern Quality and Status badges reuse this exact recipe; only colour mapping changes.
- **TradingView embed via `initChart()` function** in `docs/projects/screener/stock.html` lines 1535–1580 — flip one config field (`interval`) and reuse verbatim.
- **`docs/projects/screener/stock.html` mobile bottom-nav / responsive grid pattern** — pattern drilldown should respect the same mobile breakpoints for consistency.

### Established Patterns
- **Single inline `<style>` block per HTML file, no external CSS.** Convention across all DCF/calculator/moat pages. Pattern pages follow.
- **Vanilla JS only, no frameworks.** Calculator, screener, moat, portfolio index — all hand-rolled JS. Pattern pages follow. No React/Vue/Svelte.
- **In-page iframe navigation from the portfolio shell.** Cards do NOT open new tabs (REQ NAV-01); they post-message back to the shell which swaps the iframe src.
- **Atomic data loading via `fetch('./data.json')`** — DCF screener pattern. Pattern screener follows. No service worker, no caching layer.
- **Loading / Error / Empty state divs** with display:none initial state, shown by state machine in the load promise. Pattern screener follows.
- **`window.postMessage` from iframe sub-pages back to parent shell for navigation** — DCF stock.html does this for "back to home." Pattern stock.html follows the same protocol for the "Back to scanner" button.
- **Skip-nav link, sr-only labels, visible :focus-visible ring** — accessibility baseline established Phase 6. Pattern pages match.
- **Two distinct dark themes coexisting in the portfolio** — GitHub-blue (`#0d1117`) for tables/portfolio shell; analytical-dark (`#080c12`) for drilldowns/moat. Pattern pages adopt the established split (D-06).
- **The portfolio shell loads pattern via on-demand iframe** — same `pendingTicker` mechanism could pre-load a specific ticker if needed (it isn't for Phase 11, but the wire is there for future enhancements like deep-linking from elsewhere).

### Integration Points
- **New files:**
  - `docs/projects/patterns/index.html` (estimated 700–900 lines, mirroring DCF screener index density)
  - `docs/projects/patterns/stock.html` (estimated 1500–2000 lines, mirroring DCF stock.html density)
  - `docs/projects/patterns/og-image.png` (one polished annotated chart, exported for social sharing)
  - Optional: `docs/projects/patterns/CLAUDE.md` (project-level doc mirroring `docs/projects/screener/CLAUDE.md`)
- **Modified files:**
  - `docs/index.html` — add card markup (one `<a class="card">` block) and one entry in the `projects` registry. No CSS changes (existing `.card` styles apply).
  - `docs/sitemap.xml` — add `<url>` entries for both new pages.
- **Read-only consumers (Phase 11 does NOT write to):**
  - `docs/projects/patterns/data.json` — Phase 10 writes nightly; Phase 11 reads.
  - `docs/projects/patterns/stats.json` — Phase 10 writes nightly; Phase 11 reads.
  - `docs/projects/patterns/charts/*.png` — Phase 10 writes nightly; Phase 11 references via row.chart_path.
  - `docs/projects/patterns/_backtest_aggregates.json` — Phase 10 reads this; Phase 11 ignores (it's a Phase 10 build input, not a frontend contract).
  - `docs/projects/screener/data.json` — DCF screener writes; Phase 11 reads ONLY on drilldown for cross-link check.

### Things to NOT Do
- Do NOT introduce a JS framework, build step, or bundler. The portfolio is hand-rolled vanilla; introducing tooling breaks the deployment model (GitHub Pages serves static files as-is).
- Do NOT refactor the existing DCF screener / stock.html / moat pages to share a CSS file. The redundancy is deliberate — each page is self-contained for deployment simplicity. Pattern pages copy what they need.
- Do NOT modify the portfolio shell's iframe navigation logic. Just register the new project and add the card.
- Do NOT extend or reshape `data.json` / `stats.json` / chart PNGs. Phase 10 owns those contracts; Phase 11 is read-only. If a new field is genuinely needed, that's a Phase 10 amendment, not a Phase 11 change.
- Do NOT add a backend dependency. The pattern scanner project is fully static like the moat and DCF screener — no Flask/Render calls.

</code_context>

<specifics>
## Specific Ideas

- **The user explicitly weighed and rejected tighter Pattern Quality cutoffs** (≥0.75 green) after I confirmed today's data tops out at 0.726 — they preferred a launch with a populated green tier over reserving green for hypothetically-cleaner future detections. This is the right product call: a green-free launch on day one undermines the badge as a signal. The conservative cutoff (0.50 / 0.25) is locked, with the understanding that the constant may be revisited after ~30 nightly runs.
- **The product framing carried over from Phase 10** ("show the strategy in motion so visitors can audit accuracy themselves") drove three of the four decisions: (a) the drilldown PNG-as-hero (D-07), (b) the dedicated Status column + filter chips (D-10, D-11), and (c) the surfacing of the actual cut + N in the backtest stat-card subtitle (D-13). All three exist to let a visitor verify the methodology rather than take it on faith.
- **The two-theme split is a portfolio rhythm choice, not a per-project styling decision.** Visitors who navigate the DCF screener experience the same blue→analytical transition when they navigate the pattern scanner. This makes the portfolio feel coherent across projects even though each project has its own content.
- **The legend band is the only piece of original visual design Phase 11 produces.** Everything else is recombination of existing patterns: badges, table, stat cards, hero, TradingView embed. The 5-bar diagram is new content — the planner should not over-engineer it (vanilla SVG, simple bar rectangles, labelled with text below; not a full mini-charting library).
- **The annotated PNG file path is on disk and committed by Phase 10** — Phase 11 just references it via `row.chart_path`. No image generation, no canvas manipulation, no bbox overlay code in Phase 11. The image IS the artefact.

</specifics>

<deferred>
## Deferred Ideas

- **Revisit Pattern Quality cutoffs after ~30 nightly runs** — once a real empirical histogram exists, planner may propose tighter cutoffs (e.g., 0.60/0.25 or even percentile-based). One-line constant change. NOT blocking Phase 11.
- **ONNX-aware re-scoring of Phase 9 backtest cache** (~5 min one-shot) so `stats.json` can carry stratified-by-tier aggregates ("win-rate when Pattern Quality is green"). Explicitly flagged in Phase 9 SUMMARY and Phase 10 D-12 as a Phase 11 follow-up. Currently NOT scoped into Phase 11 — would need its own plan slot. Worth doing because it makes the screener's "audit accuracy" narrative even stronger (visitors could see whether the model's high-quality picks actually win more).
- **YOLO output bbox overlay on the annotated PNG** — Phase 10 D-13 chose algorithmic bbox only. A future enrichment could draw the model's bbox dashed alongside the algorithmic one to demonstrate visual agreement. Adds bbox-decoding complexity in the renderer; not a Phase 11 concern.
- **Confirmation-type variant strip in the legend** — considered for D-05, rejected because it crowds first-impression UX. Could come back if visitor feedback shows confusion about the Type column.
- **Trend-filter checklist in the legend** — considered for D-05, rejected to keep the legend lean. The filter data is per-row in `data.json.filters`; the drilldown can show it (per Claude's Discretion above). If visitors miss it, promote to legend.
- **Confidence threshold slider on the screener** (PAT2-02 in REQUIREMENTS deferred list) — Phase 11 ships with the 3-tier badge instead; the slider is a v2 enrichment.
- **Historical detections per ticker** (PAT2-01) — currently only the 20-day window is exposed; full history accumulation is v2.
- **Uptrend context panel on drilldown** (PAT2-03) — HH/HL count, 20-SMA slope direction. Phase 11 surfaces the three booleans (above_50sma, hh_hl, sma_cluster) but not the numeric context. v2 enrichment.
- **Real thumbnail PNG for the home-page card** — Phase 11 ships with the existing `card-thumbnail-placeholder` CSS gradient and a TODO. A real screenshot/export comes when one annotated chart is judged visually compelling enough.
- **Per-page CLAUDE.md** for the patterns project — DCF screener has one (`docs/projects/screener/CLAUDE.md`). Suggested but not blocking; planner's call whether to scope into Phase 11.
- **Active-trade-window view** ("show me only `open` rows") — covered by D-11's filter chips at the row level. If visitors want a dedicated landing URL for "live trades," that's a Phase 11.x enhancement (one extra hash route).
- **Cross-link FROM DCF drilldown back TO pattern drilldown** — UI-04 covers patterns→DCF only. Symmetric link (DCF→patterns when a ticker has a current detection) would require modifying `docs/projects/screener/stock.html` to fetch `docs/projects/patterns/data.json` and check inclusion. Out of Phase 11 scope; worth doing in a separate small phase if the symmetry feels natural.

### Reviewed Todos (not folded)

None — no pending todos were reviewed during this discussion.

</deferred>

---

*Phase: 11-frontend*
*Context gathered: 2026-05-16*
