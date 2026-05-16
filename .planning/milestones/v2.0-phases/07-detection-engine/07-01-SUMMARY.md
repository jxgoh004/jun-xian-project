---
phase: 07-detection-engine
plan: 01
subsystem: pattern-scanner
tags: [python, detection, pytest, finance, candlestick, dataclass, atr, sma]

requires:
  - phase: 06-website-marketing-revamp
    provides: stable portfolio shell ready for new project addition
provides:
  - "scripts/pattern_scanner/detector.py — pure-Python inside-bar-spring detector with detect(df, ticker) public API"
  - "scripts/pattern_scanner/__init__.py — package re-exports Detection and detect"
  - "tests/ harness at repo root with pytest.ini, conftest.py (network marker auto-skip), synthetic_ohlc fixture"
  - "12 unit tests locking DET-01..DET-04 against the synthetic OHLC fixture (no network required)"
  - "requirements-dev.txt pinning pytest>=8.4,<9 (dev-only; runtime requirements.txt unchanged)"
  - "CLI ticker validation regex ^[A-Z0-9.-]{1,10}$ enforced before yfinance fetch (T-07-01)"
affects:
  - phase 07-detection-engine plan 02 (live yfinance regression suite)
  - phase 08-training-data-generation (will call detect() per window for annotation)
  - phase 09-backtesting (consumes Detection dataclass directly)
  - phase 10-batch-pipeline (imports detect() in nightly GitHub Actions job)
  - phase 11-frontend (renders Detection.bars and Detection.is_spring badge)

tech-stack:
  added:
    - pytest>=8.4,<9 (dev-only)
  patterns:
    - "slice-first idiom for indicator evaluation: view = df.iloc[:k + 1]; metric = compute(view).iloc[-1]"
    - "Wilder ATR via series.ewm(alpha=1/14, adjust=False, min_periods=14).mean() — no new dep"
    - "Frozen @dataclass with to_dict() for JSON serialisation; no Pydantic"
    - "pytest network marker + --no-network CLI flag pattern (research example 5)"
    - "deferred yfinance import inside _fetch_ohlc keeps unit tests fast"

key-files:
  created:
    - "scripts/pattern_scanner/__init__.py"
    - "scripts/pattern_scanner/detector.py"
    - "tests/__init__.py"
    - "tests/conftest.py"
    - "tests/test_detector_schema.py"
    - "pytest.ini"
    - "requirements-dev.txt"
    - ".planning/phases/07-detection-engine/07-01-SUMMARY.md"
  modified: []

key-decisions:
  - "Wilder ATR(14) via pandas ewm(alpha=1/14, adjust=False) — industry-standard, no new dep"
  - "Detection dataclass frozen=True; mutating fields after construction raises FrozenInstanceError"
  - "All filter booleans always evaluated (D-08); only the AND of all three gates emission"
  - "CLI ticker validation regex ^[A-Z0-9.-]{1,10}$ enforced BEFORE yfinance fetch (T-07-01)"
  - "Pattern scan loop iterates mother_idx in range(60, n - 1); break_offset bounds-checked inside, accommodating spring case (offset 2 confirmation)"
  - "Helpers return native Python bool (not numpy.bool_) so callers can rely on `is True` semantics"

patterns-established:
  - "Slice-first idiom: every filter computes on df.iloc[:k+1] then reads .iloc[-1] — eliminates entire class of look-ahead bugs"
  - "Per-filter booleans always populated in Detection.filters; emission gate is a separate AND of the three values"
  - "Synthetic OHLC test fixtures via pd.bdate_range(start, periods) keep tests deterministic and offline"

requirements-completed: [DET-01, DET-02, DET-03, DET-04]

duration: ~45min
completed: 2026-05-02
---

# Phase 7 Plan 01: Detection Engine — Inside Bar Spring Detector Summary

**Implemented the algorithmic 5-bar inside bar spring detector with frozen Detection dataclass, the slice-first no-look-ahead idiom, Wilder ATR, and 12 offline unit tests locking DET-01..DET-04 — public API `detect(df, ticker) -> list[Detection]` ready for downstream phases 8–11 to consume directly.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-02
- **Completed:** 2026-05-02
- **Tasks:** 1/1
- **Files created:** 7
- **Files modified:** 0

## Accomplishments

- Built a pure-Python detector module that encodes the entire locked ruleset (D-01..D-14) without adding any runtime dependency.
- Established the project's first formal `tests/` directory with a real pytest harness, a `network` marker that auto-skips on `--no-network` or `PYTEST_OFFLINE=1`, and a reusable `synthetic_ohlc` fixture.
- Enforced the no-look-ahead invariant via the slice-first idiom (`df.iloc[:k+1]` before computing SMA / ATR / swing pivots) and a dedicated truncation-invariance regression test.
- Mitigated T-07-01 (CLI input validation) with a `^[A-Z0-9.-]{1,10}$` regex check that fires BEFORE the yfinance call; covered by `test_cli_ticker_validation` using a `monkeypatch` on `_fetch_ohlc` (no network).

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 scaffolding + detector module + 12 unit tests** — `06feaaa` (feat)

## Files Created

- `scripts/pattern_scanner/__init__.py` — package marker; re-exports `Detection` and `detect` for ergonomic imports.
- `scripts/pattern_scanner/detector.py` — full module: `Detection` frozen dataclass, all classifiers, ATR/SMA/swing-pivot helpers, `_sma_cluster`, `_build_detection`, public `detect()` API, deferred-import `_fetch_ohlc`, and `main()` CLI with `_TICKER_RE` gate.
- `tests/__init__.py` — package marker for pytest collection.
- `tests/conftest.py` — `pytest_addoption(--no-network)`, `pytest_configure` registers the `network` marker, `pytest_collection_modifyitems` skips network tests when offline; `synthetic_ohlc` fixture builds tz-naive business-day OHLC frames from `(O,H,L,C)` tuples.
- `tests/test_detector_schema.py` — 12 unit tests:
  - `test_pin_bar_classifier` (DET-01) — D-01 thresholds + classifier precedence
  - `test_mark_up_bar_classifier` (DET-01) — D-02 thresholds + bullish guard
  - `test_ice_cream_bar_classifier` (DET-01) — D-03 thresholds + bullish guard
  - `test_inside_bar_rule` (DET-01) — D-04 strict inequality both sides
  - `test_atr14_wilder` — Wilder ATR via `ewm(alpha=1/14, adjust=False)` with NaN-on-first-13 guarantee
  - `test_swing_pivots` — 5-bar fractal high & low at known index
  - `test_sma_cluster` — within-band True; far-from-band False
  - `test_detect_returns_detection_list` (DET-01) — engineered 5-bar setup with full filter pass produces a Detection at the expected indices
  - `test_spring_same_bar` (DET-02) — engineered spring case yields `is_spring=True`
  - `test_no_lookahead_truncation_invariance` (DET-03) — `detect(df.iloc[:k+1])` reproduces the same detections at the same indices as `detect(df)`
  - `test_detection_record_schema` (DET-04) — every D-10 key present; `to_dict()` round-trips through `json.dumps`; frozen-dataclass mutation raises
  - `test_cli_ticker_validation` (T-07-01) — `main(["...", "rm -rf /"])` returns non-zero and never invokes `_fetch_ohlc`; `main(["...", "AAPL"])` invokes the (mocked) fetch
- `pytest.ini` — `testpaths = tests`, `network` marker registered, no auto plugin loading from `_dev/`.
- `requirements-dev.txt` — `pytest>=8.4,<9` (dev-only; never folded into runtime `requirements.txt`).

## Verification Run

```
python -m pytest tests/test_detector_schema.py -q
............                                                             [100%]
12 passed in 0.09s
```

`python -m pytest --collect-only -q` collects exactly the 12 tests above (no spurious collection from `_dev/`).

`python -c "from scripts.pattern_scanner.detector import Detection, detect; assert hasattr(Detection, 'to_dict')"` exits 0.

`python scripts/pattern_scanner/detector.py "rm -rf /"` exits 2 with `Invalid ticker: 'RM -RF /'` (CLI rejection path; T-07-01).

## Test Coverage Map

| Requirement | Coverage |
|-------------|----------|
| DET-01 (5-bar ruleset) | `test_pin_bar_classifier`, `test_mark_up_bar_classifier`, `test_ice_cream_bar_classifier`, `test_inside_bar_rule`, `test_detect_returns_detection_list` |
| DET-02 (spring case) | `test_spring_same_bar` |
| DET-03 (no look-ahead) | `test_no_lookahead_truncation_invariance` (also implicitly: every filter uses `df.iloc[:k+1]`) |
| DET-04 (Detection record schema) | `test_detection_record_schema` (round-trip + frozen-mutation check) |
| T-07-01 (CLI input validation) | `test_cli_ticker_validation` |

## Public API

```python
from scripts.pattern_scanner.detector import detect, Detection

detections: list[Detection] = detect(df, ticker)
# df: tz-naive DatetimeIndex, columns Open/High/Low/Close
# Each Detection has: ticker, confirmation_date, confirmation_type,
# is_spring, bars (5-bar window), mother_bar_index, confirmation_bar_index,
# filters {hh_hl, above_50sma, sma_cluster}, sma_levels {sma20, sma50, atr14}.
# .to_dict() returns a JSON-serialisable plain dict.
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Helper boolean return types coerced to native Python `bool`**
- **Found during:** Task 1 verification — `test_pin_bar_classifier` failed with `assert np.True_ is True`.
- **Issue:** Pandas `Series` boolean comparisons return `numpy.bool_`, which is `== True` but not `is True`. The acceptance test uses identity checks (`is True` / `is False`).
- **Fix:** Wrapped each helper's return in `bool(...)` and pre-cast `bar["..."]` accessors to `float(...)` so all boolean math operates on Python primitives. Applied to `_is_pin`, `_is_mark_up`, `_is_ice_cream`, `_inside_bar`, `_hh_hl_uptrend`, `_sma_cluster`.
- **Files modified:** `scripts/pattern_scanner/detector.py`
- **Commit:** `06feaaa`

**2. [Rule 1 - Bug] Outer loop range was too tight, blocking spring-case detections at the right edge**
- **Found during:** Task 1 verification — `test_spring_same_bar` returned 0 detections.
- **Issue:** Original loop `for mother_idx in range(_LOOKBACK, n - 4)` reserved 4 forward bars even though the spring case (`break_idx == conf_idx == mother + 2`) only needs 2 forward bars. With the engineered 73-bar fixture this excluded the only valid mother index.
- **Fix:** Widened the outer range to `range(_LOOKBACK, n - 1)` (only the inside bar at `mother + 1` is mandatory). The inner `if break_idx >= n: break` already bounds-checks each break/confirmation bar. The 5-bar window minimum is preserved by `min(mother_idx + 5, n)` in the inner conf scan.
- **Files modified:** `scripts/pattern_scanner/detector.py`
- **Commit:** `06feaaa`

**3. [Rule 3 - Test fixture redesign] Original engineered uptrend produced too few swing pivots**
- **Found during:** Task 1 verification — HH/HL filter returned False on the synthetic frame because `_swing_pivots` only located 1 swing high / 1 swing low.
- **Issue:** The original `_ascending_trend_rows` helper produced a near-monotonic uptrend that didn't expose enough zig-zag for 5-bar fractal pivots.
- **Fix:** Rewrote the trend helper as `_build_uptrend(n)` producing explicit 4-up / 3-down legs (visible swings every 7 bars). Repositioned the mother bar with `low ≈ last_close - 0.5` so the SMA-cluster filter passes (mother_low within ±1·ATR of SMA20). Confirmed all three filter booleans are True under the new fixture.
- **Files modified:** `tests/test_detector_schema.py`
- **Commit:** `06feaaa`

### Auth Gates

None — Plan 01 is fully offline (no network, no auth).

## Architectural Notes for Downstream Phases

- The `detect()` API is stable (D-12). Phase 10 batch can `from scripts.pattern_scanner.detector import detect, Detection` and treat it as a pure function.
- `_fetch_ohlc` is intentionally separate from `detect()` so the batch pipeline can supply its own DataFrame (e.g., from a parquet cache) without touching network code.
- Per-filter booleans in `Detection.filters` are persisted exactly as evaluated (D-08). Phase 9 backtest can stratify win-rate by `(hh_hl, above_50sma, sma_cluster)` triples without recomputation.
- `Detection.bars` carries the 5-bar OHLC window, so Phase 8 chart annotation does NOT need to slice the source df again.
- Plan 02 (live yfinance known-setup regression suite) inherits the existing `pytest.ini`, conftest, and `network` marker — no infra changes needed.

## Self-Check: PASSED

- FOUND: `scripts/pattern_scanner/__init__.py`
- FOUND: `scripts/pattern_scanner/detector.py`
- FOUND: `tests/__init__.py`
- FOUND: `tests/conftest.py`
- FOUND: `tests/test_detector_schema.py`
- FOUND: `pytest.ini`
- FOUND: `requirements-dev.txt`
- FOUND commit: `06feaaa`
- All 12 unit tests pass (`pytest -q` exits 0).
- Grep audits: `shift(-` returns 0 matches; `df.iloc[:` returns 6 matches (3 in code, 3 in docstrings) ≥ 3 required.
