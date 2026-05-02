---
phase: 8
slug: training-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `08-RESEARCH.md` §Validation Architecture (Nyquist Dimension 8).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4 (existing from Phase 7) |
| **Config file** | `pytest.ini` (existing — `testpaths = tests`, registers `network` marker) |
| **Quick run command** | `source .venv/Scripts/activate && python -m pytest tests/ -q -m "not network"` |
| **Full suite command** | `source .venv/Scripts/activate && python -m pytest tests/ -q` |
| **Phase 8 focused command** | `source .venv/Scripts/activate && python -m pytest tests/test_renderer.py tests/test_generate_training_data.py tests/test_onnx_round_trip.py tests/test_detector_apply_trend_filters_kwarg.py -q` |
| **Estimated runtime** | ~10–20 seconds (offline tests); training and ONNX round-trip are CLI gates run manually |

---

## Sampling Rate

- **After every task commit:** Run quick command (`pytest tests/ -q -m "not network"`)
- **After every plan wave:** Run full suite command + smoke `verify_onnx.py` if `models/inside_bar_v1.onnx` exists
- **Before `/gsd-verify-work`:** Full suite green AND `verify_onnx.py` exits 0 in a fresh clean venv (proves no torch leakage)
- **Max feedback latency:** 30 seconds for unit tests; training and clean-venv round-trip are manual gates

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-XX-XX | renderer | 1 | TRAIN-01 | — | mplfinance Agg backend; no path traversal in style names | unit | `pytest tests/test_renderer.py::test_render_returns_640x640_png -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | renderer | 1 | TRAIN-01 | — | deterministic given style seed | unit | `pytest tests/test_renderer.py::test_render_deterministic_same_style -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | renderer | 1 | TRAIN-02 | — | byte-distinct outputs across 3 styles | unit | `pytest tests/test_renderer.py::test_render_styles_differ -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | detector-kwarg | 1 | (Phase 7 contract) | — | default kwarg matches Phase 7 surface | regression | `pytest tests/test_detector_apply_trend_filters_kwarg.py::test_default_kwarg_matches_phase7 -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | detector-kwarg | 1 | (Phase 7 contract) | — | unfiltered output is superset of filtered | regression | `pytest tests/test_detector_apply_trend_filters_kwarg.py::test_unfiltered_is_superset -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-02 | V12 | YOLO `images/{train,val}` + `labels/{train,val}` + `data.yaml` layout under `_dev/training_dataset/` (gitignored) | unit | `pytest tests/test_generate_training_data.py::test_yolo_directory_layout -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-02 | — | positive labels normalised 0..1, class_id = 0 | unit | `pytest tests/test_generate_training_data.py::test_positive_label_format -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-02 | — | every sample uses style randomisation | unit | `pytest tests/test_generate_training_data.py::test_style_randomization_used -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-02 | — | `confirmation_date >= TRAIN_TEST_CUTOFF` excluded | unit | `pytest tests/test_generate_training_data.py::test_cutoff_enforced -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-03 | — | neg:pos ratio capped at 10:1 | unit | `pytest tests/test_generate_training_data.py::test_neg_pos_ratio_capped -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-03 | — | negative samples have empty `.txt` label files | unit | `pytest tests/test_generate_training_data.py::test_negative_labels_empty -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-03 | — | hard-negative pool = filters-disabled MINUS real positives | unit | `pytest tests/test_generate_training_data.py::test_hard_negative_set_difference -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | dataset-gen | 2 | TRAIN-04 | V6 | manifest sha256 matches dataset on-disk (integrity, not secrecy) | unit | `pytest tests/test_generate_training_data.py::test_manifest_sha256_consistent -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | train | 3 | TRAIN-04 | — | `models/inside_bar_v1.onnx` exists post-train | smoke | `test -f models/inside_bar_v1.onnx` | manual gate | ⬜ pending |
| 8-XX-XX | train | 3 | TRAIN-04 | — | opset version recorded in `models/training_summary.json` | unit | `pytest tests/test_onnx_round_trip.py::test_opset_recorded -x` | ❌ W0 | ⬜ pending |
| 8-XX-XX | verify-onnx | 4 | TRAIN-04 | V14 | clean venv with onnxruntime+numpy+Pillow ONLY (no torch); ≥1 bbox conf ≥ 0.5 on fixture | integration | `python scripts/pattern_scanner/verify_onnx.py` exits 0 | manual gate | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/known_positive_aapl_2020.png` — committed fixture (1 file, < 100 KB) for the round-trip test. Either from a known positive run of the trained model or a hand-rendered known-setup chart.
- [ ] `tests/test_renderer.py` — covers TRAIN-01 (3 tests: 640×640 output, determinism, style variance).
- [ ] `tests/test_generate_training_data.py` — covers TRAIN-02 + TRAIN-03 (8 tests using small synthetic ticker subsets).
- [ ] `tests/test_onnx_round_trip.py` — covers TRAIN-04 opset/manifest unit checks (round-trip itself is a CLI smoke).
- [ ] `tests/test_detector_apply_trend_filters_kwarg.py` — Phase 7 contract preservation (2 tests: default behaviour, unfiltered superset).
- [ ] No new framework install required — pytest already in `requirements-dev.txt`.

---

## Critical Test: Phase 7 Compatibility (regression gate)

After the `apply_trend_filters: bool = True` kwarg is added to `detect()`, the existing Phase 7 suite MUST stay green:

```bash
source .venv/Scripts/activate && python -m pytest tests/test_detector_schema.py tests/test_detector_known_setups.py -q
```

Expected: 12 + 11 = 23 tests pass (or 12 pass + 11 skip if `-m "not network"`). Any regression is a hard rollback gate.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| YOLOv8n training completes without OOM | TRAIN-04 | Long-running (4–8 h CPU; minutes on GPU); cannot be unit-tested | Run `python scripts/pattern_scanner/train.py --seed 42` and observe completion + final val mAP |
| ONNX produces ≥1 bbox conf ≥ 0.5 on fixture in CLEAN venv | TRAIN-04 | Requires creating a fresh venv with only `onnxruntime`, `numpy`, `Pillow` (no torch, no ultralytics) | Run `python scripts/pattern_scanner/verify_onnx.py` — script creates a `tempfile.TemporaryDirectory` venv and exits 0 on success |
| 1,000-positive gate behaviour (multi-style augmentation trigger) | D-08 | Requires running full S&P 500 × 10y generation; expensive | After dataset gen, inspect `dataset_manifest.json`; if `positive_count < 1000`, confirm augmentation block ran (style count > 1 per sample) |
| Cross-machine reproducibility caveat (A6) | D-15 | mplfinance + matplotlib font rendering is machine-dependent | Document in 08-SUMMARY: manifest sha256 is a per-machine equality gate, not cross-machine |

---

## Validation Sign-Off

- [ ] All Phase 8 tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all 4 missing test files + 1 fixture PNG
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for unit tests
- [ ] `nyquist_compliant: true` set in frontmatter when above are checked

**Approval:** pending
