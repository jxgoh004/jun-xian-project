# Stack Research: Inside Bar Pattern Scanner

**Milestone:** v2.0 — Inside Bar Pattern Scanner
**Researched:** 2026-05-01
**Scope:** New capabilities only — existing Flask/yfinance/pandas/numpy stack not revisited

---

## Recommended Libraries

| Library | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| `mplfinance` | `>=0.12.10` | Render 2D OHLC candlestick images for YOLOv8 training dataset | Dedicated matplotlib wrapper for financial charts. Single call produces consistent, headless PNG at fixed resolution. Works with Agg backend (no display required) in GitHub Actions. Returns exact pixel dimensions needed for annotation coordinates. |
| `matplotlib` | `>=3.8` | Required backend for mplfinance; also used for annotation overlays if needed | mplfinance depends on matplotlib. Pin >=3.8 to ensure compatibility with numpy 2.x (numpy 2.4.4 is already installed). |
| `ultralytics` | `>=8.0,<9.0` | YOLOv8 model training and ONNX export | Official YOLOv8 library. Train locally, export to ONNX once, commit artifact. Do NOT install in GitHub Actions pipeline — torch dependency is ~2GB. Training is a one-time or occasional offline step. |
| `onnxruntime` | `>=1.18` | Inference on the exported YOLOv8 ONNX model in the nightly pipeline | CPU-only, ~20MB. No torch dependency. Runs YOLOv8 inference from the exported `.onnx` file. Compatible with GitHub Actions free tier. This is the only ML library that goes into the production pipeline. |
| `Pillow` | `>=10.0` | Image preprocessing before ONNX inference (resize, normalize to tensor) | Required for loading mplfinance-generated PNGs and converting to numpy arrays for onnxruntime input. Already a transitive dependency of several installed packages; pinning for explicitness. |
| `scipy` | `>=1.12` | Optional: NMS (non-maximum suppression) post-processing for YOLOv8 output boxes | If implementing custom NMS after ONNX inference rather than using ultralytics utilities. Lightweight alternative to pulling in full ultralytics for the pipeline. Only add if needed. |

**Libraries NOT recommended (with reasons below).**

---

## Version Pinning Concerns

### numpy 2.x compatibility
numpy 2.4.4 is already installed. This is a major version bump with breaking changes from 1.x. Key concern: matplotlib >=3.8 required for numpy 2.x compatibility. mplfinance 0.12.x depends on matplotlib; as long as matplotlib >=3.8 is pinned, no issues. ultralytics 8.x supports numpy 2.x from version 8.2+ onwards — pin `ultralytics>=8.2` to be safe.

### pandas 3.x compatibility
pandas 3.0.2 is already installed. pandas 3.0 drops some deprecated 1.x APIs (e.g. `DataFrame.append`, `.swaplevel` changes). Custom backtesting logic using `.iloc`, `.loc`, and vectorized column operations is unaffected. mplfinance accepts pandas DataFrames with OHLCV columns — the yfinance output format (columns: Open, High, Low, Close, Volume, index: DatetimeIndex) is exactly what mplfinance expects with no transformation.

### torch / ultralytics isolation
ultralytics installs torch, torchvision, and ~15 other heavy dependencies. Total install size: ~3-4GB. This must NEVER go into `requirements.txt` for the production/pipeline environment. Use a separate `requirements-training.txt` for the local training step. The GitHub Actions nightly pipeline uses only `onnxruntime` for inference.

---

## Integration Notes

### yfinance → mplfinance (no transformation needed)
`yfinance.Ticker(symbol).history(period='10y', interval='1d')` returns a DataFrame with columns `[Open, High, Low, Close, Volume]` and a `DatetimeIndex`. mplfinance's `mpf.plot()` accepts this directly. No column renaming required.

```python
import yfinance as yf
import mplfinance as mpf

df = yf.Ticker("AAPL").history(period="10y", interval="1d")
# Slice a 5-bar window around a detected pattern
window = df.iloc[i-2:i+3]  # 5 bars: mother + inside + 3 confirmation candidates
mpf.plot(window, type='candle', style='charles', savefig='output.png',
         figsize=(2.24, 2.24), dpi=100)  # 224x224px for YOLOv8 input
```

### mplfinance → YOLOv8 annotation
Bounding box coordinates for the annotation file must be computed in YOLO format (normalized x_center, y_center, width, height). Because mplfinance renders at a fixed `figsize` + `dpi`, the pixel coordinates of individual candle bodies are deterministic. The annotation logic in the dataset generator computes coordinates from the price values using the known matplotlib axis scale.

### ONNX inference pipeline
The nightly GitHub Actions pipeline:
1. Fetches OHLC data via yfinance (already implemented pattern)
2. Renders 5-bar window PNGs via mplfinance (new)
3. Feeds PNGs into onnxruntime session (new)
4. Filters detections by confidence threshold (new)
5. Writes results to `docs/projects/patterns/data.json` (same pattern as screener)

### Custom backtesting → pandas only
The backtesting engine uses only pandas (already installed). Pattern: for each detected setup at index `i`, slice `df.iloc[i+1:i+1+hold_period]`, compute return as `(exit_price - entry_price) / entry_price`. Entry price = next bar's open. Vectorized across 10 years of daily bars per ticker.

---

## What NOT to Add

| Library | Why Not |
|---------|---------|
| `plotly` | Produces interactive HTML/SVG — wrong output format for training image generation. Image export requires kaleido dependency and adds complexity. mplfinance gives cleaner PNG output with less code. |
| `matplotlib` direct (without mplfinance) | Drawing individual OHLC candles requires manual rectangle patches and line segments — ~100 lines of boilerplate for what mplfinance does in 3 lines. Training images must be visually consistent; mplfinance enforces that. |
| `vectorbt` | Overkill for this backtest. vectorbt is designed for portfolio-level simulations with multiple concurrent positions, complex entry/exit logic, and parameter sweeps. The inside bar scanner only needs: enter next open after confirmation bar, hold N bars, compute return. 30 lines of pandas covers it. vectorbt brings numba, scikit-learn, and ~500MB of dependencies. |
| `backtesting.py` | Event-driven sequential loop across 500 tickers × 10 years is slow. The library's OOP structure adds abstraction to a calculation that's fundamentally a vectorized array lookup. Custom pandas runs faster and is easier to audit. |
| `ta-lib` | Technical analysis library sometimes used for pattern detection. Not needed here — the inside bar ruleset is implemented algorithmically in Python directly (5-bar OHLC comparison), not via TA-Lib's pattern recognition. Also has a complex C extension install. |
| `opencv-python` | Sometimes used for image preprocessing. Not needed — Pillow is sufficient for the PNG → numpy array conversion onnxruntime requires. Adding cv2 brings a ~200MB binary for no gain. |
| `onnxruntime-gpu` | GitHub Actions runs on CPU. GPU variant requires CUDA setup and is unnecessary for batch overnight processing of ~500 single images. CPU onnxruntime is fast enough (YOLOv8n inference: ~15ms/image on CPU). |
| `torch` / `torchvision` in pipeline | Training-time only. Never goes into the production requirements. If ultralytics utilities are needed post-training (e.g. to inspect the ONNX), use them locally. The pipeline must stay lightweight for GitHub Actions free tier. |

---

## Suggested requirements additions

Two separate files to prevent torch from polluting the pipeline environment:

**`requirements.txt`** (production + pipeline — add these):
```
mplfinance>=0.12.10
matplotlib>=3.8
onnxruntime>=1.18
Pillow>=10.0
```

**`requirements-training.txt`** (local training only — new file):
```
ultralytics>=8.2,<9.0
# torch and torchvision installed automatically by ultralytics
```

---

## Confidence Assessment

| Claim | Confidence | Basis |
|-------|------------|-------|
| mplfinance is correct choice over plotly/matplotlib direct | HIGH | Domain-specific: plotly is wrong output format; mplfinance exists precisely for this use case |
| ultralytics is the correct YOLOv8 library | HIGH | It's the official Ultralytics repo — no alternative for training YOLOv8 |
| onnxruntime CPU for pipeline inference | HIGH | Standard practice; well-established pattern |
| Custom pandas over vectorbt/backtesting.py | HIGH | Backtesting logic complexity doesn't justify framework overhead |
| mplfinance version >=0.12.10 | MEDIUM | Version range from training data (cutoff Aug 2025); PyPI not verified |
| onnxruntime version >=1.18 | MEDIUM | Version range from training data; PyPI not verified |
| ultralytics>=8.2 for numpy 2.x compat | MEDIUM | Based on known numpy 2.x compatibility timeline in ultralytics changelog; not verified against current release |
| pandas 3.0.2 / numpy 2.4.4 installed | HIGH | Verified from .venv dist-info filenames in local filesystem |
