# Phase 8: Training Pipeline - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

A reproducible **offline** training pipeline that consumes Phase 7's `Detection` records and produces a committed ONNX artifact at `models/inside_bar_v1.onnx` loadable by `onnxruntime` without `torch`. Concretely the phase delivers: (1) a chart renderer that produces 60-bar 2D OHLC candlestick PNGs via mplfinance with randomised rendering style; (2) a YOLOv8-format dataset generator that emits one `inside_bar_spring` bbox per positive plus background images for hard negatives, capped at 10:1 negatives:positives; (3) a YOLOv8n training script that fine-tunes from `yolov8n.pt` and exports to ONNX with a logged opset; (4) a clean-venv round-trip test using a committed test fixture before the model is committed; (5) a shared train/test split config that Phase 9's backtester will inherit. Inference orchestration, the nightly batch pipeline, backtesting forward-return computation, and any frontend rendering are explicitly out of scope.

</domain>

<decisions>
## Implementation Decisions

### Chart Framing & Bounding Box (D-01 — D-04)

- **D-01 — Window size:** Each training image renders **60 daily bars** (~3 months). Chosen to match the Phase 7 HH/HL swing-pivot lookback (CONTEXT D-05) so the model receives the same trend context the algorithmic filters used. Same window applies to positives and negatives.
- **D-02 — Bounding box extent:** Tight on the **5-bar cluster only** (mother → confirmation). Geometry: `x0 = mother bar left edge`, `x1 = confirmation bar right edge`, `y0 = min(low) over 5 bars`, `y1 = max(high) over 5 bars`. No padding on any side. Cleanest ground truth — the model learns the cluster shape, not surrounding context.
- **D-03 — Pattern position:** Pattern is **right-aligned** — the confirmation bar is the rightmost bar in the chart. Eliminates train/inference framing mismatch: at inference time the nightly pipeline (Phase 10) scans 60-bar windows ending on the most recent bar, so train and inference distributions match exactly.
- **D-04 — Output PNG dimensions:** **640 × 640 px**, the YOLOv8 native input size. Set `imgsz=640` in training config. The mplfinance figsize/DPI randomisation (per research) renders to a buffer that is then resized to 640×640 — this preserves style randomisation while giving YOLO a consistent input.

### Training Universe & Volume (D-05 — D-08)

- **D-05 — Ticker universe:** **Full S&P 500 current constituents** (~503 tickers). Matches the Phase 10 inference universe exactly. Survivor bias is documented as a known limitation in REQUIREMENTS Out of Scope and is acceptable for a portfolio piece.
- **D-06 — Date range:** **10 years** of daily history per ticker, fetched via yfinance auto_adjust (same idiom as `yahoo_finance_fetcher.py` and `scripts/pattern_scanner/detector.py.__main__`). Aligns with Phase 9's planned 10-year backtest window.
- **D-07 — Shared train/test split config (created in this phase):** Phase 8 introduces `scripts/pattern_scanner/split_config.py` (or `split_config.yaml`) exposing a single `TRAIN_TEST_CUTOFF` constant — initial **placeholder value `2024-01-01`**, leaving roughly the last ~2 years as an out-of-sample test slice. Phase 9 will validate or revise this date when designing the backtest, but the file lives in this phase from day one. Both this phase's training data generator AND the Phase 9 backtester import the same constant — single source of truth from day one. Detections with `confirmation_date >= TRAIN_TEST_CUTOFF` are excluded from the training set.
- **D-08 — Minimum positive sample threshold:** Training proceeds only when the dataset contains **≥ 1,000 positive samples** (lower bound of YOLOv8n's 1k–5k single-class range per research). If fewer, trigger a multi-style augmentation step (re-render each detection with multiple randomised styles to reach ≥ 1,000). The threshold check is part of the dataset generator script, not a separate gate.

### Negative Sampling Strategy (D-09 — D-12)

- **D-09 — Negative-to-positive ratio:** **10 : 1** (locked by TRAIN-03). Applied globally across the dataset, not per-ticker.
- **D-10 — Negative source — hard negatives only:** Negatives come from running a "filters-disabled" variant of `detect()` that skips all three trend filters but still requires the 5-bar inside-bar-spring cluster shape (mother → inside → break-below within 3 bars → confirmation type). The candidate pool is `(filters-disabled detections) − (real filtered detections)`. This forces the model to learn the trend-filter discrimination — not just "is there an inside bar". The filters-disabled variant should be implemented by adding a `apply_trend_filters: bool = True` kwarg to Phase 7's `detect()` (or a thin sibling `_detect_unfiltered()` helper) — coordinate with Phase 7 module surface.
- **D-11 — Negative framing:** Identical 60-bar right-aligned 640×640 PNG geometry as positives. Label files are **empty** (YOLO standard for background images). Single-class model — no separate "negative" class label.
- **D-12 — No per-ticker cap:** The natural distribution stands. A high-volatility ticker contributing more samples is acceptable; the 5% / 10% caps were considered and rejected to avoid losing positives below the 1,000 threshold. If post-training error analysis shows ticker-style overfit, revisit in a future iteration.

### Dataset Commit Policy & Reproducibility (D-13 — D-15)

- **D-13 — Repo artifacts:** Commit **only** (a) the trained `models/inside_bar_v1.onnx`, (b) one or two known-positive PNG fixtures in `tests/fixtures/` for the round-trip test, and (c) the `dataset_manifest.json` (see D-15). The full training dataset (~1k positives + ~10k negatives × ~50 KB ≈ 500 MB+ of PNGs) is **not** committed. Dataset is regenerable from `detect()` + a deterministic seed. No Git LFS.
- **D-14 — Generated dataset location:** Training PNGs and labels written under a gitignored directory (e.g., `_dev/training_dataset/{images,labels}/{train,val}/` and `data.yaml`). Add an entry to `.gitignore` for this directory.
- **D-15 — Dataset reproducibility — seed + manifest:** The dataset generator script accepts a `--seed` arg and is fully deterministic given (seed, ticker list, date range, `TRAIN_TEST_CUTOFF`). It writes `dataset_manifest.json` next to the generated dataset and ALSO commits a copy under `models/dataset_manifest.json`. The committed manifest records: positive count, negative count, ticker list, date range used, `TRAIN_TEST_CUTOFF` value at generation, generator seed, sha256 of every produced PNG concatenated. Anyone with the same yfinance data revision can rebuild bit-for-bit and verify by hash.

### Training Environment & Hyperparameters (D-16 — D-19)

- **D-16 — Hardware target:** Local hardware. Both CPU and GPU paths are supported (ultralytics auto-detects). Document final wall time per epoch and total training time in `08-SUMMARY.md`. No external service (Colab, cloud) — keeps the build offline-reproducible.
- **D-17 — Locked hyperparameters / model setup:**
  - Pre-trained starting weights: `yolov8n.pt` (auto-downloaded by ultralytics on first run; not committed).
  - `imgsz = 640`.
  - Single class: `inside_bar_spring`.
  - Augmentation: **disable horizontal flip** (`fliplr = 0.0`); other ultralytics defaults stand.
  - Class loss weighting: `cls_pw` (positive weight) tuned to compensate for the 10:1 imbalance.
  - ONNX export: `model.export(format="onnx", opset=<chosen>, dynamic=False)` — opset version logged to stdout AND recorded in `08-SUMMARY.md`.
- **D-18 — Claude's discretion (training):** epochs (with early-stop on val mAP plateau), batch size (`batch=-1` auto-fit or fixed integer based on hardware), learning rate schedule (default cosine), warmup epochs, train/val split ratio within the pre-cutoff data (suggest 80/20 random within train-period — time-based split not required because the train/test boundary already enforces no leakage).
- **D-19 — Round-trip test:** Before the ONNX is committed, the training script (or a separate `verify_onnx.py`) loads the exported `models/inside_bar_v1.onnx` in a clean venv that has only `onnxruntime` and `Pillow` installed (no torch, no ultralytics) and runs inference on the committed fixture PNG(s). Pass criterion: at least one bbox with confidence ≥ 0.5 returned for the known positive. Fail criterion: empty output OR import errors. The clean-venv check is run in CI for any PR that touches `models/inside_bar_v1.onnx`.

### Module Surface (D-20)

- **D-20 — New files in `scripts/pattern_scanner/`** (consistent with Phase 7's package layout):
  - `renderer.py` — mplfinance headless PNG renderer with randomised style; pure function takes a 60-bar DataFrame slice + style seed → PIL Image / PNG bytes.
  - `generate_training_data.py` — orchestrator: iterates S&P 500, calls `detect()` for positives and `detect(apply_trend_filters=False)` for the hard-negative candidate pool, applies cutoff, applies 10:1 cap, calls `renderer.py` per sample, writes YOLO directory structure and `dataset_manifest.json`. Offline only — never imported by any GitHub Actions workflow.
  - `train.py` — wraps `ultralytics.YOLO("yolov8n.pt").train(...)` with the locked hyperparameters; runs validation; calls `model.export(format="onnx", ...)`.
  - `verify_onnx.py` — clean-venv round-trip test (D-19).
  - `split_config.py` (or `.yaml`) — exposes `TRAIN_TEST_CUTOFF`.

### Claude's Discretion

- Exact mplfinance style randomisation parameters (DPI range, figsize range, candle width range, background shade variants — research suggested 3+ styles).
- Whether `split_config` is a `.py` constant or a `.yaml` file (the only requirement is that both Phase 8 and Phase 9 can import/read it).
- Internal helper function names within new modules.
- Whether `generate_training_data.py` parallelises yfinance fetches (likely yes given S&P 500 × 10y), and how — same pattern as `scripts/fetch_sp500.py` is acceptable.
- The `cls_pw` exact value and any auxiliary YOLO loss weights.
- ONNX opset version (whatever ultralytics defaults to that onnxruntime ≥ 1.18 supports — log it).
- Whether `verify_onnx.py` runs as a subprocess in a temporary venv created by the script itself, or is invoked manually before commit / via a CI job.

### Folded Todos

None — no pending todos matched Phase 8.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level
- `.planning/PROJECT.md` — Milestone v2.0 vision, scope guardrails, Out of Scope list.
- `.planning/REQUIREMENTS.md` §"Training Pipeline (offline)" — TRAIN-01..TRAIN-04 acceptance criteria.
- `.planning/ROADMAP.md` §"Phase 8: Training Pipeline" — Goal, dependencies, success criteria.

### Upstream phase contract
- `.planning/phases/07-detection-engine/07-CONTEXT.md` — Detection record schema (D-10), public API `detect(df, ticker)`, no-look-ahead invariants (D-14), confirmation type / `is_spring` semantics (D-09).
- `scripts/pattern_scanner/detector.py` — The implemented detector. Phase 8 will need a `apply_trend_filters: bool = True` switch (or a `_detect_unfiltered` sibling) added on top — coordinate with Phase 7's module API stability promise.
- `.planning/phases/07-detection-engine/07-SUMMARY.md` — What was actually delivered, including any deviations from CONTEXT.

### Research / domain knowledge
- `.planning/research/SUMMARY.md` — Stack additions (mplfinance, ultralytics in `requirements-training.txt` only; onnxruntime in `requirements.txt`), Watch Out For #1 (look-ahead bias in annotation), #2 (renderer-style memorisation → randomise DPI/figsize/candle width across 3+ styles, disable horizontal flip), #3 (ONNX opset mismatch — log opset, round-trip in clean venv), #4 (class imbalance → cap negatives 10:1, `cls_pw`).
- `C:/Users/zenng/.claude/projects/C--Users-zenng-Desktop-portfolio-jun-xian-project/memory/project_milestone2_pattern_scanner.md` — Full ruleset reference (4-day-old point-in-time observation; `07-CONTEXT.md` is authoritative where they conflict).

### Codebase pattern references (for downstream reuse)
- `scripts/fetch_sp500.py` — Reference for batch S&P 500 iteration; `generate_training_data.py` should mirror its argparse, ticker iteration, per-ticker error handling, and JSON output idioms.
- `yahoo_finance_fetcher.py` — Existing yfinance idiom (auto_adjust=True, version 0.2.65). 10y daily fetch in `generate_training_data.py` should match this style.
- `.planning/codebase/CONVENTIONS.md` — snake_case files/functions, PascalCase classes, leading underscore for private helpers, UPPER_SNAKE_CASE constants.
- `.planning/codebase/STRUCTURE.md` — Confirms `scripts/pattern_scanner/` package layout for pipeline scripts; `tests/` directory at repo root for pytest collection.
- `requirements.txt` — Phase 8 must NOT add ultralytics or torch here. Add a NEW file `requirements-training.txt` with `ultralytics>=8.2,<9.0`. Add `mplfinance>=0.12.10`, `matplotlib>=3.8`, `onnxruntime>=1.18`, `Pillow>=10.0` to the production `requirements.txt`.

### Out-of-scope-but-related (do not implement here)
- Nightly inference orchestration & GitHub Actions workflow — Phase 10.
- Backtesting forward-return computation — Phase 9 (consumes the same `TRAIN_TEST_CUTOFF`).
- Frontend screener / drilldown — Phase 11.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`scripts/pattern_scanner/detector.py` `detect()` function** — The positive-sample source. Phase 8 will extend its signature with `apply_trend_filters: bool = True` (default preserves Phase 7 contract; `False` returns the unfiltered candidate pool used for hard negatives — D-10).
- **`scripts/pattern_scanner/detector.py` `Detection` dataclass** — `bars` field (5 dicts of OHLC + date) is the renderer's input contract for positives; `mother_bar_index` and `confirmation_bar_index` define the bbox extents (D-02).
- **`scripts/fetch_sp500.py`** — Argparse, ticker iteration, per-ticker error handling, JSON output. Direct template for `generate_training_data.py`.
- **`yahoo_finance_fetcher.py`** — yfinance idiom (auto_adjust, version pin). 10y daily fetch follows the same style.
- **`tests/conftest.py` and `tests/test_detector_*.py`** — Existing pytest scaffold from Phase 7. Phase 8 will add `tests/test_renderer.py` (fixture image determinism), `tests/test_generate_training_data.py` (manifest correctness, 10:1 ratio, cutoff enforcement), and `tests/test_onnx_round_trip.py` (clean-venv ONNX inference).

### Established Patterns
- **Python conventions** — snake_case modules and functions, PascalCase classes, leading underscore for private helpers, UPPER_SNAKE_CASE module constants. CONVENTIONS.md confirms.
- **Standalone CLI per script** — Each `scripts/...` module has an `if __name__ == "__main__"` block with argparse (see `detector.py` and `fetch_sp500.py`). Phase 8 modules follow the same idiom.
- **Pure-function core, thin CLI wrapper** — `detector.py` exposes `detect()` as a pure function and a CLI on top. `renderer.py` and `generate_training_data.py` follow the same split.
- **Deterministic seeded outputs** — Phase 8 introduces a project-wide convention: any script that consumes randomness accepts `--seed` and is bit-for-bit reproducible.

### Integration Points
- **New top-level file:** `requirements-training.txt` (training-only deps; never installed by Render or any CI workflow).
- **Updated `requirements.txt`:** Adds `mplfinance>=0.12.10`, `matplotlib>=3.8`, `onnxruntime>=1.18`, `Pillow>=10.0`. Verify numpy 2.x compatibility with onnxruntime via the round-trip test (research Open Question).
- **New committed binary:** `models/inside_bar_v1.onnx` (~6–12 MB). New top-level `models/` directory.
- **New committed manifest:** `models/dataset_manifest.json`.
- **New committed fixtures:** `tests/fixtures/known_positive_*.png` (1–2 small PNGs for the round-trip test).
- **Updated `.gitignore`:** Excludes the generated `_dev/training_dataset/` directory and `yolov8n.pt` cache.
- **Phase 7 module surface:** Add `apply_trend_filters: bool = True` kwarg to `detect()` (or a sibling `_detect_unfiltered`) — must preserve Phase 7's existing call sites (CLI + the known-setup pytest suite).
- **`scripts/pattern_scanner/split_config.py`** — New shared file. Phase 9 will import from it.

</code_context>

<specifics>
## Specific Ideas

- The mismatch between **train-time framing** (right-aligned, confirmation = last bar) and **inference-time framing** (Phase 10 scanning windows ending today) is eliminated by D-03. This is the single biggest distribution-shift risk in CV-based pattern detection — the user explicitly chose the framing that makes them identical.
- **Hard negatives = filters-disabled detector minus real positives** (D-10) is a strong methodological choice: the model learns to discriminate "filtered-passing inside bar spring" from "filter-failing inside bar spring", not "pattern vs nothing". The portfolio narrative is "the model learns the same trend logic the algorithm encodes" — this decision keeps the demonstration honest.
- The placeholder cutoff `2024-01-01` in D-07 reserves ~2 years for Phase 9's out-of-sample backtest. Phase 9 may revise; the constant lives in one file from day one so revision is safe.
- The **1,000-positive gate (D-08)** is a real guardrail, not a wish. If the detector + 10y × 503 tickers + cutoff yields fewer, the dataset generator triggers multi-style augmentation before allowing training to proceed. Failure mode is loud, not silent.
- The **clean-venv round-trip test (D-19)** is the structural mitigation for research Watch-Out #3 (ONNX opset mismatch causes silent wrong output) — it is the difference between catching a broken model in CI and shipping a broken model to nightly inference.
- **No quality_score** field is added on Phase 8 detections. The YOLOv8 confidence score is the canonical confidence signal (carried forward from Phase 7 D-10 reasoning).

</specifics>

<deferred>
## Deferred Ideas

- **Multi-class YOLO (separate `spring` vs `full_5bar`)** — explicitly deferred since Phase 7 (D-09). Re-evaluate after first training run if model performance suggests separating helps recall.
- **Per-ticker sample cap** (5% or 10%) — considered and deferred (D-12). Revisit only if post-training error analysis shows ticker-style overfitting.
- **Dataset committed under Git LFS** — rejected as overkill (D-13). Revisit only if the seeded generator turns out non-reproducible across yfinance data revisions.
- **Cloud / Colab training** — rejected (D-16) to keep the build offline. Revisit if local training time becomes prohibitive (> 2h per run).
- **Volume bars / SMA overlays in training images** — not discussed. Pure-OHLC candle images are the baseline. Adding overlays could be a Phase 8.5 / iteration-2 experiment if recall is poor.
- **Time-based train/val split inside the pre-cutoff data** — not adopted (default is random 80/20). Reconsider if val metrics are misleadingly optimistic relative to Phase 9's out-of-sample test.
- **YOLOv8s upgrade if YOLOv8n under-fits** — research Confidence Assessment flagged this. Adds ~16 MB to the repo; revisit only if YOLOv8n recall is unacceptable.

### Reviewed Todos (not folded)

None — no pending todos were reviewed in this discussion.

</deferred>

---

*Phase: 08-training-pipeline*
*Context gathered: 2026-05-02*
