---
phase: 10-batch-pipeline
plan: 01
subsystem: testing
tags: [pytest, batch-pipeline, wave0, nyquist, tdd-red]

# Dependency graph
requires:
  - phase: 09-backtesting-engine
    provides: simulate_trade contract; _load_onnx_session/_score_detection inference shape; _spring_setup_rows canonical fixture
  - phase: 07-detection-engine
    provides: Detection dataclass field surface (mother_bar_index, confirmation_bar_index, bars, filters)
provides:
  - 7 RED-phase pytest scaffolds covering every Phase 10 invariant from 10-VALIDATION.md
  - Locked contract for scripts.pattern_scanner.run_pipeline public API (test surface)
  - Anti-vacuous detection-count guard on the ONNX-fallback test (revision BLOCKER #3)
  - Collection-safe import structure for charts test (revision BLOCKER #2)
  - Required end-to-end smoke test for main() orchestrator (revision BLOCKER #1)
affects: [10-02 (renderer publication style), 10-04 (run_pipeline.py helpers), 10-05 (export_aggregates), 10-06 (main() orchestrator), 10-07 (workflow YAML)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 RED-phase scaffolds — failing-but-collectible pytest skeletons that lock the contract Plan 10-04/06 must satisfy"
    - "Lazy-import inside test bodies (revision BLOCKER #2) — keeps collection green between staggered green-phase plans"
    - "Anti-vacuous detection-count guard (revision BLOCKER #3) — len(detections) >= 1 BEFORE asserting yolo_conf=None"

key-files:
  created:
    - tests/test_run_pipeline_pending.py
    - tests/test_run_pipeline_window.py
    - tests/test_run_pipeline_atomic.py
    - tests/test_run_pipeline_charts.py
    - tests/test_run_pipeline_onnx_fallback.py
    - tests/test_run_pipeline_main.py
    - tests/test_run_pipeline_stats.py
    - .planning/phases/10-batch-pipeline/10-01-SUMMARY.md
  modified: []

key-decisions:
  - "RED-phase scaffolds use the existing tests/conftest.py synthetic_ohlc fixture — no new conftest.py, no new fixture infrastructure"
  - "Charts test imports _cleanup_stale_pngs at module top-level (Plan 10-04 dep) but lazy-imports _render_publication_chart inside the two render-test function bodies (Plan 10-06 dep) so collection succeeds between the two green-phase landings (revision BLOCKER #2)"
  - "ONNX-fallback test imports _spring_setup_rows from tests.test_detector_apply_trend_filters_kwarg (canonical 74-row fixture, pre-resolved import path per revision BLOCKER #3) and asserts len(data['detections']) >= 1 BEFORE asserting yolo_conf=None — prevents the contract assertion from being vacuously true if the fixture produces zero detections"
  - "Main smoke test (test_main_smoke_with_synthetic_ohlc) promoted from optional to REQUIRED per revision BLOCKER #1 — it is the load-bearing assertion that 10-VALIDATION.md row 1 (PIPE-01 nightly workflow) references"
  - "95% completion threshold tested with succeeded=19/failed=1 (19/20=95.0% boundary inclusive -> True) and succeeded=18/failed=2 (18/20=90% -> False) — locks the >=0.95 comparison shape"
  - "is_spring key normalization (RESEARCH L868) asserted via both 'pin_True not in keys' AND 'pin_spring in keys' — implementation-agnostic about whether build_stats_json or export_aggregates does the rename"

patterns-established:
  - "RED-phase Wave 0 scaffolds: imports fail with ModuleNotFoundError until production module lands; pytest collection error is the expected state"
  - "Test seam monkeypatch idiom for run_pipeline_mod: fetch_sp500_tickers, _fetch_ohlc, time.sleep, ONNX_PATH — all four patched as a unit via patched_universe / patched_pipeline fixtures"
  - "FakeDet @dataclass(frozen=True) stand-in for Detection — mirrors the field surface simulate_trade reads, keeps tests isolated from detector.py changes"

requirements-completed: [PIPE-01, PIPE-02, PIPE-03]

# Metrics
duration: 12min
completed: 2026-05-12
---

# Phase 10 Plan 01: Wave 0 RED-phase test scaffolds for run_pipeline Summary

**7 failing-but-collectible pytest scaffolds covering every Phase 10 invariant — locks the contract Plan 10-04 (helpers) and Plan 10-06 (main orchestrator) must satisfy before they GREEN.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-12T (plan execution start)
- **Completed:** 2026-05-12
- **Tasks:** 3 (12 named tests across 7 files)
- **Files created:** 7 test files + this SUMMARY

## Accomplishments

- **7 test files** committed in three atomic groups covering every Phase 10 invariant from 10-VALIDATION.md (pending-state, BDay window, atomic JSON write, stale-PNG cleanup, render determinism, ONNX-absence fallback, 95% threshold, stats fallback chain, is_spring key normalization, end-to-end smoke).
- **12 named test functions** total: 2 pending + 1 window + 1 atomic + 3 charts + 1 ONNX + 3 main + 3 stats = 14 (exceeds the 12+ floor in the plan).
- **Revision BLOCKER #1 closed:** `test_main_smoke_with_synthetic_ohlc` shipped as REQUIRED in `tests/test_run_pipeline_main.py` — the load-bearing assertion for 10-VALIDATION.md row 1.
- **Revision BLOCKER #2 closed:** `tests/test_run_pipeline_charts.py` top-level imports only `_cleanup_stale_pngs` (Plan 10-04 dep). `_render_publication_chart` (Plan 10-06 dep) is lazy-imported inside the two render-test function bodies so module collection succeeds between the two green-phase plans.
- **Revision BLOCKER #3 closed:** `tests/test_run_pipeline_onnx_fallback.py` imports `_spring_setup_rows` from the canonical `tests.test_detector_apply_trend_filters_kwarg` (verified at execution start: returns 74 rows). The test asserts `len(data["detections"]) >= 1` BEFORE asserting `yolo_conf is None`, preventing the contract from being vacuously satisfied if the fixture ever changes shape.

## Task Commits

Each task was committed atomically:

1. **Task 1: pending + window tests** — `68268b0` (test)
2. **Task 2: atomic + charts + onnx-fallback tests** — `0bcc64a` (test)
3. **Task 3: main + stats tests** — `cde55ac` (test)

_Note: Wave 0 RED-phase plan — only `test(...)` commits per TDD; GREEN commits land in Plans 10-04 (helpers) and 10-06 (main + render + smoke)._

## Files Created/Modified

- `tests/test_run_pipeline_pending.py` — D-02 `_resolve_status` wrapper coverage (2 tests: pending state + simulate_trade delegation with 14-key contract).
- `tests/test_run_pipeline_window.py` — D-01 20-BDay cutoff coverage (1 test: fixed today=2026-05-11 with 5 in-window + 5 out-of-window dates).
- `tests/test_run_pipeline_atomic.py` — D-17 / PIPE-02 atomic write coverage (1 test: pre-existing `.tmp` scratch overwritten then cleaned by `os.replace`).
- `tests/test_run_pipeline_charts.py` — D-15 / PIPE-03 (3 tests: set-difference cleanup, PNG magic-byte write, byte-deterministic SHA-256). Top-level `_cleanup_stale_pngs` import + lazy `_render_publication_chart` imports inside render-test bodies.
- `tests/test_run_pipeline_onnx_fallback.py` — D-08 / Phase 9 D-14 graceful ONNX-absence (1 test: `pytest.warns(UserWarning, match="ONNX model not found")` + anti-vacuous `len(detections) >= 1` guard).
- `tests/test_run_pipeline_main.py` — D-16 / PIPE-01 95% threshold + smoke (3 tests: `succeeded=19/failed=1 -> True`, `succeeded=18/failed=2 -> False`, end-to-end smoke with required pipeline_status keys).
- `tests/test_run_pipeline_stats.py` — D-11 fallback chain (3 tests: sparse `by_type_x_spring` fallback metadata, ultimate `all` fallback + cell-key shape, `pin_True -> pin_spring` rename).
- `.planning/phases/10-batch-pipeline/10-01-SUMMARY.md` — this document.

## Decisions Made

- **Followed plan as specified.** All test bodies match the contracts written in the plan's `<action>` blocks; the three revision BLOCKERs were honored verbatim.
- **No new conftest.py.** Reused `tests/conftest.py` `synthetic_ohlc` fixture exactly as the plan required.
- **Spring-fixture import path locked** (revision BLOCKER #3) — verified at execution start that `from tests.test_detector_apply_trend_filters_kwarg import _spring_setup_rows` resolves and returns a 74-row sequence (`len(rows)=74`).
- **`tests/__init__.py` not added.** The repo already supports `from tests.test_X import …` imports across test files (the Phase 9 `test_backtest_yolo_conf_fallback.py` uses the same idiom: `from tests.test_generate_training_data import _spring_setup_rows`). Pytest's rootdir + sys.path injection handles this without an `__init__.py`.

## Deviations from Plan

None — plan executed exactly as written.

The plan was unusually prescriptive (it included verbatim test-body excerpts for nearly every named test), and the three revision BLOCKERs had already been resolved at planning time. Execution was mechanical transcription with three sanity checks:

1. Spring-fixture import path verified to resolve (`_spring_setup_rows()` returns 74 rows).
2. After each task's commit, `pytest --collect-only` was run on that task's files to confirm RED state (`ModuleNotFoundError: No module named 'scripts.pattern_scanner.run_pipeline'`).
3. After all 3 tasks, the full 7-file sweep confirmed all 7 files RED on import — the exact Wave 0 state the plan specified.

## Issues Encountered

- **Bash environment lacks POSIX utilities** (`ls`, `head`, `tail`, `git`). The execution environment is Git Bash on Windows but the PATH is restricted. Worked around by invoking `git` via its absolute path `D:/apps/Git/cmd/git.exe` and using `.venv/Scripts/python.exe` directly for pytest. No PowerShell available either via the Bash tool (so `powershell -NoProfile -Command` fails). All git operations succeeded via the absolute-path workaround; no commits were lost or duplicated.

## RED Phase Verification

Final collection sweep (executed after all 3 task commits):

```
$ .venv/Scripts/python.exe -m pytest tests/test_run_pipeline_*.py --collect-only

collected 0 items / 7 errors

ERROR tests/test_run_pipeline_pending.py
  E   ModuleNotFoundError: No module named 'scripts.pattern_scanner.run_pipeline'
ERROR tests/test_run_pipeline_window.py
  E   ModuleNotFoundError: No module named 'scripts.pattern_scanner.run_pipeline'
ERROR tests/test_run_pipeline_atomic.py
  E   ModuleNotFoundError: No module named 'scripts.pattern_scanner.run_pipeline'
ERROR tests/test_run_pipeline_charts.py
  E   ModuleNotFoundError: No module named 'scripts.pattern_scanner.run_pipeline'
ERROR tests/test_run_pipeline_onnx_fallback.py
  E   ImportError: cannot import name 'run_pipeline' from 'scripts.pattern_scanner'
ERROR tests/test_run_pipeline_main.py
  E   ImportError: cannot import name 'run_pipeline' from 'scripts.pattern_scanner'
ERROR tests/test_run_pipeline_stats.py
  E   ModuleNotFoundError: No module named 'scripts.pattern_scanner.run_pipeline'
```

All 7 files RED on import — exactly as designed. Plan 10-04 creates `scripts/pattern_scanner/run_pipeline.py` with `_resolve_status`, `_window_cutoff`, `_atomic_write_json`, `_cleanup_stale_pngs`, `build_stats_json` and the `run_pipeline` module re-export — which GREENs the pending/window/atomic/charts-cleanup/stats tests. Plan 10-06 adds `_render_publication_chart` and `main()` which GREENs the two render-tests + the three main() tests (smoke + the two threshold tests) + the ONNX-fallback test.

## TDD Gate Compliance

This is a `type: execute` plan with `tdd="true"` on each task — Wave 0 RED-phase only. Per the plan-level TDD gate sequence:

- **RED gate:** Satisfied. Three `test(10-01): …` commits exist (`68268b0`, `0bcc64a`, `cde55ac`).
- **GREEN gate:** Deferred to downstream plans by design (Plans 10-04 + 10-06). Not a Wave 0 concern.
- **REFACTOR gate:** N/A (RED phase only).

The git log will show `test(10-01): scaffold …` × 3, then much later `feat(10-04): …` for the helpers and `feat(10-06): …` for the orchestrator + render. This staggered RED→GREEN pattern is the intended Wave 0 contract; it is documented in the plan's `<objective>` and in 10-VALIDATION.md "Wave 0 Requirements".

## Self-Check

**File existence:**
- FOUND: tests/test_run_pipeline_pending.py
- FOUND: tests/test_run_pipeline_window.py
- FOUND: tests/test_run_pipeline_atomic.py
- FOUND: tests/test_run_pipeline_charts.py
- FOUND: tests/test_run_pipeline_onnx_fallback.py
- FOUND: tests/test_run_pipeline_main.py
- FOUND: tests/test_run_pipeline_stats.py
- FOUND: .planning/phases/10-batch-pipeline/10-01-SUMMARY.md

**Commit existence (via git log --oneline):**
- FOUND: 68268b0 (test(10-01): scaffold pending+window tests for RED phase)
- FOUND: 0bcc64a (test(10-01): scaffold atomic+charts+onnx-fallback tests for RED phase)
- FOUND: cde55ac (test(10-01): scaffold main+stats tests for RED phase)

**RED-phase collection state:** All 7 files fail at import with `ModuleNotFoundError` / `ImportError` on `scripts.pattern_scanner.run_pipeline` — the documented Wave 0 RED state.

## Self-Check: PASSED

## Next Phase Readiness

- **Wave 0 contract locked.** Every Phase 10 invariant from 10-VALIDATION.md has a named test on disk. Plan 10-04 can now ship `run_pipeline.py` with confidence that the test suite will catch contract drift.
- **No blockers** for Plan 10-02 (renderer publication style), Plan 10-04 (run_pipeline helpers), Plan 10-05 (export_aggregates), Plan 10-06 (main orchestrator), or Plan 10-07 (workflow YAML). All downstream `<verify>` blocks can reference these test files.
- **No state mutations.** STATE.md and ROADMAP.md left untouched per the executor key_rules — orchestrator updates those after all plans complete.

---
*Phase: 10-batch-pipeline*
*Completed: 2026-05-12*
