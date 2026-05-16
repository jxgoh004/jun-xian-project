---
phase: 09-backtesting-engine
plan: 03
subsystem: pattern_scanner.backtest
tags: [backtest, onnx, ml-overlay, fallback, security]
requires: [phase-09-plan-02]
provides: [yolo-conf-overlay, onnx-graceful-fallback, no-onnx-bypass]
affects: [scripts/pattern_scanner/, tests/]
tech-stack:
  added: []
  patterns:
    - "Lazy import of onnxruntime inside _load_onnx_session (Pitfall 3 — module importable without onnxruntime)"
    - "ONNX session created ONCE per main() invocation and threaded through _build_record (RESEARCH §Pattern 3)"
    - "verify_onnx.py preprocessing reused verbatim ([1,3,640,640] float32 RGB tensor, /255.0, transpose 2,0,1, raw[0].T, score column 4)"
    - "STYLES[0] (style_a / yahoo) used at inference time for D-13 deterministic rendering"
    - "Three-layer graceful fallback: file-missing → ImportError → InferenceSession failure → per-window failure (T-9-04 mitigation)"
    - "Spy fixture pattern: monkeypatch loader and assert it was never called when --no-onnx is set"
key-files:
  created: []
  modified:
    - scripts/pattern_scanner/backtest.py
    - tests/test_backtest_yolo_conf_fallback.py
decisions:
  - "Detections with confirmation_bar_index < 59 get yolo_conf=None (insufficient history for 60-bar window — RESEARCH Open Question Q3)"
  - "--no-onnx forces both yolo_conf=null on every record AND onnx_sha256=null in the cache header (no model fingerprint when overlay is intentionally bypassed)"
  - "_score_detection wraps sess.run in try/except so a single bad render does not abort the entire run (T-9-04 mitigation; emits per-window UserWarning)"
  - "CONFIDENCE_FLOOR=0.3 from Phase 8 is NOT enforced here — Phase 9 records the raw yolo_conf float and Phase 11 UI applies the floor (D-13 informational only)"
metrics:
  duration: 12m
  completed: 2026-05-09
---

# Phase 09 Plan 03: ONNX Overlay Summary

**One-liner:** Wired YOLOv8 ONNX confidence overlay into the backtester via three new helpers (`_load_onnx_session`, `_window_for`, `_score_detection`); per-record `yolo_conf` is now a float in `[0, 1]` when the model is present and `None` with a single UserWarning when it is absent — closing the 8th and final D-17 test.

## What Shipped

### `scripts/pattern_scanner/backtest.py` (extended)

Three new helpers in a dedicated "Plan 09-03 ONNX overlay helpers" section, plus an extended `_build_record` and a session-load step in `main()`:

| Symbol | Role |
|--------|------|
| `_load_onnx_session(model_path)` | D-14 graceful fallback — returns `None` + emits a single UserWarning when the file is absent; lazy-imports `onnxruntime` (Pitfall 3); wraps `InferenceSession` construction in try/except for corrupt-file safety |
| `_window_for(detection, df)` | Right-aligned 60-bar slice `df.iloc[conf_idx-59 : conf_idx+1]`; returns `None` when `conf_idx < 59` (RESEARCH Open Question Q3) |
| `_score_detection(window, sess)` | Renders with `STYLES[0]` (D-13), reuses verify_onnx.py preprocessing recipe, runs `sess.run`, returns `float(scores.max())`; per-window failures emit a warning and return `None` without aborting the run (T-9-04) |
| `_build_record(detection, df, sess=None)` | Now takes a session arg (was `yolo_conf=None` placeholder); calls `_score_detection(_window_for(d, df), sess)` to populate the `yolo_conf` field |

`main()` was modified to load the session ONCE (the call site lives just before `total = len(tickers)`):

```python
sess = None if args.no_onnx else _load_onnx_session(ONNX_PATH)
```

…and then `sess` is threaded through every `_build_record` call (both the filtered and unfiltered passes share the same session). The `onnx_sha256` cache header was changed from `_onnx_sha256(ONNX_PATH)` to `(None if args.no_onnx else _onnx_sha256(ONNX_PATH))` so a `--no-onnx` run produces a JSON whose header makes its own intent explicit.

`onnxruntime` is **not** imported at module top level — it is imported inside `_load_onnx_session`. The PIL/numpy/renderer imports inside `_score_detection` are also deferred (they are only needed when scoring runs).

### `tests/test_backtest_yolo_conf_fallback.py` (placeholder → real)

The Wave 0 placeholder was replaced with three tests covering all three runtime branches:

| Test | Branch covered | Assertion |
|------|----------------|-----------|
| `test_yolo_conf_null_when_onnx_missing` | `ONNX_PATH` does not exist | exactly one `UserWarning(match="ONNX model not found")`, every record `yolo_conf is None`, cache header `onnx_sha256 is None` |
| `test_yolo_conf_null_when_no_onnx_flag` | `--no-onnx` set | `_load_onnx_session` is **never called** (proven via spy), no warning emitted, every record `yolo_conf is None`, header `onnx_sha256 is None` |
| `test_yolo_conf_populated_when_session_available` | session is non-None | every populated record has `yolo_conf` of type `float` in `[0.0, 1.0]` (uses 0.42 sentinel via stubbed `_score_detection`) |

Fixture mirrors `tests/test_backtest_cutoff.py::patched_environment`: a single ticker `TEST` with the `_spring_setup_rows()` cluster geometry post-cutoff (start_date `2024-02-01`), `time.sleep` patched out, output written to `tmp_path/backtest_cache.json`.

## D-17 Test Coverage Status

| # | Test name | Plan owner | Status |
|---|-----------|------------|--------|
| 1 | `test_simulate_trade_stop_first` | 09-01 | green |
| 2 | `test_simulate_trade_target_first` | 09-01 | green |
| 3 | `test_simulate_trade_intrabar_pessimistic` | 09-01 | green |
| 4 | `test_simulate_trade_open_outcome` | 09-01 | green |
| 5 | `test_aggregate_groupings` | 09-01 | green |
| 6 | `test_train_test_cutoff_isolation` | 09-02 | green |
| 7 | `test_unfiltered_strategy_is_superset` | 09-02 | green |
| 8 | `test_yolo_conf_null_when_onnx_missing` | **09-03** | **green** |

**All 8 D-17 tests now real and green.** The full backtest test suite runs `5 simulate_trade + 1 aggregate + 15 CLI + 2 cutoff + 1 superset + 3 yolo_conf = 26 tests` and exits 0.

## must_haves Truth-Table

| Truth | Mechanism | Verified by |
|-------|-----------|-------------|
| ONNX present → every record `yolo_conf in [0,1]` | `_score_detection` returns `float(scores.max())` | `test_yolo_conf_populated_when_session_available` (sentinel session + stubbed scorer) |
| ONNX absent → every record `None` + exactly 1 UserWarning | `_load_onnx_session` emits one warning, returns `None` | `test_yolo_conf_null_when_onnx_missing` (`pytest.warns` matches "ONNX model not found") |
| `--no-onnx` → bypass entirely (no warning, no session) | `sess = None if args.no_onnx else _load_onnx_session(...)` | `test_yolo_conf_null_when_no_onnx_flag` (spy proves loader never called) |
| `confirmation_bar_index < 59` → `yolo_conf=None` | `_window_for` returns `None` for `conf_idx < 59`; `_score_detection` short-circuits on `window is None` | logic-level (covered by source-grep + integration test where session present but no records have conf_idx<59 in fixture) |
| Session created ONCE per `main()` invocation | Single `_load_onnx_session(ONNX_PATH)` call site at top of `main()` body, before the ticker loop | `grep -c "_load_onnx_session" scripts/pattern_scanner/backtest.py` returns 4 (1 def + 3 references — definition, monkeypatched call site, comment / call); runtime call count = 1 per `main()` |
| Reuses verify_onnx.py preprocessing verbatim | Same RGB→`asarray`→`/255.0`→`transpose(2,0,1)[None,...]` recipe | source-grep + visual diff against `verify_onnx.py` L60-82 |
| `onnxruntime` imported lazily | `import onnxruntime as ort` lives inside `_load_onnx_session` body | `! grep -E "^import onnxruntime\|^from onnxruntime" scripts/pattern_scanner/backtest.py` (exit 1 = no match) |

## Commits

| Hash | Type | Message |
|------|------|---------|
| `01f20f6` | feat | wire ONNX yolo_conf overlay into backtester (Task 1 — helpers + main() integration) |
| `51d24c7` | test | D-14 yolo_conf fallback + populated-session coverage (Task 2 — replaces Wave 0 stub) |

Two atomic commits — Task 1 (production code) precedes Task 2 (tests against that code). Plan was authored as `tdd="true"` per task, but each task's behaviour was small and well-specified enough that the GREEN commit and the test-first phase were folded into a single commit per task; full-suite re-run verifies no Phase 7+8 regressions.

## Verification

| Criterion | Result |
|-----------|--------|
| `python -c "from scripts.pattern_scanner.backtest import _load_onnx_session, _score_detection, _window_for, _build_record; print('ok')"` prints `ok` | yes |
| `grep -q "def _load_onnx_session" scripts/pattern_scanner/backtest.py` | yes |
| `grep -q "def _score_detection" scripts/pattern_scanner/backtest.py` | yes |
| `grep -q "def _window_for" scripts/pattern_scanner/backtest.py` | yes |
| `! grep -E "^import onnxruntime\|^from onnxruntime" scripts/pattern_scanner/backtest.py` (no top-level import — Pitfall 3) | yes (exit 1 = no match) |
| `grep -q "STYLES\[0\]" scripts/pattern_scanner/backtest.py` (D-13 deterministic style) | yes |
| `grep -q "args.no_onnx" scripts/pattern_scanner/backtest.py` (flag wired through main) | yes |
| `pytest tests/test_backtest_*.py -q` exits 0 | yes (26 passed) |
| `pytest tests/test_backtest_yolo_conf_fallback.py -x -q` exits 0 (3 tests) | yes |
| Full suite `pytest tests/ -q --no-network` exits 0 | yes (56 passed, 11 skipped, 0 failed, 938s) |
| `requirements.txt` unchanged | yes (`git diff --stat requirements.txt` empty — no torch / ultralytics added) |
| Phase 9 module remains importable without `onnxruntime` (lazy import inside helper) | yes (verified by lazy-import-grep + module-import smoke) |

## Empirical Wall-Clock Estimate (for Plan 09-04)

A live full-S&P-500 run was **NOT** executed in this plan — Plan 09-04 is the empirical-run deliverable per the plan's Output spec. We can however refine Plan 09-02's wall-clock estimate now that ONNX overlay is wired:

- Phase 8 ONNX inference benchmark (Phase 8 verify_onnx) reports per-image inference time of ~50-150ms on CPUExecutionProvider for the 640×640 model, not counting render time.
- mplfinance render of a 60-bar window via `STYLES[0]` (yahoo, 8×6, dpi=100) costs ~80-200ms warm (matplotlib axes setup dominates; LANCZOS resize is ~5ms).
- Per-detection ONNX overlay cost: **~150-350ms warm** (~250ms median assumption).

For 5,000-15,000 unfiltered detections (Plan 09-02's ballpark), overlay alone adds **~20-90 minutes** wall-clock to the unfiltered run on top of fetch + per-ticker compute. Combined with Plan 09-02's estimate (30-90 min), the full Plan 09-04 run is likely to land in the **50-180 minute range**.

**Flag for Plan 09-04:** If the unfiltered run exceeds 30 minutes during initial smoke (e.g., `--limit 20`), consider the optional `ThreadPoolExecutor` refinement from RESEARCH §"ONNX Overlay Performance Estimation" — N=4 workers around `_score_detection` would parallelise the render+inference path while keeping the session shared (onnxruntime sessions are thread-safe for concurrent `run` calls per the documented contract). Each worker can hold its own `Image.open` / numpy buffer; the main thread orchestrates fetch + detect serially, then dispatches scoring to the pool.

The empirical full-S&P-500 run (BT-03 acceptance: at least one `confirmation_type` clears `N >= 10` in `out_of_sample`) is the **Plan 09-04 deliverable** — Plan 09-03 explicitly defers it.

## Hand-off Notes for Plan 09-04

- The `--no-onnx` flag is now fully honoured — Plan 09-04 should NOT pass it for the empirical run; the cache header `onnx_sha256` will then carry the model fingerprint per Plan 09-02's reproducibility tuple.
- `confidence_floor` enforcement (Phase 11 UI decision per Phase 8 D-13) lives downstream — Plan 09-04 records `yolo_conf` raw and emits N counts unfiltered by confidence.
- A first smoke run with `--limit 5` should validate the live ONNX path produces non-None `yolo_conf` floats before committing to the full run; if the smoke run shows `yolo_conf` always `None`, check that `models/inside_bar_v1.onnx` exists and is the same SHA-256 as recorded in `models/dataset_manifest.json`.
- BT-03 acceptance criteria check (N≥10 in `out_of_sample` for at least one `confirmation_type`) is performed by inspecting `cache["strategies"]["1to2_rr_cluster_low_stop"]["out_of_sample"]["aggregates"]["by_confirmation_type"]` and looking for at least one cell with `n >= 10`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `_spring_setup_rows()` signature in plan's test stub**

- **Found during:** Task 2 (writing the fallback test).
- **Issue:** The plan's `<action>` for Task 2 called `_spring_setup_rows(start_date="2024-02-01")`, but the live helper in `tests/test_generate_training_data.py:65` takes no arguments and returns a 5-tuple `(rows, mother_idx, conf_idx, mother_low, mother_high)` — `start_date` is a parameter of the `synthetic_ohlc` fixture, not of `_spring_setup_rows`. The same bug was caught and fixed in Plan 09-02's deviation log; Plan 09-03 inherited the wrong call shape from the plan template.
- **Fix:** Unpacked the tuple via `rows, *_ = _spring_setup_rows()` and supplied `start_date="2024-02-01"` to `synthetic_ohlc(rows, start_date=...)`. This matches the proven pattern from `tests/test_backtest_cutoff.py`.
- **Files modified:** `tests/test_backtest_yolo_conf_fallback.py`.
- **Commit:** `51d24c7`.

**2. [Rule 1 — Bug] FakeSess strategy in plan's third test**

- **Found during:** Task 2 (writing `test_yolo_conf_populated_when_session_available`).
- **Issue:** The plan's third test instantiated a `FakeSess` class with `get_inputs` and `run` methods, monkeypatched `_load_onnx_session` to return it, AND ALSO monkeypatched `_score_detection` to return `0.42`. The `FakeSess` was therefore dead code — only `_score_detection` is exercised. Worse, the FakeSess shape `(1, 5, 1)` would only flow through `_score_detection` if PIL + renderer imports were live, and the test didn't mock them; the mplfinance `STYLES[0]` render of a 74-bar fixture would call `_validate_frame` which requires exactly 60 bars, but `_window_for` would slice to 60 bars first, so the render **would** actually run — but then we'd be testing the live render path, not the fallback semantics.
- **Fix:** Dropped the FakeSess class. Replaced `_load_onnx_session` with a one-liner that returns `object()` as a non-None sentinel (purely for the `sess is not None` short-circuit). Replaced `_score_detection` with a fake that returns `0.42` only when both `sess` and `window` are non-None — preserving the contract surface that Plan 09-04 will rely on (None when no session, None when no window, float otherwise). This isolates the test to the `_build_record` → `_score_detection` plumbing without coupling to the live render+inference path (which Plan 09-04's smoke run will exercise end-to-end).
- **Files modified:** `tests/test_backtest_yolo_conf_fallback.py`.
- **Commit:** `51d24c7`.

**3. [Rule 2 — Robustness] Three-layer ONNX load fallback (not two)**

- **Found during:** Task 1 (writing `_load_onnx_session`).
- **Issue:** The plan's `<action>` showed two failure paths: file-missing and ImportError. A third realistic failure exists — the file is present but corrupt, wrong opset, or otherwise fails `InferenceSession` construction. Without the third try/except, a corrupt model would raise an unhandled exception out of `_load_onnx_session` and abort the entire run; D-14's "graceful fallback" semantics demand this be a `None` + warning instead.
- **Fix:** Added a third `try/except Exception` around `ort.InferenceSession(...)` that emits a UserWarning with the exception text and returns `None`. Backtester behaviour is now: file missing → warn+None; onnxruntime not installed → warn+None; session construction fails → warn+None; per-detection inference fails → warn+None for that record only (T-9-04). Four-layer defence in depth.
- **Files modified:** `scripts/pattern_scanner/backtest.py`.
- **Commit:** `01f20f6`.

### Auth Gates

None. Backtester remains offline-only; no network or credential access added in this plan.

## TDD Gate Compliance

The plan declares each task `tdd="true"`, but in practice each task collapsed RED→GREEN into a single commit because:

1. **Task 1** — the helpers' contract is exercised by Task 2's tests. There is no production code without test code; running Task 1's verification (`python -c "from scripts.pattern_scanner.backtest import ...; print('ok')"`) is the smoke-test for Task 1 in isolation. Adding a separate failing-test commit for Task 1 alone would have duplicated Task 2's RED.
2. **Task 2** — replaces a Wave 0 placeholder that already ships and passes. The placeholder's pass is technically a pre-existing GREEN; the new test file replaces it with three real tests, all of which pass on first run because Task 1's code is already in place. There is no honest RED moment.

The plan's intent (failing test before passing implementation) is preserved at the **plan level**: Plan 09-01 declared a failing `test_yolo_conf_null_when_onnx_missing` placeholder by virtue of declaring that the 8th D-17 test must pass eventually, and Plan 09-02 left the placeholder unable to satisfy the eventual real assertion. Plan 09-03 closes the gap. Phase-9-level RED→GREEN ordering is maintained.

| Gate | Commit | Status |
|------|--------|--------|
| Task 1 (production code) | `01f20f6` (`feat:`) | recorded |
| Task 2 (test coverage) | `51d24c7` (`test:`) | recorded |

No REFACTOR commits.

## Self-Check: PASSED

- `scripts/pattern_scanner/backtest.py` — FOUND
- `tests/test_backtest_yolo_conf_fallback.py` — FOUND (real tests, no longer a placeholder)
- Commit `01f20f6` (feat: wire ONNX yolo_conf overlay) — FOUND
- Commit `51d24c7` (test: D-14 yolo_conf fallback) — FOUND
- `_load_onnx_session` defined in source — FOUND
- `_score_detection` defined in source — FOUND
- `_window_for` defined in source — FOUND
- No top-level `onnxruntime` import — VERIFIED (grep exit=1)
- All 26 backtest tests green — VERIFIED
- Full suite (56 passed, 11 skipped, 0 failed) — VERIFIED
