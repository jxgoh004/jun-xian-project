---
phase: 09-backtesting-engine
reviewed: 2026-05-10T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - scripts/pattern_scanner/backtest.py
  - tests/test_backtest_simulate_trade.py
  - tests/test_backtest_aggregate.py
  - tests/test_backtest_cli.py
  - tests/test_backtest_cutoff.py
  - tests/test_backtest_unfiltered_superset.py
  - tests/test_backtest_yolo_conf_fallback.py
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
  resolved:
    - CR-01
    - WR-02
status: partially_resolved
---

# Phase 9: Code Review Report

**Reviewed:** 2026-05-10
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the offline backtester (`scripts/pattern_scanner/backtest.py`) and its six pytest modules. Overall the code is well structured: pure-function core (`simulate_trade`, `aggregate`, `_partition_*`), explicit float-coercion at every output site (Pitfall 1/2/7), lazy `yfinance` and `onnxruntime` imports (Pitfall 3), and good test coverage of the documented decisions D-01..D-14.

However, several real bugs and quality defects exist. The most important is a **BLOCKER on D-12 (filtered superset invariant)**: the unfiltered list is built from `all_dets` instead of being post-filtered by exit-time *resolution*, but a far more concrete leakage exists in how `_partition_filtered` is dead code while `main()` does the partition inline using `_is_filtered`, plus a structural bug where `main()` does **not** call `detect()` with `apply_trend_filters=False` in a way that mirrors the docstring promise on edge cases. The most damaging class of defect, though, is in **`simulate_trade`**: D-04 docstring says "gap-down at or below stop -> recorded as 'stop' with possibly worse-than-1R R", but the actual returned record sets `exit_price = entry_open` while the comment says R should be `(entry_open - stop) / risk`. Since `risk = entry_open - stop`, that always evaluates to **+1.0**, not "worse than -1.0" — i.e., a gap-down stop-out is currently booked as a +1R **win**. This is a real correctness bug.

Additional concerns: (1) `_validate_ticker_token` accepts strings starting with `-` or `.` (e.g., `-AAPL`, `.A`) which are pathological and not real tickers; the regex is mirrored from `detector.py` so the bug is shared, but T-9-01 hardening here should be tighter than the upstream regex. (2) `aggregate` does not preserve numeric type if any record's `R` is a `numpy.float64` — the per-cell `float()` cast happens but the per-record `r["R"]` flowing into `sum()` and `median()` is whatever the caller produced. `simulate_trade` does coerce, so this is currently safe, but `aggregate` has no defensive cast on the input, so if a future caller passes raw numpy values, the JSON serializer's `default=str` will silently stringify numpy scalars in any unknown nested context. (3) The `_score_detection` import block bundles `PIL`, `numpy`, and `renderer` into a single `try/except ImportError` — a partial-install (PIL present, numpy missing) would emit one warning but the warning text only references the first failure, hiding which dep is missing. (4) Tests in `test_backtest_yolo_conf_fallback.py` do not assert that exactly **one** UserWarning is emitted (the test description says "exactly one" but `pytest.warns` only asserts ">= 1").

---

## Critical Issues

### CR-01: D-04 gap-down stop returns R = +1.0 (booked as a win), not "worse than -1.0R" [RESOLVED]

**Resolution (2026-05-10, commit 7f152d7):** D-04 branch reordered to fire BEFORE the `risk <= 0` guard (was unreachable dead code). 1R reference now anchored to the confirmation bar's close — a stable pre-gap value already on `df`. Gap-throughs now record R < -1.0 with magnitude proportional to the gap. Added regression tests `test_simulate_trade_gap_down_through_stop` (R = -2.0) and `test_simulate_trade_gap_down_exactly_at_stop` (R = 0.0; confirms div-by-zero hazard gone). All 28 backtest tests pass.

**File:** `scripts/pattern_scanner/backtest.py:115-130`
**Issue:** The D-04 branch handles `entry_open <= stop_price` (gap-down at or through the stop on the entry bar). Per the docstring (line 70): "D-04 entry-bar gap-down: open <= stop -> recorded as 'stop' with possibly worse-than-1R R." The intent is clearly that `R` should be `<= -1.0` (a gap *through* the stop is worse than a clean stop).

The math computes:
```python
risk = entry_open - float(stop_price)        # line 96 — POSITIVE only when entry_open > stop
...
if entry_open <= float(stop_price):           # line 116 — TRUE iff risk <= 0
    R = (entry_open - float(stop_price)) / risk
    # R = risk / risk = +1.0  ← BUG: gap-down through stop booked as +1R WIN
```

When `entry_open == stop_price`, `risk == 0` and you get a `ZeroDivisionError`. When `entry_open < stop_price`, `risk` is negative, numerator is negative, so `R = +1.0`.

The unreachability question: line 99 (`if risk <= 0`) catches the `risk <= 0` case first, so line 116's branch can only execute when `risk > 0`, i.e., `entry_open > stop_price` — which contradicts the branch's own condition `entry_open <= stop_price`. **The D-04 branch on lines 116-130 is unreachable dead code.** The actual gap-down path falls into the "Pathological: stop at or above entry" branch at lines 99-113, which itself returns `R = (entry_open - stop) / max(abs(entry_open - stop), 1e-9)`, producing `R = -1.0` for any gap-down (numerator negative, denominator positive) — that's the correct sign but it caps the magnitude at exactly `-1.0`, again **failing to record "possibly worse-than-1R R"**.

Net effect: any entry-bar gap-down through the stop produces `R = -1.0` (capped), and the documented "possibly worse than -1R" semantics are silently violated. There is no test exercising a gap-down where `entry_open < stop_price` (verify in `test_backtest_simulate_trade.py` — only stop_first, target_first, intrabar, and open are covered).

**Fix:** Reorder/rewrite so the gap-down branch is reachable AND uses the *gap-down's natural risk* (the original planned risk from before the gap) rather than the post-gap `risk`. Two viable options:

```python
# Option A (matches docstring): use planned-risk (the prior bar's stop distance) for R
# This requires passing planned_risk in, OR computing it from the original entry plan.
# Simplest patch — measure R against |target - stop| / 2 (i.e., 1R distance):
planned_risk = float(target_price) - float(stop_price)  # = 2R, so 1R = planned_risk / 2
# but this is brittle; cleaner: pass an explicit `planned_entry` arg.

# Option B (concrete and minimal):
# Keep risk = entry_open - stop_price. For gap-down, compute R relative to a hypothetical
# "intended risk" = stop_distance from the *previous bar's close* or detection's entry plan.
# Then:
if entry_open <= float(stop_price):
    intended_risk = ... # 1R reference distance from detection metadata
    R = (entry_open - float(stop_price)) / intended_risk  # negative, magnitude can exceed 1
```

Add a regression test: gap-down where `entry_open < stop_price` (e.g., entry_open=9.0, stop=9.5) and assert `R < -1.0`.

---

## Warnings

### WR-01: `_partition_filtered` is dead code; `main()` re-implements it inline

**File:** `scripts/pattern_scanner/backtest.py:313-319` (defn) and `scripts/pattern_scanner/backtest.py:555-558` (call site)
**Issue:** `_partition_filtered` is defined and exported but `main()` does the partition inline:
```python
all_dets = detect(df, ticker, apply_trend_filters=False)
f_dets = [d for d in all_dets if _is_filtered(d)]
```
This is exactly what `_partition_filtered(all_dets, _is_filtered)` returns. Two parallel implementations of the same logic invite drift. Also, no test imports `_partition_filtered` — confirmed by grep through the test files supplied.
**Fix:** Either delete `_partition_filtered`, or call it from `main()`:
```python
f_dets, all_dets = _partition_filtered(detect(df, ticker, apply_trend_filters=False), _is_filtered)
```

### WR-02: `_validate_ticker_token` accepts leading-`.` and leading-`-` ticker strings [RESOLVED]

**Resolution (2026-05-10, commit 59f5d0e):** Tightened `_TICKER_RE` in `detector.py` (the single source of truth — `backtest.py` imports it) to `^[A-Z0-9][A-Z0-9.-]{0,9}$`. Leading `.` and `-` now rejected; internal punctuation preserved (BRK.B / BRK-B still valid). Added parametrized `test_invalid_ticker_leading_punct` covering `-AAPL`, `.A`, `..`, `--`, `.`, `-`, `.AAPL`, `-A`. All 61 detector + backtest tests pass.

**File:** `scripts/pattern_scanner/backtest.py:287-297` (regex inherited from `detector.py:48`)
**Issue:** `_TICKER_RE = re.compile(r"^[A-Z0-9.-]{1,10}$")` — the character class permits `.` and `-` anywhere, so `.A`, `-AAPL`, `..`, `--`, `-` all pass validation. T-9-01 mitigation rationale is "before any yfinance call", but yfinance/curl-style argv injection is not the only concern: leading-`-` tokens like `-AAPL` could be parsed as flags by some downstream tool, and `..` clearly looks path-traversal-shaped. The test at `test_backtest_cli.py:9-17` does not include these adversarial cases.
**Fix:** Tighten the regex (keep `detector.py` aligned) to require an alphanumeric leading character:
```python
_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,9}$")
```
And add to `test_backtest_cli.py`:
```python
@pytest.mark.parametrize("bad_token", ["-AAPL", ".A", "..", "--", ".", "-"])
def test_invalid_ticker_leading_punct(bad_token):
    with pytest.raises(argparse.ArgumentTypeError):
        _validate_ticker_token(bad_token)
```

### WR-03: `_score_detection` swallows `numpy`/`PIL`/`renderer` import failures into one warning

**File:** `scripts/pattern_scanner/backtest.py:402-411`
**Issue:** A single `try/except ImportError` covers three imports. If only one is missing, the exception's `name` attribute identifies the missing module but the warning text just interpolates `exc`. More importantly: this `try/except` runs **on every detection** — for a 500-ticker run with thousands of detections, if `PIL` is uninstalled you get one warning per call (Python only deduplicates by exact text+filename+lineno + simplefilter rules). Because the warning text varies with `exc`, dedup may not collapse them.
**Fix:** Cache the import-failure state at module/function level and emit the warning once (mirror `_load_onnx_session`'s pattern):
```python
_OVERLAY_IMPORTS = None  # module-level

def _score_detection(window, sess) -> "float | None":
    global _OVERLAY_IMPORTS
    if sess is None or window is None:
        return None
    if _OVERLAY_IMPORTS is None:
        try:
            from PIL import Image
            import numpy as np
            from scripts.pattern_scanner.renderer import render, STYLES
            _OVERLAY_IMPORTS = (Image, np, render, STYLES)
        except ImportError as exc:
            warnings.warn(f"ML overlay deps missing ({exc.name}); yolo_conf will be null.",
                          UserWarning, stacklevel=2)
            _OVERLAY_IMPORTS = False
    if _OVERLAY_IMPORTS is False:
        return None
    Image, np, render, STYLES = _OVERLAY_IMPORTS
    ...
```

### WR-04: ONNX-fallback test does not enforce "exactly one" UserWarning

**File:** `tests/test_backtest_yolo_conf_fallback.py:49-50`
**Issue:** The phase docstring (and the prompt's review-area list) require "fallback path produces exactly 1 UserWarning when model file missing". `pytest.warns(UserWarning, match=...)` only asserts that **at least one** warning matching the pattern was emitted — it does not assert the count. With `_score_detection` called per-detection, if `PIL`/`numpy`/`renderer` were also missing in CI, you'd see N additional warnings and the test would still pass. Test is too lax for the documented invariant.
**Fix:** Use `warnings.catch_warnings(record=True)` and assert `len(...) == 1`:
```python
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    rc = backtest_mod.main(["--seed", "42", "--tickers", "all", "--out", str(out_path)])
matching = [x for x in w if issubclass(x.category, UserWarning)
            and "ONNX model not found" in str(x.message)]
assert len(matching) == 1, f"expected exactly 1 ONNX-missing warning, got {len(matching)}"
```

### WR-05: `simulate_trade` does not validate that `df.index` is a `DatetimeIndex`

**File:** `scripts/pattern_scanner/backtest.py:165-213`
**Issue:** Lines 168, 182, 196, 213 compute `(df.index[j] - entry_date).days`. This requires both operands to be timestamps; if `df.index` happens to be a `RangeIndex` (e.g., `df.reset_index()` was called upstream by mistake), `.days` raises `AttributeError`. There is also no defense if `entry_date` is a `numpy.datetime64` rather than a `Timestamp` — subtraction yields a `timedelta64`, which has `.days` but the int conversion behaviour can differ for negative values. With the broad `except Exception` in `main()` (line 562), this would be silently logged as a per-ticker failure and the run would continue, producing an incomplete cache.
**Fix:** Add a precondition early in `simulate_trade`:
```python
if not isinstance(df.index, pd.DatetimeIndex):
    raise TypeError(f"df.index must be DatetimeIndex, got {type(df.index).__name__}")
```

### WR-06: `main()` broad `except Exception` masks programming bugs

**File:** `scripts/pattern_scanner/backtest.py:562-563`
**Issue:** The comment says "match gen_training_data.py L224-227", but matching a precedent does not mean it's correct. A `KeyError` from a typo in `_build_record` (e.g., `df.iloc[entry_idx]["Opn"]`) or a `TypeError` from WR-05 will be swallowed into a `print()` line, producing a cache that is silently missing data for some tickers. There is no aggregate sentinel ("N tickers failed") in the output JSON.
**Fix:** At minimum, count failures and emit them in the cache header so a downstream consumer can detect them:
```python
errors: list[dict] = []
...
except Exception as exc:
    errors.append({"ticker": ticker, "error": repr(exc)})
    print(f"[{i}/{total}] {ticker}: unexpected error — {exc}")
...
cache["ticker_errors"] = errors  # downstream can warn if non-empty
```
Better: narrow the except to `(yfinance.YFinanceError, KeyError, ValueError, requests.RequestException)` — let real bugs (TypeError, AttributeError) surface.

---

## Info

### IN-01: Two identical `if hit_stop` branches collapsed inelegantly

**File:** `scripts/pattern_scanner/backtest.py:157-184`
**Issue:** Lines 157-170 (`if hit_stop and hit_target`) and lines 171-184 (`if hit_stop`) return literally identical records. The first conditional is dead given the second always handles the stop case the same way.
**Fix:** Drop the conjunction branch — `hit_stop` alone is sufficient since D-03 says stop wins when both hit:
```python
if hit_stop:  # D-03: pessimistic — stop wins even if target also hit this bar
    return {... R: -1.0, exit_reason: "stop" ...}
if hit_target:
    return {... R: 2.0, exit_reason: "target" ...}
```

### IN-02: Pathological-risk branch silently changes the meaning of `risk` field

**File:** `scripts/pattern_scanner/backtest.py:99-113`
**Issue:** When `risk <= 0`, the output record sets `"risk": float(risk)` (a non-positive number) but the R-multiple was computed with a sentinel `max(..., 1e-9)`. Downstream consumers reading `risk` as a positive distance will get garbage. There is no flag in the record indicating "this is a pathological detection".
**Fix:** Either skip pathological detections entirely (return `None` and filter in `_build_record`), or add an explicit `"degenerate": True` flag to the record so aggregate consumers can exclude them.

### IN-03: `aggregate` casts `win_rate`/`avg_return_r` but not the input `R` values

**File:** `scripts/pattern_scanner/backtest.py:248-260`
**Issue:** Per-cell output values are explicitly `float()`-coerced (Pitfall 1/2/7 compliant). But `sum(r["R"] for r in rs) / n` will produce a `numpy.float64` if any caller passes numpy-typed records — Python's `/` on numpy scalars stays numpy. The wrapping `float(avg_return_r)` saves you, but `median(r["hold_days"] for r in resolved)` could yield `numpy.int64` if a caller stores numpy ints, and `int(median_hold_days)` saves that one too. Currently safe given `simulate_trade`'s coercions; document this contract or harden `aggregate`.
**Fix:** Add a one-liner at the top of `aggregate`:
```python
# Defensive: aggregate is the JSON-encoder boundary; do not trust numpy types in inputs
records = [{k: (float(v) if isinstance(v, (int, float)) and k in ("R",) else
                int(v) if isinstance(v, int) and k in ("hold_days",) else v)
            for k, v in r.items()} for r in records]
```
…or simply note the precondition in the docstring.

### IN-04: `_iso(ts)` raises `AttributeError` if passed a `str`

**File:** `scripts/pattern_scanner/backtest.py:53-55`
**Issue:** `ts.strftime("%Y-%m-%d")` assumes `ts` has `.strftime`. If a caller ever passes the already-stringified `confirmation_date` (which `_identity` does, line 45), it would crash. Currently safe because `_iso` is only called on `df.index` values, but the helper has no input validation and no docstring example showing acceptable types.
**Fix:** Cosmetic — accept both:
```python
def _iso(ts) -> str:
    if isinstance(ts, str):
        return ts
    return pd.Timestamp(ts).strftime("%Y-%m-%d")
```

### IN-05: `aggregate` ignores `n < 1` branch which can never trigger

**File:** `scripts/pattern_scanner/backtest.py:241-242`
**Issue:** `n = len(rs)` after `buckets[key].append(r)` — `n` is always `>= 1` for any key present in `buckets`. The `if n < 1: continue` is dead code; D-09 omits empty cells but no key with empty list can exist in a defaultdict that's only ever appended to.
**Fix:** Remove the dead check, or comment it as defense-in-depth. Either is fine.

---

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
