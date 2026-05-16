---
phase: 11-frontend
subsystem: ui
tags: [frontend, vanilla-js, github-pages, screener, drilldown, tradingview, svg-legend, sitemap, og-image, accessibility, seo, analytical-dark, github-blue]

# Dependency graph
requires:
  - phase: 10-batch-pipeline
    provides: "docs/projects/patterns/data.json (~44 detections, atomic-written nightly, with full simulate_trade resolution and pipeline_status.completed flag); stats.json (D-13 fallback chain by_type_x_spring → by_confirmation_type → all); annotated chart PNGs in charts/{TICKER}_{DATE}.png"
provides:
  - "docs/projects/patterns/index.html — sortable/filterable screener with 5-bar SVG legend, Pattern Quality + Status badges, status filter chips, stale banner, empty state (761 lines)"
  - "docs/projects/patterns/stock.html — per-stock drilldown with annotated PNG hero (LCP), TradingView daily candles, 5-bar OHLC anatomy, status-driven resolution card, 3-up backtest stat cards via D-13 fallback, on-demand DCF cross-link (1011 lines)"
  - "docs/projects/patterns/og-image.png — 1200×630 social-card image for both pattern pages (112 KB, from APD_2026-04-20.png)"
  - "docs/index.html third project card (Pattern Scanner, inserted first per D-17) + patterns registry entry"
  - "docs/sitemap.xml entries for both new pattern pages"
  - "Reusable tierFor(yolo_conf) tier function (inclusive >= boundaries, 0.50 / 0.25) — copied verbatim by sibling drilldown page"
  - "Status normalisation idiom (row.status || '').toLowerCase() — Pitfall 5 mitigation"
affects: [marketing surface for LinkedIn/Twitter previews, SEO discovery, future PAT2-* enrichments will plug into these shells]

# Tech tracking
tech-stack:
  added: []  # zero new runtime dependencies — verbatim recombination of existing portfolio CSS/HTML/JS patterns
  patterns:
    - "Inline <style> + inline <script> per page (no external CSS, no bundler) — matches DCF screener convention"
    - "ES5-idiom vanilla JS (var + function expressions) — matches existing portfolio convention"
    - "Inline SVG legend band with <title>+<desc> for a11y (new pattern; first appearance in the portfolio)"
    - "Status filter chips as real <button> with aria-pressed (radio-style toggle) — new component pattern"
    - "Stale-data banner driven by pipeline_status.completed (new pattern; data-confidence surface)"
    - "On-demand cross-resource fetch with silent absence (DCF cross-link, UI-04) — new opportunistic-feature pattern"
    - "LCP override on hero image: loading=eager + fetchpriority=high while keeping D-20 lazy default elsewhere"
    - "D-13 stats fallback chain (specific → general) gated by n_floor=10"
    - "Letterboxed og-image generation (PIL thumbnail + brand-coloured canvas) — new pattern usable for future projects"

key-files:
  created:
    - "docs/projects/patterns/index.html (761 lines)"
    - "docs/projects/patterns/stock.html (1011 lines)"
    - "docs/projects/patterns/og-image.png (1200×630, 112 KB)"
  modified:
    - "docs/index.html (+16 / -2 — Pattern Scanner card inserted first; patterns registry entry)"
    - "docs/sitemap.xml (+10 / -0 — two new <url> entries)"

key-decisions:
  - "GitHub-blue index theme, analytical-dark drilldown theme — mirrors the DCF screener split (D-06) for portfolio-wide rhythm"
  - "Pattern Quality (NOT Confidence) label with absolute 0.50 / 0.25 cutoffs (D-01, D-02) — 'how textbook is this shape' framing, with the cutoff revisitable after ~30 nightly runs"
  - "Always-visible 5-bar SVG legend band above the controls (D-04, D-05) — first-time visitor learns the rule without clicking; confirmation types deferred to column tooltips"
  - "PNG hero above TradingView on drilldown (D-07) — the algorithmic 5-bar bbox is the page's hero artefact and the LCP candidate"
  - "TradingView interval='D' (D-08 flip from analog's 'W') — pattern scanner is bar-by-bar; weekly compresses inside-bar shape"
  - "exitCopy() derived from {status, exit_date, exit_price} (Pitfall 1) — exit_reason is a phantom field; code-level prohibition enforced via plan-level lint gate"
  - "DCF cross-link via on-demand fetch with silent absence (D-14) — defensive; today 44/44 pattern tickers are in DCF data"
  - "Stale-data banner driven by pipeline_status.completed (D-15) — only shown when nightly run flagged incomplete"
  - "Pattern Scanner card inserted FIRST in the home grid (D-17) — newest project surfaces first to recruiters"
  - "og-image source = APD_2026-04-20.png (yolo_conf=0.5516, first green-tier detection); letterboxed on #080c12 background (D-18)"

patterns-established:
  - "Two-theme portfolio split is canonical: tables/index pages = GitHub-blue (#0d1117); drilldowns/moat = analytical-dark (#080c12)"
  - "Inline SVG legend band with viewBox / <title> / <desc> / 480px caption-only fallback — reusable for any future first-impression diagram"
  - "Status filter chip strip with 5 radio-style <button> + aria-pressed + live counts from the full dataset — reusable component"
  - "Drilldown LCP discipline: eager + fetchpriority=high + explicit width/height on hero, lazy default everywhere else"
  - "Plan-level forbidden-string scan (PowerShell -match for exit_reason) as a lint gate during verification — catches phantom-field reintroduction"

requirements-completed: [UI-01, UI-02, UI-03, UI-04, UI-05]

# Metrics
duration: "~75 min total (Plan 11-01 ~30 min + Plan 11-02 ~25 min + Plan 11-03 ~20 min)"
completed: 2026-05-16
---

# Phase 11: Frontend Summary

**Inside Bar Pattern Scanner is now a fully discoverable portfolio project: sortable/filterable screener with first-time-visitor 5-bar SVG legend, per-stock drilldown with annotated PNG hero and TradingView daily candles and D-13-fallback backtest stats, plus a home-page card (inserted first), social-card og-image, and sitemap entries — completing the v2.0 milestone end-to-end.**

## Performance

- **Duration:** ~75 min across three plans (Plan 11-01 ~30 min · Plan 11-02 ~25 min · Plan 11-03 ~20 min)
- **Started:** 2026-05-16 (session)
- **Completed:** 2026-05-16
- **Plans:** 3 / 3
- **Tasks:** 7 (2 + 2 + 3 across the three plans)
- **Files created:** 3 (2 HTML pages + 1 PNG asset)
- **Files modified:** 2 (`docs/index.html` + `docs/sitemap.xml`)

## Accomplishments

### Plan 11-01 — Screener index (UI-01, UI-02)
- `docs/projects/patterns/index.html` (761 lines) — single-file static page rendering today's 44 detections sorted by `confirmation_date` desc.
- 8-column sortable table: ticker, company, sector, confirmation date, confirmation type, **Pattern Quality** badge (4-tier: clean ≥0.50 / standard ≥0.25 / loose / dash for null), current price, **Status** badge (green target / red stop / blue open / grey pending).
- Always-visible inline SVG legend band (viewBox `0 0 600 140`) with 5 labelled candle figures and a mother-low dashed reference line; collapses to caption-only below 480px.
- 5-chip status filter strip (All / Open / Target / Stop / Pending) with live counts from the full dataset, radio-style `aria-pressed`, accent-tinted active state.
- Stale-data banner (`role="status" aria-live="polite"`) wired to `pipeline_status.completed === false`, with `failed_count` surfaced.
- Empty-state card when `detections.length === 0` (legend stays visible — visitors still learn the pattern).
- Phase 6 accessibility baseline: skip-nav to `#detection-table`, single `<h1>`, sr-only labels on search + sector controls, `aria-sort` on every header, badge text paired with colour (never colour-only), `:focus-visible` ring.

### Plan 11-02 — Per-stock drilldown (UI-03, UI-04)
- `docs/projects/patterns/stock.html` (1011 lines) — analytical-dark drilldown cloned verbatim from `docs/projects/screener/stock.html`.
- Three parallel fetches via `Promise.all`: `./data.json` (find detection by `?ticker=`), `./stats.json` (D-13 fallback chain), `../screener/data.json` (on-demand DCF cross-link check).
- Hero band with status-driven glow (`glow-green` / `-red` / `-blue` / `-yellow`), Status pill + Pattern Quality pill + filter pills (Trend ✓ / Above 50-SMA ✓ / Cluster ✓), ticker badge, company name, sector / industry, current price.
- Annotated PNG hero with explicit `loading="eager"` + `fetchpriority="high"` + `decoding="async"` + explicit `width`/`height` — LCP-optimised (Pitfall 7).
- TradingView Advanced Chart widget with `interval: 'D'` (daily, flipped from analog's 'W' per D-08), `script.onerror` fallback intact.
- 5-bar OHLC anatomy table (Mother / Inside / Break / Confirm / Continuation) reading `detection.bars[]`.
- Status-driven Trade Resolution card with derived `exitCopy()` headline (never reads `exit_reason` — Pitfall 1 phantom field).
- 3-up Backtested Outcomes stat cards (Win Rate with N · Avg Return R · Median Hold Days) sourced via D-13 fallback chain (`by_type_x_spring` → `by_confirmation_type` → `all`, n_floor=10), with subtitle disclosing the actual cut used ("Based on N=710 out-of-sample ice_cream detections").
- DCF cross-link card "View DCF analysis for {TICKER} →" rendered only when the ticker is present in `../screener/data.json` (silent absence per D-14).
- Static `<title>` = `Inside Bar Pattern Detail | Goh Jun Xian` (Pitfall 3); JS rewrites `document.title` to `{TICKER} — {company_name} | Pattern Scanner` after data loads.
- Native `<a href="index.html">` back-link — works iframed AND direct-deep-link (Pitfall 4).

### Plan 11-03 — Portfolio shell wiring (UI-05)
- `docs/index.html` (+16 / -2): Pattern Scanner card inserted FIRST in the `.projects` grid (D-17 order: patterns → screener → calculator); `patterns: 'projects/patterns/index.html'` added as the first key in the `var projects = { ... }` registry. Hash router and `postMessage` handler untouched.
- `docs/projects/patterns/og-image.png` (1200×630, 112 KB): letterboxed render of `charts/APD_2026-04-20.png` (yolo_conf=0.5516, first green-tier detection in document order) on `#080c12` brand background.
- `docs/sitemap.xml` (+10 / -0): two new `<url>` entries — `/projects/patterns/` (priority 0.8, changefreq daily) and `/projects/patterns/stock.html` (priority 0.7, changefreq daily). Total 5 URLs; remains valid XML.
- `docs/robots.txt` verified permissive (`Allow: /`, no `Disallow` rules) — no change needed.
- Human-verify checkpoint walked through 20 visual + interaction + SEO + console + responsive checks. **APPROVED.** (Four user-flagged items were check-interpretation misunderstandings, not code defects — captured in Plan 11-03 SUMMARY for future-self context.)

## Requirements Completed (UI-* contract)

| Req | Description | Status | Where |
|-----|------------|--------|-------|
| UI-01 | Pattern scanner page with sortable/filterable detections table | Complete | Plan 11-01 → `docs/projects/patterns/index.html` |
| UI-02 | Static pattern legend explaining the 5-bar structure | Complete | Plan 11-01 → inline SVG legend band |
| UI-03 | Per-stock drilldown with hero, TradingView, annotated PNG, anatomy table, stat cards | Complete | Plan 11-02 → `docs/projects/patterns/stock.html` |
| UI-04 | Drilldown cross-link to DCF screener for tickers present in screener data.json | Complete | Plan 11-02 → on-demand fetch with silent absence |
| UI-05 | Pattern scanner card on the portfolio home page | Complete | Plan 11-03 → `docs/index.html` card + registry entry |

All 5 UI requirements satisfied. Phase 11 is complete.

## Decisions Honoured (CONTEXT.md D-01 .. D-20)

| Decision | What it stipulates | How honoured |
|---|---|---|
| D-01 | Badge label = "Pattern Quality" (not "Confidence") | Used verbatim on screener column header + drilldown pill |
| D-02 | Tier cutoffs = 0.50 / 0.25 absolute (not percentile) | `tierFor()` uses `>= 0.50` / `>= 0.25` literals; same function copied verbatim by drilldown |
| D-03 | Badge palette reuses DCF screener green / yellow / red | Same hex (`#3fb950` / `#e3b341` / `#f85149`) and 0.15-alpha background recipe |
| D-04 | Legend = always-visible diagram band above controls | Inline SVG band (viewBox 0 0 600 140), sits between header and controls |
| D-05 | Legend scope = 5-bar structure only (no types, no filters) | Diagram shows Mother / Inside / Break / Confirm / Continuation; confirmation types appear in column only |
| D-06 | Mirror DCF theme split: blue index, analytical-dark drilldown | `#0d1117` tokens on index; `#080c12` + Syne + DM Sans + DM Mono on stock.html |
| D-07 | Hero = annotated PNG; TradingView below | PNG `<figure>` precedes TradingView mount; LCP override applied to PNG |
| D-08 | TradingView interval='D' (daily), dark theme, advanced widget | Verbatim copy of analog `initChart()`, single-field flip W → D |
| D-09 | Drilldown stack: nav → hero → PNG → TV → anatomy → resolution → stats → DCF cross-link | Implemented in this exact top-down order |
| D-10 | Dedicated coloured Status column on screener | 8th column; pill colours match the D-10 mapping |
| D-11 | 5 status filter chips above the table with live counts | All / Open / Target / Stop / Pending — counts computed once from full dataset |
| D-12 | Default sort = confirmation_date desc | `sortCol='confirmation_date'; sortDir=-1` in JS + matching `aria-sort` in HTML |
| D-13 | Stats fallback chain by_type_x_spring → by_confirmation_type → all, with cut shown in subtitle | Implemented in drilldown stat-card loader; subtitle prints "Based on N=X ..." with the actual cut |
| D-14 | DCF cross-link via on-demand fetch with silent absence | `fetch('../screener/data.json')` only on drilldown; `.catch(() => silent)`; card omitted when ticker not present |
| D-15 | Stale banner driven by pipeline_status.completed | Banner element with `role="status"`, shown only when `completed === false` |
| D-16 | Empty detections array → empty-state card; legend stays visible | Implemented; table hides, legend remains |
| D-17 | Home-page card: structure mirrors DCF card; patterns first in suggested order | Card markup matches; insertion is first child of `.projects`; registry has patterns as first key |
| D-18 | Full SEO/OG/Twitter meta stack on both pattern pages; og-image.png; sitemap entries | Meta tags in both heads (canonical, og:*, twitter:*); 112 KB 1200×630 og-image; 2 sitemap URLs |
| D-19 | Phase 6 a11y baseline: keyboard nav, focus rings, semantic HTML, sr-only labels, badge text | Skip-nav, single `<h1>`, sr-only labels, aria-pressed chips, aria-sort headers, focus-visible ring, badge label+colour |
| D-20 | Performance budget matches Phase 6: lazy PNG, async TradingView, inline CSS, LCP < 2.5s | All hero images lazy by default; TradingView async; inline `<style>`; LCP override on drilldown hero PNG |

All 20 CONTEXT decisions honoured. No deferrals.

## Pitfall Mitigations (1 .. 8)

| Pitfall | Mitigation | Verification |
|---|---|---|
| 1 — `exit_reason` is a phantom field (never present in `data.json`) | `exitCopy()` derives entirely from `status` + `exit_date` + `exit_price` + `entry_date` + `hold_days`; no read of `.exit_reason` anywhere in the JS | Grep for `\.exit_reason` returns 0 code matches in stock.html (only one explanatory comment); plan-level lint gate codified |
| 2 — DCF `data.json` is ~1.23 MB (do not fetch on screener index) | Fetch happens ONLY inside `maybeShowCrossLink()` on the drilldown; never invoked from index.html | One `fetch('../screener/data.json')` site in stock.html; zero in index.html |
| 3 — Static `<title>` must survive no-JS crawlers | HTML `<title>` is the static crawlable string; JS rewrites `document.title` only AFTER fetch resolves | `<title>Inside Bar Pattern Detail \| Goh Jun Xian</title>` present in source; document.title overwrite happens after Promise.all resolves |
| 4 — Back-link must work iframed AND direct-deep-link | Native `<a href="index.html">` (no postMessage, no JS handler) — browser handles both modes | Anchor element in stock.html top nav; works from inside the portfolio shell iframe and from a direct browser visit |
| 5 — `status` casing inconsistency | All comparisons go through `(row.status \|\| '').toLowerCase()` | 4+ `.toLowerCase()` call sites at every status-comparison point (filter chips, badge class, hero glow class, resolution card outline) |
| 6 — Legend band crowds the table on small screens | 480px breakpoint hides the SVG and shows the caption only | `@media (max-width: 480px)` rule hides `.legend-svg` and keeps `.legend-caption` |
| 7 — Annotated PNG is the LCP candidate on drilldown | `loading="eager"`, `fetchpriority="high"`, `decoding="async"`, explicit `width`/`height` — hard-coded in HTML, never overridden by JS | All 4 attributes present in the `<img>` tag inside `.annotated-hero` |
| 8 — Inclusive `>=` boundaries on Pattern Quality tiers | `tierFor()` uses `>= 0.50` and `>= 0.25` exactly (not `>` strict) so the boundary values land in the higher tier | Both literals present in `tierFor()` on both index.html and stock.html |

All 8 RESEARCH-flagged pitfalls mitigated and verified.

## File Inventory

### Created (3)

| File | Lines / Size | Purpose |
|---|---|---|
| `docs/projects/patterns/index.html` | 761 lines | Screener page — table + legend + chips + stale banner |
| `docs/projects/patterns/stock.html` | 1011 lines | Drilldown — hero, PNG, TradingView, anatomy, resolution, stats, DCF link |
| `docs/projects/patterns/og-image.png` | 1200×630, 112 KB | Social-card image (LinkedIn / Twitter preview) for both pages |

### Modified (2)

| File | Δ | Purpose |
|---|---|---|
| `docs/index.html` | +16 / -2 | Third project card (inserted first) + registry entry `patterns: 'projects/patterns/index.html'` |
| `docs/sitemap.xml` | +10 / -0 | Two new `<url>` entries for `/projects/patterns/` and `/projects/patterns/stock.html` |

### Verified, unchanged

| File | Status |
|---|---|
| `docs/robots.txt` | Already permissive (`Allow: /`, no `Disallow` rules) — no edit required |

## All Commits (Phase 11)

Per the user's `git-attribution-guard` rule, no AI co-author trailer on any commit. All authored as `Goh Jun Xian <zenn.goh.is@hotmail.com>`.

### Plan 11-01
- `f9dda75` — `feat(11-01): scaffold patterns/index.html — head, theme, header, legend SVG, controls strip, table skeleton`
- `81a44bc` — `feat(11-01): wire data load + render + filter + sort for patterns/index.html`
- `5f2c113` — `docs(11-01): complete patterns screener index plan`

### Plan 11-02
- `acce6a7` — `feat(11-02): scaffold patterns drilldown page (stock.html)`
- `3c0f7b5` — `feat(11-02): wire drilldown JS — fetch, render, TradingView (interval D)`
- `8ae4656` — `docs(11-02): complete patterns drilldown plan`

### Plan 11-03
- `93c4af4` — `feat(11-03): add Pattern Scanner card and registry entry to portfolio home`
- `419927e` — `feat(11-03): export patterns og-image and register URLs in sitemap`
- (this commit) — `docs(11-03): complete portfolio shell wiring plan + phase SUMMARY`
- (next commit) — `chore(11): mark phase 11 complete in state/roadmap/requirements`

## Deferred Follow-ups

Carried forward from CONTEXT.md Deferred Ideas + individual plan SUMMARYs. None blocking.

1. **Revisit Pattern Quality tier cutoffs after ~30 nightly runs** — current cutoffs (`>= 0.50` green, `>= 0.25` yellow) are conservative absolutes. Once an empirical histogram of `yolo_conf` exists across ~30 nightly cron runs, the planner may tighten (e.g., 0.60 / 0.30) or switch to percentile-based. One-line change to `tierFor()` constants in both `index.html` and `stock.html`.
2. **Real card thumbnail PNG for `docs/index.html`** — Plan 11-03 ships the Pattern Scanner card with the existing `.card-thumbnail-placeholder` CSS gradient and a TODO. A real screenshot or export from one annotated `charts/*.png` (the most visually striking textbook example) can replace the placeholder when one is judged compelling enough. Same pattern as the screener / calculator cards.
3. **ONNX-aware re-scoring of Phase 9 backtest cache** — a ~5-minute one-shot would let `stats.json` carry tier-stratified aggregates ("win-rate when Pattern Quality is green"). Flagged in Phase 9 SUMMARY and Phase 10 D-12 as a Phase 11+ enrichment. Would make the screener's "audit accuracy" narrative even stronger (visitors could see whether the model's high-quality picks actually win more) without changing the frontend contract beyond a stats-card subtitle tweak.
4. **YOLO output bbox overlay on the annotated PNG** — Phase 10 D-13 chose algorithmic bbox only. A future enrichment could draw the model's bbox dashed alongside the algorithmic one to demonstrate visual agreement. Adds bbox-decoding complexity in the renderer; not a Phase 11 concern.
5. **PAT2-*** (Pattern Scanner Iteration 2 — REQUIREMENTS.md deferred section): confidence threshold slider on the screener (PAT2-02), historical detections per ticker (PAT2-01), uptrend context panel on drilldown (PAT2-03), additional confirmation bar types beyond Pin / Mark Up / Ice-cream (PAT2-04).
6. **Cross-link FROM DCF drilldown back TO pattern drilldown** — UI-04 only covers patterns → DCF. Symmetric link would require modifying `docs/projects/screener/stock.html` to fetch `docs/projects/patterns/data.json` and check inclusion. Out of Phase 11 scope; worth a separate small phase if the symmetry feels natural.

## User Setup Required

None — pure static-site delivery. No environment variables, no external services, no deployment configuration beyond the standard GitHub Pages push-to-main. The screener and drilldown read `./data.json` / `./stats.json` / `charts/*.png` written nightly by Phase 10's already-running GHA workflow.

## Roadmap Completion

**Milestone v2.0 — Inside Bar Pattern Scanner: COMPLETE.**

| Phase | Status | Completed |
|-------|--------|-----------|
| Phase 7. Detection Engine | Complete | 2026-05-01 |
| Phase 8. Training Pipeline | Complete | 2026-05-08 |
| Phase 9. Backtesting Engine | Complete | 2026-05-10 |
| Phase 10. Batch Pipeline | Complete | 2026-05-15 |
| Phase 11. Frontend | **Complete** | **2026-05-16** |

Phase 11 satisfies all five ROADMAP success criteria:
1. ✅ Screener page displays a sortable, filterable detections table (UI-01)
2. ✅ Static pattern legend explains the 5-bar structure (UI-02)
3. ✅ Drilldown shows annotated chart + 5-bar anatomy + backtest stats (UI-03)
4. ✅ Drilldown cross-links to DCF screener (UI-04)
5. ✅ Portfolio home page displays a pattern scanner card that navigates in-page (UI-05)

End-to-end, the Inside Bar Pattern Scanner is a working portfolio project: visitors land on `jxgoh004.github.io/jun-xian-project/`, click the first card, see today's detections with quality / status / price, drill into any row to see the algorithmic 5-bar bbox + live TradingView chart + backtested outcomes, and cross-link to the DCF analysis for the same ticker. The marketing surface (og-image, sitemap, robots) is wired for LinkedIn / Twitter / search-engine discovery.

## Verification Status

| Check | Result |
|-------|--------|
| All 5 UI-* requirements satisfied | PASS |
| All 20 CONTEXT D-* decisions honoured | PASS (no deferrals) |
| All 8 RESEARCH pitfalls mitigated | PASS (verified per-plan) |
| Three plans complete (11-01, 11-02, 11-03) | PASS |
| All per-task commits authored by `Goh Jun Xian <zenn.goh.is@hotmail.com>` (no AI trailer) | PASS |
| End-to-end browser walkthrough on `python -m http.server 8000 --directory docs` (20 checks) | PASS (APPROVED) |
| Phase 11 marks completion of Milestone v2.0 | PASS |

## Self-Check: PASSED

- FOUND: `docs/projects/patterns/index.html` (761 lines).
- FOUND: `docs/projects/patterns/stock.html` (1011 lines).
- FOUND: `docs/projects/patterns/og-image.png` (112 464 bytes, 1200×630).
- FOUND: `docs/index.html` modified by `93c4af4`.
- FOUND: `docs/sitemap.xml` modified by `419927e`.
- FOUND commits `f9dda75`, `81a44bc`, `5f2c113` (Plan 11-01).
- FOUND commits `acce6a7`, `3c0f7b5`, `8ae4656` (Plan 11-02).
- FOUND commits `93c4af4`, `419927e` (Plan 11-03 implementation).

---
*Phase: 11-frontend*
*Completed: 2026-05-16*
