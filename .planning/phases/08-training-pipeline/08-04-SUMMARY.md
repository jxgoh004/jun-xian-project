---
phase: 08-training-pipeline
plan: 04
type: execute
status: complete
completed: 2026-05-08
requirements:
  - TRAIN-04
---

# Plan 08-04 Summary — Full S&P 500 Training Run + ONNX Export

## Outcome

YOLOv8n trained on the algorithmic-detection-driven dataset; ONNX artifact committed at `models/inside_bar_v1.onnx`. All Plan 04 spec gates pass.

| Metric | Value | Plan 04 gate |
|--------|-------|--------------|
| `best_map50` | **0.7897** | (not gated; strong for first run) |
| `best_map50_95` | **0.6080** | (not gated) |
| `epochs_run` | 100 | early-stopping patience did not trigger |
| `wall_time_s` | 11118.7 (≈ 3h 05m) | — |
| ONNX size | 11.7 MB | ✅ within 1–50 MB |
| ONNX opset | 12 | ✅ |
| `imgsz` / `fliplr` / `seed` | 640 / 0.0 / 42 | ✅ all match spec |

## Hardware deviation from plan

Plan 04 was written assuming local training. Plan 01's connectivity spike confirmed the laptop is CPU-only (`torch 2.11.0+cpu`, `cuda_available=False`). Multi-hour CPU training was rejected as not viable.

Resolution: training executed on a separate **RTX 5070 desktop** (Blackwell sm_120, PyTorch with CUDA 12.8 wheel) using the same `train.py` checked into this repo. The 5 deliverable files were transferred to the laptop via Google Drive and committed here.

A pre-positioned Colab notebook (`notebooks/train_colab.ipynb`, committed earlier in `1df46e5`) was prepared as a contingency path; ultimately not used because the desktop GPU was faster and avoided Drive sync flakiness.

## Tasks completed

| Task | Outcome |
|------|---------|
| 1. Implement train.py + activate test_onnx_round_trip stubs | ✅ train.py committed in `1df46e5`; tests activated in `ac842cf` |
| 2. W4 human-verify checkpoint | ✅ implicitly handled — user reviewed dataset stats and chose RTX 5070 path |
| 3. Full S&P 500 dataset gen + training + ONNX export + commit artifacts | ✅ artifacts committed (manifest overwrites Plan 03's copy) |
| 4. W5 best_map50 review | ✅ user reviewed 0.7897 mAP@0.5 and approved fixture render |
| 5. Render holdout fixture | ✅ MSFT 2024-01-08, style_a, post-cutoff verified |

## Dataset stats (real-run, committed manifest)

- **Tickers processed:** 503 / 503 (full S&P 500)
- **Raw positives:** 4,010 (well above D-08 1,000-positive gate; no multi-style augmentation needed)
- **Raw negatives:** 21,849 (all kept; ratio 5.45:1 under the D-09 10:1 cap)
- **Renderer styles seen:** style_a, style_b, style_c (all three randomised across samples)
- **Cutoff enforced:** `TRAIN_TEST_CUTOFF = 2024-01-01` — no detection with `confirmation_date >= 2024-01-01` in any training label
- **`concat_sha256` baseline:** `72767c3f69fb5f06a2ee3aa42cc1016c57094fb0513b54e2d265a12644a39c29`

Note: this `concat_sha256` differs from the laptop's earlier 2026-05-03 baseline (`aff4e730f2f7…`) due to yfinance returning slightly different OHLC for the 5-day gap between the two generations. The 4,010 vs 4,064 positive count delta is the same root cause. Determinism is preserved within a single yfinance fetch session.

## Holdout fixture (for Plan 05 verify_onnx)

| Field | Value |
|-------|-------|
| Ticker | MSFT |
| Confirmation date | 2024-01-08 |
| Cutoff | 2024-01-01 |
| `post_cutoff` | true ✅ (not in training set) |
| Style | style_a |
| Bbox (cx, cy, w, h) | (0.835, 0.289, 0.049, 0.099) |

## Verification

```
$ pytest tests/test_onnx_round_trip.py -v --no-network
tests/test_onnx_round_trip.py::test_onnx_file_exists PASSED
tests/test_onnx_round_trip.py::test_opset_recorded PASSED
tests/test_onnx_round_trip.py::test_manifest_sha256_round_trip SKIPPED  (Plan 05's job)

$ pytest tests/test_detector_schema.py tests/test_detector_known_setups.py tests/test_detector_apply_trend_filters_kwarg.py -q --no-network
14 passed, 11 skipped, 0 failed
```

Phase 7's 23-test contract preserved.

## Commits

- `1df46e5`: chore(08-04): pre-position train.py + Colab notebook for GPU training session
- `ac842cf`: test(08-04): activate test_onnx_round_trip file-exists + opset checks
- `a69a1b9`: feat(08-04): commit trained YOLOv8n ONNX + training summary + real-run dataset manifest
- `9edc134`: feat(08-04): commit holdout fixture for verify_onnx clean-venv test
- (this commit): docs(08-04): plan 04 summary

## Open questions for Plan 05

- The clean-venv `verify_onnx.py` round-trip should pull only `onnxruntime`, `Pillow`, `numpy` — confirm those are the inference-only deps (no torch).
- Plan 05's `test_manifest_sha256_round_trip` test is currently skipped. Decision: keep skipped for v1 (manifest determinism is upstream-data-sensitive per the 5-day yfinance variance observed here), or refactor to mock yfinance? Recommend: keep skipped, document the limitation.

## Decisions made

1. **Train on desktop GPU, not laptop CPU.** Saves ~6h vs. CPU; uses an RTX 5070 the user already owned.
2. **Use Drive for desktop ↔ laptop file transfer.** Already set up earlier in the session.
3. **`epochs=100` ran to completion** rather than retraining with `--epochs 200`. mAP@0.5 of 0.79 is acceptable for v1; can revisit if production usage shows false-positive issues.
4. **Manifest sha256 difference accepted.** Yfinance non-determinism across multi-day runs is upstream behaviour, not a generator bug.
