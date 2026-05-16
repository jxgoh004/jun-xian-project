---
phase: 07-detection-engine
reviewed: 2026-05-02T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - scripts/pattern_scanner/__init__.py
  - scripts/pattern_scanner/detector.py
  - tests/__init__.py
  - tests/conftest.py
  - tests/test_detector_schema.py
  - tests/test_detector_known_setups.py
  - pytest.ini
  - requirements-dev.txt
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-05-02
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 7 ships a clean, well-documented inside-bar-spring detector with a thoughtful test suite covering schema, classifier rules, indicator math, and look-ahead invariance at both unit and integration scale. The locked finance domain rules (D-01..D-14) are faithfully encoded, the slice-first idiom is consistently applied, `shift(-1)` is absent module-wide, and the CLI ticker validator (T-07-01) lands BEFORE the yfinance call as designed.

No critical bugs and no security vulnerabilities were found. Two warnings flag (a) a documentation/implementation divergence in the swing-pivot lookback window — the docstring says "60-bar lookback ending at confirmation" but `_swing_pivots` scans the full pre-confirmation view — and (b) a tautological assertion in `test_atr14_wilder` that compares `_compute_atr` against an identical pandas expression rather than an independent Wilder reference. Five info items cover an unused import, a frozen-dataclass mutability caveat, an overly broad `pytest.raises(Exception)`, a `bars` array that can be shorter than 5 near the right edge of a frame, and minor robustness on the spring-window assumption.

The no-look-ahead invariant — the most load-bearing safety property of the module — is intact at the implementation level. The test suite validates it both synthetically (`test_no_lookahead_truncation_invariance`) and at integration scale.

## Warnings

### WR-01: Swing-pivot lookback window does not match documented spec

**File:** `scripts/pattern_scanner/detector.py:18, 162-189, 192-201`
**Issue:** Module docstring (line 18) and the trend filter description state "5-bar fractal pivots over 60-bar lookback ending at confirmation". The implementation in `_hh_hl_uptrend` calls `_swing_pivots(view)` where `view = df.iloc[:conf_idx + 1]` — the full pre-confirmation slice, which can be hundreds or thousands of bars. The 60-bar lookback is never applied; pivots can come from anywhere in the historical record. This produces a more permissive HH/HL filter than documented and changes the meaning of "last 2 swing highs/lows" to "last 2 globally visible swing highs/lows," not "within the recent 60 bars." For long histories, the "last" pivots will typically still be recent, but this is data-dependent and the test suite does not lock the window.
**Fix:** Either tighten the implementation to match the spec, or update the docstring to reflect the actual behavior. Tightened implementation:
```python
def _hh_hl_uptrend(view: pd.DataFrame) -> bool:
    """HH/HL filter (D-05): last 2 swing highs ascending AND last 2 swing lows ascending,
    measured over the trailing _LOOKBACK bars ending at the confirmation bar."""
    window = view.iloc[-_LOOKBACK:] if len(view) > _LOOKBACK else view
    sh, sl = _swing_pivots(window)
    if len(sh) < 2 or len(sl) < 2:
        return False
    last_high = float(window["High"].iloc[sh[-1]])
    prev_high = float(window["High"].iloc[sh[-2]])
    last_low = float(window["Low"].iloc[sl[-1]])
    prev_low = float(window["Low"].iloc[sl[-2]])
    return bool(last_high > prev_high and last_low > prev_low)
```
Recommend tightening the implementation rather than relaxing the docstring — the 60-bar window is finance-meaningful (recent regime) and the broader spec was clearly the design intent.

### WR-02: `test_atr14_wilder` is a tautology, not a Wilder reference test

**File:** `tests/test_detector_schema.py:140-171`
**Issue:** The test computes a reference ATR via:
```python
ref = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
```
which is the exact same expression used inside `_compute_atr` (detector.py:157). `pd.testing.assert_series_equal(atr, ref)` is therefore asserting that pandas equals itself; it does NOT validate the Wilder recursion. If `_compute_atr` were silently changed to use `alpha=1/13` or `min_periods=15`, the test would also break, but if both sides drifted together (e.g., a refactor that extracted the EWM expression), the test would pass on incorrect math. The comment at line 159 ("ATR_14 = SMA of TR over first 14 bars. Wilder smoothing == EMA with alpha = 1/period") describes the expected reference but isn't actually computed in the test.
**Fix:** Compute the Wilder recursion explicitly so the test is independent of the implementation:
```python
# True Wilder reference: ATR[14] = mean of first 14 TRs; ATR[k] = (ATR[k-1]*13 + TR[k]) / 14 for k > 14.
period = 14
ref_vals = [float("nan")] * len(tr)
seed = tr.iloc[1:period + 1].mean()  # first 14 valid TRs (TR[0] is NaN due to prev_close)
ref_vals[period] = seed
for k in range(period + 1, len(tr)):
    ref_vals[k] = (ref_vals[k - 1] * (period - 1) + float(tr.iloc[k])) / period
ref = pd.Series(ref_vals, index=tr.index)
# Compare from index 14 onward (where both seed and recursion are defined).
pd.testing.assert_series_equal(
    atr.iloc[period:], ref.iloc[period:], check_names=False
)
```
This test now fails if anyone breaks the Wilder math, regardless of how the implementation expresses it.

## Info

### IN-01: Unused `numpy` import in detector.py

**File:** `scripts/pattern_scanner/detector.py:40`
**Issue:** `import numpy as np` is declared but `np.` is never referenced anywhere in `detector.py`. Dead import.
**Fix:** Remove the line. If a future edit needs numpy, reintroduce it locally.

### IN-02: Frozen `Detection` is shallowly immutable; mutable fields can be mutated and `hash()` will raise

**File:** `scripts/pattern_scanner/detector.py:52-68`
**Issue:** `@dataclass(frozen=True)` blocks attribute reassignment but does not deep-freeze the contained `bars: List[Dict]`, `filters: Dict`, or `sma_levels: Dict`. A consumer can do `d.bars.append(...)` or `d.filters["hh_hl"] = False` and silently corrupt the record. Additionally, `frozen=True` (default `eq=True`) makes the class hashable in principle, but `hash(d)` will raise `TypeError: unhashable type: 'list'` at runtime if anyone tries to put a Detection in a set or dict key. The current test suite never exercises hashing, so this is latent.
**Fix:** Either (a) document the invariant ("Detection is shallowly frozen; do not mutate `bars`, `filters`, `sma_levels` after construction") or (b) wrap the mutable fields in immutable equivalents — e.g., `bars: tuple` and `filters: types.MappingProxyType` — at construction time. For now, a docstring note is sufficient since the module never returns Detection to a consumer that hashes it.

### IN-03: Overly broad `pytest.raises(Exception)` for frozen-dataclass assignment

**File:** `tests/test_detector_schema.py:447-448`
**Issue:** The frozen-dataclass assertion uses `with pytest.raises(Exception):`. This will pass on ANY exception, including unrelated bugs (e.g., an `AttributeError` from a typo in the field name). The expected exception is `dataclasses.FrozenInstanceError`.
**Fix:**
```python
import dataclasses
...
with pytest.raises(dataclasses.FrozenInstanceError):
    d.ticker = "MSFT"  # type: ignore[misc]
```

### IN-04: `bars` list silently truncated when confirmation is near the right edge

**File:** `scripts/pattern_scanner/detector.py:271-283`
**Issue:** The `bars` window is built with `end = min(mother_idx + 5, len(df))`, so for a confirmation that lands on the very last bar of `df` (e.g., when running `detect()` on a stream cut off at confirmation, or in the truncation-invariance test), `bars` may contain fewer than 5 entries. The integration test `test_known_setup_is_detected` asserts `len(d.bars) == 5`, so a setup whose 5-bar window extends past the data end would fail that assertion. Today this never happens because (a) the integration fixtures are mid-history and (b) the truncation test does not assert `len(bars) == 5`. But a future consumer iterating over `d.bars` and indexing positionally (e.g., `d.bars[4]`) would crash.
**Fix:** Either pad the truncated `bars` to 5 entries with `None` placeholders, or document that `len(bars) <= 5` and only equals 5 when the full window is available. Recommended docstring update on the `bars` field:
```
bars: List[Dict]   # 1-5 dicts {date,open,high,low,close} from mother bar onward.
                   # Length is exactly 5 in normal use; may be < 5 only when the
                   # confirmation lands within 4 bars of the right edge of the input.
```

### IN-05: `test_cli_ticker_validation` does not exercise the empty-args path

**File:** `tests/test_detector_schema.py:455-478`
**Issue:** `main()` has three exit paths: `len(argv) < 2 -> 1`, regex mismatch -> `2`, success -> `0`. The test covers paths 2 and 3 but not path 1 (running with no ticker arg). A regression that, e.g., changes the usage check to `len(argv) < 1` would not be caught.
**Fix:** Add one assertion:
```python
rc_no_arg = det.main(["detector.py"])
assert rc_no_arg == 1
assert fetch_calls["count"] == 1  # still only the one valid call from earlier
```

---

_Reviewed: 2026-05-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
