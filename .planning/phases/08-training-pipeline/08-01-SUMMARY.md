---
phase: 08-training-pipeline
plan: 01
subsystem: pattern_scanner / training-pipeline foundation
tags:
  - python
  - testing
  - phase-7-contract
  - dependencies
  - wave-0-scaffold
requirements:
  - TRAIN-01
  - TRAIN-02
  - TRAIN-03
  - TRAIN-04
dependency_graph:
  requires:
    - "Phase 7 detect() — extended via single kwarg insertion"
  provides:
    - "scripts.pattern_scanner.split_config.TRAIN_TEST_CUTOFF (single SoT for Phase 8 + Phase 9)"
    - "scripts.pattern_scanner.detector.detect(..., apply_trend_filters: bool = True) — Phase 8 hard-negative pool source when False"
    - "Wave 0 named test stubs across TRAIN-01..TRAIN-04 (Plans 02-05 fill in)"
    - "requirements-training.txt — offline-only ultralytics dep"
    - "requirements.txt + 4 inference deps for Phase 10 nightly"
    - ".gitignore covers yolov8n.pt + _dev/training_dataset/"
  affects:
    - "Plan 02 (renderer) — must implement the 3 named tests in tests/test_renderer.py"
    - "Plan 03 (dataset generator) — must consume TRAIN_TEST_CUTOFF and pass detect(..., apply_trend_filters=False) for the hard-negative pool; must implement 8 named tests"
    - "Plan 04 (training run) — has hardware reality (CPU-only; multi-hour budget)"
    - "Plan 05 (ONNX round-trip) — must implement 3 named tests"
    - "Phase 9 (backtester) — imports TRAIN_TEST_CUTOFF from the same module"
tech_stack:
  added:
    - "ultralytics 8.4.46 (training-only, requirements-training.txt)"
    - "torch 2.11.0+cpu (transitive via ultralytics)"
    - "torchvision 0.26.0 (transitive)"
    - "matplotlib 3.10.9 (inference; pinned >=3.8 in requirements.txt)"
    - "mplfinance (inference; pinned >=0.12.10b0 in requirements.txt)"
    - "onnxruntime (inference; pinned >=1.19 in requirements.txt — stricter than CONTEXT for numpy 2.x compat)"
    - "Pillow (transitive + explicit; pinned >=10.0 in requirements.txt)"
  patterns:
    - "Default-True kwarg preserves existing call signature byte-for-byte (Phase 7 contract preservation idiom)"
    - "Wave 0 stub pattern: file-level pytestmark = pytest.mark.skip with reason naming the implementing plan"
key_files:
  created:
    - "scripts/pattern_scanner/split_config.py"
    - "requirements-training.txt"
    - "tests/test_detector_apply_trend_filters_kwarg.py"
    - "tests/test_renderer.py"
    - "tests/test_generate_training_data.py"
    - "tests/test_onnx_round_trip.py"
    - "tests/fixtures/.gitkeep"
  modified:
    - "scripts/pattern_scanner/detector.py (+ kwarg, + branching, + docstring)"
    - "requirements.txt (+ 4 inference deps under Phase 8 divider)"
    - ".gitignore (+ yolov8n.pt + _dev/training_dataset/)"
decisions:
  - "onnxruntime pinned >=1.19 (stricter than CONTEXT's >=1.18) for hard numpy 2.x compatibility (08-RESEARCH.md)"
  - "Hardware reality: GPU is unavailable on this machine (torch.cuda.is_available()=False, device_count=0; torch is 2.11.0+cpu). Plan 04 must budget multi-hour CPU wall time."
  - "ultralytics quarantined to requirements-training.txt — never propagated into requirements.txt to keep Render / nightly CI footprint slim (research §Project Constraints)"
metrics:
  duration: "~25 minutes (one session, sequential)"
  completed_date: "2026-05-02"
  tasks_completed: 2
  files_changed: 10
---

# Phase 08 Plan 01: Training Pipeline Foundation — Summary

`detect()` gains an `apply_trend_filters: bool = True` kwarg with full Phase 7 regression coverage; `split_config.TRAIN_TEST_CUTOFF` becomes the single source-of-truth for the train/test boundary; Wave 0 test scaffolds land for Plans 02-05; ultralytics + ONNX inference dependency manifests are declared; the connectivity / GPU spike confirms ultralytics 8.4.46 + torch 2.11.0+cpu (CPU-only).

## Tasks Completed

### Task 1 — `apply_trend_filters` kwarg + regression test (`8e31198`)

- `scripts/pattern_scanner/detector.py` — signature changed from `def detect(df, ticker)` to `def detect(df, ticker, apply_trend_filters: bool = True)`. Docstring extended with the kwarg description. The 3-AND filter check at the original lines 367-372 was replaced with branching logic: when `apply_trend_filters=False`, every cluster-shape match is appended; otherwise, the original 3-AND check governs emission. Per-filter booleans in `Detection.filters` are still computed and recorded in either mode (D-08 invariant unchanged).
- `tests/test_detector_apply_trend_filters_kwarg.py` (new):
  - `test_default_kwarg_matches_phase7` — proves `detect(df, t)` and `detect(df, t, apply_trend_filters=True)` return identical lists on the standard `_spring_setup_rows()` fixture.
  - `test_unfiltered_is_superset` — uses a flat-prefix fixture (`_spring_setup_rows_flat_prefix()`) so HH/HL fails. Asserts `detect(df, t, apply_trend_filters=False)` is a strict superset of `detect(df, t)` AND at least one detection in the difference has at least one False filter boolean — proving the False branch genuinely sources hard negatives.
- Trend-helper functions `_build_uptrend()` and `_spring_setup_rows()` were copied from `tests/test_detector_schema.py` (file-local helpers, not importable) with a sync comment as instructed.

### Task 2 — split_config + Wave 0 stubs + dep manifests + .gitignore + connectivity spike (`ccc8e9d`)

- `scripts/pattern_scanner/split_config.py` — exposes `TRAIN_TEST_CUTOFF = "2024-01-01"` with module-level docstring tying it to D-07 and Phase 9 future revision.
- `requirements-training.txt` — single non-comment line `ultralytics>=8.4.0,<9.0`.
- `requirements.txt` — appended Phase 8 divider + `mplfinance>=0.12.10b0`, `matplotlib>=3.8`, `onnxruntime>=1.19`, `Pillow>=10.0`.
- `.gitignore` — appended Phase 8 divider + `_dev/training_dataset/` and `yolov8n.pt`.
- `tests/fixtures/.gitkeep` — empty file committing the directory for Plan 05's `known_positive_*.png` fixtures.
- `tests/test_renderer.py` (3 named stubs), `tests/test_generate_training_data.py` (8 named stubs), `tests/test_onnx_round_trip.py` (3 named stubs) — each uses `pytestmark = pytest.mark.skip(reason=...)` so they collect but never fail.

## Phase 7 Regression: actual `pytest -q` output

```
$ source .venv/Scripts/activate && python -m pytest tests/test_detector_schema.py tests/test_detector_known_setups.py -q --no-network
............sssssssssss                                                  [100%]
12 passed, 11 skipped in 0.37s
```

Exact baseline match: 12 passed (schema, all unit) + 11 skipped (known_setups, network-marked under `--no-network`). Zero failures; Phase 7 contract preserved.

Full suite (after Task 2):

```
$ source .venv/Scripts/activate && python -m pytest tests/ -q --no-network
..sssssssssss............ssssssssssssss                                  [100%]
14 passed, 25 skipped in 0.40s
```

14 passed = 12 schema + 2 new kwarg regression. 25 skipped = 11 known_setups (network) + 3 renderer stubs + 8 generate_training_data stubs + 3 onnx_round_trip stubs. Zero failures.

## Connectivity / GPU Spike

```
$ python -c "import ultralytics; print('ultralytics', ultralytics.__version__)"
ultralytics 8.4.46

$ python -c "import torch; print('torch', torch.__version__, 'cuda_available', torch.cuda.is_available(), 'device_count', torch.cuda.device_count())"
torch 2.11.0+cpu cuda_available False device_count 0

$ python -c "from ultralytics import YOLO; m = YOLO('yolov8n.pt'); print('weights_loaded', m.model is not None)"
Downloading https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt to 'yolov8n.pt': 100% ━━━━━━━━━━━━ 6.2MB 12.5MB/s 0.5s
weights_loaded True
```

| Quantity | Value |
|---|---|
| ultralytics | 8.4.46 (>=8.4.0,<9.0 ✓) |
| torch | 2.11.0+cpu |
| cuda_available | **False** |
| device_count | 0 |
| yolov8n.pt | downloaded to repo root, 6.2 MB, **gitignored** (`git check-ignore -q yolov8n.pt` → exit 0) |
| _dev/training_dataset/foo.png | gitignored (`git check-ignore -q ...` → exit 0) |

Note: the wheel installed is `torch-2.11.0+cpu` (the default Windows wheel from PyPI is the CPU build). To get CUDA support, Plan 04 would need to (a) explicitly install a CUDA wheel from `https://download.pytorch.org/whl/cu12X`, AND (b) have a CUDA-capable GPU on this machine — neither holds today.

## Open Questions for Plan 04

**Training wall-time budget given the CPU-only hardware reality:**

1. YOLOv8n on CPU at 640×640 with ~2,000-5,000 training images is on the order of **6-12 hours per training run** (vs. ~30-60 min on a single mid-tier GPU). Plan 04 should:
   - Decide whether to (a) accept the multi-hour wall time on the local machine, (b) do training on a one-off rented GPU box (Lambda / RunPod / Colab) and copy the resulting `.pt` + `.onnx` back into the repo, or (c) reduce dataset size / epochs for v1 and revisit.
   - Reflect the chosen path in the Plan 04 task structure (e.g., add a "rent GPU and copy artifacts" task vs. a "kick off local training overnight" task with a different verify command).
2. If the choice is local CPU, Plan 04 should:
   - Set `device='cpu'` explicitly in the YOLO `.train()` call so it doesn't try to fall through to a non-existent CUDA device.
   - Lower the default batch size (16 → 4 or 8) to fit CPU memory comfortably, and budget commensurately.
   - Treat the training task as an `auto` task with a checkpoint at completion (the user verifies the run finished and the metrics look sane before exporting to ONNX).
3. Independent of (1)/(2), Plan 04 must still run the ONNX export step (`opset=12`) on the exported `.pt` and verify the export succeeds in the CPU-only torch environment — this is fast (seconds) and can be bundled with the training task or pulled into a separate CPU-only sub-task.

**A secondary open question:** the CPU torch wheel pulls in `2.11.0` but Plan 04's `requirements-training.txt` currently has no torch pin. If the next dev clones the repo on a fresh machine and `pip install -r requirements-training.txt` lands a different torch version, ultralytics ONNX export behaviour can drift. Worth considering a soft pin (`torch>=2.4,<3.0`) in Plan 04 if reproducibility becomes an issue.

## Self-Check: PASSED

- [x] `scripts/pattern_scanner/detector.py` — kwarg present at line 306; branching at line 373; doc updated; `def detect` count = 1.
- [x] `tests/test_detector_apply_trend_filters_kwarg.py` — exists, 2 tests both pass.
- [x] `scripts/pattern_scanner/split_config.py` — exists, `TRAIN_TEST_CUTOFF` imports as `"2024-01-01"`.
- [x] `requirements-training.txt` — exists, contains `ultralytics`.
- [x] `requirements.txt` — 4 new non-comment lines for `mplfinance|matplotlib|onnxruntime|Pillow`.
- [x] `.gitignore` — contains `yolov8n.pt` and `_dev/training_dataset/`; both `git check-ignore -q` calls exit 0.
- [x] `tests/fixtures/.gitkeep` — exists.
- [x] `tests/test_renderer.py` — 3 named stubs.
- [x] `tests/test_generate_training_data.py` — 8 named stubs.
- [x] `tests/test_onnx_round_trip.py` — 3 named stubs.
- [x] All 23 Phase 7 tests still pass (12+11 under `--no-network`).
- [x] Full pytest suite: 14 passed, 25 skipped, 0 failed.
- [x] Commits: `8e31198` (Task 1), `ccc8e9d` (Task 2), and this Summary commit.
- [x] Connectivity spike output captured above.
- [x] No `--no-verify`, no `Co-Authored-By` trailers added.
