# Phase 11: Frontend - Research

**Researched:** 2026-05-16
**Domain:** Static vanilla HTML/CSS/JS frontend (GitHub Pages) consuming pre-computed pipeline outputs
**Confidence:** HIGH

## Summary

Phase 11 is a recombination phase, not a new-technology phase. It ships three deliverables (`docs/projects/patterns/index.html`, `docs/projects/patterns/stock.html`, plus a card and registry entry on `docs/index.html`) that mirror the existing DCF screener pages line-for-line in skeleton — only the column set, badge variants, hero content, and a small SVG legend diagram differ. Every CSS token, badge geometry, sticky-thead, sortable-column, skip-nav, sr-only, focus-ring, TradingView embed, and `chart-fallback` pattern already exists on disk and is copy-paste-ready. Confirmed against the actual files: 707 lines for the GitHub-blue screener index, 1809 lines for the analytical-dark stock.html.

The Phase 10 data contracts on disk (`docs/projects/patterns/data.json`, `stats.json`, `_backtest_aggregates.json`, `charts/*.png`) verify almost exactly as CONTEXT.md promised — with one schema deviation flagged: per-detection rows carry `status`/`entry_*`/`exit_*` fields directly at the top level (not nested in a `simulate_trade` object), and **`exit_reason` is NOT present** in the on-disk data. Planner must derive the human-readable "Hit target at $X on YYYY-MM-DD" copy from `status` + `exit_date` + `exit_price`, not read an `exit_reason` field. Two other Phase-10-emergent fields (`errors_truncated`, `style_substitutions`) appear in `pipeline_status` — frontend can safely ignore them.

**Primary recommendation:** Treat this phase as "fork the DCF screener pages, swap columns/hero/stat-cards/CSS-tokens already extracted in §Standard Stack below, add one ~150px SVG legend band, register one new project in the portfolio shell." The only original visual design Phase 11 produces is the 5-bar SVG legend; everything else is verbatim reuse with documented token changes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Render detection table | Browser / Client | — | Static page; client-side filter/sort against fetched JSON |
| Fetch detection data | Browser / Client | CDN / Static | `fetch('./data.json')` from GitHub Pages |
| Fetch backtest stats | Browser / Client | CDN / Static | `fetch('./stats.json')` from GitHub Pages |
| Cross-link DCF availability check | Browser / Client | CDN / Static | `fetch('../screener/data.json')` on drilldown only |
| Annotated chart display | CDN / Static | — | PNG served from `docs/projects/patterns/charts/`; `<img>` with `loading="lazy"` |
| Live-price chart | Browser / Client (3rd party) | — | TradingView Advanced Chart widget loaded via `<script async>` |
| 5-bar legend diagram | Browser / Client | — | Inline SVG, no external request |
| Project navigation | Browser / Client | — | Hash routing + on-demand iframe in `docs/index.html` shell |
| Sub-page → shell back-navigation | Browser / Client | — | `window.parent.postMessage({type:'navigate', project:null}, '*')` |
| SEO / OG meta | CDN / Static | — | Static `<meta>` tags emitted at build time (commit time) |
| Sitemap | CDN / Static | — | Static `docs/sitemap.xml` with new URL entries |

Phase 11 is exclusively client-tier work. Zero new backend, zero new build step, zero new dependencies.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Pattern Quality Badge (D-01 — D-03)**
- D-01: Column label = "Pattern Quality" (NOT "Confidence"). UI-01's "confidence badge" wording predates the empirical understanding of what `yolo_conf` actually measures.
- D-02: Tier cutoffs = 0.50 / 0.25 absolute. Green: `yolo_conf ≥ 0.50`. Yellow: `0.25 ≤ yolo_conf < 0.50`. Red: `yolo_conf < 0.25`. Grey/dash: `yolo_conf === null`. Cutoffs locked once in code; NOT percentile-based. Today's distribution: 10 green / 19 yellow / 15 red.
- D-03: Badge palette reuses existing valuation badge colours from DCF screener index lines 222–256: green `#3fb950` / yellow `#e3b341` / red `#f85149` with `rgba(R,G,B,0.15)` bg + `rgba(R,G,B,0.3)` border.

**Pattern Legend (D-04 — D-05)**
- D-04: Always-visible diagram band above controls. ~140–180px tall horizontal band. SVG preferred. NOT collapsible, NOT tooltip-only. Plain-language caption below.
- D-05: Diagram scope = 5-bar structure ONLY. Confirmation types and trend filters are NOT in the legend band.

**Visual Theme (D-06)**
- `patterns/index.html` → GitHub-blue theme (`#0d1117`, system fonts, 8px radius) — mirror DCF `screener/index.html` CSS variable block.
- `patterns/stock.html` → Analytical-dark theme (`#080c12`, Syne + DM Sans + DM Mono, dot-grid background, 12px radius) — mirror DCF `screener/stock.html` CSS variable block.
- Copy CSS variable blocks verbatim. Pattern-specific styling extends, does not replace.

**Drilldown Layout (D-07 — D-09)**
- D-07: Hero = annotated PNG; TradingView below. PNG ~640px max-width.
- D-08: TradingView config = daily bars (`interval: 'D'`), dark theme, advanced-chart widget. Mirror DCF `screener/stock.html` lines 1535–1580; flip `interval` from `'W'` to `'D'`. Reuse `script.onerror` fallback verbatim.
- D-09: Information stack: top nav → hero band → annotated PNG → TradingView → 5-bar OHLC anatomy → resolution card → backtest stat cards (3-up) → DCF cross-link card.

**Status Surfacing (D-10 — D-12)**
- D-10: Dedicated coloured Status column. green=target, red=stop, blue=open, grey=pending. Reuse badge geometry with different colour mapping. Sortable.
- D-11: Status filter chips above the table. Five chips: `All` `Open` `Target` `Stop` `Pending`. Counts dynamic from loaded data. Radio-style (single-active).
- D-12: Default sort = `confirmation_date` desc (newest first). NOT sorted by status.

**Stats Fallback (D-13)**
- Per-row fallback: `by_type_x_spring` → `by_confirmation_type` → `all`. Lookup key: `f"{confirmation_type}_{is_spring ? 'spring' : 'extended'}"`. Show actual cut + N used in stat-card subtitle. Hide / dash any metric whose `n < n_floor` (10).

**Cross-Link (D-14)**
- DCF cross-link via on-demand fetch of `docs/projects/screener/data.json` on drilldown page load. Silent absence when ticker not in DCF data. Defensive check.

**Empty / Stale States (D-15 — D-16)**
- D-15: Stale data banner when `pipeline_status.completed === false`. Yellow banner above controls: "Data may be stale — last nightly pipeline run reported {failed_count} ticker failures." When true: standard "Last updated: {as_of_date}" subtitle.
- D-16: Empty detections render an empty-state card: "No active inside-bar-spring setups in the last 20 trading days." Legend band stays visible.

**Home-Page Card (D-17)**
- Anchor: `<a href="#patterns" class="card" data-project="patterns" aria-label="Open Inside Bar Pattern Scanner project">`.
- Thumbnail: `card-thumbnail-placeholder` div initially with TODO for real PNG.
- Title: "Inside Bar Pattern Scanner".
- `card-benefit`: "AI-curated chart setups, updated every trading day".
- Description: "Computer-vision-graded inside-bar-spring detections across the S&P 500, with backtested outcomes per setup type."
- Tags: `Python`, `ONNX`, `Computer Vision`, `Finance`.
- Registry entry: `patterns: 'projects/patterns/index.html'` added at `docs/index.html` line 406–409.
- Card order: patterns first, then DCF screener, then calculator (planner's suggested order).

**SEO & Marketing (D-18)**
- Full SEO/OG/Twitter meta stack on BOTH pattern pages. Mirror `docs/projects/screener/index.html` lines 6–17.
- og:image: `docs/projects/patterns/og-image.png` (high-res export of one chosen annotated chart).
- Single `<h1>` per page.
- Update `docs/sitemap.xml` with both new URLs.
- Verify `docs/robots.txt` doesn't block `/projects/patterns/`.

**Accessibility (D-19)**
- Match Phase 6 baseline: keyboard-nav with `:focus-visible` ring, `<a>` for navigable cards, `<label class="sr-only">` for inputs, badge text accessible to screen readers (no colour-only meaning), skip-nav link to the table.

**Performance (D-20)**
- Lazy-load TradingView (async already).
- Lazy-load annotated PNG via `loading="lazy"` + explicit width/height for CLS.
- Inline critical CSS in a single `<style>` block per HTML file.
- Lighthouse target: LCP < 2.5s.

### Claude's Discretion

- Exact diagram artwork for the legend band (SVG vs static PNG). Suggest SVG.
- Mobile breakpoint behaviour for the legend band. Suggest collapse-with-text-fallback below 480px.
- Exact column hide order on mobile for the screener table. Suggest hiding sector + chips-collapse-to-dropdown at 640px (matches DCF analog).
- Whether to show `filters` (3 booleans) on the drilldown. Suggest small 3-pill filter strip.
- Whether to show nice-language exit reason. Suggest yes ("Hit target at $310.70 on 2026-05-14").
- R-multiple rendering format. Suggest `+0.53R` (signed, suffixed).
- Whether `as_of_date` surfaces in header. Suggest header subtitle "Last updated: …".
- DCF cross-link card icon. Planner's call.

### Deferred Ideas (OUT OF SCOPE)

- Revisit Pattern Quality cutoffs after ~30 nightly runs.
- ONNX-aware re-scoring of Phase 9 backtest cache (~5 min one-shot) → stratified-by-tier stats.
- YOLO output bbox overlay on the annotated PNG.
- Confirmation-type variant strip in legend.
- Trend-filter checklist in legend.
- Confidence threshold slider (PAT2-02).
- Historical detections per ticker (PAT2-01).
- Uptrend context panel on drilldown (PAT2-03).
- Real thumbnail PNG for the home-page card.
- Per-page CLAUDE.md for patterns project.
- Active-trade-window dedicated URL.
- Cross-link FROM DCF drilldown back TO pattern drilldown (symmetric).
- Any change to Phase 10 data contracts.
- Any backend / Flask API work.
- Any new framework, bundler, or build step.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Pattern scanner page (`docs/projects/patterns/index.html`) shows a sortable, filterable table of current detections — ticker, company, sector, detection date, confirmation type, **Pattern Quality** badge (D-01 reframing), current price | §Standard Stack (DCF screener clone), §Code Examples (sticky-thead, sortable headers, badge geometry, fetch+render loop) |
| UI-02 | Static pattern legend above the table explains the 5-bar structure for first-time visitors | §Code Examples (inline SVG 5-bar legend skeleton); legend is the only original visual design in Phase 11 |
| UI-03 | Per-stock drilldown (`docs/projects/patterns/stock.html`) shows hero, TradingView chart, annotated YOLOv8 detection image, 5-bar pattern anatomy table, backtest stat cards | §Standard Stack (DCF stock.html clone), §Code Examples (TradingView `initChart` verbatim with `interval: 'D'`, `chart-fallback` div, hero glow pattern) |
| UI-04 | Drilldown cross-links to the DCF screener drilldown when ticker is present in screener `data.json` | §Code Examples (on-demand fetch + ticker membership check), §Performance budget warning: screener data.json is 1.23 MB on disk, NOT 800 KB per CONTEXT estimate |
| UI-05 | Pattern scanner is added as a project card on the portfolio home page | §Code Examples (verbatim `projects` registry block + card markup from `docs/index.html` lines 357–391, 406–409) |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla HTML5 | — | Page structure | Project convention — `CLAUDE.md` mandates no frameworks |
| Vanilla CSS (single inline `<style>` per file) | — | All styling | Project convention across calculator/screener/moat |
| Vanilla JavaScript (ES5 idiom, `var` + function expressions) | — | All interactivity | Existing pages use ES5-style code; preserve for consistency |
| TradingView Advanced Chart Widget | external script | Drilldown live price chart | Already used by DCF `screener/stock.html`; same widget URL |
| Google Fonts (Syne, DM Sans, DM Mono) | — | Analytical-dark theme typography | Already imported on `screener/stock.html` and `moat/index.html` |
| Inline SVG | — | 5-bar legend diagram | Vector-crisp at any zoom; no external HTTP request; vanilla DOM API |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | — | — | This phase introduces **no new dependencies**. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline SVG legend | mplfinance-rendered static PNG fixture | Adds one image asset and one HTTP request; SVG wins on flexibility, accessibility, and zero-request cost. Confirmed by CONTEXT (Claude's Discretion). |
| TradingView Advanced Chart | Lightweight charting library (e.g. lightweight-charts) | Would require new dep + custom data fetch. TradingView is "free, reliable, already proven on DCF stock.html." Defer alternatives. |
| Vanilla JS table render | Hand-rolled web component | Adds shadow DOM ceremony for zero benefit at this size. Existing DOM-API pattern handles 44 rows trivially. |
| Server-rendered HTML (Jekyll/Eleventy) | Static-site generator | Breaks the "edit + commit + deploy" zero-build flow. Project CLAUDE.md explicitly bans new build steps. |

**Installation:**
```bash
# Nothing to install. Phase 11 modifies/creates HTML+CSS+JS files only.
# Existing requirements.txt and Node tooling are untouched.
```

**Version verification:** N/A — no package dependencies are added. The TradingView widget is loaded from `https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js` (versionless evergreen URL — same as DCF stock.html line 1551).

## Architecture Patterns

### System Architecture Diagram

```
                          ┌──────────────────────────┐
                          │   docs/index.html        │
                          │   (portfolio shell)      │
                          │   - hash router          │
                          │   - projects registry    │
                          │   - on-demand iframe     │
                          └──────────────┬───────────┘
                                         │ #patterns
                                         │ → src=projects/patterns/index.html
                                         ▼
              ┌──────────────────────────────────────────┐
              │  patterns/index.html (GitHub-blue)       │
              │                                          │
              │  [SVG 5-bar legend band — UI-02]         │
              │  [pipeline_status banner — D-15]         │
              │  [search + sector + status chips]        │
              │  [sortable, filterable table — UI-01]    │
              │                                          │
              │  fetch('./data.json')                    │
              │     ↓                                    │
              │  parse → filter → sort → render rows     │
              │     ↓                                    │
              │  click row → location.href =             │
              │     'stock.html?ticker=<SYM>'            │
              └─────────────┬────────────────────────────┘
                            │ ?ticker=AAPL
                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │  patterns/stock.html (analytical-dark)                   │
   │                                                          │
   │  [top nav — sticky]                                      │
   │  [hero band — ticker, company, status, quality, price]   │
   │  [annotated PNG — <img loading="lazy"> from chart_path]  │
   │  [TradingView embed — initChart(sym), interval:'D']      │
   │  [5-bar anatomy table — bars[]]                          │
   │  [resolution card — entry/exit/R/hold_days/status]       │
   │  [stat cards 3-up — win-rate, avg-R, median-hold]        │
   │  [DCF cross-link card — UI-04]                           │
   │                                                          │
   │  fetch('./data.json')   → row for this ticker            │
   │  fetch('./stats.json')  → fallback chain                 │
   │  fetch('../screener/data.json') → DCF cross-link check   │
   └──────────────────────────────────────────────────────────┘

External dependencies:
  - TradingView CDN (script load; graceful fallback on error)
  - Google Fonts CDN (preconnect + stylesheet for Syne/DM Sans/DM Mono)

Data dependencies (all read-only from local GitHub Pages):
  - docs/projects/patterns/data.json        (Phase 10 writes; UI-01/03/04 read)
  - docs/projects/patterns/stats.json       (Phase 10 writes; UI-03 reads)
  - docs/projects/patterns/charts/*.png     (Phase 10 writes; UI-03 references via row.chart_path)
  - docs/projects/screener/data.json        (DCF; UI-04 reads stocks[].ticker only)
```

### Recommended Project Structure

```
docs/
├── index.html                              # MODIFIED — add card + registry entry
├── sitemap.xml                             # MODIFIED — add 2 URLs
├── robots.txt                              # UNCHANGED — already Allow: /
└── projects/
    └── patterns/                           # NEW directory (file-system layout)
        ├── index.html                      # NEW — screener (GitHub-blue theme)
        ├── stock.html                      # NEW — drilldown (analytical-dark)
        ├── og-image.png                    # NEW — high-res annotated chart for OG/Twitter
        ├── data.json                       # EXISTS — Phase 10 writes
        ├── stats.json                      # EXISTS — Phase 10 writes
        ├── _backtest_aggregates.json       # EXISTS — Phase 10 input (Phase 11 ignores)
        └── charts/
            └── {TICKER}_{DATE}.png         # EXISTS — Phase 10 writes ~40 files
```

### Pattern 1: Fetch-then-Render Single-Page (used by UI-01 and UI-03)

**What:** Page loads with hidden loading/error/table divs; one `fetch()` populates state; state machine swaps which div is visible.

**When to use:** Both pattern pages. Mirrors `docs/projects/screener/index.html` lines 369–376 and 639–659.

**Example:** See §Code Examples → "Load-state machine" and "Fetch + render bootstrap."

### Pattern 2: Hash-Routed In-Page Navigation (UI-05)

**What:** Portfolio shell (`docs/index.html`) maps URL hash to project src via a `projects` registry, then injects an iframe on demand. Sub-pages signal "go home" with `window.parent.postMessage({type:'navigate', project:null}, '*')`.

**When to use:** New project card registration. Add ONE entry to the registry; the existing router handles everything else.

**Example:** See §Code Examples → "Portfolio shell registry + card markup."

### Pattern 3: Inline SVG Diagram (UI-02 — the only new visual)

**What:** A `<svg>` block inline in the HTML body, dimensioned with `viewBox`, drawn with `<rect>` for each of 5 candle bodies (mother / inside / break / confirm / continuation) and `<text>` labels below. Stylable via class names + theme variables.

**When to use:** Once, on the screener index page, sitting between the page header and the controls strip.

**Example:** See §Code Examples → "5-bar legend SVG skeleton."

### Pattern 4: Stats Lookup with Three-Level Fallback (D-13)

**What:** Build a lookup key from `confirmation_type` + `is_spring`; look in `stats.by_type_x_spring`; if `n < n_floor`, look in `stats.by_confirmation_type[confirmation_type]`; if still `n < n_floor`, use `stats.all`. Track which level resolved and surface it in the stat-card subtitle.

**When to use:** Once per drilldown page load, for the backtest stat cards.

**Example:** See §Code Examples → "Stats fallback chain."

### Anti-Patterns to Avoid

- **Inventing a `simulate_trade` nested object** — the on-disk schema has `status`/`entry_*`/`exit_*` as top-level row fields, NOT nested under a `simulate_trade` key. CONTEXT.md's prose is descriptive ("the full simulate_trade payload"), not literal. Verified by reading `docs/projects/patterns/data.json` (every row inspected, 40+ rows).
- **Reading a non-existent `exit_reason` field** — see Common Pitfalls → Pitfall 1.
- **Hand-rolling a CSS file or split stylesheets** — every existing project page uses a single inline `<style>` block. Maintaining that convention keeps deployments zero-build.
- **Modifying the portfolio shell's iframe/router logic** — the existing `navigate()` function at `docs/index.html` lines 423–472 already handles arbitrary entries in the `projects` map. Only the registry needs a one-line addition.
- **Driving badge meaning by colour alone** — D-19 mandates pairing colour with text inside every pill. Test by simulating monochrome / Windows High Contrast.
- **Treating `card-thumbnail-placeholder` as a temporary hack** — it's the established convention (DCF screener card uses it too, line 359). The "real thumbnail PNG" is explicitly deferred (CONTEXT Deferred Ideas).
- **Tier cutoffs computed from a percentile of the loaded dataset** — D-02 locks them as absolute constants. Computing a percentile would make the colour drift night to night.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Live price chart | Custom canvas chart from yfinance data | TradingView Advanced Chart widget (already proven on DCF `stock.html`) | TradingView ships zoom, pan, indicators, tooltips, dark theme, mobile gestures. Reinventing this is weeks of work. |
| In-page project navigation | New router code in pattern pages | Existing portfolio shell hash router + `postMessage` protocol | Already tested for 5+ months across DCF screener and calculator. Adding a new entry costs one line. |
| Table sticky-thead | Custom sticky implementation | `position: sticky; top: 0;` on `<thead> th` per DCF index lines 144–149 | CSS-native, GPU-composited, zero JS. |
| Sortable column headers | Pre-built table sort library | `data-col` attribute + click handler + `data-sort="asc"/"desc"` CSS pseudo-element arrow (DCF index lines 166–174, 682–696) | 25 lines of vanilla JS handles every sort case in the codebase today. |
| Search debounce | Lodash / utility lib | Inline `debounce(fn, ms)` from DCF index lines 410–415 | One closure, 6 lines. |
| Dark-theme palette | Tailwind dark variants / CSS-in-JS | Existing CSS variable token sets (DCF screener for GitHub-blue, DCF stock.html for analytical-dark) | Verbatim copy. Reinventing tokens fragments the portfolio's visual language. |
| Skip-nav link | A11y library | Inline `<a>` with off-screen `top:-100%` + `onfocus="this.style.top='8px'"` (DCF index line 342) | Two lines, zero deps. |
| Loading/Error/Empty state divs | State management library | Hidden divs with `display:none`; flip in `.then()`/`.catch()` (DCF index lines 369–376, 623–634) | Native CSS visibility. |
| Atomic data load | Service worker, IndexedDB cache | `fetch('./data.json')` once on DOMContentLoaded | Phase 10 writes atomically; browser HTTP cache handles repeat loads. |
| Mobile breakpoint | A11y/responsive library | One `@media (max-width: 640px)` block hiding columns + tightening padding (DCF index lines 319–338) | Project's established breakpoint. |
| OG image generation | Cloud OG service | One static PNG (`og-image.png`) committed to `docs/projects/patterns/` | Established convention; DCF screener reuses calculator's thumbnail.png as og:image. |

**Key insight:** This phase has zero "deceptively complex" problems. Every requirement maps to a pattern that already exists, working, in the codebase. The temptation to "modernize" or "improve" while we're here is the trap — discipline is verbatim reuse + token-only customization.

## Common Pitfalls

### Pitfall 1: Reading a non-existent `exit_reason` field

**What goes wrong:** CONTEXT.md (D-09, D-02-via-Phase-10) describes "the per-row `simulate_trade` resolution block" including `exit_reason`. The on-disk `docs/projects/patterns/data.json` rows DO NOT contain `exit_reason`. A planner who treats CONTEXT.md as ground truth will instruct the executor to render `row.exit_reason`, producing `undefined` / empty cells in production.
**Why it happens:** CONTEXT.md's description of "the full simulate_trade payload" is aspirational — it references Phase 9's `simulate_trade()` API surface, not the actual JSON contract Phase 10 emits. Phase 10 emits `status` + `entry_*`/`exit_*` fields directly at the row top level, no nested object.
**How to avoid:** Derive the human-readable exit copy from `status` + `exit_date` + `exit_price`:
  - `target` → `"Hit target at $" + exit_price.toFixed(2) + " on " + exit_date`
  - `stop` → `"Stopped out at $" + exit_price.toFixed(2) + " on " + exit_date`
  - `open` → `"Open trade (entered " + entry_date + ", " + (hold_days) + " days held)"`
  - `pending` → `"Pending entry — confirmation just printed; entry at next open"`
**Warning signs:** A console.log of any detection row showing no `exit_reason` key. A drilldown rendering empty / "undefined" in the resolution card.

### Pitfall 2: Trusting CONTEXT.md's 800 KB DCF data.json estimate (UI-04 perf budget)

**What goes wrong:** CONTEXT D-20 estimates `docs/projects/screener/data.json` at ~800 KB. The actual file on disk is **1,225,721 bytes (~1.20 MB)**. A planner who treats the 800 KB estimate as accurate may set Lighthouse perf budgets that fail in CI.
**Why it happens:** CONTEXT was written before re-measurement; the screener has accreted fields over the past phases (moat column, additional ratios).
**How to avoid:** Fetch the DCF data.json **only on drilldown** (UI-04), not on the screener index (it's not needed there). Use `fetch('../screener/data.json')` with `Accept-Encoding: gzip` (default). Document the real size (~1.2 MB; ~250 KB gzipped over the wire on GitHub Pages). LCP isn't affected because the drilldown LCP is the annotated PNG, fetched eagerly from local origin.
**Warning signs:** Network tab showing a single large JSON download on the screener index page (means UI-04 cross-link logic was accidentally placed on index.html).

### Pitfall 3: `stock.html` Title Tag Defaults to "Stock Overview"

**What goes wrong:** The DCF analog `docs/projects/screener/stock.html` ships with `<title>Stock Overview</title>` (line 6) — a generic placeholder that gets overwritten via `document.title = ticker + ' — ' + company_name` after fetch. Anyone who shares the URL **before** the JS runs (e.g., a crawler, a Slack preview, a slow network) sees "Stock Overview" as the OG title.
**Why it happens:** Static `<title>` can't know which ticker is in the URL. SEO meta tags are static at request time; only post-JS rewriting personalises them.
**How to avoid:** For `patterns/stock.html`, choose a richer static title that survives non-JS environments — e.g., `"Inside Bar Pattern Detail | Goh Jun Xian"`. Set the og:title and og:description statically too (don't reuse a placeholder). The JS rewrite happens after fetch as usual, but the static fallback should still be a credible portfolio-quality string.
**Warning signs:** A crawler-eye view of `stock.html?ticker=AAPL` showing a non-descript title.

### Pitfall 4: Forgetting to forward `postMessage` "back to scanner" from `stock.html`

**What goes wrong:** DCF `screener/stock.html` line 702 uses `<a href="index.html" class="btn-back">← Screener</a>` — a direct anchor that triggers a full iframe navigation inside the portfolio shell. This works in DCF because the user enters via the shell and stays inside the iframe. But pattern visitors who land directly on `patterns/stock.html?ticker=AAPL` (deep link from outside, e.g., a shared URL) won't have a shell to return to.
**Why it happens:** Two access modes for the page (iframed via shell vs. direct deep link).
**How to avoid:** Use the same `href="index.html"` anchor. Inside an iframe, the browser navigates the iframe content (correct behaviour — shell stays intact). Outside an iframe (direct deep link), the browser navigates the top window to `patterns/index.html` (correct behaviour — the user lands on the scanner page). No conditional logic needed; native anchor semantics handle both cases. DCF stock.html ships exactly this way and works in both modes.
**Warning signs:** A "back to scanner" button that uses `window.history.back()` or a postMessage handler — both break the direct-deep-link case.

### Pitfall 5: Computing Status Counts Without Coercion to Lowercase

**What goes wrong:** Status filter chips show `Open (10) Target (4) Stop (29) Pending (1)`. If the JS counts via `if (row.status === 'open')` but a row carries `'Open'` or `'OPEN'`, the count is wrong.
**Why it happens:** Phase 10 emits lowercase status strings (`open` / `target` / `stop` / `pending`) — verified on disk — but a future code change might capitalise them.
**How to avoid:** Normalise once: `const status = (row.status || '').toLowerCase();` before any comparison. Defensive but cheap.
**Warning signs:** Chip count `(0)` for a status that visibly appears in the table.

### Pitfall 6: SVG Legend Band Crowding the Viewport on Mobile

**What goes wrong:** A ~180px-tall always-visible legend pushes the table below the fold on a 667px-tall iPhone SE viewport. Visitors see only the legend, no detections.
**Why it happens:** CONTEXT D-04 mandates always-visible. Mobile breakpoint behaviour is Claude's Discretion.
**How to avoid:** Below 480px, swap the SVG legend for a one-sentence text caption: "Inside bar spring — a brief break-below after a tight pullback, recovered by the next bar." Keep visual continuity by using the same caption font/colour as the desktop version. Save the SVG-only block for ≥480px.
**Warning signs:** Lighthouse mobile screenshot showing legend > 50% of viewport height.

### Pitfall 7: Lazy-Loading the LCP Image

**What goes wrong:** `loading="lazy"` on the annotated PNG defers it until viewport-near, but on the drilldown the PNG IS above the fold and IS the LCP. Lazy-loading the LCP candidate penalises LCP score directly.
**Why it happens:** D-20 mentions `loading="lazy"` for the annotated PNG. The intent was "set explicit dimensions to prevent CLS," not "prevent it from preloading."
**How to avoid:** Use `loading="eager"` + `decoding="async"` + `fetchpriority="high"` on the drilldown's annotated PNG (it's the hero / LCP element). Set explicit `width` and `height` attributes for CLS prevention. The mobile bottom-nav fold check still wants `loading="lazy"` on the TradingView container, but the annotated PNG specifically should be eager.
**Warning signs:** Lighthouse "Largest Contentful Paint" target failing, with the annotated PNG flagged as the LCP element.

### Pitfall 8: Tier Math Bug — Inclusive vs Exclusive Boundaries

**What goes wrong:** D-02 specifies `green: yolo_conf >= 0.50` and `yellow: 0.25 <= yolo_conf < 0.50`. If the JS uses `>` instead of `>=` at the boundary, a row with `yolo_conf = 0.50` exactly gets a yellow badge instead of green.
**Why it happens:** Off-by-one error masquerading as off-by-epsilon.
**How to avoid:** Write the tiering function as a single `if/else if/else` chain with `>=` boundaries, matching D-02 verbatim:
```js
function tierFor(yolo_conf) {
  if (yolo_conf === null || yolo_conf === undefined) return 'na';
  if (yolo_conf >= 0.50) return 'green';
  if (yolo_conf >= 0.25) return 'yellow';
  return 'red';
}
```
**Warning signs:** Boundary rows visually mis-coloured; today's `yolo_conf = 0.5516` for APD (highest in dataset) being yellow.

## Code Examples

Verified patterns from existing files. All file references are absolute paths in this repo.

### Example 1: GitHub-Blue CSS Variable Token Block (verbatim — copy into `patterns/index.html`)

Source: `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\projects\screener\index.html` lines 22–31.

```css
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --accent: #58a6ff;
  --text: #c9d1d9;
  --text-bright: #f0f6fc;
  --text-dim: #8b949e;
  --radius: 8px;
}
```

### Example 2: Analytical-Dark CSS Variable Token Block (verbatim — copy into `patterns/stock.html`)

Source: `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\projects\screener\stock.html` lines 14–40.

```css
:root {
  --bg:           #080c12;
  --surface:      #0f1520;
  --surface2:     #161e2e;
  --surface3:     #1e2840;
  --border:       #1e2840;
  --border-mid:   #2a3550;
  --accent:       #58a6ff;
  --accent-dim:   #1f6feb;
  --accent-glow:  rgba(88,166,255,0.18);
  --green:        #3fb950;
  --green-bg:     rgba(63,185,80,0.08);
  --green-border: rgba(63,185,80,0.25);
  --yellow:       #e3b341;
  --yellow-bg:    rgba(227,179,65,0.08);
  --yellow-border:rgba(227,179,65,0.25);
  --red:          #f85149;
  --red-bg:       rgba(248,81,73,0.08);
  --red-border:   rgba(248,81,73,0.25);
  --text:         #a8b4c8;
  --text-dim:     #546278;
  --text-bright:  #e8edf5;
  --mono:         'DM Mono', monospace;
  --sans:         'DM Sans', sans-serif;
  --display:      'Syne', sans-serif;
  --radius:       12px;
}
```

Body backdrop (dot-grid) — source lines 44–62:

```css
body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
  background-image: radial-gradient(circle, #1e2840 1px, transparent 1px);
  background-size: 28px 28px;
  background-attachment: fixed;
}
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background: linear-gradient(160deg, rgba(8,12,18,0.97) 0%, rgba(8,12,18,0.93) 100%);
  pointer-events: none;
  z-index: 0;
}
body > * { position: relative; z-index: 1; }
```

Google Fonts import (drop in `<head>` before `<style>`):

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### Example 3: Badge Component CSS (geometry verbatim, palette mapped to Pattern Quality + Status)

Source for badge geometry: `docs/projects/screener/index.html` lines 213–256.

```css
/* Base — verbatim from DCF screener line 213-220 */
.badge {
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  display: inline-block;
}

/* Pattern Quality variants — D-01..D-03 */
.badge-quality-green {
  background: rgba(63, 185, 80, 0.15);
  color: #3fb950;
  border: 1px solid rgba(63, 185, 80, 0.3);
}
.badge-quality-yellow {
  background: rgba(227, 179, 65, 0.15);
  color: #e3b341;
  border: 1px solid rgba(227, 179, 65, 0.3);
}
.badge-quality-red {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
  border: 1px solid rgba(248, 81, 73, 0.3);
}
.badge-quality-na {
  background: rgba(139, 148, 158, 0.10);
  color: #8b949e;
  border: 1px solid rgba(139, 148, 158, 0.2);
}

/* Status variants — D-10 */
.badge-status-target {
  background: rgba(63, 185, 80, 0.15);
  color: #3fb950;
  border: 1px solid rgba(63, 185, 80, 0.3);
}
.badge-status-stop {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
  border: 1px solid rgba(248, 81, 73, 0.3);
}
.badge-status-open {
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
  border: 1px solid rgba(88, 166, 255, 0.3);
}
.badge-status-pending {
  background: rgba(139, 148, 158, 0.10);
  color: #8b949e;
  border: 1px solid rgba(139, 148, 158, 0.3);
}
```

### Example 4: Sticky-Thead Sortable Column Pattern (verbatim CSS + JS skeleton)

CSS source: `docs/projects/screener/index.html` lines 144–174.

```css
.screener-table thead th {
  position: sticky;
  top: 0;
  background: var(--surface);
  border-bottom: 2px solid var(--border);
  z-index: 10;
  cursor: pointer;
  user-select: none;
  padding: 10px 12px;
  text-align: left;
  color: var(--text-dim);
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.screener-table thead th[data-sort="asc"]::after  { content: ' \2191'; color: var(--accent); }
.screener-table thead th[data-sort="desc"]::after { content: ' \2193'; color: var(--accent); }
```

JS source: `docs/projects/screener/index.html` lines 562–570 + 682–696. Adapt `sortCol` default to `'confirmation_date'`, `sortDir` to `-1` (newest first per D-12).

```js
var sortCol = 'confirmation_date';
var sortDir = -1;

function updateSortIndicators() {
  document.querySelectorAll('.screener-table thead th[data-col]').forEach(function (th) {
    th.removeAttribute('data-sort');
    if (th.getAttribute('data-col') === sortCol) {
      th.setAttribute('data-sort', sortDir === 1 ? 'asc' : 'desc');
    }
  });
}

document.querySelectorAll('.screener-table thead th[data-col]').forEach(function (th) {
  th.addEventListener('click', function () {
    var col = this.getAttribute('data-col');
    if (col === sortCol) { sortDir = sortDir === 1 ? -1 : 1; }
    else { sortCol = col; sortDir = -1; }
    updateSortIndicators();
    renderTable();
  });
});
```

### Example 5: TradingView `initChart` (verbatim with `interval` flipped per D-08)

Source: `docs/projects/screener/stock.html` lines 1535–1580. Only change: `interval: 'W'` → `interval: 'D'`.

```js
function initChart(sym) {
  var outer = document.getElementById('tv-chart');
  outer.innerHTML = '';

  var container = document.createElement('div');
  container.className = 'tradingview-widget-container';
  container.style.cssText = 'width:100%;height:100%;min-height:340px;';
  outer.appendChild(container);

  var widgetDiv = document.createElement('div');
  widgetDiv.className = 'tradingview-widget-container__widget';
  widgetDiv.style.cssText = 'width:100%;height:100%;min-height:340px;';
  container.appendChild(widgetDiv);

  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  script.async = true;
  var config = {
    autosize: true,
    symbol: sym.replace(/-/g, '.'),
    interval: 'D',                       // <-- D-08: daily bars (was 'W')
    timezone: 'Etc/UTC',
    theme: 'dark',
    style: '1',
    locale: 'en',
    hide_top_toolbar: false,
    hide_legend: false,
    save_image: false,
    calendar: false,
    allow_symbol_change: false,
    backgroundColor: 'rgba(8,12,18,1)',
    gridColor: 'rgba(30,40,64,0.5)',
    support_host: 'https://www.tradingview.com'
  };
  script.textContent = JSON.stringify(config);

  script.onerror = function() {
    outer.innerHTML =
      '<div class="chart-fallback">' +
      '<span style="font-size:24px">📊</span>' +
      '<span>Chart unavailable offline</span>' +
      '</div>';
  };
  container.appendChild(script);
}
```

`chart-fallback` CSS — source: `docs/projects/screener/stock.html` lines 285–296:

```css
.chart-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 340px;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-dim);
  flex-direction: column;
  gap: 8px;
}
```

### Example 6: Portfolio Shell Registry + Card Markup

Card markup source: `docs/index.html` lines 357–369 (verbatim DCF screener card as the template).

```html
<!-- INSERT FIRST in the .projects grid per D-17 (patterns first, then DCF screener, then calculator) -->
<a href="#patterns" class="card" data-project="patterns"
     aria-label="Open Inside Bar Pattern Scanner project">
  <div class="card-thumbnail-placeholder" role="img" aria-label="Inside Bar Pattern Scanner preview"></div>
  <h2>Inside Bar Pattern Scanner</h2>
  <p class="card-benefit">AI-curated chart setups, updated every trading day</p>
  <p>Computer-vision-graded inside-bar-spring detections across the S&amp;P 500, with backtested outcomes per setup type.</p>
  <div class="tags" aria-label="Technologies used">
    <span class="tag">Python</span>
    <span class="tag">ONNX</span>
    <span class="tag">Computer Vision</span>
    <span class="tag">Finance</span>
  </div>
</a>
```

Registry source: `docs/index.html` lines 406–409. Apply one-line addition:

```js
var projects = {
  calculator: 'projects/calculator/index.html',
  screener:   'projects/screener/index.html',
  patterns:   'projects/patterns/index.html'   // <-- add this line
};
```

The existing `navigate()` function (lines 423–472) and `message` listener (lines 480–493) handle the new entry without modification. The `pendingTicker` mechanism (line 411) is calculator-specific and untouched.

### Example 7: 5-Bar Legend SVG Skeleton (the only original visual; UI-02)

Place between page header and `.controls` strip on `patterns/index.html`. ~140–180px tall (D-04). Vector-based, no external request.

```html
<section class="legend-band" aria-label="Inside bar spring 5-bar structure">
  <svg viewBox="0 0 600 140" role="img" aria-labelledby="legend-title legend-desc"
       width="100%" style="max-width:600px; height:auto; display:block; margin:0 auto;">
    <title id="legend-title">Inside Bar Spring — 5-bar anatomy</title>
    <desc id="legend-desc">A schematic showing the mother bar, inside bar, break-below bar, confirmation bar, and continuation bar that together form the inside bar spring pattern.</desc>

    <!-- Bar 1: Mother bar -->
    <rect x="60"  y="30" width="40" height="60" rx="2" fill="#3fb950" opacity="0.85"/>
    <line x1="80"  y1="20"  x2="80"  y2="100" stroke="#3fb950" stroke-width="1.5"/>
    <text x="80"  y="118" text-anchor="middle" font-size="11" fill="#c9d1d9" font-family="-apple-system, Segoe UI, sans-serif">Mother</text>

    <!-- Bar 2: Inside bar (smaller, contained within mother range) -->
    <rect x="160" y="45" width="40" height="30" rx="2" fill="#8b949e" opacity="0.8"/>
    <line x1="180" y1="40"  x2="180" y2="80"  stroke="#8b949e" stroke-width="1.5"/>
    <text x="180" y="118" text-anchor="middle" font-size="11" fill="#c9d1d9" font-family="-apple-system, Segoe UI, sans-serif">Inside</text>

    <!-- Bar 3: Break-below (low pierces mother's low) -->
    <rect x="260" y="55" width="40" height="35" rx="2" fill="#f85149" opacity="0.85"/>
    <line x1="280" y1="50"  x2="280" y2="108" stroke="#f85149" stroke-width="1.5"/>
    <text x="280" y="128" text-anchor="middle" font-size="11" fill="#c9d1d9" font-family="-apple-system, Segoe UI, sans-serif">Break</text>

    <!-- Bar 4: Confirmation (closes back above mother's low; "spring") -->
    <rect x="360" y="35" width="40" height="55" rx="2" fill="#3fb950" opacity="0.95"/>
    <line x1="380" y1="25"  x2="380" y2="95"  stroke="#3fb950" stroke-width="1.5"/>
    <text x="380" y="118" text-anchor="middle" font-size="11" fill="#c9d1d9" font-family="-apple-system, Segoe UI, sans-serif">Confirm</text>

    <!-- Bar 5: Continuation -->
    <rect x="460" y="25" width="40" height="55" rx="2" fill="#3fb950" opacity="0.7"/>
    <line x1="480" y1="15"  x2="480" y2="85"  stroke="#3fb950" stroke-width="1.5"/>
    <text x="480" y="118" text-anchor="middle" font-size="11" fill="#c9d1d9" font-family="-apple-system, Segoe UI, sans-serif">Continuation</text>

    <!-- Dashed mother-low reference line that "Break" pierces and "Confirm" recovers -->
    <line x1="40" y1="92" x2="520" y2="92" stroke="#8b949e" stroke-width="1" stroke-dasharray="4 4" opacity="0.5"/>
    <text x="540" y="96" font-size="10" fill="#8b949e" font-family="-apple-system, Segoe UI, sans-serif">mother low</text>
  </svg>
  <p class="legend-caption">
    <strong>Inside bar spring</strong> — a brief break-below after a tight pullback, recovered by the next bar.
  </p>
</section>
```

```css
.legend-band {
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
.legend-caption {
  text-align: center;
  font-size: 13px;
  color: var(--text-dim);
  margin-top: 4px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}
.legend-caption strong {
  color: var(--text-bright);
  font-weight: 600;
}
@media (max-width: 480px) {
  .legend-band svg { display: none; }
  .legend-caption { padding: 16px; }
}
```

The colour story: mother (calm green) → inside (compression grey) → break (red dip) → confirm (recovery green) → continuation (continuation green). Dashed line shows the mother's low — the level that defines the "spring." Planner can refine wording and exact bar dimensions.

### Example 8: Stale-Data Banner (D-15)

The portfolio has no existing "Last updated" banner pattern beyond the subtitle text on `screener/index.html` line 347 (`<p id="last-updated" class="subtitle">Loading data&hellip;</p>`). Phase 11 introduces the banner-style component below as a minimal extension fitting GitHub-blue tokens.

```html
<!-- Conditionally inserted before .controls when pipeline_status.completed === false -->
<div class="stale-banner" role="status" aria-live="polite" id="stale-banner" style="display:none;">
  <span class="stale-banner-icon" aria-hidden="true">⚠</span>
  <span id="stale-banner-text">Data may be stale — last nightly pipeline run reported {N} ticker failures.</span>
</div>
```

```css
.stale-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 24px 0;
  padding: 10px 14px;
  background: rgba(227, 179, 65, 0.10);
  border: 1px solid rgba(227, 179, 65, 0.3);
  border-radius: var(--radius);
  color: #e3b341;
  font-size: 13px;
}
.stale-banner-icon { font-size: 16px; }
```

```js
if (data.pipeline_status && data.pipeline_status.completed === false) {
  var banner = document.getElementById('stale-banner');
  var failed = data.pipeline_status.failed_count || 0;
  document.getElementById('stale-banner-text').textContent =
    'Data may be stale — last nightly pipeline run reported ' + failed + ' ticker failures.';
  banner.style.display = '';
}
```

The "Last updated: 2026-05-15" subtitle remains as the standard `<p id="last-updated">` element (same idiom as DCF screener). Banner appears IN ADDITION when the pipeline reports incompleteness.

### Example 9: SEO / OG / Twitter Meta Stack (verbatim mirror)

Source structure: `docs/projects/screener/index.html` lines 6–17. Adapted for both new pattern pages.

`patterns/index.html`:

```html
<title>Inside Bar Pattern Scanner — AI-Graded Setups | Goh Jun Xian</title>
<meta name="description" content="Live computer-vision-graded inside-bar-spring detections across the S&amp;P 500. Pattern Quality badge, backtested outcomes per setup type. Updated nightly.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://jxgoh004.github.io/jun-xian-project/projects/patterns/">
<meta property="og:title" content="Inside Bar Pattern Scanner — AI-Graded Setups | Goh Jun Xian">
<meta property="og:description" content="Live computer-vision-graded inside-bar-spring detections across the S&amp;P 500. Pattern Quality badge, backtested outcomes per setup type. Updated nightly.">
<meta property="og:image" content="https://jxgoh004.github.io/jun-xian-project/projects/patterns/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Inside Bar Pattern Scanner — AI-Graded Setups | Goh Jun Xian">
<meta name="twitter:description" content="Live computer-vision-graded inside-bar-spring detections across the S&amp;P 500. Pattern Quality badge, backtested outcomes per setup type. Updated nightly.">
<meta name="twitter:image" content="https://jxgoh004.github.io/jun-xian-project/projects/patterns/og-image.png">
<link rel="canonical" href="https://jxgoh004.github.io/jun-xian-project/projects/patterns/">
<meta name="theme-color" content="#0d1117">
```

`patterns/stock.html`:

```html
<title>Pattern Detail — Inside Bar Scanner | Goh Jun Xian</title>
<meta name="description" content="Annotated chart, 5-bar anatomy, live-trade resolution, and backtest stats for an inside-bar-spring detection from the nightly scanner.">
<meta property="og:type" content="article">
<meta property="og:url" content="https://jxgoh004.github.io/jun-xian-project/projects/patterns/stock.html">
<meta property="og:title" content="Pattern Detail — Inside Bar Scanner | Goh Jun Xian">
<meta property="og:description" content="Annotated chart, 5-bar anatomy, live-trade resolution, and backtest stats for an inside-bar-spring detection from the nightly scanner.">
<meta property="og:image" content="https://jxgoh004.github.io/jun-xian-project/projects/patterns/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pattern Detail — Inside Bar Scanner | Goh Jun Xian">
<meta name="twitter:description" content="Annotated chart, 5-bar anatomy, live-trade resolution, and backtest stats for an inside-bar-spring detection from the nightly scanner.">
<meta name="twitter:image" content="https://jxgoh004.github.io/jun-xian-project/projects/patterns/og-image.png">
<link rel="canonical" href="https://jxgoh004.github.io/jun-xian-project/projects/patterns/stock.html">
<meta name="theme-color" content="#080c12">
```

JS sets a richer `document.title` after fetch (same idiom as DCF stock.html line 1587):
```js
document.title = stock.ticker + ' — ' + (stock.company_name || stock.ticker) + ' | Inside Bar Scanner';
```

**OG image notes:**
- Filename: `og-image.png` (one image referenced by both pages; same convention DCF uses for `calculator/thumbnail.png`).
- Recommended dimensions: 1200×630 (Open Graph / Twitter summary_large_image standard). Source the image from one polished annotated chart PNG in `docs/projects/patterns/charts/` — pick visually striking textbook example (planner picks; suggest `COST_2026-05-07.png` or `AVGO_2026-05-13.png` since they're large, recognisable tickers).
- Crop / pad the original 640×640 PNG to 1200×630 with dark padding to match analytical-dark theme — manual one-time export, not a build step.

### Example 10: Sitemap Addition

Source: `docs/sitemap.xml` (5 lines today). Two new entries:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://jxgoh004.github.io/jun-xian-project/</loc>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://jxgoh004.github.io/jun-xian-project/projects/calculator/</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jxgoh004.github.io/jun-xian-project/projects/screener/</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jxgoh004.github.io/jun-xian-project/projects/patterns/</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jxgoh004.github.io/jun-xian-project/projects/patterns/stock.html</loc>
    <changefreq>daily</changefreq>
    <priority>0.6</priority>
  </url>
</urlset>
```

`docs/robots.txt` verified: `User-agent: * \n Allow: / \n Sitemap: https://jxgoh004.github.io/jun-xian-project/sitemap.xml`. Nothing blocks `/projects/patterns/`. No edits needed.

### Example 11: Accessibility Primitives (verbatim)

Source: `docs/projects/screener/index.html` lines 304–316 (skip-nav + sr-only + focus-visible).

```html
<!-- Skip-nav: place as very first child of <body> -->
<a href="#table-wrap"
   style="position:absolute;top:-100%;left:16px;z-index:10000;padding:8px 16px;background:var(--accent);color:#0d1117;font-weight:600;border-radius:8px;text-decoration:none;"
   onfocus="this.style.top='8px'" onblur="this.style.top='-100%'">Skip to scanner</a>
```

```css
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
```

Input labels (same idiom as DCF screener lines 351, 353):
```html
<label for="search" class="sr-only">Search ticker or company</label>
<input type="text" id="search" placeholder="Search ticker or company…" autocomplete="off">
<label for="sector-filter" class="sr-only">Filter by sector</label>
<select id="sector-filter">
  <option value="">All Sectors</option>
</select>
```

Badge with sr-friendly label (D-19 — colour never alone):
```html
<td aria-label="Pattern Quality: green">
  <span class="badge badge-quality-green">Clean (0.55)</span>
</td>
```

### Example 12: Stats Fallback Chain (D-13)

```js
function lookupStats(stats, confirmation_type, is_spring) {
  var n_floor = stats.n_floor || 10;
  var primaryKey = confirmation_type + '_' + (is_spring ? 'spring' : 'extended');

  var byTypeSpring = stats.stats.by_type_x_spring && stats.stats.by_type_x_spring[primaryKey];
  if (byTypeSpring && byTypeSpring.n >= n_floor) {
    return { stats: byTypeSpring, level: 'by_type_x_spring', key: primaryKey };
  }

  var byType = stats.stats.by_confirmation_type && stats.stats.by_confirmation_type[confirmation_type];
  if (byType && byType.n >= n_floor) {
    return { stats: byType, level: 'by_confirmation_type', key: confirmation_type };
  }

  return { stats: stats.stats.all, level: 'all', key: 'all' };
}

// Usage on drilldown:
var result = lookupStats(statsJson, detection.confirmation_type, detection.is_spring);
// result.stats.win_rate, result.stats.avg_return_r, result.stats.median_hold_days, result.stats.n
// Subtitle: "Based on N=" + result.stats.n + " " + result.key.replace('_', ' ') + " detections"

// Per-metric n_floor guard:
function safeMetric(value, n, floor, formatter) {
  if (n < floor) return '—';
  return formatter(value);
}
```

### Example 13: Cross-Link Defensive Check (UI-04)

```js
// On drilldown page load only (not on screener index)
fetch('../screener/data.json')
  .then(function (r) { return r.ok ? r.json() : { stocks: [] }; })
  .then(function (dcf) {
    var tickers = (dcf.stocks || []).map(function (s) { return s.ticker; });
    var ticker = getQueryParam('ticker');
    if (tickers.indexOf(ticker) !== -1) {
      // Render the cross-link card
      document.getElementById('dcf-crosslink-card').style.display = '';
      document.getElementById('dcf-crosslink-anchor').href =
        '../screener/stock.html?ticker=' + encodeURIComponent(ticker);
    }
    // Else: silent absence; card remains hidden.
  })
  .catch(function () {
    // Silent failure — DCF data unavailable shouldn't break the page.
  });
```

DCF cross-link UX precedent: the existing portfolio cross-links pattern → DCF/moat is the moat badge on `docs/projects/screener/index.html` lines 532–548 (a `<a class="moat-badge">` with `e.stopPropagation()` on click). Pattern's DCF cross-link card mirrors the same "external nav from drilldown to drilldown" semantic but uses a full card surface rather than a tag-style badge because it sits in the information stack, not in a table row.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Server-rendered table | Pre-computed JSON + client-side filter/sort | 2026-04-05 (Phase 5 — DCF screener) | Zero backend; cache-friendly; instant filter UX |
| `<div>` cards with `onclick` | `<a>` cards with `data-project` + hash router | 2026-03-31 (Phase 3) | Keyboard-native, browser-back works, semantically correct |
| Verbose inline styles | CSS variables + utility classes | 2026-04-04 (Phase 4) | Single source of truth for theme; analytical-dark introduced Phase 5 |
| Title-only meta tags | Full SEO + OG + Twitter stack | 2026-05-01 (Phase 6) | Rich link previews on LinkedIn/Slack/X |

**Deprecated/outdated patterns to avoid:**
- jQuery — never used in this codebase; do not introduce.
- Class-based components — Vanilla JS uses function declarations + event listeners.
- ESM `<script type="module">` — current pages use script tags without `type="module"`. Don't change without reason.
- `localStorage` for state — pages are stateless reads of JSON; no client persistence.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | TradingView widget URL `https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js` is still served and stable | Standard Stack, Code Example 5 | Drilldown live chart fails; existing `script.onerror` fallback renders the "Chart unavailable offline" message. Same risk as DCF screener (already in production) — no incremental exposure. |
| A2 | `loading="lazy"` on the annotated PNG (D-20) was intended as "set explicit dimensions" — the actual LCP-friendly attribute is `loading="eager" fetchpriority="high"` | Pitfall 7 | Lighthouse LCP regresses on the drilldown. Easily caught by Lighthouse CI / manual audit. Planner should default to eager for the hero PNG and document the deviation from D-20's literal wording. |
| A3 | Inline SVG for the legend (D-04 / Claude's Discretion) is preferred over a static PNG fixture | Standard Stack | If a future visual brief calls for mplfinance-rendered legends to match the chart PNGs exactly, SVG would need replacement. Low risk; CONTEXT explicitly suggests SVG. |
| A4 | OG image dimensions of 1200×630 are appropriate for Open Graph + Twitter `summary_large_image` | Example 9 | Bad social preview crops on LinkedIn/X. Standard dimensions; widely cited. |
| A5 | `confirmation_type` values in `data.json` are exactly `pin` / `mark_up` / `ice_cream` (lowercase, underscore-separated) — matching the `stats.json` keys for the fallback chain | Example 12 (Stats fallback) | Lookup misses if Phase 10 emits different casing. Mitigated by verified inspection: on-disk data.json rows confirm lowercase `pin` / `mark_up` / `ice_cream` (≈30 occurrences inspected). |
| A6 | The five PNG charts I sampled (APD, AEP, V, GWW, WAB) representative of full annotated PNG output — 640×640 dark-themed with bbox | Performance | If some PNGs are oversized (e.g., 4K), the LCP budget regresses. Phase 10 D-14 locks the publication style as deterministic; size variance is low. |
| A7 | Phase 10's `style_substitutions` and `errors_truncated` fields in `pipeline_status` are non-essential for the frontend | Code Example 8 | Frontend ignores them — banner only renders on `completed === false`. No risk. |
| A8 | A static `<title>` fallback like `"Inside Bar Pattern Detail | Goh Jun Xian"` reads acceptably in crawler / pre-JS contexts | Pitfall 3 | Suboptimal SEO if a crawler indexes the pre-JS page. Mitigated by JS rewrite on fetch (same risk DCF stock.html already carries). |

## Open Questions (RESOLVED)

1. **Should the home-page card thumbnail ship with a real PNG or with the placeholder?**
   - What we know: CONTEXT D-17 explicitly defers a real thumbnail to a future revision and prescribes the placeholder div for v1.
   - What's unclear: Whether the planner wants to compress the deferral by exporting one polished PNG at the same time as the og-image.png (since the work overlaps).
   - Recommendation: Ship with the placeholder per D-17. If the og-image export produces an obviously-card-worthy crop, the planner may opt to commit a second PNG cropped to card aspect (~1.85:1 for the existing `.card` thumbnail style) and skip the placeholder — but this is a stretch goal, not blocking.
   - **RESOLVED:** Ship with `card-thumbnail-placeholder` per D-17 Deferred Ideas. Encoded in plan `11-03` Task 1. Real PNG export deferred.

2. **Where exactly should the status filter chips sit in the controls strip?**
   - What we know: CONTEXT D-11 says "in the existing controls strip alongside the search input and sector dropdown — design judgement on exact placement."
   - What's unclear: Whether chips go LEFT of search (filter-first UX), RIGHT of sector dropdown (most-recently-added control), or BELOW the controls row (full-width chip bar).
   - Recommendation: Below the controls row, full-width, scroll-x on mobile. Reasoning: chips are visual + tap-friendly, and putting them inline with text inputs creates cognitive clutter. Planner decides; UI checker / MNC audit will validate.
   - **RESOLVED:** Chips placed inside `.controls` strip with `overflow-x: auto` on narrow viewports (chip bar collapses gracefully at ≤640px). Encoded in plan `11-01` Task 1.

3. **Should the drilldown's filter strip (Claude's Discretion: show the 3 booleans) be a row of pills or a compact line of text?**
   - What we know: All 44 current detections have all 3 filters = true. The strip is currently informational only.
   - What's unclear: Whether visual emphasis (pills) is warranted when the data is uniformly true today.
   - Recommendation: Pill row at low visual weight (smaller, grey-toned). Once a detection with mixed filter state appears (Phase 10 filtered=true mandate suggests never, but graceful display matters), pills give immediate signal. Suggest deferring to planner judgement.
   - **RESOLVED:** Low-weight pill row (`Trend ✓ / Above 50-SMA ✓ / Cluster ✓`), grey-toned, rendered in the drilldown hero band. Encoded in plan `11-02` Task 2.

4. **For the "View DCF analysis for {TICKER}" cross-link card icon (Claude's Discretion D-14 prose):**
   - What we know: No portfolio cross-link card precedent today. DCF screener has a `moat-badge` in-row link, but that's badge-style not card-style.
   - What's unclear: Whether the card should include any iconography.
   - Recommendation: Lightweight: a small `<svg>` chart-line icon (12 lines of SVG) inside the card. Avoid emojis (DCF stock.html uses `📈` in nav and `📊` in chart-fallback, but the inline SVG approach scales better and respects dark-mode glyph rendering). Planner decides.
   - **RESOLVED:** Arrow-only, no chart-line icon — minimal visual weight, matches DCF screener's link styling. Encoded in plan `11-02` Task 1 (`.cross-link-card .arrow` CSS).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Modern browser (Chrome 90+/Firefox 90+/Safari 14+) | All pages | ✓ | — | Page degrades to "no JS" view (title + meta only); no graceful render path needed for static portfolio. |
| TradingView CDN | Drilldown live chart | ✓ (assumed; reachable from GitHub Pages) | evergreen | `chart-fallback` div renders "Chart unavailable offline" via existing `script.onerror`. |
| Google Fonts CDN | Drilldown typography | ✓ (assumed; reachable) | evergreen | `font-family` falls back to `sans-serif` / `monospace` declared inheritance. Theme still renders. |
| Local `data.json` / `stats.json` / `charts/*.png` | All pages | ✓ | nightly-refreshed | Loading-state UI persists; error-state UI shown on fetch failure. |
| Local `../screener/data.json` | Drilldown UI-04 only | ✓ | nightly-refreshed | Silent omission of cross-link card on fetch failure or ticker-absence. |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None blocking.

This is a pure static-site phase — no build step, no Node tooling, no Python runtime, no compiled assets. The only thing the user's machine needs is a text editor and a browser to view the result.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None at the unit level — pure static HTML/CSS/JS. Validation is via browser tooling (Lighthouse, W3C, html-validate) + a manual UAT script + golden-fixture visual snapshots. |
| Config file | None to be created — Lighthouse is the de facto baseline (Phase 6 inheritance). |
| Quick run command | `npx --yes lighthouse https://jxgoh004.github.io/jun-xian-project/projects/patterns/ --quiet --chrome-flags="--headless"` (smoke check after deploy) |
| Full suite command | Manual UAT script (below) + Lighthouse mobile + desktop + html-validate on both new HTML files |

The project has zero existing frontend unit tests — every previous frontend phase (Phase 1–6) shipped with a manual UAT script + Lighthouse baseline. Phase 11 follows the same convention. Adding a unit-test framework solely for this phase would violate the "no new tooling" project constraint.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| UI-01 | Screener renders sortable, filterable table of detections | manual UAT + visual | "Load screener, verify 44 rows, click each column header, verify ascending/descending sort, type 'AAPL' in search and verify filter, choose sector dropdown and verify filter, click a row and verify deeplink to stock.html?ticker=…" | manual script needed |
| UI-01 | Pattern Quality badge tier colors are correct at boundaries | manual UAT | "Load with fixture data containing yolo_conf=0.499, 0.500, 0.250, 0.249, null — verify yellow/green/yellow/red/grey respectively" | manual fixture needed |
| UI-02 | Legend band visible above table, explains 5-bar structure | manual UAT + a11y audit | "Load page; verify legend band visible without scrolling on 1280×800; verify SVG has `<title>` and `<desc>`; verify caption sentence is readable; verify mobile (480px) falls back to text caption only" | manual script needed |
| UI-03 | Drilldown shows annotated PNG hero, TradingView, 5-bar table, resolution card, stat cards | manual UAT + visual | "Load stock.html?ticker=APD; verify PNG loads from charts/APD_2026-04-20.png; verify TradingView renders daily bars (not weekly); verify 5-bar OHLC table has 5 rows × 5 cols; verify resolution card shows status=open with entry/target/stop; verify stat cards show win_rate / avg_return_r / median_hold_days with N subtitle" | manual script needed |
| UI-03 | Drilldown handles all four `status` values (open / target / stop / pending) | manual UAT + fixture | "Load each of APD (open), GWW (target), AEP (stop), and (synthetic pending fixture) — verify resolution card colour outline, status text, and exit prose render correctly" | manual fixture for `pending` case |
| UI-03 | Stats fallback chain works: by_type_x_spring → by_confirmation_type → all | manual UAT + synthetic fixture | "Inject stats.json with `pin_extended.n=5` (below n_floor=10) — verify subtitle reads 'Based on N=295 pin detections' (fell back to by_confirmation_type)" | manual fixture needed |
| UI-04 | DCF cross-link card renders when ticker is in DCF data.json | manual UAT + visual | "Load stock.html?ticker=APD (present in DCF); verify cross-link card visible. Load with synthetic ticker 'XYZ123' not in DCF; verify card omitted." | manual script needed |
| UI-05 | Portfolio home page shows pattern scanner card and navigates in-page | manual UAT + a11y | "Load docs/index.html; verify 3 cards (patterns, DCF, calculator); click patterns card; verify URL hash becomes #patterns; verify iframe loads patterns/index.html; click logo; verify return to home" | manual script needed |
| Cross-cutting | Lighthouse a11y / SEO / perf scores ≥ Phase 6 baseline | automated | `npx --yes lighthouse <URL> --quiet --chrome-flags="--headless" --output=json` — assert a11y ≥ 95, SEO ≥ 95, perf ≥ 90 (mobile + desktop) | Lighthouse CI installable on demand |
| Cross-cutting | HTML validates against W3C | automated | `npx --yes html-validate docs/projects/patterns/index.html docs/projects/patterns/stock.html docs/index.html` | one-shot run |
| Cross-cutting | Stale-data banner renders when pipeline_status.completed=false | manual UAT + synthetic fixture | "Edit data.json fixture to set `pipeline_status.completed = false`; reload; verify yellow banner above controls" | manual fixture needed |
| Cross-cutting | Empty-detections state renders when data.json.detections is `[]` | manual UAT + synthetic fixture | "Use fixture data.json with empty detections array; verify empty-state card + legend still visible" | manual fixture needed |

### Sampling Rate

- **Per task commit:** Manual smoke — load both new pages in a browser, verify no console errors, scroll through table and drilldown.
- **Per wave merge:** Full UAT script + Lighthouse mobile + Lighthouse desktop + html-validate.
- **Phase gate:** Three golden-fixture snapshots (default-state, empty-state, stale-pipeline-state) reviewed visually before `/gsd-verify-work`. MNC auditor skill (per `.planning/config.json`) runs against both new HTML files.

### Wave 0 Gaps

- [ ] **`tests/uat/phase11-uat.md`** — written UAT checklist with 11 verification steps (one per row in the test map above). Not pytest; a Markdown checklist following the project's no-frontend-unit-test convention.
- [ ] **Three synthetic data.json fixtures** in `tests/fixtures/phase11/`:
  - `data-golden.json` — copy of current production data.json (40+ live detections).
  - `data-empty.json` — same shape with `"detections": []`.
  - `data-stale.json` — same shape with `pipeline_status.completed: false, failed_count: 47`.
- [ ] **Two synthetic stats.json fixtures**:
  - `stats-sparse-by-type.json` — `pin_extended.n = 5` to exercise fallback to `by_confirmation_type`.
  - `stats-all-sparse.json` — all `by_confirmation_type` cells below floor; exercise fallback to `all`.
- [ ] **One synthetic "pending" detection** appended to a fixture data.json so the drilldown can render the pending resolution path (no real-data row has `pending` today).
- [ ] **MNC Marketing Auditor invocation** — invoke the existing `.claude/skills/mnc-website-marketing-auditor/SKILL.md` against the two new HTML files before phase gate. Existing skill, no new artefact needed.

*(If `nyquist_validation` were `false` this section would be omitted, but per `.planning/config.json` it is `true` and the section is required.)*

## Security Domain

> Per `.planning/config.json`, `security_enforcement` is not explicitly set. Per default = enabled, this section is included. Phase 11 is a public read-only static frontend with no user input handling, no authentication, and no server-side state — the security surface is small but non-zero.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Public site; no auth. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | All data is public. |
| V5 Input Validation | yes (light) | Two pieces of user-controllable input: (1) the `?ticker=` query param on `stock.html` — validate against `/^[A-Z.-]{1,10}$/` before using in DOM / fetch / `document.title` to prevent XSS; (2) the search input on `index.html` — never inject as `innerHTML`, only assign to `textContent` or use as a `.indexOf()` filter operand (matches DCF screener idiom). |
| V6 Cryptography | no | No secrets in browser. |
| V7 Error Handling and Logging | yes (light) | `console.error` for fetch failures is acceptable. Never log user input back to the page. |
| V13 API and Web Service | yes (light) | All `fetch()` calls are same-origin (relative URLs). No CORS surface introduced by Phase 11. TradingView script is third-party but isolated to a single widget container; existing pattern. |
| V14 Configuration | yes | `robots.txt` already exists and allows. `Content-Security-Policy` headers are NOT set today and are not in scope for this phase (GitHub Pages serves without custom headers). |

### Known Threat Patterns for Static Vanilla JS + Iframe

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via `?ticker=AAPL<script>...</script>` reflected into the DOM | Tampering | Validate `ticker` against a strict regex before use; insert via `textContent` not `innerHTML`. The TradingView widget itself receives the ticker via JSON config (`script.textContent = JSON.stringify(config)`), which is intrinsically safe — JSON serialisation escapes script tags. |
| XSS via search input echoed back in row count or empty-state message | Tampering | Use `textContent` for any display of `searchInput.value`. Never assemble HTML from user input. (DCF screener already does this; mirror.) |
| Iframe sandboxing — parent shell trusting child postMessage | Tampering / Information Disclosure | The existing `message` listener at `docs/index.html` line 480 trusts any `event.data.type === 'navigate'` — but only accepts `project: 'calculator'` or `project: null`, both safe operations. Phase 11 adds no new message types; existing pattern continues. Hardening to validate `event.origin` is a Phase 6.x or v3 enhancement, out of scope for Phase 11. |
| Malicious `data.json` (supply-chain) injecting `<script>` into row company_name | Tampering | All row fields are inserted via `textContent` (DCF screener convention). Phase 10 is the writer and is git-controlled. Defensive in-depth: use `textContent` everywhere. |
| Third-party JS (TradingView, Google Fonts) compromise | Tampering | Accepted residual risk — same exposure as DCF screener has lived with since Phase 5. Mitigation would require CSP + SRI hashes — out of scope for static GitHub Pages without infrastructure changes. |
| Open redirect via DCF cross-link | Tampering | The cross-link anchor `href` is hardcoded as `'../screener/stock.html?ticker=' + encodeURIComponent(ticker)` — same-origin, ticker-validated. No external redirect surface. |

**Action item:** Add a single `validateTicker(s)` helper to `stock.html`:

```js
function validateTicker(s) {
  if (!s || typeof s !== 'string') return null;
  if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(s)) return null;
  return s;
}

var ticker = validateTicker(getQueryParam('ticker'));
if (!ticker) {
  // Render "Ticker not found" empty state — same idiom as DCF stock.html lines 707–710
}
```

The regex permits A–Z start, 0–9, period, hyphen, max 10 chars — covers all S&P 500 tickers including class suffixes (`BRK.B`, `BF.B`) and hyphenated forms (`BF-B`).

## Sources

### Primary (HIGH confidence)

- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\projects\screener\index.html` — read in full (707 lines). All token, badge, sticky-thead, sortable, search/sort, sr-only, focus-visible, skip-nav, and load-state patterns extracted verbatim.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\projects\screener\stock.html` — read full head (160 lines), TradingView block (1500–1580), chart-fallback (280–296), accessibility primitives (670–688), main-content scaffold (690–736). All analytical-dark patterns extracted verbatim.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\index.html` — read in full from line 335 onward (165 lines covering hero, projects grid, iframe shell, hash router, postMessage listener). Card markup and `projects` registry extracted verbatim.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\projects\patterns\data.json` — read first 120 lines + tail 297 lines + grep verification across full file. **Schema verified on disk against CONTEXT.md claims** — exit_reason field deviation flagged.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\projects\patterns\stats.json` — read in full (124 lines). Fallback chain keys (`pin_spring`, `mark_up_extended`, etc.) verified.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\sitemap.xml` — read in full (19 lines). Two new URL entries staged.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\docs\robots.txt` — read in full (5 lines). Allow: / confirmed; no Disallow blocks `/projects/patterns/`.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\.planning\phases\11-frontend\11-CONTEXT.md` — 269 lines. All 20 decisions D-01..D-20 mapped into User Constraints and code examples.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\.planning\phases\10-batch-pipeline\10-CONTEXT.md` — 248 lines. Phase 10 D-01..D-24 cross-referenced for upstream data contracts; D-02 schema (`status`, `entry_*`, `exit_*`, no nested `simulate_trade` object) verified against actual data.json.
- `C:\Users\zenng\Desktop\portfolio\jun-xian-project\.planning\config.json` — `nyquist_validation: true`, `commit_docs: true`, `mnc-website-marketing-auditor` skill loaded for executor/verifier. All confirmed.
- File-size measurement via PowerShell `Get-Item` against actual disk: `patterns/data.json = 85,336 bytes`, `screener/data.json = 1,225,721 bytes`, `patterns/stats.json = 3,317 bytes`, `patterns/_backtest_aggregates.json = 3,750 bytes`. Real evidence overrides CONTEXT.md's `~800 KB` estimate for screener data.json.

### Secondary (MEDIUM confidence)

- TradingView Advanced Chart widget URL stability — assumed evergreen based on multi-month proven use on `docs/projects/screener/stock.html`. Not re-verified via web request.
- Open Graph / Twitter `summary_large_image` recommended dimensions of 1200×630 — widely-cited convention. Not freshly verified against Meta's docs in this research session.

### Tertiary (LOW confidence)

- None. All claims in this research either came from direct file inspection or from CONTEXT.md (which is the user-locked decision record). No web searches were necessary because the entire phase scope is internal recombination of existing assets.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every pattern verified against live source on disk; no new dependencies introduced.
- Architecture: HIGH — system diagram traced through actual files (`docs/index.html` router → iframe → child page → `fetch()` → render).
- Pitfalls: HIGH — Pitfalls 1 (exit_reason) and 2 (data.json size) caught by direct disk verification; the rest are inherited from established conventions and Phase 6 a11y baseline.
- Data contracts: HIGH — `data.json` schema verified row-by-row; `stats.json` schema verified; one deviation from CONTEXT.md (exit_reason absent) flagged as a planning risk.
- Code examples: HIGH — all examples are verbatim copies with line-number citations, except the SVG legend (Example 7) which is the only original visual design Phase 11 produces; the planner / executor should refine bar dimensions and copy to taste.
- Validation: MEDIUM — manual-UAT-only is the established convention but means there's no executable regression suite; flagged fixtures-needed in Wave 0.
- Security: MEDIUM — passive risk analysis based on the static-site threat model; no CSP / SRI hardening proposed because GitHub Pages doesn't ship custom headers.

**Research date:** 2026-05-16
**Valid until:** 2026-07-15 (60 days — patterns and conventions stable; Phase 10 contract verified frozen; only re-verify if Phase 10 schema is changed or a new browser baseline emerges).
