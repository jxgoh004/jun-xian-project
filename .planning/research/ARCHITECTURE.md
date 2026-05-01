# Architecture Research: Inside Bar Pattern Scanner

**Project:** Inside Bar Pattern Scanner (Milestone v2.0)
**Researched:** 2026-05-01
**Research type:** Integration architecture for new pipeline component
**Confidence:** HIGH — based on deep codebase analysis of all existing workflows, scripts, and data contracts

---

## Integration Points

### What Already Exists (Unchanged)

| Component | Location | Relevance to Pattern Scanner |
|-----------|----------|------------------------------|
| yfinance OHLC fetcher | `yahoo_finance_fetcher.py` | Already fetches historical price data; `yf.download()` gives daily OHLC for any ticker |
| S&P 500 ticker list | `scripts/fetch_sp500.py` lines 134-174 | Wikipedia fetch with Chrome UA header — reuse as-is |
| Nightly GitHub Actions pattern | `.github/workflows/nightly-screener.yml` | Exact template to copy: checkout → setup-python 3.11 → pip install → run script → git commit → push |
| Static data.json pattern | `docs/projects/screener/data.json` | Envelope shape `{updated_at, stocks:[]}` — pattern to follow |
| `docs/projects/screener/` frontend | `index.html`, `stock.html` | Dark theme CSS variables, table+drilldown pattern to replicate |
| `git add` selective staging | nightly-screener.yml line 32 | Pattern: stage only the changed JSON file by path, not `git add .` |

### What Must Change

| Component | Change Required |
|-----------|----------------|
| `requirements.txt` | Add `ultralytics`, `onnxruntime`, `opencv-python-headless`, `mplfinance` (or `matplotlib` if already present) |
| `docs/index.html` | Add pattern scanner project card to project grid |
| `.gitignore` | Add `models/*.onnx` if model stored at GitHub Releases (not in repo); add `scripts/pattern_scanner/__pycache__/` |

### What Is New

| Component | Location | Purpose |
|-----------|----------|---------|
| Detection engine | `scripts/pattern_scanner/detector.py` | Algorithmic 5-bar inside bar spring ruleset |
| Chart renderer | `scripts/pattern_scanner/renderer.py` | Renders OHLC candlestick images for training + inference |
| YOLOv8 inference wrapper | `scripts/pattern_scanner/model.py` | Loads ONNX, runs inference, returns confidence + bounding box |
| Batch pipeline entry | `scripts/pattern_scanner/run_scan.py` | Orchestrates ticker loop, calls detector + model, writes data.json |
| Training data generator | `scripts/pattern_scanner/generate_training_data.py` | One-time offline script — NOT in CI |
| Nightly workflow | `.github/workflows/pattern-scan.yml` | Cron job for detection pipeline only |
| Frontend screener | `docs/projects/patterns/index.html` | Table + filters for detected setups |
| Frontend drilldown | `docs/projects/patterns/stock.html` | Annotated chart + confidence + backtest stats |
| Output data | `docs/projects/patterns/data.json` | Detection results per ticker |
| Annotated charts | `docs/projects/patterns/charts/` | Pre-rendered PNG per detection (see Decision 2) |
| ONNX model | `models/inside_bar_v1.onnx` | Stored in repo under 25MB (see Decision 1) |

---

## New Components

### `scripts/pattern_scanner/detector.py`

Pure-Python algorithmic detection. No ML dependency — this runs independently of the model and produces its own `algo_detected: true/false` flag alongside the model confidence score. The algorithmic flag is the ground truth label generator for training data.

**Responsibility:** Given a list of OHLC bars (from yfinance), apply the 5-bar inside bar spring ruleset. Return list of detection events with bar index, setup type, and computed metrics (e.g., range contraction ratio, volume ratio on spring bar).

**Inputs:** `pd.DataFrame` with columns `Open, High, Low, Close, Volume` indexed by date.
**Outputs:** List of dicts `{date, algo_detected, setup_quality_score, window_bars}`.

### `scripts/pattern_scanner/renderer.py`

Renders a fixed-size candlestick chart image for a detection window (e.g., 20 bars of context). Used both during training data generation (offline) and during inference in the nightly scan (to produce the annotated chart stored in `docs/projects/patterns/charts/`).

**Library:** `mplfinance` for candlestick rendering. Produces deterministic PNG output at fixed resolution (e.g., 640x480) suitable for YOLOv8 input.

**Key constraint:** Must run headless — no display required. Use `matplotlib` backend `Agg` explicitly (`matplotlib.use('Agg')`). This is critical for GitHub Actions which has no display server.

### `scripts/pattern_scanner/model.py`

Thin wrapper around `onnxruntime.InferenceSession`. Loads the ONNX model once (module-level singleton), runs inference on a chart image array, and returns `{confidence: float, bbox: [x,y,w,h] or None}`.

**Reason for ONNX over `.pt`:** ONNX eliminates the `torch` dependency from the inference path. The GitHub Actions runner does not need PyTorch installed at runtime — only `onnxruntime` (~15MB). Training still uses the full `ultralytics` + `torch` stack, but that is offline only.

### `scripts/pattern_scanner/run_scan.py`

Main entry point for the nightly workflow. Mirrors the structure of `scripts/fetch_sp500.py`:
- Accepts `--limit N` for local testing
- Fetches S&P 500 ticker list (reuse `fetch_sp500_tickers()` — either import or copy)
- For each ticker: fetch OHLC → run algorithmic detection → if detected, render chart → run ONNX inference → collect result
- Writes `docs/projects/patterns/data.json`
- Writes annotated chart PNGs to `docs/projects/patterns/charts/{TICKER}.png` for detections only

**Rate limiting:** Same 0.5s sleep between tickers as the screener script.

### `scripts/pattern_scanner/generate_training_data.py`

One-time offline script. Fetches 10 years of OHLC for S&P 500, runs algorithmic detector across all bars, renders chart windows, writes YOLOv8-format annotations (`labels/*.txt`, `images/*.png`). Never runs in CI. Output lives in `_dev/training_data/` (not committed — add to `.gitignore`).

---

## Data Flow

```
[GitHub Actions — nightly cron]
         |
         v
scripts/pattern_scanner/run_scan.py
         |
         |-- fetch_sp500_tickers()
         |       |
         |       v
         |   Wikipedia HTML → [AAPL, MSFT, ... ~503 tickers]
         |
         |-- for each ticker:
         |       |
         |       v
         |   yfinance.download(ticker, period="60d")
         |       → pd.DataFrame [Open, High, Low, Close, Volume]
         |
         |       |
         |       v
         |   detector.detect(df)
         |       → [{date, algo_detected, setup_quality_score, window_bars}]
         |
         |   (if algo_detected):
         |       |
         |       v
         |   renderer.render_window(df, window_bars)
         |       → PNG bytes (640x480)
         |
         |       |
         |       v
         |   model.infer(png_bytes)
         |       → {confidence: 0.87, bbox: [...]}
         |
         |       |
         |       v
         |   write chart to docs/projects/patterns/charts/{TICKER}.png
         |
         v
docs/projects/patterns/data.json
    {
      "updated_at": "2026-05-01T06:00:00Z",
      "detections": [
        {
          "ticker": "AAPL",
          "company_name": "Apple Inc.",
          "sector": "Technology",
          "detection_date": "2026-04-30",
          "algo_detected": true,
          "algo_quality_score": 0.82,
          "model_confidence": 0.87,
          "setup_type": "inside_bar_spring",
          "chart_path": "charts/AAPL.png",
          "backtest_win_rate": 0.64,
          "backtest_avg_return_pct": 4.2,
          "backtest_avg_hold_days": 8,
          "backtest_sample_n": 47,
          "current_price": 182.50,
          "wk52_high": 198.20,
          "wk52_low": 143.90
        }
      ]
    }

         |
         v
docs/projects/patterns/index.html
    (JavaScript reads data.json, renders table)
         |
    [user clicks row]
         v
docs/projects/patterns/stock.html?ticker=AAPL
    (loads data.json, filters to ticker,
     renders <img src="charts/AAPL.png">,
     shows confidence + backtest stats)
```

**Offline training flow (not in CI):**

```
scripts/pattern_scanner/generate_training_data.py
    → _dev/training_data/images/*.png
    → _dev/training_data/labels/*.txt   (YOLO format)
    → _dev/training_data/dataset.yaml

[manual on local machine with GPU or Colab]
yolo train model=yolov8n.pt data=dataset.yaml epochs=100
    → runs/detect/train/weights/best.pt

yolo export model=best.pt format=onnx
    → best.onnx → (rename) models/inside_bar_v1.onnx
    → commit to repo
```

---

## Key Decisions

### Decision 1: Where to store the ONNX model

**Recommended: In the repo under `models/inside_bar_v1.onnx`**

Rationale:
- YOLOv8n ONNX export is typically 6-12MB. GitHub's file size limit is 100MB; the soft recommendation is to stay under 50MB. A nano model is well within bounds.
- Storing in-repo means the GitHub Actions workflow has the model available at `actions/checkout` with zero extra steps. No download step, no GitHub Releases API call, no runtime failure risk if the release URL changes.
- GitHub Releases introduces a download step that can fail silently in CI if the URL changes or the release is deleted. It also complicates version tracking — you lose the ability to `git log` model version history.
- Runtime download (fetch from URL at inference time) is fragile: a network blip during the nightly job causes a silent skip of all inference results, and the job still "succeeds" unless you add explicit error handling.
- The model is a build artifact of the offline training step. It changes infrequently (once per retraining cycle). It belongs in version control alongside the code that depends on it.
- Add `models/*.onnx` to `.gitattributes` with `filter=lfs` only if size exceeds 50MB — a nano model will not.

**Rejected alternatives:**
- GitHub Releases: Extra download step in CI, URL fragility, loses git history for model.
- Runtime download: Network dependency during nightly job; silent failure mode; no version pin.
- Git LFS: Overkill at 6-12MB. LFS requires setup on every clone and adds complexity for no gain at this size.

### Decision 2: Where to store annotated chart images

**Recommended: Static PNG files in `docs/projects/patterns/charts/`**

Rationale:
- The pattern scanner only detects against the most recent 60 days of data. At any given time, the number of concurrent detections across S&P 500 is small — typically 5-30 stocks showing an inside bar spring setup. Each chart PNG at 640x480 is roughly 30-80KB. Even 50 detections = ~4MB total. This is a negligible addition to the repository.
- Static PNG in `docs/` is served directly by GitHub Pages with zero JavaScript overhead. The frontend just sets `<img src="charts/AAPL.png">`. No decoding, no canvas rendering, no base64 bloat.
- Base64 inline in data.json is rejected: A 60KB image as base64 becomes ~80KB of text embedded in JSON. If there are 30 detections, data.json balloons by 2.4MB just for images. The screener table (which does not show charts) must download all of that on first load even though it never uses it. This conflicts with the existing screener's design principle of fast first load.
- Generating charts at page-load from raw OHLC data is rejected: It requires shipping a candlestick rendering library (Chart.js financial, or a custom canvas renderer) to the browser, adds hundreds of milliseconds of render time, and makes the drilldown page depend on additional data fetches. The pre-rendered PNG approach keeps the frontend as dumb as the screener frontend.
- Stale chart handling: The nightly workflow only writes a PNG for tickers currently detected. Old charts for tickers no longer detected are simply not linked from the new data.json. The `charts/` directory will accumulate stale files over time, but this is a known trade-off — a cleanup step (`git rm docs/projects/patterns/charts/*.png` before writing new charts) can be added to the workflow when it becomes a concern.

**Rejected alternatives:**
- Base64 in data.json: JSON bloat, forces full download on table load.
- Generated at page-load: Frontend complexity, extra JS dependency, slower drilldown.
- Separate CDN: Unnecessary infrastructure for a portfolio project.

### Decision 3: GitHub Actions workflow structure for CPU-heavy inference

**Recommended: Single job, sequential processing, no matrix parallelism**

Rationale:
- `ubuntu-latest` on GitHub Actions free tier provides a 2-vCPU runner. `onnxruntime` on CPU for a YOLOv8n model runs inference in approximately 50-200ms per image depending on resolution. At 503 tickers with algorithmic pre-filtering (only ~10-30% will trigger the chart render + ONNX step), the inference load is manageable.
- The bottleneck is not inference — it is the yfinance OHLC fetch. 503 tickers × 0.5s sleep = ~4.2 minutes minimum, matching the existing screener's nightly runtime.
- Total estimated runtime: 8-15 minutes. GitHub Actions free tier allows up to 6 hours per job. No timeout risk.
- Matrix parallelism (splitting tickers across N jobs) is premature optimization for this scale. It adds complexity (artifact merging, data.json assembly across job outputs) that is not justified when a single sequential job fits comfortably within time limits.
- The workflow should explicitly pin `onnxruntime` (CPU-only package: `onnxruntime`, not `onnxruntime-gpu`) to avoid the GPU variant being pulled in on the GitHub-hosted runner where CUDA is not available.
- Use `opencv-python-headless` instead of `opencv-python` to avoid display server dependencies on the CI runner.

**Workflow skeleton:**

```yaml
name: Nightly Pattern Scan

on:
  schedule:
    - cron: '0 7 * * 1-5'   # 07:00 UTC weekdays — after screener completes at 06:00
  workflow_dispatch:

permissions:
  contents: write

jobs:
  pattern-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pattern scan
        run: python scripts/pattern_scanner/run_scan.py
      - name: Commit results
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/projects/patterns/data.json docs/projects/patterns/charts/
          git diff --staged --quiet || git commit -m "chore: nightly pattern scan update"
          git push
```

**Cron offset from screener:** Schedule at 07:00 UTC (one hour after the screener at 06:00) to avoid simultaneous pushes that could cause a merge conflict on `main`. The two workflows commit to completely different files, but concurrent pushes to the same branch still race. Staggering by 1 hour eliminates this.

### Decision 4: Training pipeline location

**Recommended: One-time offline only — never in CI**

Rationale:
- Training YOLOv8 requires PyTorch, CUDA (for reasonable speed), and hours of compute. A full training run on S&P 500 10-year data is a multi-hour job on a GPU machine or multiple hours on CPU in a Colab notebook. This is not suitable for a nightly workflow.
- GitHub Actions free tier has no GPU. CPU training of YOLOv8n for even 50 epochs on a dataset of several thousand images would take hours and consume the entire free-tier minutes budget.
- The correct separation is: training is a human-triggered, offline event that produces a versioned artifact (the ONNX file), which is then committed to the repo. The CI/CD pipeline consumes that artifact but never produces it.
- `generate_training_data.py` and any training scripts live in `scripts/pattern_scanner/` but are never referenced by any workflow YAML. They are development tools.
- Model retraining cadence: On-demand when the detection ruleset changes, enough new labeled data is collected, or model accuracy degrades. Not automated.
- Output of training: `models/inside_bar_v1.onnx` committed to repo with a semantic version bump in the filename when the model is updated (e.g., `inside_bar_v2.onnx`). The inference wrapper in `model.py` references the path by a constant, making version bumps a single-line change.

### Decision 5: data.json schema for pattern detections

**Recommended schema:**

```json
{
  "updated_at": "2026-05-01T07:00:00Z",
  "detections": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "current_price": 182.50,
      "detection_date": "2026-04-30",
      "setup_type": "inside_bar_spring",
      "algo_detected": true,
      "algo_quality_score": 0.82,
      "model_confidence": 0.87,
      "chart_path": "charts/AAPL.png",
      "backtest": {
        "win_rate": 0.64,
        "avg_return_pct": 4.2,
        "avg_hold_days": 8,
        "sample_n": 47,
        "lookback_years": 10
      },
      "setup_metrics": {
        "range_contraction_ratio": 0.61,
        "volume_ratio_spring_bar": 0.43,
        "bars_in_consolidation": 3,
        "spring_bar_close_pct": 0.78
      }
    }
  ]
}
```

**Schema rationale:**

- `detections` (not `stocks`) — the array contains only tickers with active detections, not all 503. This keeps data.json small (5-30 entries on any given night vs 503).
- `algo_detected` and `model_confidence` are kept separate. The algorithmic detector is the source of truth for whether the pattern exists structurally. The model confidence scores how visually clean the setup looks. A row with `algo_detected: true` but `model_confidence: 0.45` is a borderline setup that the user should assess with more skepticism. Merging these into a single score would hide this distinction.
- `chart_path` is a relative path string. The frontend constructs the `<img src>` as `../patterns/charts/AAPL.png` or uses a base path. Do not embed the full GitHub Pages URL — keeping it relative makes local testing work without config changes.
- `backtest` is a nested object, not flat fields. This groups the five backtest metrics together and makes the schema self-documenting. The frontend can check `if (data.backtest)` to guard against tickers whose history is too short for backtesting.
- `setup_metrics` is a nested object for the raw pattern measurements. These are displayed in the drilldown page to show the trader exactly why the pattern was flagged. They double as debugging information during model development.
- `updated_at` follows the same ISO 8601 format as the screener's `data.json` for consistency.
- Sector and industry are included to support table filtering (same filter pattern as the screener).
- No `trends` array (unlike screener data.json) — the pattern scanner drilldown does not need multi-year financial trend charts. Keeping it out reduces payload size.

---

## Suggested Build Order

### Phase 1: Data pipeline foundation

**Build first because:** Everything else depends on having reliable OHLC data flow and a working algorithmic detector. Establishing the data contract (what columns come out of yfinance, what the detector returns) gates all downstream work.

Tasks:
1. Write `scripts/pattern_scanner/detector.py` — algorithmic 5-bar inside bar spring ruleset with unit tests using synthetic OHLC fixtures
2. Extend `scripts/pattern_scanner/` with a yfinance OHLC helper (wraps `yf.download()`, handles delisted tickers gracefully)
3. Write `scripts/pattern_scanner/run_scan.py` stub — ticker loop, calls detector, writes data.json with `algo_detected` fields only (no model yet)
4. Verify on 10 tickers locally: `python scripts/pattern_scanner/run_scan.py --limit 10`

**Deliverable:** `docs/projects/patterns/data.json` written with algorithmic detection results, no model confidence yet.

### Phase 2: Training data generation and model training

**Build second because:** Requires the detector from Phase 1 as the label source. Training is offline/manual — the output (ONNX file) is what Phase 3 depends on.

Tasks:
1. Write `scripts/pattern_scanner/renderer.py` — candlestick chart renderer (mplfinance, headless, fixed 640x480)
2. Write `scripts/pattern_scanner/generate_training_data.py` — 10-year OHLC fetch, detector sweep, chart render, YOLO annotation output
3. Generate training dataset locally (this takes time — run once, store in `_dev/training_data/`)
4. Train YOLOv8n locally or in Colab: `yolo train model=yolov8n.pt data=dataset.yaml`
5. Export to ONNX: `yolo export model=best.pt format=onnx`
6. Commit `models/inside_bar_v1.onnx` to repo

**Deliverable:** `models/inside_bar_v1.onnx` committed, validated with a quick local inference test.

### Phase 3: Backtesting engine

**Build third because:** Backtest results are static per-ticker stats computed once and stored in data.json. They can be computed in a standalone pass over historical data without needing the model. The backtester can run against algorithmic detections from Phase 1 to pre-compute stats before the full pipeline is wired.

Tasks:
1. Write `scripts/pattern_scanner/backtester.py` — given a list of algorithmic detection events from historical data, compute forward returns over N-day hold periods, derive win rate and average return
2. Run backtester across 10-year history for all S&P 500 tickers
3. Write backtest results to a separate `_dev/backtest_cache.json` (keyed by ticker) — the nightly scan script reads this at startup to attach stats to current detections without re-computing 10 years each night
4. Alternatively: embed backtest stats computation in `run_scan.py` but gate it behind `--full-backtest` flag (nightly job uses cached file; manual re-run with flag refreshes the cache)

**Deliverable:** Backtest stats available for current detections in data.json.

### Phase 4: Full inference pipeline

**Build fourth because:** Requires renderer from Phase 2 (to produce chart images during the nightly scan) and ONNX model from Phase 2.

Tasks:
1. Write `scripts/pattern_scanner/model.py` — `onnxruntime` wrapper, loads model once, `infer(image_array) -> confidence`
2. Integrate renderer + model into `run_scan.py`: for each algo-detected ticker, render chart → run inference → write PNG to `docs/projects/patterns/charts/` → attach confidence to data.json record
3. Test locally: `python scripts/pattern_scanner/run_scan.py --limit 20`
4. Create `.github/workflows/pattern-scan.yml` — cron at 07:00 UTC weekdays
5. Add `onnxruntime`, `mplfinance`, `opencv-python-headless` to `requirements.txt`
6. Verify workflow runs end-to-end on `workflow_dispatch`

**Deliverable:** Full nightly pipeline running in CI, writing data.json + chart PNGs.

### Phase 5: Frontend

**Build last because:** Frontend is read-only against data.json. It can be built and tested against static fixture data while the pipeline is being refined. But building it last avoids premature commitment to a schema that may still evolve during phases 1-4.

Tasks:
1. Create `docs/projects/patterns/index.html` — table of current detections, filterable by sector, sortable by confidence/date, dark theme matching screener
2. Create `docs/projects/patterns/stock.html` — drilldown with annotated chart (`<img src="charts/{ticker}.png">`), confidence badge, backtest stats panel, setup metrics table
3. Add pattern scanner card to `docs/index.html` project grid
4. Verify data.json staleness banner (same pattern recommended in CONCERNS.md for the screener)

**Deliverable:** Live portfolio page at `docs/projects/patterns/index.html`.

---

## Architecture Constraints Inherited from Existing Codebase

| Constraint | Source | Impact on Pattern Scanner |
|------------|--------|--------------------------|
| Static site only (GitHub Pages) | Deployment decision | All output must be pre-computed; no server-side rendering or live API calls from frontend |
| `requirements.txt` is shared | Single file for all Python deps | Adding `ultralytics` (for training scripts) pulls in PyTorch as a CI dependency; prefer NOT adding `ultralytics` to requirements.txt — use it only in the offline training environment; CI only needs `onnxruntime` |
| Nightly workflows must push to `main` | `contents: write` permission pattern | Schedule pattern-scan.yml at 07:00 UTC to avoid race with screener at 06:00 UTC |
| Vanilla JS, no build step | Project convention | Frontend pages must be self-contained HTML — no npm, no bundler |
| `git add` by explicit path | nightly-screener.yml line 32 convention | Stage only `docs/projects/patterns/data.json` and `docs/projects/patterns/charts/` — never `git add .` |
| yfinance rate limits | Existing screener sleep(0.5) pattern | Keep same 0.5s sleep between tickers in pattern scanner loop |

---

## Critical Constraint: `requirements.txt` and the PyTorch Problem

The existing `requirements.txt` is used by both the Render Flask API (`Procfile: gunicorn api_server:app`) and the GitHub Actions workflows. Adding `ultralytics` to this file would install PyTorch on the Render dyno (wasted memory) and on every CI run (slow — PyTorch is ~800MB).

**Solution:** Split dependencies or use extras:

Option A (recommended): Keep `requirements.txt` lean (no `ultralytics`). Add a separate `requirements-training.txt` with `ultralytics torch torchvision`. CI uses `requirements.txt` only. Training is done offline with `pip install -r requirements-training.txt`.

Option B: Use pip extras in a single file with `--extra-index-url` and conditional installs. More complex to maintain.

The CI `requirements.txt` for the pattern scanner needs only:
- `onnxruntime` (CPU inference)
- `mplfinance` (chart rendering)
- `opencv-python-headless` (image array processing)
- `yfinance` (already present)
- `pandas`, `numpy` (already present)

This keeps CI install time comparable to the current screener workflow.
