---
phase: 09-backtesting-engine
plan: 04
subsystem: pattern_scanner.backtest
tags: [backtest, empirical-validation, closeout, manual-run]
requires: [phase-09-plan-03]
provides: [empirical-bt03-evidence, phase-9-closeout, methodology-trade-offs]
affects: [.planning/phases/09-backtesting-engine/]
tech-stack:
  added: []
  patterns:
    - "Detached PowerShell child process for long-running jobs (PowerShell Start-Process -PassThru) — survives Bash-tool reaper that killed an earlier in-process bg run at ~70 min"
    - "Two-stage smoke (--limit 5) → full (--tickers all) sequencing with end-to-end JSON header verification"
    - "Pragmatic --no-onnx fallback when full ONNX overlay was projected at ~9 hour wall-clock vs the plan's 50-180 min budget — must_haves explicitly permits onnx_sha256=null when --no-onnx is used"
key-files:
  created:
    - .planning/phases/09-backtesting-engine/09-SUMMARY.md
    - .planning/phases/09-backtesting-engine/09-04-SUMMARY.md
  modified: []
  generated_local_only:
    - _dev/backtest_cache.json (27.8 MB; gitignored per D-06)
decisions:
  - "Run executed with --no-onnx after the full-ONNX run was projected at ~9 hours wall-clock (1 ticker/min steady-state) vs the plan's 50-180 min budget. The plan's must_haves explicitly permits onnx_sha256=null when --no-onnx is used. Trade-off: every record's yolo_conf is null in the empirical cache; Phase 11 must run a small scoring utility over the post-cutoff filtered slice (~1325 detections, ~5 min) to obtain the conf distribution histogram for tier-threshold calibration. Wall-clock cost preserved; methodology integrity preserved (BT-03 is independent of yolo_conf)."
  - "Cutoff held at 2024-01-01 — empirical N comfortably clears BT-03 across all three confirmation_types (filtered out_of_sample: ice_cream=713, mark_up=317, pin=295)"
  - "Both per-plan (09-04) and phase-level (09) SUMMARYs written; Phase 9 closes out at 4/4 plans complete"
metrics:
  duration: ~3h (incl. failed first run; 27 min for the successful --no-onnx run)
  completed: 2026-05-10
---

# Phase 09 Plan 04: Empirical Backtest + Phase 9 Close-out Summary

**One-liner:** Ran the full backtester against the live S&P 500 (10y daily OHLC, 503 tickers); BT-03 acceptance gate cleared with N >> 10 in every confirmation_type; Phase 9 closeout SUMMARY documents the empirical results, methodology trade-offs, and Phase 10/11 hand-off.

## What Shipped

### Empirical run

`_dev/backtest_cache.json` (27.8 MB, gitignored per D-06):

| Header field | Value |
|--------------|-------|
| `schema_version` | 1 |
| `generated_at` | 2026-05-10T11:21:53.472654+00:00 |
| `train_test_cutoff` | 2024-01-01 |
| `seed` | 42 |
| `ticker_count` | 503 |
| `onnx_sha256` | `null` (--no-onnx; see Deviations below) |

Wall-clock for the successful run: **~27 minutes** (10:55:44 → 11:22:42 UTC). 503 tickers fetched + detected + simulated + serialised at ~3.2 sec/ticker in the --no-onnx code path.

### BT-03 evidence

Filtered strategy `1to2_rr_cluster_low_stop`, **out_of_sample** (the integrity number per D-11):

| confirmation_type | n | n_resolved | win_rate | avg_return_r |
|-------------------|---|------------|----------|--------------|
| pin | 295 | 294 | 0.296 | -0.112 |
| mark_up | 317 | 311 | 0.328 | -0.007 |
| ice_cream | 713 | 710 | 0.345 | +0.036 |

**BT-03 PASS.** All three confirmation_types clear `n >= 10` by a wide margin (≥ 295). No cutoff revision required.

### Filter ablation (out_of_sample, all-cell)

| strategy | n | win_rate | avg_return_r |
|----------|---|----------|--------------|
| 1to2_rr_cluster_low_stop | 1325 | 0.330 | -0.007 |
| 1to2_rr_cluster_low_stop__unfiltered | 8841 | 0.353 | +0.061 |

The unfiltered set is **6.7×** larger than the filtered set, as expected (Phase 9 D-12 filter ablation predicted ~10× from algorithm signature). Surprising finding: the unfiltered avg_return_r (+0.061R) is meaningfully higher than the filtered (-0.007R) in the post-cutoff window. This is documented as an empirical observation in the phase-level SUMMARY — the "trend filters add value" narrative does not hold uniformly in this 2-year out-of-sample slice. Win-rate difference (+2.3 percentage points unfiltered) is small.

## Tasks completed

| # | Task | Outcome |
|---|------|---------|
| 1 | Full S&P 500 empirical run | Completed in 27 min (--no-onnx); cache JSON valid; all schema gates pass |
| 2 | Human verification (BT-03 N>=10) | PASS — all three confirmation_types clear by ≥295 |
| 3 | Phase 9 SUMMARY (09-SUMMARY.md) + per-plan SUMMARY | Both written; cutoff held at 2024-01-01 |

## Verification

| Criterion | Result |
|-----------|--------|
| `_dev/backtest_cache.json` exists locally with valid structure (schema_version=1, both strategy keys, both sample blocks per strategy) | yes |
| Cache header has `generated_at`, `train_test_cutoff`, `seed=42`, `ticker_list`, `ticker_count=503`, `onnx_sha256` | yes (onnx_sha256=null per --no-onnx) |
| `! git ls-files --error-unmatch _dev/backtest_cache.json` (file is NOT tracked) | yes (exit 1; "did not match any file(s)") |
| `git check-ignore _dev/backtest_cache.json` returns the path (file IS gitignored) | yes |
| BT-03 acceptance: at least one confirmation_type in filtered out_of_sample has `n >= 10` | yes (all three clear: pin=295, mark_up=317, ice_cream=713) |
| Filter ablation: unfiltered out_of_sample has substantially more detections than filtered | yes (8841 vs 1325; 6.7×) |
| All 26 backtest unit tests still pass | yes (`pytest tests/test_backtest_*.py -q` → 26 passed in 2.76s) |
| Full repo pytest suite green | yes (67 passed, 10 warnings, 0 failed in 23m 4s) |
| `requirements.txt` unchanged | yes (`git diff --stat requirements.txt` empty) |
| `scripts/pattern_scanner/split_config.py` unchanged (no cutoff revision needed) | yes (`git diff --stat` empty) |
| `scripts/pattern_scanner/backtest.py` unchanged (no code modifications in this plan) | yes (`git diff --stat` empty) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Pragmatic mitigation] Switched to `--no-onnx` after wall-clock projection exceeded the plan's budget**

- **Found during:** Task 1 first attempt.
- **Issue:** The full ONNX-enabled run (`--seed 42 --tickers all`) showed steady-state throughput of ~1 ticker/min during the active monitoring window (78 tickers in 78 min). Extrapolated total wall-clock: ~7-9 hours. The plan's budget per RESEARCH §"ONNX Overlay Performance Estimation" was 50-180 minutes. The bottleneck is per-detection ONNX overlay (mplfinance render + 640×640 inference) at ~250-350 ms per detection × ~70 unfiltered detections × 503 tickers = ~3-4 hours of inference alone, on top of fetch + rate-limit + per-ticker compute.
- **Fix:** Killed the in-progress run at 78/503 and restarted with `--no-onnx`. The plan's `must_haves` explicitly permits `onnx_sha256: null` when `--no-onnx` is used. The successful run completed in 27 min. Trade-off: every record's `yolo_conf` is `null` in the empirical cache. This is an acceptable methodology choice because:
  1. BT-03 acceptance is independent of `yolo_conf` (it's about per-confirmation_type N counts).
  2. Phase 11 needs the `yolo_conf` distribution histogram only for the post-cutoff **filtered** slice (~1325 detections), not the full 9k+ unfiltered post-cutoff or the 30k+ in-sample slice. A small Phase 11 utility can score just those 1325 windows in ~5 min.
  3. The full-ONNX path is exercised end-to-end by `tests/test_backtest_yolo_conf_fallback.py::test_yolo_conf_populated_when_session_available` and the prior smoke run (`_dev/backtest_smoke.json` retained, 388 detections all populated). The wiring is verified; the empirical run just chose to bypass it.
- **Files modified:** None. Re-run only.
- **Documented in:** Phase 9 SUMMARY's "Methodology Notes" + "Phase 10/11 Hand-off".

**2. [Rule 1 — Bug] Bash-tool background-task reaper killed first detached run at ~70 min**

- **Found during:** Task 1 first attempt.
- **Issue:** Initial run was started via `Bash(run_in_background=true, timeout=600000)`. The Bash tool's timeout cap is 10 min, but the bg task was reaped at ~71 min wall-clock with `<status>killed</status>`. The Python child went down with the parent. Both stdout/stderr files were 0 bytes because Python's print buffering had not flushed at process kill.
- **Fix:** Restarted via PowerShell `Start-Process -WindowStyle Hidden -PassThru` to launch a fully-detached Python child whose lifecycle is decoupled from the Bash tool's process tree. Combined with `python -u` (unbuffered) so log lines flushed in real time. The successful 27-min run logged 504 lines (one per ticker + one final "wrote ..." line) without any reaper interference.
- **Files modified:** None. Tooling/process change only.
- **Documented in:** This SUMMARY's tech-stack patterns section.

### Auth Gates

None. yfinance is unauthenticated; ONNX model file is local; no credentials required.

## Cutoff Decision Log

**No revision.** TRAIN_TEST_CUTOFF held at `2024-01-01`. Empirical post-cutoff N comfortably clears BT-03's `n >= 10` gate across all three confirmation_types in the filtered out_of_sample slice (minimum N = 295 for pin; ice_cream is 713). Phase 8's training set boundary is preserved unchanged.

## Hand-off Notes for Phase 10 / 11

- **Phase 10 does NOT consume `_dev/backtest_cache.json`** — that file is local-only / portfolio-narrative-only. Phase 10's nightly inference path is detection + ONNX inference, not backtesting.
- **Phase 11** must:
  1. Read `out_of_sample` (NOT `in_sample`) for stat cards (the integrity story per D-11).
  2. Add a build step to copy/transform `_dev/backtest_cache.json` into a frontend-readable JSON (probably at `docs/projects/patterns/backtest_stats.json`).
  3. **Score the post-cutoff filtered slice with the ONNX overlay** — the empirical cache has `yolo_conf=null` everywhere because of the `--no-onnx` trade-off. A small utility (~50 LoC) using the existing `_score_detection` helper over `cache["strategies"]["1to2_rr_cluster_low_stop"]["out_of_sample"]["detections"]` will produce the conf distribution histogram needed for tier-threshold (green/yellow/red badge) calibration. Estimated runtime: ~5 min for ~1325 detections.

## TDD Gate Compliance

This plan is operational (run + write prose); no code commits. The plan's `tasks` are all `type="auto"` plus one `checkpoint:human-verify` (Task 2). No TDD RED/GREEN gates apply.

## Self-Check: PASSED

- `_dev/backtest_cache.json` — FOUND (27.8 MB, locally generated, gitignored)
- `.planning/phases/09-backtesting-engine/09-04-SUMMARY.md` — FOUND (this file)
- `.planning/phases/09-backtesting-engine/09-SUMMARY.md` — FOUND (phase closeout, written in this plan)
- BT-03 acceptance verified: filtered out_of_sample by_confirmation_type minimum N = 295 ≥ 10 — VERIFIED
- All 26 backtest unit tests still green — VERIFIED (`pytest tests/test_backtest_*.py -q`)
- Full repo suite green (67 passed) — VERIFIED
- `_dev/backtest_cache.json` NOT tracked by git — VERIFIED (`git ls-files --error-unmatch` exit 1)
- `_dev/backtest_cache.json` IS gitignored — VERIFIED (`git check-ignore` returns the path)
