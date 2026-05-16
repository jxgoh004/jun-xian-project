# Personal Portfolio Website

## Current Milestone

**No active milestone.** v2.0 (Inside Bar Pattern Scanner) shipped 2026-05-16. v3.0 scope is undefined — see Backlog at the bottom of this file for candidate directions.

---

## What This Is

A personal portfolio site at https://jxgoh004.github.io/jun-xian-project/ that showcases finance × AI tools Jun Xian has built. Every project encodes real domain knowledge — not API-call demos — and is reachable in-page from a single home grid.

Three projects currently live:

1. **Intrinsic Value Calculator** (Phase 3, v1.0) — DCF intrinsic-value calculator backed by a Render-hosted Flask API (yfinance + FinViz).
2. **S&P 500 Stock Screener** (Phase 5, v1.0) — Nightly batch DCF across ~500 tickers, sortable/filterable table + per-stock drilldown with spider chart.
3. **Inside Bar Pattern Scanner** (v2.0) — Nightly YOLOv8 ONNX inference on 2D OHLC chart images. Sortable screener with status filters and 5-bar legend; per-stock drilldown with annotated PNG hero, TradingView daily chart, 5-bar anatomy, resolution card, 3-up backtest stats, and on-demand DCF cross-link.

## Core Value

Visitors can quickly understand who Jun Xian is as a developer and interact with working finance × AI projects in a professional, accessible, single-page experience.

## Requirements

### Validated

<!-- v1.0 — Portfolio Site -->

- ✓ **HOME-01** — Home page displays personal logo in top-left corner — v1.0
- ✓ **HOME-02** — Home page includes introduction section with bio, skills/technologies, and contact links — v1.0
- ✓ **SHOW-01** — Home page displays project showcase section with visual card grid — v1.0
- ✓ **SHOW-02** — Each project card shows title, thumbnail image, description, and category tags — v1.0
- ✓ **SHOW-03** — Intrinsic value calculator is integrated as the first featured project — v1.0
- ✓ **NAV-01** — Clicking a project card loads that project running in-page — v1.0
- ✓ **NAV-02** — Clicking the logo returns user to home page from any project — v1.0
- ✓ **PERF-01** — Site uses modern, clean aesthetic with professional styling — v1.0
- ✓ **PERF-02** — Site is fully responsive across mobile, tablet, and desktop — v1.0
- ✓ **PERF-03** — Site passes Core Web Vitals (LCP < 2.5s) — v1.0
- ✓ **DEPLOY-01** — Site is deployable to GitHub Pages as a static site — v1.0
- ✓ **DEPLOY-02** — Site structure allows adding future projects via code editing — v1.0

<!-- v1.x — S&P 500 Screener (added mid-v1.0 milestone) -->

- ✓ S&P 500 batch DCF pipeline writing `docs/projects/screener/data.json` — v1.0 (Phase 5)
- ✓ Screener frontend with sortable/filterable table and per-stock drilldown — v1.0 (Phase 5)

<!-- v2.0 — Inside Bar Pattern Scanner -->

- ✓ **DET-01** — Pattern detector identifies bullish inside bar spring setups using the 5-bar ruleset — v2.0
- ✓ **DET-02** — Detector handles the spring case where break-below bar and confirmation bar are the same bar — v2.0
- ✓ **DET-03** — Detector applies trend filters with no look-ahead at the pattern-end bar — v2.0
- ✓ **DET-04** — Detector outputs structured detections with ticker, confirmation date, type, and 5-bar OHLC context — v2.0
- ✓ **TRAIN-01** — Chart renderer produces consistent 2D OHLC candlestick PNGs from yfinance DataFrames — v2.0
- ✓ **TRAIN-02** — Training data generator produces YOLOv8-format annotations with style randomisation — v2.0
- ✓ **TRAIN-03** — Training pipeline applies 10:1 negative-sample cap — v2.0
- ✓ **TRAIN-04** — YOLOv8n trained and exported as ONNX (opset 12) to `models/inside_bar_v1.onnx` — v2.0
- ✓ **BT-01** — Backtester computes forward-return stats with fixed entry rule (open of confirmation+1) — v2.0
- ✓ **BT-02** — Hard time-based train/test split shared between training and backtest configs — v2.0
- ✓ **BT-03** — Win rate / avg return / median hold written to `_dev/backtest_cache.json` — v2.0
- ✓ **PIPE-01** — Nightly GitHub Actions workflow runs detection + ONNX inference + writes results — v2.0
- ✓ **PIPE-02** — `data.json` written atomically with `pipeline_status` field — v2.0
- ✓ **PIPE-03** — Annotated PNG charts written to `docs/projects/patterns/charts/` with stale-PNG cleanup — v2.0
- ✓ **PIPE-04** — Workflow runs at 07:00 UTC weekdays using only onnxruntime (no torch) — v2.0
- ✓ **UI-01** — Pattern scanner page with sortable/filterable detections table — v2.0
- ✓ **UI-02** — Static 5-bar pattern legend above the table — v2.0
- ✓ **UI-03** — Per-stock drilldown with hero, TradingView chart, annotated YOLOv8 image, 5-bar anatomy, backtest stat cards — v2.0
- ✓ **UI-04** — Drilldown cross-links to DCF screener drilldown when ticker present — v2.0
- ✓ **UI-05** — Pattern scanner card on portfolio home page — v2.0

### Active

<!-- v3.0 to be defined; populate here once the next milestone is planned. -->

_None._

### Backlog / Deferred

- **POLISH-01** — Dark-mode toggle with WCAG AA contrast compliance
- **POLISH-02** — Smooth animations and hover effects on cards and navigation
- **POLISH-03** — Performance badge displaying Lighthouse score
- **PAT2-01** — Historical detections per ticker (requires history accumulation in `data.json`)
- **PAT2-02** — Confidence threshold slider filter on the screener
- **PAT2-03** — Uptrend context panel on drilldown (HH/HL count, 20-SMA slope direction)
- **PAT2-04** — Additional confirmation bar types beyond Pin / Mark Up / Ice-cream
- **CONT-01** — Project case studies with problem/approach/outcome context
- **CONT-02** — Live GitHub activity integration showing recent commits
- **PORT-02** — Downloadable resume / link to LinkedIn

### Out of Scope (still)

- Real-time / streaming detection (daily bars; nightly batch is methodologically correct)
- Buy/sell signal labels or price targets (legal ambiguity; false authority for a portfolio piece)
- P&L simulation or equity curve (misleading without proper position sizing; stat cards are sufficient)
- Editable pattern parameters in UI (the encoded ruleset IS the demonstration of domain knowledge)
- Live model inference API (static-site architecture; pre-computed `data.json` is the correct fit)
- GPU training in CI (YOLOv8 training is a one-time offline step; ONNX is the deliverable)
- Survivor-bias-free constituent list (requires paid data; documented as known limitation in frontend)
- Separate tabs/windows for projects (projects run in-page)
- Backend CMS or admin panel
- Authentication / user accounts
- Blog or article section

## Context

**Live deployment:** https://jxgoh004.github.io/jun-xian-project/ — GitHub Pages serving `docs/`.

**Three running surfaces:**

| Surface | Hosting | Stack | Updated by |
|---------|---------|-------|------------|
| Portfolio shell + DCF calculator + screener + pattern scanner | GitHub Pages (static) | Vanilla HTML/CSS/JS | Git push |
| Calculator API | Render (Flask) | Python 3, Flask 3.1.3, yfinance, FinViz scraper | Render auto-deploy on push |
| Screener `data.json` | GitHub Pages (committed by CI) | Static JSON | Nightly GHA cron 06:00 UTC weekdays |
| Pattern scanner `data.json` + `stats.json` + PNG charts | GitHub Pages (committed by CI) | Static JSON + PNG | Nightly GHA cron 07:00 UTC weekdays |

**Tech stack additions through v2.0:** YOLOv8 (offline training only; never in `requirements.txt`), onnxruntime (inference), mplfinance + matplotlib (chart rendering), Pillow (og-image generation), PyYAML (workflow lint tests), pytest (test harness across detector/backtest/renderer/generator).

**Repository layout (paperwork-relevant excerpt):**

```
.planning/
  PROJECT.md                # this file
  ROADMAP.md                # current (post-v2.0) — milestone summary
  STATE.md                  # current execution state
  MILESTONES.md             # accomplishments per milestone
  RETROSPECTIVE.md          # per-milestone postmortems
  milestones/
    v2.0-ROADMAP.md
    v2.0-REQUIREMENTS.md
    v2.0-MILESTONE-AUDIT.md
    v2.0-phases/            # 07–11 archived
```

## Constraints

- **Hosting:** GitHub Pages (static-only). Any backend (calculator API) lives on Render.
- **Navigation:** Logo top-left returns to home; projects run in-page.
- **Design:** Modern, professional, minimalist. Twin-theme convention: tables / index pages use GitHub-blue (#0d1117); drilldowns / moat use analytical-dark (#080c12).
- **CI dependencies:** Inference only. Never install `torch` or `ultralytics` in `requirements.txt`; PIPE-04 invariant pinned by a static lint test.
- **Train/test split:** `TRAIN_TEST_CUTOFF = 2024-01-01`, single source of truth in `scripts/pattern_scanner/split_config.py`, imported by both `generate_training_data.py` and `backtest.py`.

## Key Decisions

| Decision                                                                  | Rationale                                                                                                       | Outcome     |
|---------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|-------------|
| GitHub Pages for hosting                                                  | Free, reliable, integrates with git workflow, perfect for static portfolio                                      | Validated — v1.0 |
| Keep intrinsic value calculator API on Render                             | Calculator needs Python backend; GitHub Pages is static-only                                                    | Validated — v1.0 |
| Vanilla JavaScript (no framework)                                         | Existing calculator uses vanilla JS; consistency and simplicity for small site                                  | Validated — v1.0 |
| Single-page in-page navigation with hash routing + iframe                 | Clean UX, fast transitions, avoids full page reloads                                                            | Validated — v1.0 |
| Card / grid layout for projects                                            | Modern standard for portfolios; scales as projects are added                                                    | Validated — v1.0 |
| Twin-theme split: GitHub-blue for index pages, analytical-dark for drilldowns | Portfolio-wide rhythm; new theme is reserved for drilldown screens (DCF screener stock.html → moat → patterns) | Validated — v2.0 |
| YOLOv8 training is offline only; `ultralytics` never in `requirements.txt` | CI must stay torch-free; ONNX is the only deliverable for the inference path                                    | Validated — v2.0 |
| ONNX artefact committed in-repo (`models/inside_bar_v1.onnx`, ~6–12 MB, opset 12) | Smaller than 100 MB git limit; no external model registry needed for portfolio-scale traffic                | Validated — v2.0 |
| GHA cron at 07:00 UTC weekdays (1h after DCF screener at 06:00 UTC)        | Daily bars only; nightly is methodologically correct; staggered to avoid simultaneous git push pressure         | Validated — v2.0 |
| Annotated PNG charts as static assets (not base64 in JSON)                | Keeps `data.json` light, lets `<img>` cache normally, matches DCF screener's PNG-on-disk pattern                | Validated — v2.0 |
| Three-bucket trade simulation (`stop_first` / `target_first` / `open`) with intrabar-pessimistic resolution | Honest backtest framing; avoids look-ahead in same-bar resolution                                    | Validated — v2.0 |
| `TRAIN_TEST_CUTOFF = 2024-01-01` single source of truth                    | Shared between training config and backtest partition; one literal, zero leakage                                | Validated — v2.0 |
| Hard exit semantics derived from `{status, exit_date, exit_price}` (no `exit_reason` field) | Pitfall 1 — phantom-field discipline; enforced by plan-level forbidden-string lint               | Validated — v2.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated → move to Out of Scope with reason
2. Requirements validated → move to Validated with milestone reference
3. New requirements emerged → add to Active
4. Decisions to log → add to Key Decisions
5. "What This Is" still accurate? Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Out of Scope audit — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-16 after v2.0 milestone*
