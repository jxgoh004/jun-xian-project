# Phase 8: Training Pipeline — Research

**Researched:** 2026-05-02
**Domain:** YOLOv8n training pipeline for an algorithmically-annotated single-class candlestick pattern detector; mplfinance headless rendering; ONNX export + clean-venv round-trip; deterministic offline reproducibility.
**Confidence:** HIGH

---

## Summary

Phase 8 builds an offline-only training pipeline that takes Phase 7's `Detection` records, renders each setup as a 60-bar 640×640 candlestick PNG with style-randomised mplfinance, generates YOLOv8-format labels (positives) and empty `.txt` files (hard-negative backgrounds at a 10:1 cap), trains `yolov8n.pt` for one class via `ultralytics.YOLO.train(...)`, exports to ONNX with a logged opset, and round-trips the artifact in a clean venv before commit. Six new files land in `scripts/pattern_scanner/` (renderer, generator, trainer, verifier, split_config) plus three new `tests/`, one new `requirements-training.txt`, four new entries in `requirements.txt`, an `.onnx` artifact, a manifest, and 1–2 fixture PNGs.

The phase is heavily constrained — CONTEXT.md D-01 through D-20 lock virtually every architectural choice. Research therefore focuses on the **mechanics** the planner must hand to the executor: exact mplfinance API for buffer-rendered fixed-pixel PNGs, the YOLOv8 directory contract, the `model.train(...)` and `model.export(...)` parameter surface, the ONNX→onnxruntime postprocessing recipe (NMS responsibility), how to add `apply_trend_filters: bool = True` to Phase 7 without breaking 23 existing tests, and what "bit-for-bit reproducibility" can actually mean given yfinance backend variance and matplotlib font rendering.

The dominant unresolved technical risk is **renderer non-determinism across OS/font installations**. mplfinance + matplotlib do not produce byte-identical PNGs across machines unless font caches and rcParams are pinned — so the dataset_manifest sha256 claim must be scoped to "reproducible on this machine with this seed" rather than "byte-identical across the world." The seed locks Python `random.Random` and numpy `default_rng`; matplotlib font selection is a separate axis.

**Primary recommendation:** Pin Python 3.14 + numpy 2.4.4 + ultralytics 8.4.46 + onnxruntime 1.25.1 + mplfinance 0.12.10b0 + matplotlib 3.10.9 + Pillow 12.2.0. Use `mplfinance.plot(df, type="candle", style=..., figsize=..., update_width_config={"candle_width": ...}, savefig=dict(fname=BytesIO_buf, dpi=..., bbox_inches="tight", pad_inches=0))`, then `Pillow.Image.open(buf).resize((640, 640), Image.LANCZOS)`. Export with `model.export(format="onnx", opset=12, dynamic=False, imgsz=640, simplify=True)` — opset 12 is the Ultralytics-recommended baseline for broad onnxruntime compatibility. Add `apply_trend_filters: bool = True` as a **kwarg to existing `detect()`** (not a sibling) — preserves all 23 Phase 7 call sites, the kwarg default reproduces current behavior. Class imbalance with empty-label backgrounds is handled by YOLOv8 **objectness loss balance**, not `cls_pw` (which is for multi-class confusion); recommend leaving `cls_pw=1.0` (default) and relying on the 10:1 cap + box/objectness loss weights — this is the single biggest correction to the locked CONTEXT D-17 assumption.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Chart framing & bbox (D-01 — D-04):**
- D-01 Window: 60 daily bars (~3 months) per training image, same for positives and negatives.
- D-02 Bbox: tight on 5-bar cluster only — `x0 = mother bar left edge, x1 = confirmation bar right edge, y0 = min(low), y1 = max(high)` over the 5 bars. No padding.
- D-03 Position: confirmation bar is the rightmost bar in the chart (right-aligned framing — eliminates train/inference distribution shift).
- D-04 PNG dimensions: 640 × 640 px (YOLOv8 native input size, `imgsz=640`).

**Training universe & volume (D-05 — D-08):**
- D-05 Universe: full S&P 500 current constituents (~503 tickers) — matches Phase 10 inference universe.
- D-06 History: 10 years daily via yfinance auto_adjust.
- D-07 Shared split: this phase creates `scripts/pattern_scanner/split_config.py` exposing `TRAIN_TEST_CUTOFF = "2024-01-01"` (placeholder; Phase 9 may revise but file stays here). Detections with `confirmation_date >= TRAIN_TEST_CUTOFF` excluded from training.
- D-08 Threshold: ≥ 1,000 positive samples; trigger multi-style augmentation if below.

**Negative sampling (D-09 — D-12):**
- D-09 Ratio: 10:1 negatives:positives globally.
- D-10 Source: hard negatives only — `(filters-disabled detect()) − (real filtered detections)`. Implement via `apply_trend_filters: bool = True` kwarg on Phase 7's `detect()`.
- D-11 Framing: identical 60-bar right-aligned 640×640 PNGs; empty `.txt` label files (YOLO background convention).
- D-12 No per-ticker cap.

**Reproducibility (D-13 — D-15):**
- D-13 Commit only: `models/inside_bar_v1.onnx`, 1–2 fixture PNGs in `tests/fixtures/`, `models/dataset_manifest.json`. Dataset itself NOT committed.
- D-14 Generated dataset under gitignored `_dev/training_dataset/{images,labels}/{train,val}/` + `data.yaml`.
- D-15 `--seed` arg + `dataset_manifest.json` (positive count, negative count, ticker list, date range, `TRAIN_TEST_CUTOFF`, seed, sha256-of-concatenated-PNGs).

**Training (D-16 — D-19):**
- D-16 Local CPU/GPU; auto-detect via ultralytics.
- D-17 `yolov8n.pt`, `imgsz=640`, single class `inside_bar_spring`, `fliplr=0.0`, `cls_pw` "tuned" (see correction in §Common Pitfalls), opset logged.
- D-18 Claude's discretion: epochs (with early stop), batch (auto or fixed), LR schedule (default cosine), warmup, train/val split (80/20 random within train period).
- D-19 Round-trip: clean venv with only `onnxruntime`, `numpy`, `Pillow`; pass = ≥ 1 bbox with confidence ≥ 0.5 on fixture; CI on PRs touching the `.onnx`.

**Module surface (D-20):**
- New files in `scripts/pattern_scanner/`: `renderer.py`, `generate_training_data.py`, `train.py`, `verify_onnx.py`, `split_config.py`.

### Claude's Discretion

- mplfinance style randomisation parameter ranges (DPI, figsize, candle width, background shade variants — CONTEXT suggests 3+ styles).
- `split_config` as `.py` constant or `.yaml` file (research recommends `.py` — see §Architecture Patterns).
- Internal helper function names within new modules.
- Whether `generate_training_data.py` parallelises yfinance fetches (research recommends sequential first, parallelise only if >2 h locally).
- `cls_pw` exact value (research recommends default 1.0 — see §Common Pitfalls).
- ONNX opset (research recommends `opset=12`).
- Whether `verify_onnx.py` runs subprocess in temp venv vs CI job (research recommends programmatic temp venv via `venv` module + subprocess).

### Deferred Ideas (OUT OF SCOPE)

- Multi-class YOLO (separate `spring` vs `full_5bar`).
- Per-ticker sample cap (5% / 10%).
- Dataset committed under Git LFS.
- Cloud / Colab training.
- Volume bars / SMA overlays in training images.
- Time-based train/val split inside pre-cutoff data.
- YOLOv8s upgrade if YOLOv8n under-fits.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRAIN-01 | Chart renderer produces consistent 2D OHLC candlestick PNGs from yfinance DataFrames using mplfinance | §Code Examples — Renderer; §Architecture Patterns — Renderer module |
| TRAIN-02 | Training data generator produces YOLOv8-format annotations from algorithmic detections, with rendering-style randomisation (DPI, figsize, candle width) | §Code Examples — Style randomization; §Architecture Patterns — Generator module |
| TRAIN-03 | Training pipeline applies negative sampling capped at 10:1 to manage class imbalance | §Code Examples — Generator; §Common Pitfalls — `cls_pw` correction |
| TRAIN-04 | YOLOv8n model is trained on the generated dataset and exported as ONNX (opset version logged) to `models/inside_bar_v1.onnx` | §Code Examples — Trainer; §Code Examples — Verifier; §Architecture Patterns — Train/Export module |

---

## Project Constraints (from CLAUDE.md)

| Directive | Source | Impact on Plan |
|-----------|--------|----------------|
| Python virtualenv `.venv` is mandatory; activate before any `python`/`pip` | CLAUDE.md MEMORY (`feedback_venv.md`) | Every plan task that runs Python MUST start with `source .venv/Scripts/activate` (Windows Git Bash) or `.venv\Scripts\activate.bat` (cmd). Already followed by Phase 7. |
| No AI co-author trailers in commits; use `git-attribution-guard` | CLAUDE.md MEMORY (`feedback_git_attribution.md`) | Plan executor commit messages must NOT include `Co-Authored-By: Claude*` lines. |
| Prefer code-review-graph MCP tools over Grep/Read where applicable | CLAUDE.md (MCP tools section) | When understanding the impact of adding `apply_trend_filters` kwarg to `detect()`, use `query_graph` / `get_impact_radius` to verify call sites. |
| Backend on Heroku/Render = no torch/ultralytics in `requirements.txt` | Research/SUMMARY.md + REQUIREMENTS Out of Scope | Hard split: `requirements-training.txt` for ultralytics+torch (offline only); `requirements.txt` adds only inference deps (mplfinance, matplotlib, onnxruntime, Pillow). |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Algorithmic detection for positives | Phase 7 detector (`detect()`) | — | Already shipped in Phase 7; Phase 8 imports it as-is |
| Hard-negative candidate generation | Phase 7 detector (`detect(apply_trend_filters=False)`) | Phase 8 generator (set arithmetic) | Detector owns the rule; generator owns the difference operation |
| Chart rendering (DataFrame → PNG bytes) | `scripts/pattern_scanner/renderer.py` (offline) | mplfinance + matplotlib | Pure function; no side effects; reusable by Phase 10's annotated-chart writer for nightly runs |
| Dataset assembly + manifest | `scripts/pattern_scanner/generate_training_data.py` | — | Orchestrator only; calls renderer + detector |
| Model training | `scripts/pattern_scanner/train.py` | ultralytics | One-time offline; never imported by CI workflows |
| ONNX inference (verify) | `scripts/pattern_scanner/verify_onnx.py` | onnxruntime + Pillow + numpy | Round-trip gate; runs in temp venv WITHOUT torch/ultralytics |
| Train/test split source-of-truth | `scripts/pattern_scanner/split_config.py` | — | Single constant `TRAIN_TEST_CUTOFF`; Phase 9 backtester imports same module |

---

## Standard Stack

### Core Training Dependencies (`requirements-training.txt` — NEW file, offline only)

| Library | Recommended Pin | Purpose | Why Standard | Source |
|---------|----------------|---------|--------------|--------|
| ultralytics | `>=8.4.0,<9.0` (verified `8.4.46` available) | YOLOv8n train + ONNX export | Canonical YOLOv8 implementation; one-line `.export(format="onnx")` | [VERIFIED: pip index 2026-05-02] |
| torch | (transitive, `>=1.8`) | ultralytics dependency | Auto-installed by ultralytics; resolves to `2.11.0` on Python 3.14 | [VERIFIED: pip dry-run 2026-05-02] |

### Production Dependencies (added to `requirements.txt`)

| Library | Recommended Pin | Purpose | Why Standard | Source |
|---------|----------------|---------|--------------|--------|
| mplfinance | `>=0.12.10b0` (verified `0.12.10b0` is current stable) | Headless candlestick PNG rendering | Single call accepts yfinance DataFrames; `savefig` accepts `io.BytesIO`; consistent across training and Phase 10 annotated charts | [VERIFIED: pip dry-run 2026-05-02] |
| matplotlib | `>=3.8` (currently `3.10.9` available; required by mplfinance) | mplfinance backend; numpy 2.x compatibility | Pin >=3.8 for numpy 2.x compatibility | [CITED: research/SUMMARY.md] |
| onnxruntime | `>=1.18` (currently `1.25.1` available — pin to `>=1.19` for hard numpy 2.x compatibility) | YOLOv8 inference in nightly CI | CPU-only ~15 MB; no torch dependency; runs on GitHub Actions free tier | [VERIFIED: pip index 2026-05-02; numpy 2.x supported >=1.19 per onnxruntime issue #21063] |
| Pillow | `>=10.0` (currently `12.2.0` available) | PNG load + numpy array conversion for onnxruntime input | Avoids opencv (~200 MB pull) | [CITED: research/SUMMARY.md; VERIFIED pip 2026-05-02] |

### Versions Verified Live (`pip index versions` on 2026-05-02 in this project's `.venv`)

```
Python:        3.14.4
numpy:         2.4.4 (already installed)
pandas:        3.0.2 (already installed)
yfinance:      0.2.65 (already installed; pinned in requirements.txt)
ultralytics:   8.4.46 (latest)
torch:         2.11.0 (transitive; resolves on Py 3.14)
onnxruntime:   1.25.1 (latest)
mplfinance:    0.12.10b0 (current stable; "b0" is normal — mplfinance has been in beta since 2020)
matplotlib:    3.10.9 (latest)
Pillow:        12.2.0 (latest)
```

`pip install --dry-run mplfinance` and `pip install --dry-run ultralytics` both resolve cleanly into the existing `.venv` (Python 3.14.4, numpy 2.4.4) — no version conflicts. [VERIFIED 2026-05-02]

### Alternatives Considered

| Instead of | Could Use | Why Rejected |
|------------|-----------|--------------|
| mplfinance | matplotlib direct + `Rectangle` patches | Re-implements candle rendering for no benefit; mplfinance is purpose-built |
| Pillow | OpenCV (cv2) | OpenCV pulls ~200 MB into nightly CI for image loading we don't need |
| ultralytics CLI (`yolo detect train ...`) | ultralytics Python API | Python API allows hyperparam logging + opset capture in one script; CLI requires post-hoc parsing |
| Manual ONNX export via `torch.onnx.export` | `model.export(format="onnx", ...)` | ultralytics handles input shape, NMS placement, and opset selection correctly |

### Installation

`requirements.txt` (production — used by Render and all CI):
```
# ── Existing ──
flask==3.1.3
flask-cors==6.0.2
yfinance==0.2.65
curl_cffi>=0.7.0
pandas>=2.2.0
numpy>=1.26.0
requests==2.32.5
beautifulsoup4==4.13.5
lxml==6.0.1
gunicorn==23.0.0
openai>=1.0.0
python-dotenv>=1.0.0
# ── Added in Phase 8 (inference dependencies — required by Phase 10 nightly pipeline) ──
mplfinance>=0.12.10b0
matplotlib>=3.8
onnxruntime>=1.19
Pillow>=10.0
```

`requirements-training.txt` (NEW file — offline training only; never installed by Render or any CI workflow):
```
# Training-only dependencies. Never install in production / nightly CI.
# Install via: source .venv/Scripts/activate && pip install -r requirements-training.txt
ultralytics>=8.4.0,<9.0
```

`requirements-dev.txt` (already exists from Phase 7):
```
pytest>=8.4,<9
```

---

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────┐
                         │  S&P 500 ticker list    │
                         │  (Wikipedia scrape, as  │
                         │  in scripts/fetch_sp500.│
                         │  py)                    │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │ yfinance 10y daily      │
                         │ history per ticker      │
                         └────────────┬────────────┘
                                      │
                ┌─────────────────────┴─────────────────────┐
                │                                           │
                ▼                                           ▼
   ┌────────────────────────┐                   ┌────────────────────────┐
   │ detect(df, ticker)     │                   │ detect(df, ticker,     │
   │                        │                   │  apply_trend_filters=  │
   │ → real positives       │                   │  False)                │
   │   (filters PASS)       │                   │ → unfiltered candidates│
   └───────────┬────────────┘                   └───────────┬────────────┘
               │                                            │
               │     ┌──────────────────────────────────────┘
               │     │ set difference
               ▼     ▼
   ┌────────────────────────┐                   ┌────────────────────────┐
   │ Apply TRAIN_TEST_CUTOFF│                   │ Hard-negative candidates│
   │ (drop conf_date >=     │                   │ (filters-disabled MINUS │
   │  cutoff)               │                   │  real-positives)        │
   └───────────┬────────────┘                   └───────────┬────────────┘
               │                                            │
               │  if positives < 1000 → multi-style augment │  cap at 10× positives
               ▼                                            ▼
            ┌───────────────────────────────────────────────┐
            │ For each positive AND negative sample:        │
            │   df_window = df.iloc[conf_idx-59 : conf_idx+1] (60 bars)│
            │   style = random.choice(STYLES)               │
            │   png_bytes = renderer.render(df_window, style)│
            │   resize to 640×640 via PIL                   │
            │   write _dev/training_dataset/images/.../X.png│
            │   write _dev/training_dataset/labels/.../X.txt│
            │      (positive: "0 cx cy w h" normalized)     │
            │      (negative: "" empty file)                │
            └───────────────────────┬───────────────────────┘
                                    ▼
            ┌───────────────────────────────────────────────┐
            │ data.yaml + dataset_manifest.json             │
            │   manifest: positives, negatives, tickers,    │
            │   date_range, cutoff, seed, sha256s           │
            └───────────────────────┬───────────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ ultralytics.YOLO     │
                         │ ("yolov8n.pt")       │
                         │ .train(data=...,     │
                         │  imgsz=640,          │
                         │  epochs=N, batch=B,  │
                         │  fliplr=0, ...)      │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ best.pt (ultralytics)│
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ model.export(        │
                         │  format="onnx",      │
                         │  opset=12,           │
                         │  dynamic=False,      │
                         │  imgsz=640,          │
                         │  simplify=True)      │
                         │ + LOG opset version  │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ models/inside_bar_v1 │
                         │      .onnx           │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ verify_onnx.py:      │
                         │  - mkdir tmp_venv    │
                         │  - python -m venv ...│
                         │  - pip install       │
                         │     onnxruntime      │
                         │     Pillow numpy     │
                         │  - subprocess call:  │
                         │     load fixture PNG │
                         │     run inference    │
                         │     assert ≥1 bbox   │
                         │     conf ≥ 0.5       │
                         └──────────┬───────────┘
                                    ▼
                              git commit:
                       models/inside_bar_v1.onnx
                       models/dataset_manifest.json
                       tests/fixtures/known_positive_*.png
```

### Component Responsibilities

| Component | File | Imports From | Imported By |
|-----------|------|-------------|-------------|
| Renderer | `scripts/pattern_scanner/renderer.py` | `mplfinance`, `matplotlib`, `Pillow`, `io` | `generate_training_data.py`; (Phase 10) `run_scan.py` for annotated charts |
| Generator | `scripts/pattern_scanner/generate_training_data.py` | `renderer`, `detector`, `split_config`, `yfinance`, `random`, `numpy.random` | nothing — CLI only |
| Trainer | `scripts/pattern_scanner/train.py` | `ultralytics`, `pathlib`, `json` | nothing — CLI only |
| Verifier | `scripts/pattern_scanner/verify_onnx.py` | `subprocess`, `venv`, `pathlib`, `tempfile` | nothing — CLI only |
| Split config | `scripts/pattern_scanner/split_config.py` | (none) | `generate_training_data.py`, Phase 9 `backtester.py` |
| Detector kwarg | `scripts/pattern_scanner/detector.py` (modified) | (no new imports) | `generate_training_data.py`, Phase 9, Phase 10 |

### Recommended Project Structure (after Phase 8)

```
scripts/pattern_scanner/
├── __init__.py                      # existing — exports detect, Detection
├── detector.py                      # modified: new kwarg apply_trend_filters
├── renderer.py                      # NEW
├── generate_training_data.py        # NEW
├── train.py                         # NEW
├── verify_onnx.py                   # NEW
└── split_config.py                  # NEW

models/                              # NEW top-level directory
├── inside_bar_v1.onnx               # NEW (committed, ~6-12 MB)
└── dataset_manifest.json            # NEW (committed)

tests/
├── conftest.py                      # existing
├── fixtures/                        # NEW directory
│   └── known_positive_aapl_2020.png # NEW (committed, ~50-80 KB)
├── test_detector_known_setups.py    # existing
├── test_detector_schema.py          # existing
├── test_renderer.py                 # NEW
├── test_generate_training_data.py   # NEW
└── test_onnx_round_trip.py          # NEW

_dev/training_dataset/               # NEW, GITIGNORED
├── images/{train,val}/*.png
├── labels/{train,val}/*.txt
├── data.yaml
└── dataset_manifest.json            # local copy; committed copy lives in models/

requirements.txt                     # modified (4 new lines)
requirements-training.txt            # NEW
.gitignore                           # modified (add _dev/training_dataset/, yolov8n.pt)
```

### Pattern 1: Slice-First (Inherited from Phase 7)

**What:** Compute trend indicators on `df.iloc[:end_idx + 1]`, never on the full frame.
**When to use:** Anywhere the generator needs to evaluate "what did the chart look like at confirmation time?"
**Source:** Phase 7's detector enforces this — the generator must NOT undo it. Specifically: when slicing the 60-bar window for rendering, slice on `[conf_idx - 59 : conf_idx + 1]` so the rightmost bar is the confirmation bar (D-03).

```python
# Source: scripts/pattern_scanner/detector.py (Phase 7)
window_start = max(0, conf_idx - 59)
window_end = conf_idx + 1   # exclusive — gives 60 bars ending AT conf_idx
df_window = df.iloc[window_start:window_end]
assert len(df_window) == 60, f"window len {len(df_window)} != 60 — ticker has insufficient history"
```

### Pattern 2: Pure Function + CLI Wrapper

**What:** `renderer.render(df_window, style) -> bytes` is a pure function; the CLI is a thin `if __name__ == "__main__"` shim around it. Same idiom as `detector.detect()`.
**When to use:** Any new module in `scripts/pattern_scanner/`.
**Source:** Phase 7 `detector.py` lines 305-376 (pure `detect()`) + lines 391-410 (CLI `main()`).

### Pattern 3: Deterministic Seeded Outputs

**What:** Every script that consumes randomness accepts `--seed`. Use `random.Random(seed)` and `numpy.random.default_rng(seed)` — never the global `random` / `np.random` state.
**When to use:** `generate_training_data.py` (style choice, train/val split, negative subsampling) and `train.py` (ultralytics `seed=N`).
**Why:** Per CONTEXT D-15, dataset must be re-buildable bit-for-bit. Note: this guarantees reproducibility OF THE GENERATOR'S RANDOM CHOICES. It does NOT guarantee identical PNG bytes across machines (matplotlib font hinting varies). The manifest sha256 should be documented as "reproducible on the same machine with the same yfinance data revision" — see §Common Pitfalls #6.

### Anti-Patterns to Avoid

- **Loading the entire dataset into RAM before writing.** With 1k positives + 10k negatives × 640×640 RGB ≈ 13 GB. Stream: render → write → free. 
- **Using `plt.show()` or any interactive backend.** Set `matplotlib.use("Agg")` at the top of `renderer.py` BEFORE importing pyplot/mplfinance to force the non-interactive backend.
- **Hand-rolling a candle drawing function.** mplfinance is the standard; using `matplotlib.patches.Rectangle` directly invents work for no benefit.
- **Calling `detect()` without `apply_trend_filters=False`** when generating hard negatives — the entire methodological premise (D-10) collapses if the negative pool is just "random windows."
- **Embedding NMS in postprocessing OUTSIDE the ONNX graph if `simplify=False` is also off.** ultralytics 8.x does NOT include NMS in the exported ONNX by default; the verifier MUST apply NMS in numpy. See §Code Examples — Verifier.
- **Treating `cls_pw` as the imbalance lever** for empty-label backgrounds. See §Common Pitfalls #4.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Candlestick rendering | Custom `Rectangle` patches in matplotlib | `mplfinance.plot(..., type="candle")` | Handles wick/body/colour/spacing for arbitrary bar count; auto-sizes axes |
| YOLOv8 training loop | Custom PyTorch detection-head training | `ultralytics.YOLO("yolov8n.pt").train(...)` | Full pipeline: dataloader, augmentations, mAP eval, early stopping, checkpointing — single API call |
| ONNX export from YOLOv8 | Manual `torch.onnx.export(...)` | `model.export(format="onnx", ...)` | ultralytics knows the model's expected input/output spec and embeds correct metadata |
| YOLOv8 ONNX postprocessing in inference | Reinvent IoU + class-NMS | `numpy` IoU + custom NMS (see §Code Examples) — but DO build it ourselves because torchvision is not available in the inference venv | Verifier runs in clean venv WITHOUT torchvision; must use numpy NMS. Pure-numpy NMS is ~30 lines of well-known code. |
| Train/val split | Manual file moves | `random.Random(seed).shuffle(...)` then slice | 80/20 random within pre-cutoff is sufficient |
| Style randomization | Hand-tweaked `style` dicts at every call | `mplfinance.make_mpf_style(...)` factory + a list of 3 named styles | mplfinance has a documented style system |

**Key insight:** Phase 8 is integration plumbing. The hard parts (CV training, ONNX export, candle rendering) are all single-API-call operations from established libraries. The risk lies in plumbing mistakes — wrong directory layout, wrong label normalization, opset mismatch, missing NMS — not in algorithmic novelty.

---

## Code Examples

> All code is illustrative scaffolding for the planner — exact field names and helper APIs are at executor discretion subject to CONTEXT decisions.

### Renderer — `scripts/pattern_scanner/renderer.py`

```python
# Source: docs.mplfinance + matplotlib backend docs + project context
"""Headless mplfinance candlestick renderer with style randomization.

Pure function; no global state; safe to call concurrently if matplotlib
is forced to Agg before import.
"""
from __future__ import annotations
import io
from dataclasses import dataclass
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # MUST come before pyplot/mplfinance import
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from PIL import Image

# Three named style variants — randomization happens at the parameter level
# inside each style choice (D-17 fliplr=0 + research Watch-Out #2).
@dataclass(frozen=True)
class RenderStyle:
    name: str
    base_style: str         # "yahoo" | "charles" | "classic"
    figsize: tuple          # (w, h) inches
    dpi: int
    candle_width: float     # mplfinance update_width_config["candle_width"]
    facecolor: str          # background

STYLES = (
    RenderStyle("style_a", "yahoo",   (8, 6),  100, 0.6, "#ffffff"),
    RenderStyle("style_b", "charles", (10, 7), 120, 0.5, "#fafafa"),
    RenderStyle("style_c", "classic", (6, 5),   90, 0.7, "#f5f5f5"),
)

def render(df: pd.DataFrame, style: RenderStyle, target_size: int = 640) -> bytes:
    """Render a candlestick PNG of `df` to bytes, then resize to `target_size`x`target_size`.

    Args:
        df: 60-row DataFrame with Open/High/Low/Close columns and DatetimeIndex.
        style: one of `STYLES` (or any RenderStyle).
        target_size: final square pixel dimension (640 per D-04).

    Returns:
        PNG bytes of the resized image (target_size × target_size).
    """
    if len(df) != 60:
        raise ValueError(f"render expects 60 bars; got {len(df)}")

    mpf_style = mpf.make_mpf_style(
        base_mpf_style=style.base_style,
        facecolor=style.facecolor,
        rc={"font.family": "DejaVu Sans"},  # pin font to reduce cross-OS variance
    )

    buf = io.BytesIO()
    mpf.plot(
        df,
        type="candle",
        style=mpf_style,
        figsize=style.figsize,
        update_width_config={"candle_width": style.candle_width},
        axisoff=True,                      # no axis labels — pure picture
        savefig=dict(
            fname=buf,
            dpi=style.dpi,
            bbox_inches="tight",
            pad_inches=0,
        ),
    )
    plt.close("all")  # critical: prevents memory growth across thousands of renders

    buf.seek(0)
    img = Image.open(buf).convert("RGB").resize((target_size, target_size), Image.LANCZOS)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def compute_bbox_normalized(df: pd.DataFrame, mother_idx_in_window: int,
                             confirmation_idx_in_window: int,
                             target_size: int = 640) -> tuple[float, float, float, float]:
    """Return (cx, cy, w, h) normalized to 0..1 for the 5-bar cluster (D-02).

    NOTE: This is computed in DATA coordinates (bar indices + price levels) and
    must be transformed to image coordinates via the renderer's inverse mapping.
    Implementation note: it is much simpler to compute the bbox in pixel space
    by re-running the same render pipeline once with bbox-aware drawing, OR by
    deriving bbox from known mplfinance margins. See PLAN — recommended
    approach is to set fixed mplfinance figure padding and compute bar pixel
    positions arithmetically. The planner should pick one approach in PLAN.
    """
    raise NotImplementedError("planner: pick bbox approach (see code comment)")
```

> **Planner note:** Bbox computation is the single most error-prone part of TRAIN-02. Two approaches:
>
> - **Approach A (preferred for determinism):** Disable mplfinance's auto-margins (set `tight_layout=False` and explicit `subplots_adjust`), compute bar pixel positions as `x_pixel = left_margin + (bar_idx + 0.5) * (plot_width / num_bars)`, derive y-axis pixel position from the rendered axes' data-to-display transform AFTER rendering but BEFORE resize. Save axes transform via `returnfig=True`, query `ax.transData.transform((bar_idx, price))`. Then scale to 640×640.
> - **Approach B (simpler, less precise):** Render once, identify bbox by drawing a known-color marker at the 5-bar corners, find the marker pixels post-render via numpy, remove markers and re-render — overhead but trivial logic.
>
> Approach A is the standard CV-pipeline pattern. Plan should commit to Approach A and add a unit test that asserts: for a synthetic 60-bar DataFrame with the 5-bar cluster at known positions, the computed bbox encloses the cluster and excludes neighbouring bars.

### Generator — `scripts/pattern_scanner/generate_training_data.py`

```python
# Source: scripts/fetch_sp500.py orchestration pattern + YOLOv8 dataset spec
"""Offline-only training data generator.

Outputs:
    _dev/training_dataset/images/{train,val}/<id>.png    (positives + negatives)
    _dev/training_dataset/labels/{train,val}/<id>.txt    (positive: "0 cx cy w h"; negative: empty)
    _dev/training_dataset/data.yaml                       (YOLOv8 dataset config)
    _dev/training_dataset/dataset_manifest.json
    models/dataset_manifest.json                          (committed copy)
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from scripts.pattern_scanner.detector import detect, Detection
from scripts.pattern_scanner.renderer import render, STYLES, compute_bbox_normalized
from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF

DATASET_ROOT = Path("_dev/training_dataset")
MIN_POSITIVES = 1000           # D-08
NEG_POS_RATIO = 10             # D-09

def _detect_positives(df: pd.DataFrame, ticker: str) -> list[Detection]:
    """Run filtered detector. Drop detections at or after TRAIN_TEST_CUTOFF."""
    cutoff = pd.Timestamp(TRAIN_TEST_CUTOFF)
    return [d for d in detect(df, ticker)
            if pd.Timestamp(d.confirmation_date) < cutoff]

def _detect_hard_negatives(df: pd.DataFrame, ticker: str,
                            positives: list[Detection]) -> list[Detection]:
    """Run filters-disabled detector; subtract real positives by (ticker, conf_date)."""
    cutoff = pd.Timestamp(TRAIN_TEST_CUTOFF)
    all_candidates = detect(df, ticker, apply_trend_filters=False)
    positive_keys = {(d.ticker, d.confirmation_date) for d in positives}
    return [c for c in all_candidates
            if (c.ticker, c.confirmation_date) not in positive_keys
            and pd.Timestamp(c.confirmation_date) < cutoff]

def _slice_window(df: pd.DataFrame, conf_idx: int) -> pd.DataFrame:
    """60-bar slice ending AT confirmation bar (D-03 right-aligned)."""
    start = conf_idx - 59
    if start < 0:
        return None
    return df.iloc[start:conf_idx + 1]

def _write_sample(png_bytes: bytes, label_line: str | None,
                   split: str, sample_id: str) -> str:
    """Write image + label. Returns sha256 of the PNG."""
    img_path = DATASET_ROOT / "images" / split / f"{sample_id}.png"
    lbl_path = DATASET_ROOT / "labels" / split / f"{sample_id}.txt"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    lbl_path.parent.mkdir(parents=True, exist_ok=True)
    img_path.write_bytes(png_bytes)
    lbl_path.write_text(label_line if label_line is not None else "")
    return hashlib.sha256(png_bytes).hexdigest()

def _write_data_yaml(num_positives: int) -> None:
    yaml_text = (
        f"path: {DATASET_ROOT.resolve()}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"nc: 1\n"
        f"names:\n  0: inside_bar_spring\n"
    )
    (DATASET_ROOT / "data.yaml").write_text(yaml_text)

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args(argv)

    rng = random.Random(args.seed)
    np_rng = np.random.default_rng(args.seed)

    tickers = _load_sp500_tickers()      # mirror scripts/fetch_sp500.py
    if args.limit:
        tickers = tickers[: args.limit]

    positives, negatives = [], []
    for t in tickers:
        df = yf.Ticker(t).history(period="10y", auto_adjust=True)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[["Open", "High", "Low", "Close"]]
        if len(df) < 60:
            continue
        # Map detection.confirmation_date → integer index in df
        # (detector returns confirmation_bar_index already; reuse it.)
        pos = _detect_positives(df, t)
        neg = _detect_hard_negatives(df, t, pos)
        positives.extend((t, df, d) for d in pos)
        negatives.extend((t, df, d) for d in neg)

    # 1000-positive gate (D-08)
    if len(positives) < MIN_POSITIVES:
        # Multi-style augmentation: re-emit each positive with N styles to reach floor
        positives = _augment_to_floor(positives, MIN_POSITIVES, rng)

    # Cap negatives at 10:1 (D-09) globally
    cap = NEG_POS_RATIO * len(positives)
    if len(negatives) > cap:
        rng.shuffle(negatives)
        negatives = negatives[:cap]

    # 80/20 train/val split inside training period (D-18 random within pre-cutoff)
    all_samples = [("pos", x) for x in positives] + [("neg", x) for x in negatives]
    rng.shuffle(all_samples)
    n_val = len(all_samples) // 5
    val_set, train_set = all_samples[:n_val], all_samples[n_val:]

    sha_concat = hashlib.sha256()
    for split, items in (("train", train_set), ("val", val_set)):
        for kind, (ticker, df, det) in items:
            window = _slice_window(df, det.confirmation_bar_index)
            if window is None:
                continue
            style = rng.choice(STYLES)
            png = render(window, style)
            label = None
            if kind == "pos":
                bbox = compute_bbox_normalized(
                    window,
                    mother_idx_in_window=det.mother_bar_index - (det.confirmation_bar_index - 59),
                    confirmation_idx_in_window=59,
                )
                cx, cy, w, h = bbox
                label = f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
            sample_id = f"{ticker}_{det.confirmation_date}_{kind}_{style.name}"
            sha = _write_sample(png, label, split, sample_id)
            sha_concat.update(bytes.fromhex(sha))

    _write_data_yaml(num_positives=len(positives))
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "seed": args.seed,
        "tickers": tickers,
        "date_range": {"period": "10y", "cutoff": TRAIN_TEST_CUTOFF},
        "positives": len(positives),
        "negatives": len(negatives),
        "neg_pos_ratio": len(negatives) / max(len(positives), 1),
        "concat_sha256": sha_concat.hexdigest(),
        "renderer_styles": [s.name for s in STYLES],
    }
    (DATASET_ROOT / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2))
    Path("models").mkdir(exist_ok=True)
    (Path("models") / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2))
    return 0
```

### Trainer — `scripts/pattern_scanner/train.py`

```python
# Source: docs.ultralytics.com/modes/train + docs.ultralytics.com/modes/export
"""Offline trainer + ONNX exporter. Run inside .venv with requirements-training.txt installed."""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

DATASET_ROOT = Path("_dev/training_dataset")
ONNX_OUT = Path("models/inside_bar_v1.onnx")

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--batch", type=int, default=-1)        # -1 = ultralytics auto-batch
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--patience", type=int, default=20)     # early stop
    args = p.parse_args(argv)

    from ultralytics import YOLO   # deferred — don't trigger torch import at CLI parse

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(DATASET_ROOT / "data.yaml"),
        imgsz=640,                  # D-04, D-17
        epochs=args.epochs,
        batch=args.batch,
        seed=args.seed,
        patience=args.patience,
        fliplr=0.0,                 # D-17 — pattern is directional
        # cls_pw: leave at default 1.0 — see RESEARCH §Common Pitfalls #4
        # box, obj loss weights also left at default (single-class)
    )
    print(f"[train] best mAP50: {results.box.map50}, mAP50-95: {results.box.map}")
    print(f"[train] best.pt: {results.save_dir}/weights/best.pt")

    # Reload best weights and export ONNX (D-17)
    best = YOLO(Path(results.save_dir) / "weights" / "best.pt")
    onnx_path = best.export(
        format="onnx",
        opset=12,                   # broadly compatible with onnxruntime >=1.18
        dynamic=False,              # fixed input shape — required for our verifier
        imgsz=640,
        simplify=True,
    )
    print(f"[export] ONNX written: {onnx_path}")
    print(f"[export] OPSET: 12  (logged to stdout per D-17)")

    ONNX_OUT.parent.mkdir(exist_ok=True)
    shutil.copy(onnx_path, ONNX_OUT)
    summary = {
        "opset": 12,
        "imgsz": 640,
        "epochs_run": int(results.epoch + 1),
        "best_map50": float(results.box.map50),
        "best_map50_95": float(results.box.map),
        "fliplr": 0.0,
        "seed": args.seed,
    }
    (ONNX_OUT.parent / "training_summary.json").write_text(json.dumps(summary, indent=2))
    return 0
```

### Verifier — `scripts/pattern_scanner/verify_onnx.py`

```python
# Source: research/SUMMARY.md Watch Out #3 + ultralytics ONNX postprocess docs
"""Clean-venv ONNX round-trip test (D-19).

Creates a temporary venv with ONLY onnxruntime + numpy + Pillow, then runs
inference on tests/fixtures/known_positive_*.png. Returns 0 if at least one
bbox with confidence >= 0.5 is decoded; non-zero on failure.
"""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from textwrap import dedent

ONNX_PATH = Path("models/inside_bar_v1.onnx")
FIXTURES_DIR = Path("tests/fixtures")
CONFIDENCE_FLOOR = 0.5

INFERENCE_SCRIPT = dedent('''
    """Pure onnxruntime + numpy + Pillow inference (no torch, no ultralytics)."""
    import json, sys
    from pathlib import Path
    import numpy as np
    import onnxruntime as ort
    from PIL import Image

    ONNX, FIXTURE = sys.argv[1], sys.argv[2]
    sess = ort.InferenceSession(ONNX, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    out_names = [o.name for o in sess.get_outputs()]
    print(f"[verify] input: {inp.name} {inp.shape}")
    print(f"[verify] outputs: {out_names}")

    img = Image.open(FIXTURE).convert("RGB").resize((640, 640), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float32) / 255.0       # 0..1
    arr = arr.transpose(2, 0, 1)[None, ...]                # NCHW
    raw = sess.run(out_names, {inp.name: arr})[0]          # shape (1, 5, N) for single class

    # Postprocess YOLOv8 ONNX output (no NMS in graph by default).
    # Output layout: (1, 4 + nc, num_anchors). For nc=1 → (1, 5, N).
    pred = raw[0]                                           # (5, N)
    pred = pred.T                                           # (N, 5) = [cx, cy, w, h, score]
    scores = pred[:, 4]
    keep = scores >= 0.25                                   # initial conf threshold
    if not keep.any():
        print(json.dumps({"detections": [], "max_score": float(scores.max())}))
        sys.exit(1)
    boxes = pred[keep, :4]                                  # cx, cy, w, h in pixel coords
    confs = pred[keep, 4]

    # NMS (numpy, IoU 0.45)
    def nms(boxes_xywh, scores_arr, iou_thr=0.45):
        # convert xywh -> xyxy
        x1 = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2
        y1 = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2
        x2 = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2
        y2 = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2
        areas = (x2 - x1) * (y2 - y1)
        order = scores_arr.argsort()[::-1]
        kept = []
        while order.size:
            i = order[0]; kept.append(int(i))
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0, xx2 - xx1); h = np.maximum(0, yy2 - yy1)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            order = order[1:][iou <= iou_thr]
        return kept

    keep_idx = nms(boxes, confs)
    final = [{"box": boxes[i].tolist(), "conf": float(confs[i])} for i in keep_idx]
    print(json.dumps({"detections": final, "max_score": float(confs.max())}))
''').strip()


def main(argv=None) -> int:
    if not ONNX_PATH.exists():
        print(f"[verify] FAIL: {ONNX_PATH} does not exist", file=sys.stderr)
        return 2
    fixtures = sorted(FIXTURES_DIR.glob("known_positive_*.png"))
    if not fixtures:
        print(f"[verify] FAIL: no fixtures in {FIXTURES_DIR}", file=sys.stderr)
        return 3

    with tempfile.TemporaryDirectory(prefix="onnx_verify_") as tmp:
        tmp_path = Path(tmp)
        venv_path = tmp_path / "venv"
        print(f"[verify] creating clean venv at {venv_path}")
        venv.create(str(venv_path), with_pip=True)

        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        py = venv_path / bin_dir / ("python.exe" if sys.platform == "win32" else "python")
        pip = venv_path / bin_dir / ("pip.exe" if sys.platform == "win32" else "pip")

        subprocess.check_call([str(pip), "install", "--quiet",
                                "onnxruntime>=1.19", "numpy>=1.26", "Pillow>=10.0"])

        script = tmp_path / "infer.py"
        script.write_text(INFERENCE_SCRIPT)

        any_pass = False
        for fx in fixtures:
            print(f"[verify] running on {fx.name}")
            res = subprocess.run(
                [str(py), str(script), str(ONNX_PATH.resolve()), str(fx.resolve())],
                capture_output=True, text=True,
            )
            print(res.stdout)
            if res.returncode != 0:
                print(res.stderr, file=sys.stderr)
                continue
            try:
                payload = json.loads(res.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                continue
            if any(d["conf"] >= CONFIDENCE_FLOOR for d in payload["detections"]):
                any_pass = True
                print(f"[verify] PASS: {fx.name} got conf >= {CONFIDENCE_FLOOR}")

        return 0 if any_pass else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### Phase 7 detect() Modification — `scripts/pattern_scanner/detector.py`

```python
# Existing signature (Phase 7, line 305):
# def detect(df: pd.DataFrame, ticker: str) -> List[Detection]:

# Phase 8 change — add ONE kwarg with default that preserves existing behaviour:
def detect(df: pd.DataFrame, ticker: str,
            apply_trend_filters: bool = True) -> List[Detection]:
    """... existing docstring ...

    Args:
        ...
        apply_trend_filters: when True (default — Phase 7 contract), only
            emit detections whose three trend filters all pass. When False
            (Phase 8 hard-negative pool), emit every detection that passes
            the cluster shape rules regardless of filter state. Per-filter
            booleans are recorded in either mode (D-08).
    """
    # ... existing body unchanged through line 367 ...
    detection = _build_detection(...)
    if not apply_trend_filters:
        detections.append(detection)
    elif (detection.filters["hh_hl"]
          and detection.filters["above_50sma"]
          and detection.filters["sma_cluster"]):
        detections.append(detection)
    # ... unchanged ...
```

**Impact analysis:**
- All 23 existing tests in `tests/test_detector_schema.py` (12) + `tests/test_detector_known_setups.py` (11) call `detect(df, ticker)` with positional args only. Default kwarg preserves Phase 7 behaviour exactly — zero test changes required.
- Phase 7's CLI `main()` (line 408) calls `detect(df, ticker)` — unaffected.
- New test `tests/test_detector_apply_trend_filters_kwarg.py`: assert that `detect(df, t, apply_trend_filters=False)` returns ≥ as many detections as the default call on the same fixture, AND that the difference set has at least one element where one of the three filters is False.

### YOLOv8 `data.yaml` Format

```yaml
# Source: docs.ultralytics.com/datasets/detect/
path: /absolute/path/to/_dev/training_dataset
train: images/train
val: images/val
nc: 1
names:
  0: inside_bar_spring
```

### YOLOv8 Label File Format (positive)

```
# tests/example_label.txt — one line per box, normalized to image size 0..1
# class_id  cx  cy  w  h
0 0.873 0.412 0.187 0.354
```

### YOLOv8 Label File Format (negative / background)

Empty file. Same path as positive but with `.txt` extension and zero bytes:

```
# tests/example_negative.txt has zero content
```

---

## Runtime State Inventory

Phase 8 is greenfield (creates new files; modifies one with backward-compatible kwarg). No rename/refactor/migration. **Section omitted** per RESEARCH.md instructions.

---

## Common Pitfalls

### Pitfall 1: Renderer style memorization (research Watch-Out #2)
**What goes wrong:** YOLOv8 trains on a single rendering config and learns "candle width = 0.6 + white background = pattern present" rather than the abstract 5-bar shape.
**Why it happens:** Single mplfinance style across all training images.
**How to avoid:** 3+ named styles in `STYLES` tuple; randomly select per-sample via seeded `random.Random`. Disable horizontal flip (`fliplr=0.0`) — pattern is directional. **Already locked by D-17 + D-11.**
**Warning signs:** Validation mAP very high (> 0.95) but model fails on Phase 10's nightly real-world charts → trained the renderer, not the pattern.

### Pitfall 2: ONNX opset mismatch — silent wrong output (research Watch-Out #3)
**What goes wrong:** ultralytics 8.4 may export opset 17 by default; older onnxruntime (<1.18) cannot load opset 17 cleanly.
**Why it happens:** Ultralytics auto-picks "best" opset per its `best_onnx_opset` heuristic, which tracks newer versions.
**How to avoid:** Explicitly pass `opset=12` to `model.export()` — broadly compatible with onnxruntime ≥ 1.16. Log opset to stdout AND write to `training_summary.json`. Round-trip test in clean venv (D-19) catches divergence.
**Warning signs:** Verifier returns empty detection list on a fixture that visually matches a positive — load worked but inference produced silent wrong output. [CITED: github.com/ultralytics/ultralytics/issues/19498, issues/380]

### Pitfall 3: NMS responsibility — YOLOv8 ONNX export does NOT include NMS by default
**What goes wrong:** Verifier loads ONNX, runs `sess.run(...)`, finds raw `(1, 5, N)` tensor, assumes detections — but every anchor has a score. Without NMS, you get hundreds of overlapping boxes.
**Why it happens:** Default `model.export(format="onnx", ...)` exports the raw detection head; ultralytics applies NMS in Python post-inference by default.
**How to avoid:** Apply NMS in `verify_onnx.py` using pure numpy (~30 lines, see §Code Examples — Verifier). Phase 10's nightly inference will follow the same recipe — keep it in `scripts/pattern_scanner/model.py` (Phase 10 file) so the verifier and runtime use identical postprocessing.
**Warning signs:** Verifier's `max_score` is high but `len(detections)` is in the hundreds → NMS missing. [CITED: github.com/orgs/ultralytics/discussions/20712]

### Pitfall 4: `cls_pw` is the WRONG lever for empty-label background imbalance — IMPORTANT CORRECTION TO CONTEXT D-17
**What goes wrong:** D-17 says `cls_pw` is "tuned to compensate for the 10:1 imbalance." But `cls_pw` is the **classification-loss positive weight** — it scales positive class weights vs other CLASSES. With ONE class and BACKGROUND as empty labels, `cls_pw` has effectively no impact.
**Why it happens:** `cls_pw` is for multi-class confusion (penalize false positives between classes). Empty-label backgrounds contribute to the **objectness** loss, not the classification loss. The 10:1 cap controls the OBJECTNESS imbalance directly by limiting the number of "no-object" gradient signals.
**How to avoid:**
- Leave `cls_pw=1.0` (default).
- Rely on the 10:1 cap (D-09) — this is the actual mechanism.
- If recall is low after first training, the next levers are (in order): (a) increase `box` and `obj` loss weights, (b) lower `conf` floor in val, (c) consider focal loss via `obj_pw`, (d) augment positives via multi-style (D-08) even if floor is met.
**Warning signs:** Val precision very high, recall very low → model is biased to "no detection." This is the imbalance failure mode; `cls_pw` won't fix it.
**Action:** Plan should NOT include a "tune cls_pw" task. Plan SHOULD include a "verify cls_pw=1.0 and document rationale in 08-SUMMARY" task. This is the most consequential research correction to CONTEXT.md. [CITED: github.com/ultralytics/ultralytics/issues/2208, #8889, #12941]

### Pitfall 5: 60-bar slicing edge case — early ticker history
**What goes wrong:** A ticker with confirmation_bar_index < 59 (e.g., a recent IPO) cannot produce a 60-bar window. `df.iloc[-1:60]` would produce a smaller frame, mplfinance would render it, and YOLO would train on a non-60-bar input.
**Why it happens:** Confirmation bars near the start of the available history.
**How to avoid:** Skip samples where `conf_idx < 59` in the generator. Already shown in `_slice_window` returning `None`.
**Warning signs:** mplfinance renders with fewer candles per image than expected; bbox normalization off.

### Pitfall 6: Reproducibility is bounded by yfinance + matplotlib font hinting
**What goes wrong:** The user expects "anyone with the same seed gets the same dataset" — but yfinance back-revises adjusted prices when corporate actions get re-classified, and matplotlib's font rasterizer differs across OS/font-cache states.
**Why it happens:**
- yfinance returns *currently-known* adjusted closes; a 2020-04-13 bar may have a slightly different adjusted close in 2024 vs 2026.
- matplotlib uses freetype + each OS has slightly different font metrics → identical Python+seed → different PNG bytes.
**How to avoid:** Document the manifest's reproducibility scope honestly:
- "Manifest sha256s reproduce when (yfinance data revision is identical) AND (Python+matplotlib+mplfinance versions match) AND (OS font rendering matches)."
- The seed reproduces all RANDOM CHOICES (style picks, train/val split, negative subsampling). It does NOT reproduce render bytes across machines.
- Pin matplotlib version explicitly. Pin a specific font in `mpf_style.rc["font.family"]` (e.g., `"DejaVu Sans"` ships with matplotlib).
**Warning signs:** Manifest sha256 mismatch on a different machine — expected; not a bug.

### Pitfall 7: Hard-negative key collision via `(ticker, confirmation_date)`
**What goes wrong:** A given ticker may have two distinct candidate detections with the same `confirmation_date` (e.g., spring + non-spring on the same bar — possible when classifier precedence picks one type but another type's confirmation closure also passes).
**Why it happens:** `(ticker, confirmation_date)` may not uniquely identify a Detection.
**How to avoid:** Per Phase 7 detector logic (line 372-373), the inner loop emits at most one detection per mother bar (`break  # one confirmation per break-below`). So `(ticker, mother_bar_index)` IS unique. Recommend keying the set difference on `(ticker, mother_bar_index, confirmation_bar_index)` rather than `confirmation_date` to be safe.
**Warning signs:** Negative count exactly equals filters-disabled count → set difference produced empty intersection → key is wrong.

### Pitfall 8: ultralytics auto-downloads `yolov8n.pt` to repo root
**What goes wrong:** Running `YOLO("yolov8n.pt")` for the first time pulls `yolov8n.pt` (~6 MB) into the current working directory. Without a `.gitignore` entry, it gets committed.
**How to avoid:** Add `yolov8n.pt` to `.gitignore` before the first training run.
**Warning signs:** Stale weights file in `git status` after first train.

### Pitfall 9: Bbox right-aligned framing makes the cluster always touch the right edge
**What goes wrong:** Per D-03, the confirmation bar is the rightmost bar — so `x1` of the bbox is always ≈ 1.0. The model can shortcut "if rightmost cluster, predict pattern." Negative images will also have right-aligned candidates, so this is mitigated by hard-negative design — but if hard negatives have any window-position diversity, the shortcut becomes valid.
**Why it happens:** Right-alignment is intentional (CONTEXT D-03 — eliminates train/inference mismatch).
**How to avoid:** Confirm hard-negative windows are ALSO right-aligned at the (filters-disabled) confirmation bar — this is already true in the generator design. Document in 08-SUMMARY: "Right-edge framing is uniform across positives and hard-negatives; the discrimination signal is INSIDE the cluster shape, not its position."
**Warning signs:** Test on a centered-cluster image (artificial) and model fails → confirms model learned "rightmost = pattern". Acceptable per D-03.

### Pitfall 10: 1000-positive gate may not be reachable on S&P 500 + 10y + filtered
**What goes wrong:** Phase 7's filter strictness (HH/HL + above 50-SMA + SMA cluster) is intentionally narrow. A naive estimate is ~5-15 detections per ticker × 503 tickers × pre-cutoff = 2,000-7,000 — but the trend-filter intersection may shrink this dramatically.
**How to avoid:**
- Plan Wave 0 should include a "dry-run count" task: run the generator with `--limit 50 --seed 42` and report positive count. Extrapolate.
- If estimate is < 1000, the multi-style augmentation (D-08) takes over; document the augmentation factor (e.g., "each of N positives rendered in 3 styles → 3N samples").
- If even with 3 styles the count is below 1000, escalate to user — milestone-blocking.
**Warning signs:** Generator logs "positives: 412" — multi-style needed. "positives: 89" — escalate.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `.venv` | All scripts (per CLAUDE.md MEMORY) | ✓ | 3.14.4 | — |
| numpy | renderer/generator/verifier | ✓ | 2.4.4 (already in venv) | — |
| pandas | generator | ✓ | 3.0.2 (already in venv) | — |
| yfinance | generator | ✓ | 0.2.65 (already pinned) | cached parquet (deferred) |
| ultralytics + torch | trainer | ✓ (dry-run resolves) | ultralytics 8.4.46, torch 2.11.0 | — |
| mplfinance | renderer | ✓ (dry-run resolves) | 0.12.10b0 | — |
| matplotlib | renderer (transitive of mplfinance) | ✓ | 3.10.9 | — |
| onnxruntime | verifier + Phase 10 | ✓ | 1.25.1 | — |
| Pillow | renderer/verifier | ✓ | 12.2.0 | — |
| `venv` stdlib module | verifier (for clean-venv test) | ✓ | stdlib in Py 3.14 | — |
| Internet (yfinance + ultralytics weight pull) | generator + trainer first run | ✓ (project routinely uses yfinance) | — | None — required |
| GPU | trainer (optional) | UNKNOWN | — | CPU path supported by ultralytics; document final wall time per D-16 |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

[VERIFIED 2026-05-02 via `pip install --dry-run ultralytics` and `pip install --dry-run mplfinance` against this project's `.venv` (Python 3.14.4, numpy 2.4.4)]

---

## Validation Architecture (Nyquist Dimension 8)

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4 (existing from Phase 7) |
| Config file | `pytest.ini` (existing — `testpaths = tests`, registers `network` marker) |
| Quick run command | `source .venv/Scripts/activate && python -m pytest tests/ -q --no-network` |
| Full suite command | `source .venv/Scripts/activate && python -m pytest tests/ -q` |
| Phase 8-specific full | `source .venv/Scripts/activate && python -m pytest tests/test_renderer.py tests/test_generate_training_data.py tests/test_onnx_round_trip.py tests/test_detector_apply_trend_filters_kwarg.py -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Status |
|--------|----------|-----------|-------------------|-------------|
| TRAIN-01 | Renderer produces 640×640 PNG from 60-bar yfinance DataFrame | unit (offline) | `pytest tests/test_renderer.py::test_render_returns_640x640_png -x` | ❌ Wave 0 |
| TRAIN-01 | Renderer is deterministic given the same style | unit (offline) | `pytest tests/test_renderer.py::test_render_deterministic_same_style -x` | ❌ Wave 0 |
| TRAIN-01 | Renderer produces visually distinct outputs across styles | unit (offline) | `pytest tests/test_renderer.py::test_render_styles_differ -x` (asserts byte-distinct outputs for the same df with 3 different styles) | ❌ Wave 0 |
| TRAIN-02 | Generator emits YOLO-format directory structure with `data.yaml` | unit (offline + tmp_path) | `pytest tests/test_generate_training_data.py::test_yolo_directory_layout -x` | ❌ Wave 0 |
| TRAIN-02 | Positive label files are normalized to 0..1 with class_id 0 | unit (offline) | `pytest tests/test_generate_training_data.py::test_positive_label_format -x` | ❌ Wave 0 |
| TRAIN-02 | Style randomisation is invoked for every sample | unit (offline) | `pytest tests/test_generate_training_data.py::test_style_randomization_used -x` | ❌ Wave 0 |
| TRAIN-02 | TRAIN_TEST_CUTOFF excludes post-cutoff detections | unit (offline) | `pytest tests/test_generate_training_data.py::test_cutoff_enforced -x` | ❌ Wave 0 |
| TRAIN-03 | Negative-to-positive ratio is exactly 10:1 in generated dataset | unit (offline + small fixture) | `pytest tests/test_generate_training_data.py::test_neg_pos_ratio_capped -x` | ❌ Wave 0 |
| TRAIN-03 | Negative samples have empty `.txt` label files | unit (offline) | `pytest tests/test_generate_training_data.py::test_negative_labels_empty -x` | ❌ Wave 0 |
| TRAIN-03 | Hard-negative pool is `filters-disabled MINUS real positives` | unit (offline) | `pytest tests/test_generate_training_data.py::test_hard_negative_set_difference -x` | ❌ Wave 0 |
| TRAIN-04 | ONNX file exists at `models/inside_bar_v1.onnx` | smoke | `test -f models/inside_bar_v1.onnx` (Bash) | manual after train |
| TRAIN-04 | ONNX opset is logged in `models/training_summary.json` | unit | `pytest tests/test_onnx_round_trip.py::test_opset_recorded -x` | ❌ Wave 0 |
| TRAIN-04 | ONNX loads in clean venv with onnxruntime+numpy+Pillow only | integration | `python scripts/pattern_scanner/verify_onnx.py` (returns 0) | manual gate |
| TRAIN-04 | ONNX produces ≥1 bbox conf ≥ 0.5 on fixture PNG | integration | (same as above) | manual gate |
| TRAIN-04 | Manifest sha256 matches dataset on-disk | unit | `pytest tests/test_generate_training_data.py::test_manifest_sha256_consistent -x` | ❌ Wave 0 |
| (Phase 7 contract) | `detect()` default kwarg preserves Phase 7 behaviour | regression | `pytest tests/test_detector_apply_trend_filters_kwarg.py::test_default_kwarg_matches_phase7 -x` | ❌ Wave 0 |
| (Phase 7 contract) | `apply_trend_filters=False` returns superset | regression | `pytest tests/test_detector_apply_trend_filters_kwarg.py::test_unfiltered_is_superset -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -q --no-network` (full unit + integration suite, network-skipped).
- **Per wave merge:** Same as above + smoke run of `verify_onnx.py` if ONNX exists.
- **Phase gate:** `verify_onnx.py` exits 0 in a NEW clean venv (not the project venv) — proves no torch leakage.

### Wave 0 Gaps

- [ ] `tests/fixtures/known_positive_aapl_2020.png` — committed fixture (1 file, < 100 KB) for the round-trip test. Must come from a known positive run of the trained model OR a hand-rendered known-setup chart.
- [ ] `tests/test_renderer.py` — covers TRAIN-01 (3 tests: 640×640 output, determinism, style variance).
- [ ] `tests/test_generate_training_data.py` — covers TRAIN-02 + TRAIN-03 (8 tests using small synthetic ticker subsets).
- [ ] `tests/test_onnx_round_trip.py` — covers TRAIN-04 opset/manifest checks (round-trip itself is a CLI smoke, not pytest).
- [ ] `tests/test_detector_apply_trend_filters_kwarg.py` — Phase 7 contract preservation (2 tests).
- [ ] No new framework install required — pytest is already in `requirements-dev.txt`.

### Critical Test: Phase 7 Compatibility

The plan MUST run the Phase 7 test suite green AFTER the kwarg change:

```bash
source .venv/Scripts/activate && python -m pytest tests/test_detector_schema.py tests/test_detector_known_setups.py -q
```

Expected: 12 + 11 = 23 tests pass (or 12 pass + 11 skip if `--no-network`). Any regression is a hard rollback gate.

---

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json`; treat as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no auth surface in offline training) |
| V3 Session Management | no | — |
| V4 Access Control | no | — (no user-facing endpoints touched) |
| V5 Input Validation | yes | yfinance ticker regex (already in `_TICKER_RE` from Phase 7); CLI argparse type-checks; `--seed` is `int`; ONNX file path validation (Path.exists) |
| V6 Cryptography | partial | sha256 manifest is for INTEGRITY not secrecy — use stdlib `hashlib.sha256`, never hand-roll |
| V12 File and Resource | yes | dataset writes confined to `_dev/training_dataset/` (gitignored); fixture committed to `tests/fixtures/`; no path traversal vectors (file IDs are `f"{ticker}_{date}_{kind}_{style}"` with predictable charset) |
| V14 Configuration | yes | `requirements-training.txt` MUST NOT be installed by Render or any CI workflow — verify by grep over `.github/workflows/` and `Procfile` |

### Known Threat Patterns for Offline ML Training

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pickle deserialization (ultralytics `.pt` files contain pickled state) | Tampering | Treat `.pt` as trusted only because it's auto-downloaded from official ultralytics CDN; never load `.pt` from untrusted sources. Document in 08-SUMMARY. |
| ONNX model tampering between commit and deploy | Tampering | Round-trip test (D-19) confirms loadable; manifest sha256 logs dataset state. Recommend ALSO logging sha256 of the committed `.onnx` itself in `training_summary.json` for tamper evidence. |
| yfinance MITM (less likely — HTTPS) | Spoofing | yfinance uses curl_cffi over HTTPS (already in production stack); no special mitigation needed |
| Path injection via ticker / sample_id | Tampering | Tickers validated by `_TICKER_RE`; sample_id constructed from `(ticker, ISO date, kind, style.name)` — all controlled values. |
| ultralytics auto-download from internet | Spoofing | The first `YOLO("yolov8n.pt")` call hits the internet. Acceptable for an offline-training one-shot; not in production CI. |
| `verify_onnx.py` subprocess pip install | Tampering / DoS | Pinning versions in the verifier's pip call (`onnxruntime>=1.19`) reduces risk; verifier runs in temp dir cleaned by `TemporaryDirectory` context manager |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | YOLOv8 ONNX export does NOT include NMS by default in opset 12 mode | Pitfall #3, Verifier | If wrong, the verifier's NMS adds redundant work but does NOT break correctness |
| A2 | `cls_pw=1.0` is correct for empty-label background imbalance — D-17's framing is incomplete | Pitfall #4 | If `cls_pw` IS the right knob and we leave it default, recall may suffer; mitigation: post-train val mAP gate already required, so we'd see this before commit |
| A3 | mplfinance + matplotlib + Pillow + onnxruntime resolve cleanly together on Python 3.14 + numpy 2.4.4 | Stack | [VERIFIED via pip dry-run 2026-05-02] — not an assumption anymore |
| A4 | `opset=12` is broadly supported by `onnxruntime >= 1.18` | Pitfall #2 | [CITED: ultralytics issue #380] |
| A5 | The 1,000-positive gate is reachable from S&P 500 × 10y × pre-cutoff filters | Pitfall #10 | If unreachable even with multi-style augmentation, milestone is blocked. Plan must include a dry-run early. |
| A6 | mplfinance renders are NOT bit-identical across machines, only within the same machine | Pitfall #6 | Manifest sha256 cannot be a cross-machine equality gate; document accordingly |
| A7 | Adding `apply_trend_filters: bool = True` kwarg to `detect()` does not break any existing test | Code Examples | [VERIFIED by code reading: no existing call site uses positional 3rd arg or **kwargs unpacking that would conflict] |
| A8 | yolov8n.pt is auto-downloaded by ultralytics on first run and lives in cwd | Pitfall #8 | If ultralytics changes this, the .gitignore entry is harmless |
| A9 | `_dev/training_dataset/` size is ≤ 10 GB (~11k samples × 640×640 RGB ≈ 13 MB raw / ~50 KB compressed × 11k = 550 MB compressed) | Architecture | If much larger, may bump against local disk limits — flag in plan to monitor |
| A10 | Bbox can be computed deterministically by disabling mplfinance auto-margins (Approach A) | Code Examples — Renderer planner note | If matplotlib's transform yields non-deterministic values across rendered figures of same size, fall back to Approach B (marker-pixel detection) — pre-commit decision required |

**Items A1-A4, A7, A8 are verified or well-cited.** Items **A2 (cls_pw correction)**, **A5 (positive count reachability)**, **A6 (cross-machine reproducibility)**, **A9 (disk size)**, and **A10 (bbox approach)** need user confirmation or are open questions to surface in the plan.

---

## Open Questions

1. **Bbox computation approach (Approach A vs Approach B)**
   - What we know: Both produce correct bboxes; A is the canonical CV-pipeline pattern; B is simpler.
   - What's unclear: Whether matplotlib's `transData.transform()` produces deterministic pixel coordinates after `bbox_inches="tight"` cropping.
   - Recommendation: Plan a Wave 0 spike (one task, ~15 min): render one chart with Approach A, log computed bbox; render the same chart with bbox-marker injection; compare. If A is within ±2 px of B, ship A.

2. **Initial yolov8n.pt source**
   - What we know: ultralytics auto-downloads from `https://github.com/ultralytics/assets/releases/...` on first call.
   - What's unclear: Whether the user's local environment can reach that URL during the planned execution window.
   - Recommendation: Plan a Wave 0 connectivity check (one Bash task): `curl -I https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt` returns 200/302.

3. **Local hardware: GPU available?**
   - What we know: D-16 says "Local CPU/GPU; ultralytics auto-detects."
   - What's unclear: Whether this machine has CUDA-capable GPU. CPU training of YOLOv8n on ~11k 640×640 images for ~50 epochs is roughly 4-8 hours.
   - Recommendation: Plan should include a GPU-check task (`python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"`) before kicking off the long training run, and document in 08-SUMMARY.

4. **Multi-style augmentation factor**
   - What we know: D-08 says "trigger if positives < 1000". CONTEXT says "multiple randomised styles."
   - What's unclear: Exact augmentation factor (2 styles? 3? 5?). Implementation detail.
   - Recommendation: Define in plan: if positives ≥ 1000, use 1 style per sample. If positives < 1000, use `ceil(1000 / N) + 1` styles per sample, capped at len(STYLES) = 3. Escalate to user if even 3× < 1000.

5. **Should the committed `.onnx` be tracked in git or via Git LFS?**
   - What we know: D-13 says "no Git LFS." 6-12 MB is well under GitHub's 100 MB hard limit and 50 MB soft warning.
   - What's unclear: GitHub Pages bandwidth/repo size impact on cloning experience.
   - Recommendation: Honor D-13 (regular git). At 12 MB, repo growth is negligible.

6. **ONNX opset 12 vs 17**
   - What we know: opset 12 is broadly safe; opset 17 is required for TensorRT 10.7 (not relevant here) and offers some perf wins on newer onnxruntime.
   - What's unclear: Whether onnxruntime 1.19+ is stable on opset 12 for YOLOv8n inference.
   - Recommendation: Lock opset 12. Revisit only if Phase 10 inference shows perf issues.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| YOLOv5 ONNX export with manual NMS post-processing | YOLOv8 `model.export(format="onnx", ...)` | ultralytics 8.0 (Jan 2023) | One-line export; NMS still post-processed by default — recipe unchanged |
| `pip install` numpy 1.x for everything | numpy 2.x (project already on 2.4.4) | Jun 2024 (numpy 2.0); onnxruntime 1.19 added support | No action needed; pin onnxruntime >= 1.19 |
| matplotlib < 3.8 with numpy 1.x | matplotlib 3.8+ with numpy 2.x | Sep 2023 (matplotlib 3.8) | Pin matplotlib >= 3.8 |
| Single-style training data → renderer memorisation | Multi-style randomization (DPI/figsize/candle width/background) | Industry pattern, no specific date | Locked by D-17 + Watch-Out #2 |
| Pickle .pt deployment in production | ONNX-only deployment (no torch in CI) | Project decision (research/SUMMARY) | Locked by Architecture Decision #1 |

**Deprecated/outdated:**
- `torchvision.ops.nms` in production inference — not available in our clean inference venv; replaced by numpy NMS.
- Hand-rolled candle drawing — mplfinance is now mature (post-1.0 stable since 2024 even though still labelled `0.12.10b0`).

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED] `pip install --dry-run` against project's own `.venv` (Python 3.14.4, numpy 2.4.4) — confirmed mplfinance 0.12.10b0, ultralytics 8.4.46, torch 2.11.0, onnxruntime 1.25.1, matplotlib 3.10.9, Pillow 12.2.0 all resolve cleanly. Date: 2026-05-02.
- [VERIFIED] `scripts/pattern_scanner/detector.py` lines 305-376 — verified `detect()` signature and call sites; positional-only call patterns in tests/test_detector_*.py confirm kwarg addition is non-breaking.
- [VERIFIED] `tests/test_detector_schema.py` 12 tests + `tests/test_detector_known_setups.py` 11 tests — call surface analysed.
- [CITED] [Ultralytics ONNX Export docs](https://docs.ultralytics.com/integrations/onnx/) — opset/parameter surface
- [CITED] [Ultralytics Train docs](https://docs.ultralytics.com/modes/train/) — `cls_pw`, `fliplr`, `imgsz`, `seed`, `patience` semantics
- [CITED] [Ultralytics Datasets docs](https://docs.ultralytics.com/datasets/detect/) — `data.yaml` format, label file format, background image convention
- [CITED] [mplfinance README](https://github.com/matplotlib/mplfinance) — `savefig=BytesIO`, `update_width_config`, `style` system

### Secondary (MEDIUM confidence)
- [Ultralytics issue #19498 — IR Version on ONNX export](https://github.com/ultralytics/ultralytics/issues/19498)
- [Ultralytics issue #380 — Specify ONNX OpSet version](https://github.com/ultralytics/ultralytics/issues/380)
- [Ultralytics discussion #20712 — YOLOv8 ONNX postprocess (NMS)](https://github.com/orgs/ultralytics/discussions/20712)
- [Ultralytics issue #2208 — class imbalance with cls_pw](https://github.com/ultralytics/ultralytics/issues/2208)
- [Ultralytics issue #8889 — background images in detection](https://github.com/ultralytics/ultralytics/issues/8889)
- [Ultralytics issue #12941 — empty background images effectiveness](https://github.com/ultralytics/ultralytics/issues/12941)
- [Ultralytics issue #13132 — single-class training without cls loss](https://github.com/ultralytics/ultralytics/issues/13132)
- [Ultralytics ONNXRuntime example main.py](https://github.com/ultralytics/ultralytics/blob/main/examples/YOLOv8-ONNXRuntime/main.py)
- [mplfinance issue #250 — saved plot sizing](https://github.com/matplotlib/mplfinance/issues/250)
- [mplfinance issue #37 — output to buffer](https://github.com/matplotlib/mplfinance/issues/37)
- [mplfinance savefig.ipynb example](https://github.com/matplotlib/mplfinance/blob/master/examples/savefig.ipynb)
- [onnxruntime Compatibility docs](https://onnxruntime.ai/docs/reference/compatibility.html)
- [onnxruntime issue #21063 — numpy 2.0 support](https://github.com/microsoft/onnxruntime/issues/21063)
- [Stitching NMS to YOLOv8n ONNX (Stephen Cow Chau)](https://stephencowchau.medium.com/stitching-non-max-suppression-nms-to-yolov8n-on-exported-onnx-model-1c625021b22)

### Tertiary (LOW confidence — flagged for validation)
- Estimated wall-clock times for CPU YOLOv8n training (4-8 h for ~11k images at 50 epochs) — based on community reports; will be empirically confirmed in 08-SUMMARY post-train.
- Estimated dataset-on-disk size (~550 MB compressed) — order-of-magnitude only; will be measured.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified live via pip dry-run on 2026-05-02 in project's own .venv.
- Architecture: HIGH — fully constrained by CONTEXT D-01..D-20; research filled in mechanics only.
- Pitfalls: HIGH — well-documented ML engineering risks; cls_pw correction (Pitfall #4) is the single material correction surfaced.
- Reproducibility scope (manifest sha256 caveats): MEDIUM — the cross-machine determinism limit is a known ML pipeline reality but not formally verified for this exact mplfinance + matplotlib combination.

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (30 days — ultralytics ships weekly; if planning slips past June, re-verify ultralytics version and any opset default changes)
