# Roadmap: Personal Portfolio Website

## Overview

The project transforms an existing Flask-served intrinsic value calculator into a static portfolio site hosted on GitHub Pages. The work moves in four delivery boundaries: first standing up the static site structure and deployment pipeline, then building the portfolio home page with project cards, then wiring the calculator as the first in-page project with working navigation, and finally polishing design and performance so the site meets professional standards across all devices.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

### Milestone v1.0 — Portfolio Site

- [x] **Phase 1: Static Foundation** - Restructure project for GitHub Pages and establish deployment pipeline (completed 2026-03-23)
- [x] **Phase 2: Portfolio Shell** - Build home page with logo, bio, and project card grid (completed 2026-03-27)
- [x] **Phase 3: Calculator Integration** - Wire intrinsic value calculator as first in-page project with navigation (completed 2026-03-31)
- [x] **Phase 4: Design and Performance** - Polish styling, responsiveness, and Core Web Vitals (completed 2026-04-04)
- [x] **Phase 5: S&P 500 Stock Screener** - Add screener pipeline and frontend as second portfolio project (completed 2026-04-05)
- [x] **Phase 6: Website Marketing Revamp** - Elevate to MNC standards: SEO, OG tags, CTAs, accessibility (completed 2026-05-01)

### Milestone v2.0 — Inside Bar Pattern Scanner

- [ ] **Phase 7: Detection Engine** - Implement the algorithmic 5-bar inside bar spring detector with full ruleset and trend filters
- [ ] **Phase 8: Training Pipeline** - Generate annotated training data and train YOLOv8n model, exporting ONNX artifact
- [ ] **Phase 9: Backtesting Engine** - Compute 10-year forward-return statistics per detection with train/test split guardrail
- [ ] **Phase 10: Batch Pipeline** - Nightly GitHub Actions workflow running detection + ONNX inference and writing results
- [ ] **Phase 11: Frontend** - Pattern scanner screener page, per-stock drilldown, and portfolio home page card

## Phase Details

### Phase 1: Static Foundation
**Goal**: A deployable static site structure exists on GitHub Pages and the project is organized for future expansion
**Depends on**: Nothing (first phase)
**Requirements**: DEPLOY-01, DEPLOY-02
**Success Criteria** (what must be TRUE):
  1. Visiting the GitHub Pages URL loads a page (no 404, no broken deployment)
  2. The repository file structure separates the portfolio shell from project assets so adding a new project requires only adding files and a card entry
  3. The existing Render-hosted API is reachable from the static frontend (CORS verified)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Restructure repo into docs/ directory with portfolio shell and calculator project subfolder
- [ ] 01-02-PLAN.md — Enable GitHub Pages deployment and verify Render API CORS

### Phase 2: Portfolio Shell
**Goal**: Visitors can land on the home page, read who you are, and see the project grid
**Depends on**: Phase 1
**Requirements**: HOME-01, HOME-02, SHOW-01, SHOW-02
**Success Criteria** (what must be TRUE):
  1. The personal logo appears in the top-left corner of the home page
  2. The introduction section is visible with bio text, a list of technologies, and at least one contact link
  3. The project showcase grid is visible with at least one card displaying a title, thumbnail image, description, and category tags
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Add hero section with bio and LinkedIn link, section label, and card thumbnail support

### Phase 3: Calculator Integration
**Goal**: Visitors can click the intrinsic value calculator card and use the full calculator without leaving the site, and can return home via the logo
**Depends on**: Phase 2
**Requirements**: SHOW-03, NAV-01, NAV-02
**Success Criteria** (what must be TRUE):
  1. Clicking the intrinsic value calculator card loads the calculator UI in-page (no new tab, no full page reload)
  2. The calculator fetches stock data from the Render API and displays results identically to the standalone version
  3. Clicking the logo from inside the calculator view returns the visitor to the home page
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Implement hash routing, iframe calculator embed, and logo home link
- [x] 03-02-PLAN.md — Deploy and verify CORS on live GitHub Pages site

### Phase 4: Design and Performance
**Goal**: The site looks and feels professional on all screen sizes and loads fast enough to pass Core Web Vitals
**Depends on**: Phase 3
**Requirements**: PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):
  1. The site renders correctly and is usable on mobile (320px), tablet (768px), and desktop (1280px+) viewports
  2. The visual design uses consistent whitespace, typography, and color so the overall impression is clean and modern
  3. Lighthouse LCP is under 2.5s and images are optimized (compressed, correct format, lazy-loaded where appropriate)
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Responsive layout (full-width main, 1200px card grid cap), mobile breakpoint at 640px, fade view transition, card hover lift
- [x] 04-02-PLAN.md — Title tag and bio rewrite, WebP thumbnail conversion with picture element, lazy loading, Lighthouse LCP verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11

### Milestone v1.0 Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Static Foundation | 2/2 | Complete   | 2026-03-23 |
| 2. Portfolio Shell | 1/1 | Complete   | 2026-03-27 |
| 3. Calculator Integration | 2/2 | Complete   | 2026-03-31 |
| 4. Design and Performance | 2/2 | Complete   | 2026-04-04 |
| 5. S&P 500 Stock Screener | 2/2 | Complete   | 2026-04-05 |
| 6. Website Marketing Revamp | 0/3 | Not started | — |

### Phase 5: S&P 500 Stock Screener Page

**Goal:** Deliver a second portfolio project: an S&P 500 stock screener with pre-calculated DCF values, sortable/filterable table, and calculator link-through
**Depends on:** Phase 4
**Plans:** 2/2 plans complete (completed 2026-04-05)

Plans:
- [x] 05-01-PLAN.md — S&P 500 batch DCF pipeline (scripts/fetch_sp500.py + nightly GitHub Actions workflow)
- [x] 05-02-PLAN.md — Screener frontend (docs/projects/screener/index.html)

### Phase 6: Website Marketing Revamp

**Goal:** Elevate the portfolio to MNC production standards — fix SEO gaps, rewrite hero messaging to reflect the platform's true purpose (sharing useful tools with everyone), add proper CTAs, fix accessibility, and wire up Open Graph for professional sharing previews
**Depends on:** Phase 5
**Success Criteria** (what must be TRUE):
  1. Sharing the portfolio URL on LinkedIn/Slack shows a rich preview with title, description, and OG image
  2. The hero section communicates the platform's purpose (useful tools for everyone) within 3 seconds, not a career summary
  3. There is a visible, styled CTA in the hero (LinkedIn button at minimum)
  4. All interactive elements are keyboard-navigable with visible focus styles
  5. Every page has a unique `<meta name="description">` and correct heading hierarchy (single `<h1>` per page)
  6. `robots.txt` and `sitemap.xml` exist in the docs/ root
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Hero rewrite + CTA buttons (messaging, LinkedIn button, value prop)
- [x] 06-02-PLAN.md — SEO: meta descriptions, OG tags, heading hierarchy, page titles, robots.txt, sitemap.xml, canonical tags
- [x] 06-03-PLAN.md — Accessibility + UX: focus styles, card `<a>` elements, form labels, badge text, screener back-link

---

## Milestone v2.0 — Inside Bar Pattern Scanner

### Overview

Adds a computer-vision-powered inside bar spring setup scanner as a new portfolio project. The work separates three concerns strictly: offline training (algorithmic detection engine feeds YOLOv8 training), nightly inference (ONNX-only, no torch in CI), and a static frontend that reads a pre-written data.json. Phases run sequentially with Phase 9 (backtesting) depending only on Phase 7 so it could notionally overlap Phase 8, but standard granularity keeps them sequential for clarity.

### Phase Checklist (v2.0)

- [ ] **Phase 7: Detection Engine** - Implement the algorithmic 5-bar inside bar spring detector with full ruleset and trend filters
- [ ] **Phase 8: Training Pipeline** - Generate annotated training data and train YOLOv8n model, exporting ONNX artifact
- [ ] **Phase 9: Backtesting Engine** - Compute 10-year forward-return statistics per detection with train/test split guardrail
- [ ] **Phase 10: Batch Pipeline** - Nightly GitHub Actions workflow running detection + ONNX inference and writing results
- [ ] **Phase 11: Frontend** - Pattern scanner screener page, per-stock drilldown, and portfolio home page card

### Milestone v2.0 Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 7. Detection Engine | 0/? | Not started | — |
| 8. Training Pipeline | 0/? | Not started | — |
| 9. Backtesting Engine | 0/? | Not started | — |
| 10. Batch Pipeline | 0/? | Not started | — |
| 11. Frontend | 0/? | Not started | — |

## Phase Details (v2.0)

### Phase 7: Detection Engine
**Goal**: The algorithmic 5-bar inside bar spring detector exists as a standalone Python module that correctly identifies setups in historical OHLC data with no look-ahead bias
**Depends on**: Phase 6 (milestone v1.0 complete)
**Requirements**: DET-01, DET-02, DET-03, DET-04
**Success Criteria** (what must be TRUE):
  1. Running the detector on 10 years of any S&P 500 ticker produces a list of detections where each detection includes ticker, confirmation date, confirmation type (Pin / Mark Up / Ice-cream), and the 5-bar OHLC context
  2. The detector correctly identifies the spring case where the break-below bar and confirmation bar are the same bar
  3. All three trend filters (HH/HL uptrend, price above 50-SMA, cluster near 20/50-SMA retracement) are evaluated using only data available at pattern-end bar — no future bars referenced
  4. A manually reviewed sample of at least 5 known setups from historical data confirms the detector flags them and does not flag the bars immediately adjacent
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md — Detection module + Wave 0 pytest scaffold + DET-01..DET-04 unit tests (Detection dataclass, classifiers, ATR/SMA/swing pivots, detect() loop with spring case, CLI ticker validation)
- [x] 07-02-PLAN.md — Live yfinance known-setup regression suite (>=5 user-approved historical setups, adjacent-bar negative test, truncation-invariance test)

### Phase 8: Training Pipeline
**Goal**: A YOLOv8n model trained on algorithmically-annotated chart images exists as a committed ONNX artifact at `models/inside_bar_v1.onnx` and can be loaded by onnxruntime without torch
**Depends on**: Phase 7
**Requirements**: TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-04
**Success Criteria** (what must be TRUE):
  1. The chart renderer produces a 2D OHLC candlestick PNG from any yfinance DataFrame using mplfinance, with rendering style (DPI, figsize, candle width) randomised across training images to prevent style memorisation
  2. The training data generator outputs a dataset with YOLOv8 directory structure (`images/train`, `labels/train`, `data.yaml`) where negative samples are capped at 10:1 ratio relative to positives
  3. YOLOv8n training completes without out-of-memory errors, and the exported ONNX model loads successfully in onnxruntime (no torch) and produces bounding box output for a known positive test image
  4. The ONNX export opset version is logged and a round-trip test confirms inference output in a clean venv before the model is committed
**Plans**: 5 plans

Plans:
- [ ] 08-01-PLAN.md — Phase 7 detect() kwarg + split_config + Wave 0 test scaffolding + connectivity/GPU spike
- [ ] 08-02-PLAN.md — renderer.py (mplfinance Agg + 3 styles + bbox computation) + 5 unit tests
- [ ] 08-03-PLAN.md — generate_training_data.py orchestrator (cutoff, 10:1 cap, hard-negatives, manifest) + 8 unit tests
- [ ] 08-04-PLAN.md — Full S&P 500 dataset run + YOLOv8n training + ONNX export (opset 12) + commit artifacts (autonomous: false)
- [ ] 08-05-PLAN.md — verify_onnx.py clean-venv round-trip + committed fixture PNG + closeout

**UI hint**: no

### Phase 9: Backtesting Engine
**Goal**: Per-detection forward-return statistics are precomputed over 10-year history and written to a cached JSON file, with a hard train/test split preventing any in-sample leakage
**Depends on**: Phase 7
**Requirements**: BT-01, BT-02, BT-03
**Success Criteria** (what must be TRUE):
  1. The backtester computes win rate (with N count), average return %, and median hold period for each confirmation type using entry at open of confirmation+1 bar and a fixed hold period
  2. The train/test cutoff date is defined in a single shared config referenced by both `data.yaml` (training config) and the backtester — no detections from the training period appear in backtest results
  3. Results are written to `_dev/backtest_cache.json` and the file can be inspected to confirm at least one confirmation type has N >= 10 detections
**Plans**: TBD

### Phase 10: Batch Pipeline
**Goal**: A nightly GitHub Actions workflow runs the full detection and inference pipeline across S&P 500 tickers and writes results atomically so the frontend always sees a consistent data.json
**Depends on**: Phase 8, Phase 9
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04
**Success Criteria** (what must be TRUE):
  1. The workflow runs successfully end-to-end on a manual trigger, producing `docs/projects/patterns/data.json` with a `detections` array and a `pipeline_status` object containing a `completed` boolean
  2. `data.json` is written atomically via a temp-file-then-rename pattern — a simulated mid-run kill does not leave a partial JSON file visible to the frontend
  3. Annotated chart PNGs are written to `docs/projects/patterns/charts/` and stale PNGs from previous runs are deleted before new charts are written
  4. The workflow is scheduled at 07:00 UTC on weekdays and installs only onnxruntime inference dependencies (no torch, no ultralytics) at runtime
**Plans**: TBD

### Phase 11: Frontend
**Goal**: Visitors to the portfolio can see current inside bar spring detections in a filterable table, drill into any detection to see the annotated chart and backtest stats, and find the scanner via the portfolio home page card
**Depends on**: Phase 10
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. The screener page (`docs/projects/patterns/index.html`) displays a sortable, filterable table of current detections with columns for ticker, company, sector, detection date, confirmation type, confidence badge (green/yellow/red tiers), and current price
  2. A static pattern legend above the screener table explains the 5-bar structure in plain language so a first-time visitor understands what they are looking at without prior knowledge
  3. The per-stock drilldown (`docs/projects/patterns/stock.html`) shows the annotated YOLOv8 detection image, a 5-bar anatomy table with dates and OHLC per bar, and backtest stat cards (win rate with N, avg return %, median hold days)
  4. The drilldown page includes a cross-link to the DCF screener drilldown for any ticker present in the screener's `data.json`
  5. The portfolio home page displays a pattern scanner project card that navigates to the screener in-page
**Plans**: TBD
**UI hint**: yes
