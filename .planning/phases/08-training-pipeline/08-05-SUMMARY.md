---
phase: 08-training-pipeline
plan: 05
type: execute
status: complete
completed: 2026-05-08
requirements:
  - TRAIN-04
---

# Plan 08-05 Summary — Clean-Venv ONNX Round-Trip + Phase 8 Closeout

## Outcome

Phase 8's binary deliverable (`models/inside_bar_v1.onnx`) is now proven loadable in a torch-free production environment. All Plan 05 spec gates pass. Phase 8 is complete (5/5 plans).

## Tasks completed

| Task | Outcome |
|------|---------|
| 1. Build `verify_onnx.py` clean-venv subprocess test | ✅ committed `21ea681`. Creates temp venv via `venv.create()`, pip-installs only `onnxruntime + numpy + Pillow`, asserts no torch/ultralytics leak, runs inference on the holdout PNG, exits 0 on conf ≥ floor. |
| 2. Activate `test_manifest_sha256_round_trip` | ✅ committed `57a8cee`. Determinism check using monkeypatched `_fetch_ohlc` + `synthetic_ohlc` fixture — runs in ms, no yfinance call. |
| 3. CONFIDENCE_FLOOR calibration (Rule-4 deviation, user-approved) | ✅ Lowered from spec's 0.5 to **0.3** based on empirical out-of-distribution behavior — see "Decisions" below. |
| 4. Run clean-venv gate end-to-end | ✅ Passed: temp venv created, inference produces correct bbox at conf 0.373. |
| 5. Full pytest regression | ✅ 30 passed, 11 skipped (network), 0 failed. |

## Verification

### `verify_onnx.py` stdout

```
[verify] creating clean venv at C:\Users\zenng\AppData\Local\Temp\onnx_verify_7_q_y9z0\venv
[verify] pip-installing onnxruntime + numpy + Pillow into clean venv
[verify] confirmed: clean venv has NO torch / ultralytics
[verify] running on known_positive_holdout.png
[verify] input: images [1, 3, 640, 640]
[verify] outputs: ['output0']
{"detections": [{"box": [534.27, 184.50, 32.04, 65.22], "conf": 0.3729}], "max_score": 0.3729}

[verify] PASS: known_positive_holdout.png got conf >= 0.3
```

### Bbox correctness vs ground truth (holdout JSON provenance)

| Quantity | Ground truth | Model | Match |
|----------|-------------|-------|-------|
| cx | 0.835 | 0.834 | ~perfect |
| cy | 0.289 | 0.288 | ~perfect |
| w  | 0.049 | 0.050 | ~perfect |
| h  | 0.099 | 0.102 | ~perfect |

Bbox IoU effectively 1.0 — model correctly localizes the pattern; only the confidence is below the original spec's 0.5.

### Full pytest

```
30 passed, 11 skipped, 10 warnings in 927.87s
```

Breakdown:
- 12 schema (Phase 7 contract preserved)
- 11 known_setups skipped (network-marked)
- 2 kwarg regression (Plan 01)
- 5 renderer (Plan 02)
- 8 generator (Plan 03)
- 3 onnx_round_trip — file_exists, opset_recorded, manifest_sha256_round_trip — all active and green

### Phase 7 23-test contract gate

```
14 passed, 11 skipped, 0 failed
```

(12 schema + 2 kwarg = 14 active; the 11 network-marked tests skip under `--no-network`.)

## Decisions

1. **CONFIDENCE_FLOOR lowered 0.5 → 0.3** (Rule-4 architectural deviation, user-approved).

   **Why:** Plan 04 reports val-split mAP@0.5 = 0.79 (in-period, pre-cutoff). The committed holdout (MSFT 2024-01-08) is **post-cutoff** — a true out-of-distribution sample. The model produces a spatially-correct detection at conf=0.37; top-5 detections cluster at 0.27–0.37 (clear spatial consensus, lower confidence calibration). Cross-checked against ultralytics' native inference path: same result. Cross-checked RGB vs BGR preprocessing: RGB is correct.

   **Trade-off:** Loosens the gate slightly, but the integrity check (clean-venv loadable, opset 12, torch-free, produces a coherent detection at the right location) is fully preserved. A corrupt or wrong-opset ONNX would still fail.

   **Phase 10 implication:** The nightly inference pipeline MUST use the same conf threshold (0.3). This is documented in the `verify_onnx.py` module docstring and recorded as a Phase 10 hand-off note below.

2. **`test_manifest_sha256_round_trip` uses synthetic data**, not a real yfinance fetch. Yfinance is non-deterministic across days (the laptop's 2026-05-03 vs desktop's 2026-05-08 generations produced different `concat_sha256` values for the same `seed=42`). The seeded determinism we want to verify is the generator's, not yfinance's; using `synthetic_ohlc` + monkeypatch isolates the right thing and runs in ms.

## Commits (Plan 05)

- `21ea681`: feat(08-05): add clean-venv ONNX round-trip verifier
- `57a8cee`: test(08-05): activate test_manifest_sha256_round_trip determinism check
- (this commit): docs(08-05): plan 05 summary

## Phase 8 closeout

**Phase 8 is COMPLETE.** All 5 plans landed; all spec gates met.

| Plan | Deliverable | Status |
|------|-------------|--------|
| 08-01 | `apply_trend_filters` kwarg, `split_config.py`, deps, GPU spike, Wave 0 stubs | ✅ |
| 08-02 | `renderer.py` (mplfinance Agg, 3 styles, bbox) + 5 tests | ✅ |
| 08-03 | `generate_training_data.py` orchestrator + 8 tests | ✅ |
| 08-04 | Trained YOLOv8n ONNX (mAP@0.5 0.79), summary, real-run manifest, holdout fixture | ✅ |
| 08-05 | `verify_onnx.py` clean-venv gate, all 3 ONNX tests active | ✅ |

### Hand-off notes for Phase 9 (Backtesting Engine)

- **Detector contract preserved:** `detect(df, ticker)` (no kwarg) still returns the Phase 7 filtered set. `detect(df, ticker, apply_trend_filters=False)` returns the unfiltered set; Phase 9 may want this for a wider backtest universe.
- **TRAIN_TEST_CUTOFF = "2024-01-01"** lives in `scripts.pattern_scanner.split_config`. Phase 9's backtester MUST import it from there — same source the dataset generator used. Ensures no in-sample leakage.
- The committed `models/dataset_manifest.json` records the full set of detection coordinates that went into training. Phase 9 can subtract these to get a pure out-of-sample test set.

### Hand-off notes for Phase 10 (Batch Pipeline)

- **Inference deps lock:** `onnxruntime>=1.19`, `Pillow>=10.0`, `numpy<2.0` (pinned; transitive ultralytics constraint), `mplfinance>=0.12.10b0`, `matplotlib>=3.8`. **NEVER** add torch or ultralytics to `requirements.txt`. The `verify_onnx.py` clean-venv gate is the structural assertion of this — re-run it before any Phase 10 deploy.
- **Confidence threshold for nightly inference: 0.3.** Calibrated against post-cutoff holdout. Pre-cutoff samples will typically score higher (training-distribution); post-cutoff samples may score 0.30–0.40 even when correct.
- **Renderer reuse:** Phase 10 should reuse `scripts/pattern_scanner/renderer.py` for the annotated chart PNGs at `docs/projects/patterns/charts/`. Same `STYLES`, but you may want to pick a single deterministic style (e.g., `STYLES[0]` = style_a) for visual consistency in the production UI rather than randomising.
- **ONNX expected per-image inference latency:** not benchmarked in Phase 8. Sample of one (the holdout fixture) ran in subprocess overhead-dominated ~30s including temp-venv-creation; raw inference is sub-second. Phase 10 should benchmark before locking GitHub Actions runner type.

### Open questions surfaced (not blockers)

- **In-period vs out-of-period confidence calibration**: should Phase 10 emit two confidence tiers (e.g., green ≥ 0.5, yellow 0.3–0.5)? The screener UI hint in ROADMAP §Phase 11 already plans confidence-tier badges — this calibration data should inform tier thresholds.
- **mAP@0.5:0.95 = 0.61** is solid but suggests the bbox tightness varies. If Phase 11's drilldown shows visibly loose bboxes, consider a Plan 04 retrain with more aggressive box-loss weighting in a future milestone.

## Files committed in Plan 05

- `scripts/pattern_scanner/verify_onnx.py` (new, 171 lines)
- `tests/test_onnx_round_trip.py` (modified — third test activated)
- `.planning/phases/08-training-pipeline/08-05-SUMMARY.md` (this file)
