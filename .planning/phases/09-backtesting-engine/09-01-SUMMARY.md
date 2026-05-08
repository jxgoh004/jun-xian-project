---
phase: 09-backtesting-engine
plan: 01
subsystem: pattern_scanner.backtest
tags: [backtest, pure-functions, wave-0, tdd]
requires: [phase-07-detection-engine]
provides: [simulate_trade, aggregate, backtest-pure-core]
affects: [scripts/pattern_scanner/, tests/]
tech-stack:
  added: []
  patterns:
    - "Pure-function core + thin CLI wrapper (mirrors detector.py / generate_training_data.py)"
    - "TDD RED/GREEN per task: failing test commit precedes implementation commit"
    - "Three-bucket trade outcome {stop, target, open} — no timeout"
    - "Pessimistic intrabar resolution — same-bar stop+target → stop wins"
    - "R-multiple return unit (stop=-1.0, target=+2.0, open=signed)"
    - "Single-pass groupby aggregator with str-coerced composite keys"
key-files:
  created:
    - scripts/pattern_scanner/backtest.py
    - tests/test_backtest_simulate_trade.py
    - tests/test_backtest_aggregate.py
    - tests/test_backtest_cutoff.py
    - tests/test_backtest_unfiltered_superset.py
    - tests/test_backtest_yolo_conf_fallback.py
  modified: []
decisions:
  - "Adapted plan's dict-row test fixtures to the existing tuple-row synthetic_ohlc signature (Rule 1)"
  - "Added sma_levels to inline _make_detection helper — required by Detection dataclass since Phase 7 D-10 (Rule 1)"
metrics:
  duration: 22m
  completed: 2026-05-08
---

# Phase 09 Plan 01: Pure-Function Backtest Core Summary

**One-liner:** Land `simulate_trade` (D-01..D-05 trade resolution) and `aggregate` (D-09 four-slice rollup) as pure functions in `scripts/pattern_scanner/backtest.py`, with 5 of the 8 D-17 tests green and 3 stubs scaffolded for downstream plans.

## What Shipped

### `scripts/pattern_scanner/backtest.py` (new)

**Public symbols:**
- `simulate_trade(df, detection, stop_price, target_price) -> dict` — forward-walks a trade entered at the open of `confirmation_bar_index + 1`, resolving as `stop`, `target`, or `open` per D-01..D-05.
- `aggregate(records, group_keys) -> dict` — single-pass groupby producing the eight D-09 cell fields per slice.

**Internal helpers:** `_identity(detection)` copies the 6 D-08 identity fields onto every record; `_iso(ts)` coerces a `pandas.Timestamp` to `YYYY-MM-DD` (mirrors `detector.py` L289).

**D-01..D-05 enforcement:**
- Entry at open of conf+1 bar (D-01).
- Three-bucket outcome `{stop, target, open}`, no timeout (D-02).
- Same-bar stop+target → stop wins (D-03).
- Entry-bar gap-down at/below stop → recorded as `stop` with R from gap (D-04).
- R-multiples: stop=-1.0, target=+2.0, open=`(last_close-entry)/risk` (D-05).

**Coercion guarantees (Pitfalls 1, 2, 7):** every numeric record field is wrapped in `float(...)`, every date field is built via `_iso(ts)` so no `numpy.float64` or `pandas.Timestamp` leaks.

### Five new test files

| File | Status | Tests |
|------|--------|-------|
| `tests/test_backtest_simulate_trade.py` | Filled (Task 2) | 4 D-17 tests pass |
| `tests/test_backtest_aggregate.py` | Filled (Task 3) | 1 D-17 test passes |
| `tests/test_backtest_cutoff.py` | Stub (placeholder) | Filled in Plan 09-02 |
| `tests/test_backtest_unfiltered_superset.py` | Stub (placeholder) | Filled in Plan 09-02 |
| `tests/test_backtest_yolo_conf_fallback.py` | Stub (placeholder) | Filled in Plan 09-03 |

**Test result:** `pytest tests/test_backtest_*.py -q` → **8 passed** (4 simulate_trade + 1 aggregate + 3 placeholder stubs).

## D-17 Test Coverage Status

| # | Test name | Plan owner | Status |
|---|-----------|------------|--------|
| 1 | `test_simulate_trade_stop_first` | 09-01 | green |
| 2 | `test_simulate_trade_target_first` | 09-01 | green |
| 3 | `test_simulate_trade_intrabar_pessimistic` | 09-01 | green |
| 4 | `test_simulate_trade_open_outcome` | 09-01 | green |
| 5 | `test_aggregate_groupings` | 09-01 | green |
| 6 | `test_train_test_cutoff_isolation` | 09-02 | stub (placeholder passes) |
| 7 | `test_unfiltered_strategy_is_superset` | 09-02 | stub (placeholder passes) |
| 8 | `test_yolo_conf_null_when_onnx_missing` | 09-03 | stub (placeholder passes) |

Plan 09-01's deliverable of "5 of 8 D-17 tests green" is met.

## Commits

| Hash | Type | Message |
|------|------|---------|
| `df1744b` | test | scaffold five Wave 0 backtest pytest stubs |
| `394b85f` | test | add failing simulate_trade tests (D-01..D-05) — RED |
| `64bbba4` | feat | implement simulate_trade pure function (D-01..D-05) — GREEN |
| `bb4b55e` | test | add failing aggregate D-09 four-slice test — RED |
| `6226b2e` | feat | implement aggregate single-pass groupby (D-09) — GREEN |

Five commits total. RED commits precede GREEN commits per TDD discipline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `synthetic_ohlc` fixture signature mismatch**
- **Found during:** Task 2 (writing simulate_trade tests).
- **Issue:** The plan's `<action>` test code passed dict rows like `{"date": ..., "open": ..., "volume": ...}` to `synthetic_ohlc(...)`, but the live fixture in `tests/conftest.py` accepts `List[Tuple[float, float, float, float]]` (open, high, low, close — no Volume column).
- **Fix:** Translated each row literal to the tuple form `(open, high, low, close)`. Numeric values and bar geometry are bit-for-bit identical to the plan's intent.
- **Files modified:** `tests/test_backtest_simulate_trade.py`.
- **Commit:** `394b85f`.

**2. [Rule 1 — Bug] `Detection` dataclass requires `sma_levels`**
- **Found during:** Task 2 GREEN run.
- **Issue:** Plan's inline `_make_detection` helper omitted the `sma_levels` field. The live `Detection` dataclass in `scripts/pattern_scanner/detector.py` (L52–64) requires `sma_levels: Dict[str, float]` per Phase 7 D-10. Construction without it raises `TypeError`.
- **Fix:** Added `sma_levels={"sma20": 10.0, "sma50": 10.0, "atr14": 0.5}` to the helper. simulate_trade does not read this field, so the dummy values don't affect the test's behavior.
- **Files modified:** `tests/test_backtest_simulate_trade.py`.
- **Commit:** `64bbba4`.

Both deviations are self-contained to the test scaffold; neither changes the implementation contract or the plan's verification criteria.

### Auth Gates

None.

## Verification

| Criterion | Result |
|-----------|--------|
| 5 Wave 0 stub files exist | yes |
| `pytest tests/test_backtest_simulate_trade.py tests/test_backtest_aggregate.py -q` exits 0 | yes (5 tests) |
| `simulate_trade` and `aggregate` importable from `scripts.pattern_scanner.backtest` | yes |
| All numeric record fields are `type(value) is float` | verified inline in tests + sanity-check one-liner |
| All date record fields match `r"\d{4}-\d{2}-\d{2}"` | verified by exit_date / entry_date assertions |
| No hardcoded `"2024-01-01"` cutoff literal in `backtest.py` | verified (grep: 0 matches) |
| `requirements.txt` unchanged | verified (`git diff --stat HEAD~4 HEAD -- requirements.txt` empty) |

## Hand-off Notes for Plan 09-02

- **Cutoff import (deliberately deferred):** Plan 09-02 must add `from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF` to `backtest.py` when wiring the orchestrator. Plan 09-01 deliberately did NOT introduce this import — the cutoff has no role in the pure-function core.
- **Detection helper:** the inline `_make_detection` in `tests/test_backtest_simulate_trade.py` is a useful template for Plan 09-02's cutoff and superset tests. It demonstrates the full Detection signature including `sma_levels`.
- **Stub format:** the three remaining stub files all import the test module under `# Module-under-test import is deferred to test bodies` — Plan 09-02 / 09-03 should preserve this idiom and only add real `from scripts.pattern_scanner.backtest import ...` lines once their referenced functions exist.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| Task 2 RED | `394b85f` (`test:`) | recorded |
| Task 2 GREEN | `64bbba4` (`feat:`) | recorded |
| Task 3 RED | `bb4b55e` (`test:`) | recorded |
| Task 3 GREEN | `6226b2e` (`feat:`) | recorded |

No REFACTOR commits — implementation matched the plan's verbatim pseudocode and required no clean-up after passing tests.

## Self-Check: PASSED

- `scripts/pattern_scanner/backtest.py` — FOUND
- `tests/test_backtest_simulate_trade.py` — FOUND
- `tests/test_backtest_aggregate.py` — FOUND
- `tests/test_backtest_cutoff.py` — FOUND
- `tests/test_backtest_unfiltered_superset.py` — FOUND
- `tests/test_backtest_yolo_conf_fallback.py` — FOUND
- Commit `df1744b` — FOUND
- Commit `394b85f` — FOUND
- Commit `64bbba4` — FOUND
- Commit `bb4b55e` — FOUND
- Commit `6226b2e` — FOUND
