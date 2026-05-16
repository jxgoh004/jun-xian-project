# Phase 8: Training Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 08-training-pipeline
**Areas discussed:** Chart framing & bbox, Training universe & volume, Negative sampling strategy, Dataset & training env

---

## Chart framing & bbox

### Q1: How many bars should each training image show?

| Option | Description | Selected |
|--------|-------------|----------|
| 60 bars (~3 mo) | Matches Phase 7 HH/HL lookback (D-05); same trend context the algorithmic filters used. | ✓ |
| 30 bars (~6 wk) | Tighter focus on the immediate setup zone; faster training, smaller PNGs. | |
| 120 bars (~6 mo) | Wider context including 50-SMA region; pattern small relative to the chart. | |

**User's choice:** 60 bars (Recommended)

### Q2: What does the YOLO bounding box enclose?

| Option | Description | Selected |
|--------|-------------|----------|
| 5 bars only, tight | Bbox covers exactly the 5 bars (mother → confirmation), tight to OHLC envelope. | ✓ |
| 5 bars + 2 bar padding | Wider on each side to avoid wick clipping; slightly fuzzier ground truth. | |
| Mother high → confirmation close | Vertical extent restricted to the "meaningful" range; risk of clipping wicks. | |

**User's choice:** 5 bars only, tight (Recommended)

### Q3: Where should the 5-bar pattern sit within the 60-bar window?

| Option | Description | Selected |
|--------|-------------|----------|
| Right-aligned | Confirmation bar is rightmost; train and inference framing identical. | ✓ |
| Random offset (5–20 from right) | Position augmentation; complicates inference scanning. | |
| Centered at bar 30 | Symmetric context but creates train/inference distribution mismatch. | |

**User's choice:** Right-aligned (Recommended)

### Q4: What output PNG dimensions for training images?

| Option | Description | Selected |
|--------|-------------|----------|
| 640 × 640 px | YOLOv8 default training resolution; no resize artifacts. | ✓ |
| 832 × 832 px | Higher resolution preserves more candle detail; slower training, more VRAM. | |
| Match figsize randomization | Output varies per image; YOLO resizes to 640 anyway. | |

**User's choice:** 640 × 640 px (Recommended)

---

## Training universe & volume

### Q5: Which ticker universe do we mine for training detections?

| Option | Description | Selected |
|--------|-------------|----------|
| Full S&P 500 current constituents | ~503 tickers; matches inference universe; survivor bias documented. | ✓ |
| S&P 500 + S&P 400 mid-caps | Wider universe (~900); mismatch with inference universe. | |
| Top 100 by liquidity | Smaller, cleaner; risks under-shooting positive count. | |

**User's choice:** Full S&P 500 current constituents (Recommended)

### Q6: How much historical data per ticker?

| Option | Description | Selected |
|--------|-------------|----------|
| 10 years | Matches Phase 9's planned backtest window. | ✓ |
| 15 years | More history but regime-drift risk (pre-2010 candle behavior differs). | |
| 5 years | Tighter, more recent regime; likely undershoots positive count. | |

**User's choice:** 10 years (Recommended)

### Q7: How does Phase 8 handle the train/test cutoff dependency on Phase 9?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 8 creates the shared config now | Single source of truth from day one; no Phase 9 retrofit risk. Placeholder `2024-01-01`. | ✓ |
| Phase 8 hardcodes its own cutoff | Pragmatic but creates refactor + risk of in-sample leakage. | |
| Defer entirely — use all 10y | Violates BT-02 / TRAIN success criterion #2. | |

**User's choice:** Phase 8 creates the shared config now (Recommended)

### Q8: What's the minimum positive-sample count threshold before we accept the dataset?

| Option | Description | Selected |
|--------|-------------|----------|
| 1,000 positives | Lower bound of YOLOv8n single-class range; triggers augmentation if missed. | ✓ |
| 500 positives | More forgiving; risks under-trained model. | |
| Don't gate | Faster but no guardrail against silently bad models. | |

**User's choice:** 1,000 positives (Recommended)

---

## Negative sampling strategy

### Q9: Where do negative samples come from?

| Option | Description | Selected |
|--------|-------------|----------|
| Hard negatives: failed detections | Mine windows where the cluster forms but ≥1 trend filter fails; strongest discriminator. | ✓ |
| Random windows from same tickers | Easy; model learns "pattern vs nothing", not "pattern vs near-miss". | |
| Mixed 50/50: half hard, half random | Hybrid; more complex, possibly overkill. | |

**User's choice:** Hard negatives only (Recommended)

### Q10: How do we frame negative samples — same window geometry as positives?

| Option | Description | Selected |
|--------|-------------|----------|
| Same 60-bar right-aligned window, no bbox label | YOLO standard for background images; identical framing to positives. | ✓ |
| Negative bbox covering 5 candidate bars | Adds class imbalance complexity; YOLO single-class + background is simpler. | |

**User's choice:** Same window, empty label files (Recommended)

### Q11: How is the hard-negative candidate pool defined?

| Option | Description | Selected |
|--------|-------------|----------|
| Detector with filters disabled | Reuses Phase 7 code; subtract real positives to get failed-filter pool. | ✓ |
| Inside-bar-only (no break-below required) | Larger pool but more diluted. | |
| Manual list of "looks similar but isn't" | High signal but doesn't scale. | |

**User's choice:** Detector with filters disabled (Recommended)

### Q12: Should we cap how many positives/negatives any single ticker can contribute?

| Option | Description | Selected |
|--------|-------------|----------|
| Cap at 5% per ticker | Forces visual diversity; ~25 samples max per ticker at 500 universe. | |
| No cap — trust natural distribution | Simpler. Risk of ticker-style overfit, but preserves positive count. | ✓ |
| Cap at 10% per ticker | Looser ceiling; middle ground. | |

**User's choice:** No cap (the user explicitly preferred not to risk losing positives below the 1,000 gate)

---

## Dataset & training env

### Q13: Do we commit the generated training dataset (PNGs + labels + data.yaml) to the repo?

| Option | Description | Selected |
|--------|-------------|----------|
| Only ONNX + tiny test fixture | Repo stays small (~10 MB); dataset regenerable. | ✓ |
| Commit dataset + ONNX | ~500 MB+ of PNGs; bloats clones. | |
| Commit dataset under Git LFS | Adds LFS dependency to a portfolio repo that doesn't otherwise need it. | |

**User's choice:** Only ONNX + tiny test fixture (Recommended)

### Q14: How is dataset regeneration made reproducible?

| Option | Description | Selected |
|--------|-------------|----------|
| Seeded generator + dataset manifest | Deterministic with `--seed`; manifest with hash for verification. | ✓ |
| Just document the command in README | Simpler but no drift detection. | |
| No reproducibility guarantee | ONNX is the artifact; dataset is internal. | |

**User's choice:** Seeded generator script + dataset manifest (Recommended)

### Q15: Where does YOLOv8n training run?

| Option | Description | Selected |
|--------|-------------|----------|
| Local hardware — CPU or GPU | Document command + wall time; no external service. | ✓ |
| Google Colab free tier | T4 GPU but adds external dependency and large transfers. | |
| Local GPU only | Hardcoded GPU requirement blocks CPU-only contributors. | |

**User's choice:** Local hardware — you decide CPU vs GPU (Recommended)

### Q16: How prescriptive should the training hyperparameters be?

| Option | Description | Selected |
|--------|-------------|----------|
| Lock the essentials, Claude picks the rest | Lock pre-trained weights, imgsz, fliplr=0, cls_pw, opset; tune epochs/batch/LR. | ✓ |
| Fully prescriptive | Lock every hyperparam; rigid, may not fit hardware. | |
| All Claude's discretion | Lower rigor on reproducibility. | |

**User's choice:** Lock the essentials, Claude picks the rest (Recommended)

---

## Claude's Discretion

- Exact mplfinance style randomisation parameters (DPI, figsize, candle width, background shade — research suggested 3+ styles).
- Whether `split_config` is a `.py` constant or a `.yaml` file.
- Internal helper function names within new modules.
- Parallelisation strategy for yfinance fetches inside `generate_training_data.py` (mirroring `scripts/fetch_sp500.py` is acceptable).
- Exact `cls_pw` value and any auxiliary YOLO loss weights.
- ONNX opset version (whatever ultralytics defaults to that onnxruntime ≥ 1.18 supports — log it).
- Whether `verify_onnx.py` runs as a subprocess in a temporary venv or is invoked manually.
- Train/val split ratio inside the pre-cutoff data (suggest 80/20 random).

## Deferred Ideas

- Multi-class YOLO (separate `spring` vs `full_5bar`) — re-evaluate after first training run if recall is poor.
- Per-ticker sample cap (5% or 10%) — revisit only if ticker-style overfit shows in error analysis.
- Git LFS for dataset — overkill given regeneration works.
- Cloud / Colab training — revisit if local training time exceeds ~2h.
- Volume bars / SMA overlays in training images — Phase 8.5 experiment if recall is poor.
- Time-based train/val split inside pre-cutoff data — reconsider if val metrics mislead.
- YOLOv8s upgrade — revisit only if YOLOv8n recall is unacceptable.
