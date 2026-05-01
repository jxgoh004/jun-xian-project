# Requirements: Personal Portfolio Website

**Defined:** 2026-03-18 (v1.0) · **Updated:** 2026-05-01 (v2.0)
**Core Value:** Visitors quickly understand who I am as a developer and interact with my working projects in a professional, accessible, single-page experience.

## v1.0 Requirements (Validated)

### Home Page
- [x] **HOME-01**: Home page displays personal logo in top-left corner
- [x] **HOME-02**: Home page includes introduction section with bio, skills/technologies, and contact links

### Project Showcase
- [x] **SHOW-01**: Home page displays project showcase section with visual card grid
- [x] **SHOW-02**: Each project card shows title, thumbnail image, description, and category tags
- [x] **SHOW-03**: Intrinsic value calculator is integrated as the first featured project

### Navigation
- [x] **NAV-01**: Clicking a project card loads that project running in-page (no new tab/window)
- [x] **NAV-02**: Clicking the logo returns user to home page from any project view

### Design & Performance
- [x] **PERF-01**: Site uses modern, clean aesthetic with whitespace and professional styling
- [x] **PERF-02**: Site is fully responsive across mobile, tablet, and desktop
- [x] **PERF-03**: Site passes Core Web Vitals (optimized images, fast loading, LCP < 2.5s)

### Deployment
- [x] **DEPLOY-01**: Site is deployable to GitHub Pages as a static site
- [x] **DEPLOY-02**: Site structure allows adding future projects via code editing

---

## v2.0 Requirements — Inside Bar Pattern Scanner

### Detection Engine

- [ ] **DET-01**: Pattern detector identifies bullish inside bar spring setups using the 5-bar ruleset (mother bar → inside bar → break-below within 3 bars → confirmation as Pin / Mark Up / Ice-cream bar)
- [ ] **DET-02**: Detector handles the spring case where break-below bar and confirmation bar are the same bar
- [ ] **DET-03**: Detector applies trend filters (HH/HL uptrend, price above 50-SMA, cluster near 20/50-SMA retracement) evaluated at the pattern-end bar with no look-ahead
- [ ] **DET-04**: Detector outputs structured detections containing ticker, confirmation date, confirmation type, and 5-bar OHLC context

### Training Pipeline (offline)

- [ ] **TRAIN-01**: Chart renderer produces consistent 2D OHLC candlestick PNGs from yfinance DataFrames using mplfinance
- [ ] **TRAIN-02**: Training data generator produces YOLOv8-format annotations from algorithmic detections, with rendering-style randomisation (DPI, figsize, candle width) to prevent renderer memorisation
- [ ] **TRAIN-03**: Training pipeline applies negative sampling capped at 10:1 to manage class imbalance
- [ ] **TRAIN-04**: YOLOv8n model is trained on the generated dataset and exported as ONNX (opset version logged) to `models/inside_bar_v1.onnx`

### Backtesting Engine

- [ ] **BT-01**: Backtester computes 10-year forward-return stats per detection using a fixed entry rule (open of confirmation+1) and fixed hold period
- [ ] **BT-02**: Backtester enforces a hard time-based train/test split shared between training config and backtest config to prevent in-sample leakage
- [ ] **BT-03**: Backtester outputs win rate (with N), avg return %, and median hold period to a cached JSON file (`_dev/backtest_cache.json`)

### Batch Pipeline

- [ ] **PIPE-01**: Nightly GitHub Actions workflow fetches OHLC data, runs algorithmic detection, runs YOLOv8 ONNX inference, and writes results
- [ ] **PIPE-02**: Pipeline writes `data.json` atomically (temp file + rename) with a `pipeline_status` field so the frontend can detect partial runs
- [ ] **PIPE-03**: Pipeline writes annotated chart PNGs to `docs/projects/patterns/charts/` and cleans stale PNGs before each run
- [ ] **PIPE-04**: Workflow runs at 07:00 UTC on weekdays (1h after the DCF screener) using only inference dependencies (onnxruntime, no torch)

### Frontend

- [ ] **UI-01**: Pattern scanner page (`docs/projects/patterns/index.html`) shows a sortable, filterable table of current detections — ticker, company, sector, detection date, confirmation type, confidence badge, current price
- [ ] **UI-02**: Static pattern legend above the table explains the 5-bar structure for first-time visitors
- [ ] **UI-03**: Per-stock drilldown (`docs/projects/patterns/stock.html`) shows hero (ticker/company/badges), TradingView chart, annotated YOLOv8 detection image, 5-bar pattern anatomy table, and backtest stat cards (win rate, avg return, median hold)
- [ ] **UI-04**: Drilldown cross-links to the DCF screener drilldown when the ticker is present in screener `data.json`
- [ ] **UI-05**: Pattern scanner is added as a project card on the portfolio home page

---

## Future Requirements (Deferred)

### Polish
- **POLISH-01**: Dark mode toggle with WCAG AA contrast compliance
- **POLISH-02**: Smooth animations and hover effects on cards and navigation
- **POLISH-03**: Performance badge displaying Lighthouse score

### Pattern Scanner Iteration 2
- **PAT2-01**: Historical detections per ticker (requires detection history accumulation in `data.json`)
- **PAT2-02**: Confidence threshold slider filter on the screener
- **PAT2-03**: Uptrend context panel on drilldown (HH/HL count, 20-SMA slope direction)
- **PAT2-04**: Additional confirmation bar types beyond Pin / Mark Up / Ice-cream

### Content
- **CONT-01**: Project case studies with problem/approach/outcome context
- **CONT-02**: Live GitHub activity integration showing recent commits
- **PORT-02**: Downloadable resume / link to LinkedIn

---

## Out of Scope

Explicitly excluded for v2.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time / streaming detection | Daily bars; nightly batch is methodologically correct |
| Buy/sell signal labels or price targets | Legal ambiguity; false authority for a portfolio piece |
| P&L simulation or equity curve | Misleading without proper position sizing; stat cards are sufficient |
| Editable pattern parameters in UI | The encoded ruleset IS the demonstration of domain knowledge |
| Live model inference API | Static-site architecture; pre-computed data.json is the correct fit |
| GPU training in CI | YOLOv8 training is a one-time offline step; ONNX is the deliverable |
| Survivor-bias-free constituent list | Requires paid data; documented as a known limitation in frontend |
| Separate tabs/windows for projects | Projects run in-page to maintain single-site experience |
| Backend CMS or admin panel | Will add projects by editing code with Claude |
| Authentication / user accounts | Public portfolio site, no login needed |

---

## Traceability

Updated during roadmap creation. Each v2.0 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DET-01 | Phase 7 | Pending |
| DET-02 | Phase 7 | Pending |
| DET-03 | Phase 7 | Pending |
| DET-04 | Phase 7 | Pending |
| TRAIN-01 | Phase 8 | Pending |
| TRAIN-02 | Phase 8 | Pending |
| TRAIN-03 | Phase 8 | Pending |
| TRAIN-04 | Phase 8 | Pending |
| BT-01 | Phase 9 | Pending |
| BT-02 | Phase 9 | Pending |
| BT-03 | Phase 9 | Pending |
| PIPE-01 | Phase 10 | Pending |
| PIPE-02 | Phase 10 | Pending |
| PIPE-03 | Phase 10 | Pending |
| PIPE-04 | Phase 10 | Pending |
| UI-01 | Phase 11 | Pending |
| UI-02 | Phase 11 | Pending |
| UI-03 | Phase 11 | Pending |
| UI-04 | Phase 11 | Pending |
| UI-05 | Phase 11 | Pending |

**Coverage (v2.0):**
- Total requirements: 20
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-03-18 (v1.0) · Updated: 2026-05-01 (v2.0)*
