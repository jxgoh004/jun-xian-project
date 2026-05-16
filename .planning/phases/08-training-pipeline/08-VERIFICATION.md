---
phase: 08-training-pipeline
verified: 2026-05-16T00:00:00Z
status: passed
score: 4/4 success criteria verified
overrides_applied: 0
roadmap_success_criteria_verified: 4
plan_must_haves_verified: 5
data_contract_invariants_verified: 6
retroactive: true
audit_ref: .planning/v2.0-MILESTONE-AUDIT.md
---

# Phase 8: Training Pipeline Verification Report

**Phase Goal:** Produce a YOLOv8n object-detection model, exported as ONNX (`models/inside_bar_v1.onnx`), trained on a deterministic 2D candlestick PNG dataset driven by Phase 7's algorithmic detector. The ONNX artifact must be loadable in a torch-free inference environment so the Phase 10 nightly batch pipeline can score detections without pulling training dependencies.

**Verified:** 2026-05-16
**Status:** PASSED
**Re-verification:** Yes — this report is **retroactive**. Phase 8 shipped on 2026-05-08 (Plan 08-05 closeout) without a phase-level VERIFICATION.md. The Milestone v2.0 audit (`.planning/v2.0-MILESTONE-AUDIT.md`, 2026-05-16) classified TRAIN-01..04 as "partial (verification gap)" purely on the basis of the missing report; every underlying requirement was already satisfied by Plan 08-01..08-05 summaries plus downstream Phase 9 + Phase 10 wiring. This document closes that governance gap by cross-checking the existing evidence against the Phase 8 success criteria.

## Goal Achievement

### ROADMAP Success Criteria (Phase 8)

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | Chart renderer: 2D mplfinance PNG with style randomization (DPI, figsize, candle width) | PASS | `scripts/pattern_scanner/renderer.py` (260 lines) exposes 3 frozen `RenderStyle` instances `STYLES` (style_a yahoo / style_b charles / style_c classic) varying base_style + figsize + dpi + candle_width + facecolor; `matplotlib.use("Agg")` forced before pyplot/mplfinance imports; 5/5 tests GREEN per 08-02-SUMMARY (`test_render_returns_640x640_png`, `test_render_deterministic_same_style`, `test_render_styles_differ`, `test_render_rejects_wrong_bar_count`, `test_compute_bbox_encloses_cluster_excludes_neighbours` with W8 spike baseline ±0.02). |
| 2 | YOLO directory structure + 10:1 negative-sample cap | PASS | `scripts/pattern_scanner/generate_training_data.py` (344 lines) writes `_dev/training_dataset/images/{train,val}` + `labels/{train,val}` + `data.yaml` (nc=1, names={0: inside_bar_spring}); 8/8 generator tests GREEN per 08-03-SUMMARY including `test_yolo_directory_layout`, `test_neg_pos_ratio_capped` (asserts `manifest["neg_pos_ratio"] <= 10.0`), `test_negative_labels_empty`, `test_hard_negative_set_difference` (3-tuple `(ticker, mother_idx, conf_idx)` key per RESEARCH §Pitfall 7), `test_cutoff_enforced`, `test_manifest_sha256_consistent`. Real-run manifest (Plan 04) records ratio 5.45:1 (21,849 neg / 4,010 pos), under the 10:1 cap. |
| 3 | YOLOv8n training completes; ONNX loads in onnxruntime; produces bbox for known positive | PASS | `models/inside_bar_v1.onnx` (11.7 MB, opset 12) committed in Plan 04 (`a69a1b9`); training_summary.json records `best_map50=0.7897`, `best_map50_95=0.6080`, `epochs_run=100`, `wall_time_s=11118.7`, `seed=42`, `imgsz=640`, `fliplr=0.0`. `scripts/pattern_scanner/verify_onnx.py` (171 lines, Plan 05 `21ea681`) clean-venv subprocess gate exits 0; on the committed holdout fixture `tests/fixtures/known_positive_holdout.png` (MSFT 2024-01-08, post-cutoff, style_a) it produces a detection at conf=0.3729 with bbox (cx=0.834, cy=0.288, w=0.050, h=0.102) — IoU ≈ 1.0 vs ground truth (0.835, 0.289, 0.049, 0.099). |
| 4 | ONNX opset logged + clean-venv round-trip passes pre-commit | PASS | `test_opset_recorded` (in `tests/test_onnx_round_trip.py`) GREEN per Plan 04 (`ac842cf`); opset 12 logged in `models/training_summary.json`. `verify_onnx.py` creates a temp venv via `venv.create()`, pip-installs only `onnxruntime + numpy + Pillow`, **asserts NO torch / NO ultralytics leakage**, runs inference, exits 0 at conf ≥ CONFIDENCE_FLOOR (0.3). Full pytest after Plan 05: 30 passed, 11 skipped (network), 0 failed (08-05-SUMMARY). |

**ROADMAP success score: 4/4**

### Plan-Level Must-Haves (per-plan SUMMARY frontmatter)

#### Plan 08-01 — Foundation (`scripts/pattern_scanner/split_config.py` + kwarg + Wave 0)

| Required Artifact | Status | Evidence |
|-------------------|--------|----------|
| `detect(df, ticker, apply_trend_filters: bool = True)` kwarg added without breaking Phase 7 signature | PASS | 08-01-SUMMARY commit `8e31198`; `test_default_kwarg_matches_phase7` + `test_unfiltered_is_superset` GREEN; Phase 7 23-test contract intact (12 passed + 11 skipped under `--no-network`). |
| `scripts/pattern_scanner/split_config.TRAIN_TEST_CUTOFF = "2024-01-01"` as single SoT | PASS | Commit `ccc8e9d`; imported by both `generate_training_data.py:57` and `backtest.py:31` (cross-phase audit row in v2.0-MILESTONE-AUDIT.md). |
| 4 Wave-0 test files committed with `pytest.mark.skip` stubs | PASS | `tests/test_renderer.py` (3 stubs → 5 real in Plan 02), `tests/test_generate_training_data.py` (8 stubs → 8 real in Plan 03), `tests/test_onnx_round_trip.py` (3 stubs → 3 real by Plan 05), `tests/test_detector_apply_trend_filters_kwarg.py` (2 real on day one). |
| Dependency manifests split: `requirements-training.txt` (ultralytics) vs `requirements.txt` (inference-only) | PASS | `requirements-training.txt` carries `ultralytics>=8.4.0,<9.0`; `requirements.txt` adds `mplfinance>=0.12.10b0`, `matplotlib>=3.8`, `onnxruntime>=1.19`, `Pillow>=10.0`. No torch / ultralytics in production manifest — structurally asserted by Phase 10's `test_requirements_has_no_training_deps`. |

#### Plan 08-02 — Renderer (`scripts/pattern_scanner/renderer.py`)

| Required Artifact | Status | Evidence |
|-------------------|--------|----------|
| `matplotlib.use("Agg")` before any pyplot/mplfinance import | PASS | renderer.py:24 (before pyplot at L32, mplfinance at L33) per 08-02-SUMMARY. |
| 3 frozen `RenderStyle` instances exposed as `STYLES` | PASS | renderer.py top-level tuple; byte-distinct outputs verified by `test_render_styles_differ`. |
| Approach A bbox: `compute_bbox_normalized()` returning `(cx, cy, w, h)` in [0,1] coerced to plain `float` | PASS | All 4 components ∈ [0,1] asserted; spike-baseline `_SPIKE_*` constants in `tests/test_renderer.py` lock geometry within ±0.02 across mplfinance versions. |
| `render()` validates `len(df) == 60` and `{Open, High, Low, Close}` columns | PASS | `test_render_rejects_wrong_bar_count` raises `ValueError(match="60 bars")` on a 50-bar slice. |

#### Plan 08-03 — Dataset generator (`scripts/pattern_scanner/generate_training_data.py`)

| Required Artifact | Status | Evidence |
|-------------------|--------|----------|
| `_detect_hard_negatives` uses `(ticker, mother_idx, conf_idx)` 3-tuple key (RESEARCH §Pitfall 7) | PASS | `test_hard_negative_set_difference` GREEN with flat-prefix fixture proving filters-on=[], filters-off≥1, and positive ∩ negative key sets are disjoint. |
| YOLO label format: 5 fields, class_id=0, all 4 floats ∈ [0,1] | PASS | `test_positive_label_format` GREEN. |
| Manifest written to BOTH `_dev/training_dataset/dataset_manifest.json` AND `models/dataset_manifest.json` | PASS | `test_yolo_directory_layout` asserts both copies exist; `models/dataset_manifest.json` committed in Plan 04 real run with `concat_sha256=72767c3f…`. |
| Same-seed determinism: `concat_sha256` identical across two runs with the same seed (monkeypatched fetch) | PASS | `test_manifest_sha256_consistent` GREEN (synthetic fixture); `test_manifest_sha256_round_trip` GREEN in Plan 05 (`57a8cee`). |
| Cutoff enforced: zero detections with `confirmation_date >= TRAIN_TEST_CUTOFF` end up in training labels | PASS | `test_cutoff_enforced` patches cutoff to `1900-01-01`, asserts no non-empty labels AND `manifest["positives"] == 0`. |

#### Plan 08-04 — Training run + ONNX export

| Required Artifact | Status | Evidence |
|-------------------|--------|----------|
| `models/inside_bar_v1.onnx` committed (1–50 MB range) | PASS | 11.7 MB on disk (commit `a69a1b9`). |
| `models/training_summary.json` with best_map50, opset, seed, imgsz, fliplr, wall_time | PASS | best_map50=0.7897; opset=12; seed=42; imgsz=640; fliplr=0.0; wall_time=11118.7s; epochs_run=100. |
| Holdout fixture committed: `tests/fixtures/known_positive_holdout.png` with post-cutoff ground-truth JSON | PASS | MSFT 2024-01-08, style_a, post_cutoff=true, ground-truth bbox (0.835, 0.289, 0.049, 0.099). Committed in `9edc134`. |
| Phase 7 contract intact after training landings | PASS | `14 passed, 11 skipped, 0 failed` after Plan 04 commits per 08-04-SUMMARY. |

#### Plan 08-05 — Clean-venv ONNX round-trip + closeout

| Required Artifact | Status | Evidence |
|-------------------|--------|----------|
| `scripts/pattern_scanner/verify_onnx.py` exits 0 in a venv with **only** `onnxruntime + numpy + Pillow` | PASS | Stdout captured in 08-05-SUMMARY: `[verify] confirmed: clean venv has NO torch / ultralytics` → `[verify] PASS: known_positive_holdout.png got conf >= 0.3`. |
| All 3 ONNX round-trip tests active (none skipped) | PASS | Plan 05 final pytest line: 30 passed (12 schema + 2 kwarg + 5 renderer + 8 generator + 3 onnx_round_trip), 11 skipped (network), 0 failed. |
| CONFIDENCE_FLOOR 0.5 → 0.3 deviation logged with rationale and Phase 10 hand-off | PASS | 08-05-SUMMARY §Decisions item 1 documents Rule-4 user-approved deviation; `verify_onnx.py` module docstring records the threshold; Phase 10 hand-off note explicitly requires the nightly pipeline to match (audit confirms Phase 10 implementation aligned). |

### Data-Contract Invariants Honoured

| Invariant | Source | Status | Evidence |
|-----------|--------|--------|----------|
| D-03 — 60-bar window right-aligned at confirmation index | 08-RESEARCH | PASS | `_slice_window()` in generate_training_data.py extracts bars ending at confirmation; bbox spike `right_edge=0.860 ≥ 0.85` per 08-02-SUMMARY. |
| D-07 — Single TRAIN_TEST_CUTOFF source-of-truth shared with Phase 9 | 08-RESEARCH | PASS | `split_config.TRAIN_TEST_CUTOFF` imported by both `generate_training_data.py:57` and `backtest.py:31`; literal "2024-01-01" appears only in split_config.py:9. |
| D-08 — ≥ 1,000 positives in training set (multi-style augmentation if below) | 08-RESEARCH | PASS | Real-run manifest: 4,010 raw positives (well above floor); `_augment_to_floor()` dead code on the live run. |
| D-09 — Negative:Positive ratio ≤ 10:1 | 08-RESEARCH | PASS | Real-run ratio 5.45:1 (21,849 / 4,010), strictly under the cap; `test_neg_pos_ratio_capped` GREEN. |
| D-17 — ≥ 3 visually distinct render styles to prevent renderer memorisation | 08-RESEARCH | PASS | All 3 styles seen on the real run (`renderer_styles_seen: ["style_a", "style_b", "style_c"]`); `test_render_styles_differ` asserts byte-distinct outputs. |
| D-18 — 20% val fraction, deterministic shuffle from seeded `random.Random` | 08-RESEARCH | PASS | `VAL_FRACTION = 0.20` constant in generate_training_data.py; single seeded `random.Random(args.seed)` drives style choice + train/val shuffle + negative subsample. |

### Cross-Phase Wiring Evidence (Phase 8 → Phase 9 → Phase 10 hand-off)

This is the strongest existing evidence that the Phase 8 deliverables actually work end-to-end — independent of the per-plan summaries, downstream phases consume Phase 8's artifacts on disk in production.

| Hand-off | Contract | Status | Evidence |
|----------|----------|--------|----------|
| Phase 8 → Phase 9 | `models/inside_bar_v1.onnx` loadable via lazy `_load_onnx_session` in `scripts/pattern_scanner/backtest.py:360-391` (three-layer fallback) | WIRED | File exists on disk (11.7 MB, opset 12). Empirical Phase 9 dev cache deliberately used `--no-onnx` (yolo_conf=null on all 40,022 records) for runtime budget — that path is the documented bypass per 09-04-SUMMARY, not a Phase 8 defect. The populated-session contract is exercised by Phase 9 unit fixture. |
| Phase 8 → Phase 9 | `split_config.TRAIN_TEST_CUTOFF` single SoT for both training cutoff and backtest partition | WIRED | 0 partition violations across 40,022 backtest records per v2.0-MILESTONE-AUDIT row 3. |
| Phase 8 → Phase 10 | Inference deps remain clean (no torch / no ultralytics) for nightly cron | WIRED | `.github/workflows/nightly-pattern-scanner.yml` install step uses `requirements.txt` only; `test_requirements_has_no_training_deps` GREEN (Phase 10 unit). |
| Phase 8 → Phase 10 | Production cron loads `models/inside_bar_v1.onnx` successfully and scores detections at threshold 0.3 | WIRED | **Three consecutive green nightly cron runs** (`0a8621d`, `413c6cc`, `5d179ec`) through 2026-05-15. Live `docs/projects/patterns/data.json` records 44 detections with non-null `yolo_conf` values; `pipeline_status.completed: true`. This is the ground-truth production proof that the ONNX artifact is loadable, scoring meaningful confidences, and operating under the calibrated 0.3 threshold. |
| Phase 8 → Phase 10 | Renderer reuse for annotated chart PNGs at `docs/projects/patterns/charts/` | WIRED | 41 annotated PNGs on disk per audit; Phase 10's `render_publication_chart` re-uses `scripts/pattern_scanner/renderer.py`. |

### Required Artifacts (Level 1-3 verification)

| Artifact | Exists | Substantive | Wired | Status |
|----------|--------|-------------|-------|--------|
| `scripts/pattern_scanner/split_config.py` | YES | YES (`TRAIN_TEST_CUTOFF = "2024-01-01"` + module docstring) | YES (imported by gen + backtest) | VERIFIED |
| `scripts/pattern_scanner/renderer.py` | YES | YES (260 lines, public API + Agg backend + 3 STYLES + Approach A bbox) | YES (consumed by generate_training_data.py and Phase 10 render_publication_chart) | VERIFIED |
| `scripts/pattern_scanner/generate_training_data.py` | YES | YES (344 lines, CLI orchestrator) | YES (produced the real-run manifest + dataset that trained inside_bar_v1.onnx) | VERIFIED |
| `scripts/pattern_scanner/verify_onnx.py` | YES | YES (171 lines, clean-venv subprocess + holdout inference) | YES (Plan 05 gate; structural assertion of no-torch invariant) | VERIFIED |
| `models/inside_bar_v1.onnx` | YES (11.7 MB) | YES (opset 12; produced by Plan 04 RTX 5070 desktop training run, mAP@0.5=0.7897) | YES (loaded by Phase 9 `_load_onnx_session` and Phase 10 nightly cron — three green runs) | VERIFIED |
| `models/training_summary.json` | YES | YES (best_map50, opset, seed, imgsz, fliplr, wall_time fields) | YES (`test_opset_recorded` reads it) | VERIFIED |
| `models/dataset_manifest.json` | YES | YES (sorted-keys deterministic JSON with positives/negatives/ratio/sha/seed/tickers/styles) | YES (Plan 05's verify_onnx.py re-reads provenance) | VERIFIED |
| `tests/fixtures/known_positive_holdout.png` | YES | YES (MSFT 2024-01-08, post-cutoff, style_a; ground-truth bbox JSON sidecar) | YES (consumed by verify_onnx.py inference round-trip) | VERIFIED |
| `requirements-training.txt` | YES | YES (`ultralytics>=8.4.0,<9.0`) | YES (quarantined from production) | VERIFIED |
| `requirements.txt` (Phase 8 additions) | YES | YES (mplfinance, matplotlib, onnxruntime, Pillow) | YES (loaded by nightly cron; structurally asserted by Phase 10 test) | VERIFIED |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| TRAIN-01 | 08-02 | Chart renderer produces consistent 2D OHLC candlestick PNGs from yfinance DataFrames using mplfinance | SATISFIED | `scripts/pattern_scanner/renderer.py` committed; 5/5 renderer tests GREEN; W8 spike baseline locks geometry. |
| TRAIN-02 | 08-03 | Training data generator produces YOLOv8-format annotations with style randomisation (DPI, figsize, candle width) | SATISFIED | `generate_training_data.py` committed; 8/8 generator tests GREEN; real-run manifest shows all 3 styles seen across 4,010 positives. |
| TRAIN-03 | 08-03 | Negative sampling capped at 10:1 | SATISFIED | `NEG_POS_RATIO = 10` constant + `test_neg_pos_ratio_capped` GREEN; real-run empirical ratio 5.45:1. |
| TRAIN-04 | 08-04 + 08-05 | YOLOv8n trained, ONNX exported with opset logged to `models/inside_bar_v1.onnx`, loadable in onnxruntime | SATISFIED | ONNX on disk (11.7 MB, opset 12); training_summary.json present; verify_onnx.py clean-venv gate PASS at conf 0.3729 IoU ~1.0; three green production cron runs confirm onnxruntime load + score path in the wild. |

### Anti-Patterns Found

None of the following stub indicators were observed in the Phase 8 deliverables:
- No `TODO`/`FIXME`/`PLACEHOLDER` blockers in the renderer or generator
- No `return None`/empty list shortcuts in the per-sample write loop
- No hardcoded empty data arrays flowing into the manifest
- No `pytestmark = pytest.mark.skip` in the four production test files (all 4 promoted from Wave 0 stub state by end of Plan 05)
- Production `requirements.txt` carries zero training-only deps (structural no-torch / no-ultralytics invariant)

### Human Verification

Phase 8 had no `gate=blocking` human checkpoint on a UI artefact — the deliverable is an offline binary model. The two implicit human gates were:
1. **Plan 08-04 W4 / W5 checkpoints:** user reviewed the dataset stats and approved the RTX 5070 desktop training path over local CPU (which would have taken 6–12h instead of 3h05m); subsequently reviewed `best_map50=0.7897` + rendered holdout fixture and approved the model for ONNX export.
2. **Plan 08-05 CONFIDENCE_FLOOR Rule-4 deviation:** user approved lowering the spec's 0.5 floor to 0.3 after seeing the post-cutoff out-of-distribution score distribution (top-5 detections clustered at 0.27–0.37 with correct spatial localisation, IoU ≈ 1.0). This was logged as a deviation in 08-05-SUMMARY §Decisions and propagated to the Phase 10 hand-off note.

Both gates are recorded in 08-04-SUMMARY and 08-05-SUMMARY respectively. The retrospective ground-truth signal — three green nightly cron runs through 2026-05-15 — is the strongest possible human-and-machine verification that the gates were called correctly.

### Tech Debt / Deferred Items

Carried forward per v2.0-MILESTONE-AUDIT §Tech Debt — Phase 8:

- **CONFIDENCE_FLOOR 0.5 → 0.3 deviation** (user-approved, Rule-4). Phase 10 inference threshold remains aligned; documented in 08-05-SUMMARY hand-off and `verify_onnx.py` module docstring. Not a blocker; revisit after ~30 nightly runs to recalibrate from empirical yolo_conf distribution.
- **Cross-machine reproducibility caveat (D-15 / A6):** mplfinance + matplotlib font rendering is machine-dependent. The manifest `concat_sha256` is a per-machine equality gate, not cross-machine — observed empirically by the 2026-05-03 laptop run vs 2026-05-08 desktop run producing different SHAs for the same `seed=42` (4,010 vs 4,064 positive count delta also driven by 5-day yfinance OHLC drift). Acceptable: determinism is preserved within a single fetch session, which is what the test asserts via monkeypatched fetch.
- **mAP@0.5:0.95 = 0.61** — bbox tightness varies. Candidate for retrain with more aggressive box-loss weighting in a future milestone. Not a v2.0 blocker; current bbox is visibly correct on production annotated PNGs (Phase 11 verification confirmed).
- **`np.random.default_rng` reserved but unused** — generator currently uses only `random.Random(args.seed)`; the numpy RNG seam is future-proofing. Cosmetic.

### Gaps Summary

No gaps. All four ROADMAP success criteria are verified end-to-end from disk artifacts + three green production cron runs. Plan-level must-haves across 08-01..08-05 are all satisfied by their respective SUMMARY commits. All six data-contract invariants hold. Cross-phase wiring to Phase 9 and Phase 10 is WIRED. The only formal "verification gap" flagged by the v2.0-MILESTONE-AUDIT was the absence of this report itself — now produced.

---

**Phase 08 retroactively verified — Milestone v2.0 governance gap closed.**

_Verified: 2026-05-16_
_Verifier: Claude (gsd-executor, retroactive verification per v2.0-MILESTONE-AUDIT recommendation #1)_
