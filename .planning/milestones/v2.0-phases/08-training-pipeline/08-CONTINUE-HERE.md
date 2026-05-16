---
phase: 08-training-pipeline
status: paused
paused_at: 2026-05-02
resume_point: Plan 08-04 (Wave 4 of 5)
plans_complete: 3
plans_total: 5
---

# Phase 8 — Resume Handoff

## Status snapshot (paused 2026-05-02)

| Wave | Plan | Status | Commits |
|------|------|--------|---------|
| 1 | 08-01 Foundation (kwarg + split_config + stubs + deps + GPU spike) | ✅ Complete | `8e31198`, `ccc8e9d`, `0a66bf2` |
| 2 | 08-02 Headless renderer (mplfinance, 3 styles, bbox) | ✅ Complete | `08064b0`, `c0a1734`, `6cd4b19` |
| 3 | 08-03 Dataset generator orchestrator (10:1 cap, hard negatives, manifest) | ✅ Complete | `a67ba21`, `2467694`, `6c41d40` |
| 4 | 08-04 Full S&P 500 dataset run + YOLOv8n training + ONNX export | ⏸ Paused — training will run on free Colab T4 (see "Hardware path") | — |
| 5 | 08-05 verify_onnx clean-venv round-trip + closeout | ⏸ Blocked on 08-04 | — |

**Test state at pause:** 27 passed, 14 skipped (11 known_setups network-marked, 3 onnx_round_trip Wave 0 stubs), 0 failed.

## Why we paused

Plan 08-04 is `autonomous: false` — it kicks off the full training run and contains two human-verify checkpoints inside it. Two reasons stopping made sense:

1. **CPU-only hardware.** Wave 1 connectivity spike confirmed `torch 2.11.0+cpu`, `cuda_available=False`, `device_count=0`. Realistic CPU wall time for YOLOv8n on ≥1,000 positives + 10× negatives at imgsz=640: 8–15 hours. That ties up the laptop with thermal-throttling and sleep risk.
2. **Two human gates inside the plan** — W4 (review hyperparameters before training) and W5 (review `best_map50` before fixture rendering). "Kick off and walk away" isn't an option.

## Hardware path: Google Colab free T4 (chosen)

**Decision:** Train on free-tier Google Colab T4 GPU. Local CPU and paid GPU rentals were considered and rejected — see "Alternatives considered" below.

**Why T4 fits:**

- YOLOv8n is ~3.2M params, ~6 MB weights. Free Colab T4 has 16 GB VRAM — uses ~2–4 GB at imgsz=640 batch=16. No OOM risk.
- Estimated wall-clock for ~1,000 positives + ~10× negatives (≈11k images, 640×640, ~50 epochs): **20–40 min** on T4. Well inside Colab free's 12h continuous-runtime ceiling.
- ultralytics has first-class Colab support — `!pip install ultralytics` + `model.train(data=..., ...)` is the documented happy path. ONNX export `model.export(format="onnx", opset=12, dynamic=False, simplify=True)` finishes in seconds.

**Caveats to plan around:**

1. **No GPU guarantee on free tier.** Colab assigns T4 *when available*. At peak hours you may be bumped to CPU or get "no GPU available". Mitigation: retry in a few hours, or upgrade to Colab Pro ($10/mo) for near-guaranteed T4. For this one-off run, plan for one or two retries.
2. **Idle disconnect (~90 min).** Training fits in 30–40 min so the 12h ceiling doesn't apply, but if you walk away mid-train and the tab idles out, the runtime dies and local disk is wiped. **Mitigation:** mount Google Drive at the start of the notebook so `runs/` writes there; on disconnect, ultralytics writes `last.pt` to Drive and a fresh runtime can resume with `resume=True`.

**Code-organisation rule:** keep `scripts/pattern_scanner/train.py` runnable both locally and on Colab — no Colab-specific imports inside it. The Colab side lives in a thin notebook that does environment setup (`pip install`, Drive mount, dataset upload/clone) and then shells out to `python -m scripts.pattern_scanner.train`. The ONNX is the deliverable; the runtime that produced it doesn't matter.

## Resume procedure (Colab path)

### Step 1 — Local: generate dataset, commit housekeeping

```bash
# Confirm tree state — Phase 8 commits (8e31198 onward) should already be on main.
git log --oneline -12

# Triage and commit the 52 restored housekeeping changes in logical groups
# (v1.0 archive cleanup, CLAUDE.md project guidance, MCP config, screener/yahoo edits).
# Do this BEFORE running the dataset generator so executor-style commits stay clean.

# Re-validate everything still green:
source .venv/Scripts/activate && python -m pytest tests/ -q --no-network
# Expected: 27 passed, 14 skipped, 0 failed.

# Generate the full dataset locally (CPU is fine, ~15–30 min):
source .venv/Scripts/activate
python -m scripts.pattern_scanner.generate_training_data --seed 42 \
    --tickers all --out _dev/training_dataset
# (Confirm exact CLI flags by reading the generator; placeholders shown above.)

# Sanity check: verify the manifest claims >=1,000 positives or document the
# multi-style augmentation alternative for D-08.
python -c "import json; m=json.load(open('_dev/training_dataset/dataset_manifest.json')); print(m['totals'])"
```

### Step 2 — Move dataset to Colab

Two options:

- **(a) Drive upload (simpler).** Zip `_dev/training_dataset/` (`tar -czf training_dataset.tgz _dev/training_dataset/`) and upload to a known Drive folder. The Colab notebook unpacks it after mounting Drive.
- **(b) Private git repo.** Push the dataset to a separate private repo (it's gitignored locally for a reason — do **not** push to the portfolio repo). Colab clones via `git clone`. Useful if you'll iterate on training; overkill for a one-shot run.

### Step 3 — Colab notebook (`notebooks/train_colab.ipynb`)

Notebook structure (you write this on first resume; commit it after the run for reproducibility):

```python
# Cell 1 — environment
from google.colab import drive
drive.mount('/content/drive')
!pip install -q ultralytics==8.4.46  # match Wave 1 spike version
!nvidia-smi  # confirm T4

# Cell 2 — fetch dataset + project code
%cd /content
!git clone https://github.com/<you>/jun-xian-project.git
%cd jun-xian-project
!cp /content/drive/MyDrive/<path>/training_dataset.tgz .
!tar -xzf training_dataset.tgz   # unpacks to _dev/training_dataset/

# Cell 3 — train via the project's own train.py (hyperparameters live there)
!python -m scripts.pattern_scanner.train \
    --data _dev/training_dataset/data.yaml \
    --weights yolov8n.pt \
    --imgsz 640 \
    --epochs 50 \
    --seed 42 \
    --runs-dir /content/drive/MyDrive/yolo_runs   # write to Drive so a disconnect is recoverable

# Cell 4 — collect deliverables
!ls -la models/
!cp models/inside_bar_v1.onnx /content/drive/MyDrive/<path>/
!cp models/training_summary.json /content/drive/MyDrive/<path>/
!cp models/dataset_manifest.json /content/drive/MyDrive/<path>/
```

W4 / W5 human-verify checkpoints become **manual notebook gates** in this environment: pause between cells to review hyperparameters before Cell 3, and review `best_map50` from Cell 3's stdout before Cell 4 ships the deliverables.

### Step 4 — Local: bring artifacts back, finish phase

```bash
# Copy the 3 files from Drive into the local repo:
#   models/inside_bar_v1.onnx
#   models/training_summary.json
#   models/dataset_manifest.json
# Plus tests/fixtures/known_positive_holdout.png + .json (Plan 08-04 Task 5 output —
# can be rendered locally OR on Colab; either is fine).

# Resume execution at Wave 4 to land the commits + summary file:
/gsd-execute-phase 8 --wave 4

# After 08-04 completes, run 08-05:
/gsd-execute-phase 8 --wave 5
```

`--wave 4` re-enters the executor on Plan 08-04 with the artifacts already on disk; the executor's job is then mostly verification + commit + SUMMARY.md (not the actual training, which already happened on Colab). Update Plan 08-04's tasks if needed to reflect "artifacts produced externally" rather than "train locally".

After both waves land, Phase 8 verification + completion gates run automatically.

## Alternatives considered

- **(B) Overnight local CPU run.** Free but ties the laptop up 8–15h; thermal/sleep/OS-update risk; not interactive enough for the W4/W5 gates. Rejected.
- **(C) Reduced scope (smaller ticker subset, fewer epochs).** Faster, but may miss the D-08 1,000-positive gate without explicit waiver. Holds as a fallback if Colab fails twice.
- **(D) Paid cloud GPU (Lambda / RunPod / Vast.ai).** ~$1–3 for the run, slightly faster setup than Colab, but Colab free is good enough for a one-shot. Hold as fallback if free tier persistently denies T4.

## Outstanding from Wave 1 spike

The Wave 1 SUMMARY explicitly punted the training-budget decision to Plan 04 — see `.planning/phases/08-training-pipeline/08-01-SUMMARY.md` "Open Questions for Plan 04". Address that question (A/B/C above) before resuming.

## Safety notes

- Working tree at pause time has **52 uncommitted changes restored from stash** — v1.0 archive deletions, modified `yahoo_finance_fetcher.py` / `stock.html` / `ROADMAP.md` / `config.json` / `CONCERNS.md`, plus new `CLAUDE.md` files and `.mcp.json`. Recommend committing these in 2–3 logical groups (e.g. "v1.0 archive cleanup", "CLAUDE.md project guidance", "MCP config", "screener/yahoo bug fixes if any") **before** resuming Wave 4 so executor commits stay clean.
- `git stash list` is empty (the pre-Phase-8 stash was popped on 2026-05-02).
- Phase 7's 23-test contract is preserved by Plan 08-01's default kwarg. Re-verify with `pytest tests/test_detector_schema.py tests/test_detector_known_setups.py -q --no-network` if anything looks off after committing the housekeeping changes.
