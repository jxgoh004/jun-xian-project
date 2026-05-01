# Research Summary: Inside Bar Pattern Scanner (v2.0)

**Project:** Inside Bar Pattern Scanner -- Milestone v2.0
**Domain:** CV-based technical analysis pattern detector with algorithmic backtesting
**Researched:** 2026-05-01
**Confidence:** HIGH

---

## Executive Summary

The Inside Bar Pattern Scanner is a batch pipeline that detects a specific 5-bar price action setup across S&P 500 constituents, validates detections using a trained YOLOv8n model, and publishes results to a static screener page -- a sister tool to the existing DCF screener. The canonical approach separates three concerns strictly: (1) offline training, which requires PyTorch/ultralytics and runs manually on local hardware; (2) nightly inference, which uses only onnxruntime (~15 MB, CPU) and runs in GitHub Actions; and (3) the frontend, which reads a pre-written data.json with no live API calls. All three layers are validated by analogous components in this codebase -- the nightly screener workflow, the static data.json pattern, and the existing screener/stock.html pages provide direct reuse targets.

The recommended technology additions are minimal: mplfinance for chart rendering, onnxruntime for inference, Pillow for image preprocessing, and a requirements-training.txt separating ultralytics from the production environment. The critical architectural decision is keeping ultralytics and torch out of requirements.txt entirely -- training is a one-time offline step that produces a committed ONNX artifact; CI only consumes that artifact. The frontend is essentially the existing screener/index.html and stock.html with detection-specific columns replacing valuation columns, requiring minimal new CSS.

The dominant risk is not engineering complexity but methodological correctness: look-ahead bias can enter through at least six independent channels (annotation timing, trend filter indexing, entry price, exit price, in-sample validation, survivor bias). Each silently inflates backtest performance with no visible error. These must be guarded at every phase, especially Phase 1 (detection engine) and Phase 3 (backtesting). Secondary risks are YOLOv8 memorising the renderer visual style rather than pattern structure, and ONNX/onnxruntime version mismatches causing silent wrong output in CI.

---

## Stack Additions

New dependencies only -- existing Flask/yfinance/pandas/numpy stack is unchanged.

| Library | Purpose | Rationale |
|---------|---------|----------|
| mplfinance>=0.12.10 | Render OHLC candlestick PNG for training + nightly annotated charts | Single call produces consistent headless PNG; accepts yfinance DataFrames directly; enforces visual consistency across training images |
| matplotlib>=3.8 | Required mplfinance backend | Pin >=3.8 for numpy 2.x compatibility (numpy 2.4.4 already installed) |
| onnxruntime>=1.18 | Run YOLOv8 inference in nightly CI pipeline | CPU-only, ~15 MB; no torch dependency; runs on GitHub Actions free tier |
| Pillow>=10.0 | PNG loading and numpy array conversion for onnxruntime input | Sufficient for all image preprocessing; avoids pulling in opencv (~200 MB) |
| ultralytics>=8.2,<9.0 | Training YOLOv8n and ONNX export | requirements-training.txt ONLY -- never in requirements.txt; pin >=8.2 for numpy 2.x compatibility |

Two-file requirements split is mandatory. requirements.txt gets the four inference libraries. requirements-training.txt (new file) gets ultralytics. Violating this installs ~3 GB of PyTorch onto Render and into every CI run.

Custom pandas backtesting uses no new library. vectorbt, backtesting.py, and ta-lib are all explicitly rejected.

---

## Feature Table Stakes

**Screener page -- must have:**
- Sortable table: ticker, company name, sector, detection date, confirmation type, confidence badge, current price
- Sector dropdown + confidence tier dropdown (High/Med/Low) + text search -- direct reuse from existing screener controls block
- Row click navigates to drilldown via URL param (pattern.html?ticker=X)
- Last-updated timestamp + results count
- Static pattern legend above the table explaining the 5-bar structure
- Mobile column hiding matching existing screener breakpoint

**Drilldown page -- must have:**
- Hero: ticker, company, price, detection date, pattern type badge, confidence tier badge, SMA context badge
- TradingView chart embed (reuse stock.html hero-right exactly)
- Annotated detection image panel -- YOLOv8 bounding box output is the primary visual proof of CV
- Pattern anatomy table: 5-bar breakdown with dates and OHLC per bar (forensic view)
- Historical performance stat cards: win rate (with N), avg return %, median hold days + entry/exit definition caption
- Cross-link footer to DCF screener drilldown if ticker present in screener data.json

**Should have (differentiators):**
- YOLOv8 confidence badge with green/yellow/red tiers (>=0.8 High, 0.6-0.8 Medium, <0.6 Low)
- SMA context badges (Near 20-SMA / Above 50-SMA) on drilldown
- Uptrend context indicator (HH/HL count, 20-SMA slope direction)

**Defer to later iteration:**
- Historical detections per ticker (requires detection history array in data.json)
- Confidence threshold slider filter (sort-by-confidence column is sufficient)
- Uptrend context panel on drilldown (filter passing is sufficient implied context for MVP)

**Anti-features -- explicitly avoid:**
- Real-time or streaming detection (daily bars; nightly batch is correct)
- Buy/sell signal labels or price targets (legal ambiguity, false authority)
- P&L simulation or equity curve (misleading; show win rate + avg return stat cards only)
- Editable pattern parameters (the encoded ruleset is the demonstration of domain knowledge)

The screener page reuses every major component from docs/projects/screener/ -- dark theme CSS variables, sticky table, controls row, panel components, badge system, loading/error states, and the static JSON data pipeline. Minimal new CSS is needed.

---

## Architecture Decisions

**Decision 1 -- ONNX model stored in repo (models/inside_bar_v1.onnx):**
YOLOv8n ONNX export is 6-12 MB, well under GitHub 100 MB limit. In-repo storage means the model is available at actions/checkout with zero extra steps, is version-tracked alongside the code, and avoids URL-fragility of GitHub Releases. Do not use Git LFS at this size. Only the .onnx is committed; the .pt checkpoint is not.

**Decision 2 -- Annotated chart PNGs stored in docs/projects/patterns/charts/:**
5-30 active detections at any time, each chart ~30-80 KB -- negligible repo footprint. GitHub Pages serves them as static files. Base64 in data.json is rejected (balloons JSON by ~2.4 MB for 30 detections, forcing screener table to download image data it never uses). Chart generation at page-load is rejected (adds canvas library dependency to browser).

**Decision 3 -- Single sequential GitHub Actions job, no matrix parallelism:**
Bottleneck is yfinance fetch (~4 min at 0.5 s/ticker), not inference (~50-200 ms/image). Total estimated runtime: 8-15 minutes. Schedule at 07:00 UTC (1 hour after screener at 06:00 UTC) to prevent concurrent push race on main.

**Decision 4 -- Training is offline only, never in CI:**
GPU training produces a versioned ONNX artifact committed to repo. generate_training_data.py and training scripts are never referenced by any workflow YAML. CI only consumes the pre-built ONNX.

**Decision 5 -- data.json schema uses detections array (not stocks):**
Only tickers with active detections written -- typically 5-30 entries, not 503. algo_detected and model_confidence are kept separate (algorithmic is structural ground truth; model confidence scores visual quality). Backtest stats are a nested backtest object. chart_path is a relative string for local-testing portability.

**New components:**
- scripts/pattern_scanner/detector.py -- algorithmic 5-bar ruleset; produces ground-truth labels
- scripts/pattern_scanner/renderer.py -- mplfinance headless PNG renderer; used offline and in nightly scan
- scripts/pattern_scanner/model.py -- onnxruntime wrapper; loads ONNX once as module-level singleton
- scripts/pattern_scanner/backtester.py -- pandas-only forward return computation; outputs to _dev/backtest_cache.json
- scripts/pattern_scanner/run_scan.py -- nightly orchestrator; mirrors structure of scripts/fetch_sp500.py
- scripts/pattern_scanner/generate_training_data.py -- offline only; never referenced by CI
- .github/workflows/pattern-scan.yml -- nightly cron at 07:00 UTC weekdays
- docs/projects/patterns/index.html + stock.html -- frontend screener and drilldown

---

## Watch Out For

1. **Look-ahead bias in annotation** -- The auto-annotator has the full 5-bar sequence when labeling historical data; the inference pipeline does not. Prevention: dataset generator must only annotate windows where bar_index < len(series) - 1 (all 5 bars are historically complete). At inference time, only call the model when today is the final bar and market close has passed.

2. **YOLOv8 memorises renderer style, not pattern structure** -- Single rendering config means the model learns exact candle width, padding, and background color rather than the abstract shape. Prevention: randomise DPI (72-150), figsize (6-10 in), candle width (0.4-0.8), background shade across 3+ styles during dataset generation. Disable horizontal flip augmentation (pattern is directional).

3. **ONNX opset mismatch causes silent wrong output** -- ultralytics exports opset 12 or 17 depending on version; older onnxruntime cannot load opset 17 and fails at load time or produces wrong output silently. Prevention: pin both ultralytics and onnxruntime to training-environment versions; log opset at export; add startup version assertion in model.py; test round-trip in clean venv before committing model.

4. **Class imbalance kills model recall** -- 10 years of S&P 500 data produces ~500:1 negative-to-positive ratio; model predicts no pattern universally and achieves 99.8% accuracy with near-zero recall. Prevention: cap negatives at 10:1 per ticker during dataset generation; use YOLOv8 cls_pw loss weighting in data.yaml.

5. **OOM kill mid-run leaves data.json partially written** -- GitHub Actions kills with SIGKILL on memory exhaustion; no Python exception, no stack trace. Prevention: write data.json atomically via os.rename() from a temp file; process tickers in batches of 50; write pipeline_status field with completed boolean so frontend can detect partial runs.

---

## Open Questions

| Question | Phase | How to Resolve |
|----------|-------|----------------|
| Spring (3-bar) and full (5-bar) patterns: one class label or two? | Phase 1/2 | One class is simpler; separate labels only worth it if frontend displays different icons per type. Decide before generating training data -- changing it requires full annotation regeneration. |
| What confidence threshold floors the screener? Sub-threshold detections shown with unconfirmed badge or excluded? | Phase 4/5 | Define threshold and display policy before building screener table. |
| Backtest cache: precomputed file or recomputed per nightly run? | Phase 3 | Precomputed _dev/backtest_cache.json is correct -- 10-year backtest across 500 tickers is not suitable for nightly recomputation. Refresh manually when ruleset changes. |
| How many positive training samples are sufficient? | Phase 2 | YOLOv8n typically needs 1,000-5,000 positives for a single-class detection task. Verify count after dataset generation and augment if below 500. |
| Should charts/ directory be cleaned before each nightly run to remove stale PNGs? | Phase 4 | A git rm step before writing new charts keeps the directory clean. Decide upfront to avoid accumulating stale files. |
| numpy 2.4.4 + onnxruntime compatibility confirmed? | Phase 3/4 | Test inference round-trip with current numpy before locking the pin. If it fails, pin numpy<2.0 in requirements.txt. |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core choices are well-established; version ranges from training data (Aug 2025 cutoff) -- PyPI not live-verified |
| Features | HIGH | Table stakes derived from direct codebase analysis of existing screener; reuse patterns are precise |
| Architecture | HIGH | All decisions based on deep examination of existing workflows, data contracts, and GitHub Pages constraints |
| Pitfalls | HIGH | Look-ahead bias, class imbalance, ONNX versioning, and OOM patterns are well-documented ML engineering risks |

**Overall confidence: HIGH**

**Gaps to address:**
- numpy 2.4.4 + onnxruntime compatibility needs a live round-trip test before committing the pipeline
- Training dataset positive sample count unknown until dataset generation runs -- may require augmentation strategy adjustment
- YOLOv8n vs. YOLOv8s model size trade-off should be evaluated after initial training (nano may have insufficient capacity; small adds ~16 MB to repo)

---

*Research completed: 2026-05-01*
*Ready for roadmap: yes*

