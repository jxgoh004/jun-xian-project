# Pitfalls Research: Inside Bar Pattern Scanner

**Domain:** CV-based pattern detector on financial OHLC charts (algorithmic + YOLOv8)
**Researched:** 2026-05-01
**Confidence:** HIGH — all claims based on established ML engineering practice, backtesting methodology, and documented GitHub Actions/ONNX behavior. No WebSearch available; based on training knowledge through Aug 2025.

---

## Critical Pitfalls

| # | Pitfall | Warning Sign | Prevention | Phase to Address |
|---|---------|--------------|------------|-----------------|
| 1 | YOLOv8 memorises chart *style*, not pattern *structure* | Near-perfect training mAP but weak on real-time charts with different rendering params | Vary rendering params in training data augmentation; separate renderer from pattern logic | Phase 2 (Dataset Generation) |
| 2 | Algorithmic labeler embeds look-ahead: annotation of bar N uses bar N+1 or N+2 data at inference time | CV model fires on charts where the full 5-bar sequence hasn't completed yet | Strict time boundary: annotate only when ALL 5 bars are historically complete; never annotate partial sequences | Phase 2 (Annotation) + Phase 1 (Detection) |
| 3 | Backtesting uses adjusted-close prices to detect patterns but unadjusted prices for entry/exit PnL | Win rate looks different from real trading; split-adjusted charts make patterns visually incorrect | Use the same adjusted-close series end-to-end; document this explicitly in the backtest module | Phase 4 (Backtesting) |
| 4 | GitHub Actions free-tier runner runs out of memory during ONNX inference over 500 tickers | Job silently killed mid-run; `data.json` written with only partial results | Split the 500-ticker list into chunks; process in batches; add checkpoint/resume | Phase 5 (Pipeline) |
| 5 | ONNX opset mismatch between training environment and inference environment | ONNX load fails or produces silent wrong output on runner | Pin `onnxruntime` version in `requirements.txt`; export with explicit opset; test round-trip in CI | Phase 3 (Training/Export) + Phase 5 |
| 6 | Auto-annotation produces class imbalance: 500:1 negative-to-positive ratio | Model predicts "no pattern" for everything and achieves 99.8% accuracy; mAP near zero | Undersample negatives during training; use weighted loss (`cls_loss` weights in YOLOv8 yaml); target 10:1 max ratio | Phase 2 (Dataset) + Phase 3 (Training) |
| 7 | Confirmation bar type (pin/markup/icecream) is annotated incorrectly for edge-case bars | Model learns wrong confirmation bar boundaries; backtest stats disagree with visual inspection | Unit-test every confirmation bar classifier against known fixtures before generating training data | Phase 1 (Detection Engine) |
| 8 | `data.json` written atomically without a staleness check | Nightly pipeline fails silently (API rate limit, runner OOM); frontend shows stale yesterday data | Write a `pipeline_status` field to `data.json`; check age on frontend load; mirror existing screener pattern | Phase 5 (Pipeline) |

---

## Look-Ahead Bias

This is the highest-risk pitfall for this project. It can enter through multiple independent channels, and each one silently inflates backtest performance.

### What Look-Ahead Bias Means Here

The inside bar spring setup requires 5 bars to be fully visible before the pattern is confirmed. Look-ahead bias occurs any time code uses information from bar N while simulating a decision that would have been made before bar N closed.

### Channel 1: Annotation at Generation Time

**How it enters:** The auto-annotator scans historical data and marks a cluster as a valid setup. The confirmation bar (bar 5) closes above the spring low. At annotation time, the full 5-bar history is available. BUT — at inference time, the model will be called after only 4 bars if bar 5 hasn't closed yet.

**Concrete example:** It is Thursday 2 PM. Bar 3 just broke below the mother bar low. Bar 4 has not closed. The pipeline runs and the model fires on this chart — but in training, this pattern was annotated using information about bar 4's close.

**Prevention:**
- The algorithmic detection engine (Phase 1) must define a strict "pattern complete" state: all 5 bars closed AND bar 4 (or bar 3 in the spring case) is the confirmation bar with a confirmed close.
- The dataset generator (Phase 2) must only call the renderer on `bars[0:5]` where `bars[4]` is a completed bar (i.e., from historical data where `bar_index < len(series) - 1`).
- At inference time (Phase 5), only call the model on charts where today's bar is bar 5 AND market close has passed (for EOD-only detection this is fine; for intraday this is risky).

### Channel 2: Trend Filter Using Forward Data

**How it enters:** The uptrend filter checks that the 20-SMA is sloping up. If you compute the 20-SMA on the full historical series and then check its slope, you are using SMA values that include future bars.

**Correct implementation:** For a pattern detected at bar index `i`, the 20-SMA used for the trend filter must be computed from `series[0:i+1]` — only bars available at detection time. Using `pandas.rolling(20).mean()` on the full series is correct as long as you never look ahead of the pattern's end bar.

**Wrong implementation:**
```python
# WRONG: computes SMA over full series including future bars, then slices
sma = df['close'].rolling(20).mean()
pattern_sma_slope = (sma[pattern_end + 5] - sma[pattern_end]) > 0
```

**Correct implementation:**
```python
# CORRECT: only use data available at pattern completion
sma = df['close'].rolling(20).mean()
pattern_sma_slope = (sma[pattern_end] - sma[pattern_end - 5]) > 0
```

### Channel 3: Backtesting Entry Price

**How it enters:** Entry is defined as "open of the bar after the confirmation bar closes." If the backtest uses `close[pattern_end]` as entry, it is entering at a price not available until bar close.

**Prevention:** Entry price = `open[pattern_end + 1]`. This is the first tradeable price after confirmation. Use `open` of the next bar, not `close` of the confirmation bar.

### Channel 4: Exit / Hold Period Calculation

**How it enters:** Backtest defines hold period as "5 bars." Calculating average return using `close[pattern_end + 5]` assumes you can exit exactly at close on day 5. This is realistic for EOD backtests. The problem enters if you calculate max-favorable-excursion (MFE) using the highest close within the hold period — this implicitly picks the best exit, not a real one.

**Prevention:** Use a fixed-rule exit: close of bar `pattern_end + N` (e.g., N=5 or N=10). Do not use highest-close-within-window as the exit price. If you compute MFE for diagnostic purposes, label it clearly as not the actual exit.

### Channel 5: In-sample Model Validation

**How it enters:** YOLOv8 is trained on all historical data. Then the same data is used to run the backtest. The model has "seen" the patterns it's being evaluated on.

**Prevention:**
- Time-based train/test split: train on data before `2022-01-01`, test on `2022–2025`.
- Never shuffle and split randomly — random splitting allows future patterns to leak into training data.
- The backtest (Phase 4) must only run on the held-out test set period.

### Channel 6: Survivor Bias in S&P 500 Universe

**How it enters:** The S&P 500 list used for backtesting is the *current* list (505 tickers today). Companies that went bankrupt, were acquired, or were removed from the index are excluded. This means the backtest only tests on companies that survived — inflating win rate.

**Mitigation:** Use a point-in-time S&P 500 constituent list if possible (survivorship-free). If not available, document this limitation explicitly in the frontend. For a portfolio project, acknowledging it is sufficient; do not claim live trading performance.

---

## GitHub Actions Resource Limits

GitHub Actions free-tier (ubuntu-latest runner) has these hard constraints:

| Resource | Limit | Relevance |
|----------|-------|-----------|
| RAM | 7 GB | ONNX inference over 500 charts; yfinance data load |
| vCPUs | 2 | ONNX runs single-threaded unless `onnxruntime` threading configured |
| Disk | 14 GB SSD | Chart image cache; model file |
| Job timeout | 6 hours | Nightly run limit |
| Artifact storage | 500 MB free | Not applicable (writing to git repo) |
| Workflow run minutes | 2,000/month (public repo: unlimited) | Public repo = no concern |

### Pitfall: Silent OOM Kill

When a runner runs out of memory, the job is killed without a Python exception — the process disappears and the step shows as "Process killed" or exits with code 137 (SIGKILL). There is no stack trace. The `data.json` write may not have completed.

**Prevention:**
- Write `data.json` to a temp file first, then `os.rename()` (atomic on Linux). If the job is killed mid-write, the old file is still intact.
- Add a `finally` block that writes a `pipeline_status` field with `completed: false` and a partial count.
- Process tickers in batches of 50. If a batch fails, the rest still complete.

### Pitfall: Model File Size and Checkout Time

YOLOv8n ONNX export is approximately 6 MB. YOLOv8s is approximately 22 MB. These are fine to commit to the repo. YOLOv8m is 50 MB — still within GitHub's 100 MB per-file limit, but close. YOLOv8l/x (100–200 MB) will exceed the limit.

**Recommendation:** Use YOLOv8n or YOLOv8s for the ONNX export. For a 5-bar chart-classification task, nano is likely sufficient. Do not commit the `.pt` checkpoint — only commit the `.onnx` export.

### Pitfall: yfinance Rate Limiting in Actions

The nightly pipeline fetches OHLC data for 500 tickers. yfinance uses Yahoo Finance's private API. Fetching 500 tickers without rate limiting triggers HTTP 429 errors. GitHub Actions runners share IP ranges — Yahoo Finance rate-limits these aggressively.

**Prevention:**
- Use `yfinance.download()` with a list of tickers (batch download) rather than 500 individual `.history()` calls. A single batch download for 500 tickers is 1 API call, not 500.
- If individual calls are needed, use `time.sleep(0.5)` between requests (already done in the existing screener pipeline).
- Cache the OHLC data file in the workflow: write a `cache/ohlc_<date>.parquet` and skip refetch if today's file exists.

### Pitfall: No Retry on Partial Failure

If Yahoo Finance is unavailable for 20 minutes mid-run, the job fails with stale data for the tickers not yet processed. GitHub Actions does not auto-retry failed jobs (unless configured with `on: workflow_run` retry logic).

**Prevention:**
- Write results incrementally: after each ticker, append to a working JSON. At the end, merge into `data.json`.
- Add `continue-on-error: true` for the individual ticker step if using a matrix strategy.
- Or add explicit retry logic in Python with exponential backoff on the data fetch.

---

## YOLOv8 Training on Synthetic Chart Images

### Pitfall 1: Rendering Artefacts as Learned Features

Matplotlib renders candles with consistent pixel-perfect geometry when called with identical parameters. YOLOv8 will learn to detect the *renderer's visual style* — exact candle width, exact padding, exact background color — rather than the abstract pattern. When production charts use a slightly different renderer (different DPI, different figsize, different candle width), the model's mAP collapses.

**Prevention:**
- Randomise rendering parameters during dataset generation: DPI (72–150), figsize (6–10 inches), candle body width (0.4–0.8), background color (pure black vs. very dark grey), wick thickness (0.5–1.5px).
- Generate at least 3 rendering "styles" and mix in training data.
- Add standard augmentations in `data.yaml`: HSV shifts, flips (horizontal flip is OK for pattern recognition if you invert the label meaning — but inside bar spring is directional, so disable horizontal flip; vertical flip is wrong for candles). Use brightness/contrast jitter only.

### Pitfall 2: Annotation Bounding Box Covers the Wrong Region

The YOLOv8 task is detection: each bounding box must tightly enclose the 5-bar pattern cluster. A common mistake is drawing the bounding box around the entire chart window rather than just the 5-bar cluster, or including extra bars in the box.

**Effect:** The model learns to detect "chart with a certain look" rather than "a specific 5-bar cluster". On a 60-bar chart, there might be 55 non-overlapping 5-bar windows — only the one with the pattern should be boxed.

**Prevention:**
- Compute bounding box from the pixel coordinates of bar 1 (mother bar left edge) to bar 5 (confirmation bar right edge), plus a small fixed padding (e.g., 5px).
- Verify visually on 10 randomly sampled annotations before generating the full dataset.
- Use a separate validation script that draws bounding boxes on chart images and outputs a sample for human inspection.

### Pitfall 3: Training Set Contains Consecutive/Overlapping Patterns

Historical financial data is a sliding window. If you detect a pattern at bar index 50 and another at bar index 52, their 5-bar clusters overlap. If both go into training data, the model sees nearly identical images with different labels — or the same image twice — causing confusion.

**Prevention:**
- After detecting all patterns algorithmically, apply non-maximum suppression by time: if two detected patterns overlap by more than 2 bars, keep only the one with the stronger confirmation signal.
- Alternatively, enforce a minimum gap of 5 bars between consecutive training samples from the same ticker.

### Pitfall 4: No True Negatives (Background Patches)

YOLOv8 requires negative examples — chart images with no pattern — to learn background vs. foreground. If the training set contains only positive examples (chart windows where a pattern exists), the model will fire on every chart.

**Prevention:**
- For every positive sample, generate 10 negative samples: random 5-bar windows from the same ticker that do NOT contain a valid inside bar spring setup (verified by the algorithmic detector returning no match).
- Include negative samples from different market conditions: trending up, trending down, choppy/sideways.

---

## Algorithmic Annotation Quality

### Pitfall 1: Spring Bar Rule Edge Case (Bar 3 == Confirmation Bar)

The pattern allows the break-below bar and the confirmation bar to be the same bar (the "spring" or failed breakdown). This means a single bar can have a low below the mother bar low AND a close inside the mother bar range. The algorithmic detector must handle this as a valid `pattern_length = 3` case (mother, inside, spring).

**Risk:** If the detector enforces `pattern_length == 5` rigidly, it misses all spring setups. These are actually the highest-quality setups (strongest rejection of the breakdown). Missing them means the model never learns to detect the strongest version of the pattern.

**Prevention:** In Phase 1, implement and unit-test the spring case explicitly. The annotation in Phase 2 should create a separate class label: `inside_bar_spring_3bar` vs. `inside_bar_spring_5bar`, OR treat them as the same class (simpler). Document the decision.

### Pitfall 2: Confirmation Bar Type Misclassification Near Boundaries

The three confirmation bar types (pin bar, markup bar, icecream bar) are defined by ratio thresholds (e.g., close in top 1/3 of range). At the boundary — e.g., close is at exactly 66.67% of range — a bar can qualify as both markup and icecream depending on floating-point precision.

**Prevention:**
- Define thresholds as closed intervals (include the boundary in one type, exclude from the other).
- Add unit tests for bars at the exact boundary values.
- The specific type label matters only for human readability in the frontend. For training purposes, all three types can share one class label (`confirmation_bar`).

### Pitfall 3: Uptrend Filter Applied Inconsistently

The trend filter (uptrend + price above 50-SMA) is applied algorithmically at detection time. If the filter is applied using data as of bar 5, it is correct. If it is applied using data as of the current date (when the batch runs), it is wrong — you would be annotating a historical pattern as valid/invalid based on today's trend, not the trend at the time of the pattern.

**Prevention:** The trend filter must be evaluated at `bar_index == pattern_end_bar`. Never re-evaluate historical pattern validity using current market state.

### Pitfall 4: OHLC Data Adjusted for Splits Mid-Pattern

When rendering a 5-bar cluster from historical data, if a stock split occurred within the 5 bars, the OHLC values are inconsistent (some bars pre-split, some post-split) unless fully adjusted-close data is used consistently.

**Prevention:** Use fully adjusted OHLC from yfinance (`auto_adjust=True`) for all rendering and annotation. Document this in the data pipeline.

---

## ONNX Inference Versioning and Compatibility

### Pitfall 1: opset Version Mismatch

YOLOv8 exports ONNX with a specific opset version (typically opset 12 or 17, depending on the Ultralytics version). `onnxruntime` versions before 1.16 do not support opset 17. If the training environment exports opset 17 but the GitHub Actions runner installs an older `onnxruntime`, inference fails at load time with:

```
onnxruntime.capi.onnxruntime_pybind11_state.InvalidGraph: [ONNXRuntimeError] : 10 : INVALID_GRAPH
```

**Prevention:**
- In `requirements.txt`, pin both `ultralytics` and `onnxruntime` to the same versions used during training.
- At ONNX export time, log the opset version used: `onnx.checker.check_model(model); print(model.opset_import)`.
- In the inference script, add a startup assertion: `assert onnxruntime.__version__ >= '1.16.0'`.

### Pitfall 2: Dynamic vs. Static Input Shape

YOLOv8 ONNX exports can use dynamic batch size or fixed batch size. If exported with `dynamic=True` but the inference code passes a fixed-shape tensor, some `onnxruntime` versions throw shape errors. If exported with `dynamic=False` and you try to batch multiple chart images, inference fails.

**Recommendation:** Export with `dynamic=False` and `batch=1` for simplicity. The nightly pipeline processes one chart at a time — batching adds complexity for minimal gain.

### Pitfall 3: NumPy Version Incompatibility

`onnxruntime >= 1.17` dropped support for NumPy 1.x in some builds. NumPy 2.0 (released mid-2024) introduced breaking changes in array API. If `onnxruntime` and `numpy` versions are not co-pinned, inference preprocessing may fail with `AttributeError: module 'numpy' has no attribute 'bool'` (numpy 2.0 removed deprecated aliases).

**Prevention:**
- Pin `numpy<2.0` or pin a specific compatible pair. As of mid-2025, `numpy==1.26.x` + `onnxruntime==1.17.x` is a known stable combination.
- Test the full inference pipeline in a clean virtualenv before committing to the Actions workflow.

### Pitfall 4: Model File Committed to Git Without LFS, Then Modified

If the ONNX model file is committed to git without Git LFS and is later retrained and recommitted, git stores the full binary diff of both versions. A 22 MB ONNX file committed twice = 44 MB in repo history permanently.

**Prevention:**
- Either use Git LFS for the model file (recommended), OR keep only one version and `git rm --cached` the old version when replacing it.
- Add `*.onnx` and `*.pt` to `.gitattributes` for LFS tracking before the first commit.

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------------|------------|
| Phase 1: Detection Engine | Confirmation bar boundary conditions | Floating-point threshold creates inconsistent labeling | Unit-test all 3 bar types at exact boundary values; use integer-math percentages |
| Phase 1: Detection Engine | Spring bar rule (3-bar case) | Missed if code enforces 5-bar minimum | Implement and test the 3-bar spring case explicitly |
| Phase 2: Dataset Generation | Bounding box annotation | Box covers full chart instead of 5-bar cluster | Compute box from pixel coords of bars 1–5; visual-inspect 10 samples |
| Phase 2: Dataset Generation | Class imbalance | 500:1 negative ratio kills recall | Cap negatives at 10:1 per ticker; use YOLOv8 `cls_pw` loss weighting |
| Phase 2: Dataset Generation | Rendering style memorisation | Single style = model learns renderer not pattern | Randomise DPI, figsize, candle width; disable horizontal flip augmentation |
| Phase 3: YOLOv8 Training | Train/test data leakage | Random split leaks future patterns into training | Time-based split only: train < 2022, test 2022–2025 |
| Phase 3: YOLOv8 Training | ONNX export opset | opset 17 not supported by older onnxruntime | Pin versions; test round-trip inference before committing model |
| Phase 4: Backtesting | Look-ahead via SMA filter | SMA evaluated at wrong bar index | SMA must be evaluated at `pattern_end_bar`; unit-test with known historical data |
| Phase 4: Backtesting | Entry price | Using close[confirmation_bar] instead of open[confirmation_bar + 1] | Define entry as open of bar after confirmation; add assertion in backtest code |
| Phase 4: Backtesting | Survivor bias | S&P 500 list is current, not point-in-time | Document limitation in frontend tooltip; do not claim live trading performance |
| Phase 5: Batch Pipeline | OOM kill | 500 ONNX inference calls crash runner | Batch in groups of 50; write atomically; add partial-failure checkpoint |
| Phase 5: Batch Pipeline | yfinance rate limiting | 500 individual history() calls hit 429 | Use batch yfinance.download() with full ticker list; add 0.5s sleep if needed |
| Phase 5: Batch Pipeline | Stale data on failure | Job fails silently; frontend shows old results | Write `pipeline_status` + timestamp to data.json; frontend shows banner if > 2 days old |
| Phase 6: Frontend | CV confidence score misrepresentation | Displaying raw YOLO confidence as "accuracy" | Label it as "detection confidence" not "win probability"; show backtest win rate separately |
