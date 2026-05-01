"""Unit tests for scripts.pattern_scanner.detector — DET-01..DET-04 schema lock.

All tests are pure-unit and run offline using the `synthetic_ohlc` fixture.
NO `@pytest.mark.network` markers in this file — live yfinance regression
tests live in `test_detector_known_setups.py` (Plan 02).
"""
from __future__ import annotations

import json
import math
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest

from scripts.pattern_scanner.detector import (
    Detection,
    _classify_confirmation,
    _compute_atr,
    _hh_hl_uptrend,
    _inside_bar,
    _is_ice_cream,
    _is_mark_up,
    _is_pin,
    _sma_cluster,
    _swing_pivots,
    detect,
)


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _make_bar(open_, high, low, close):
    """Tiny pandas Series shaped like a row from an OHLC frame."""
    return pd.Series({"Open": open_, "High": high, "Low": low, "Close": close})


def _bar_at(L, frac_open, frac_close, H_offset=10.0):
    """Return a bar with explicit fractional open/close positions in the H-L range.

    The bar runs L .. L + H_offset (so the range is H_offset).
    open  = L + frac_open * H_offset
    close = L + frac_close * H_offset
    """
    H = L + H_offset
    return _make_bar(
        L + frac_open * H_offset,
        H,
        L,
        L + frac_close * H_offset,
    )


# ──────────────────────────────────────────────────────────────────────────
# Test 1: Pin bar classifier (D-01)
# ──────────────────────────────────────────────────────────────────────────

def test_pin_bar_classifier():
    L = 100.0
    H_offset = 10.0
    # open = L + 0.7*range, close = L + 0.8*range — both >= 2/3 -> pin
    pin = _bar_at(L, 0.7, 0.8, H_offset)
    assert _is_pin(pin) is True

    # close = L + 0.5*range — below 2/3 boundary -> not a pin
    not_pin = _bar_at(L, 0.7, 0.5, H_offset)
    assert _is_pin(not_pin) is False

    # Precedence: a bar that satisfies pin returns "pin" from the classifier.
    assert _classify_confirmation(pin) == "pin"


# ──────────────────────────────────────────────────────────────────────────
# Test 2: Mark-up bar classifier (D-02)
# ──────────────────────────────────────────────────────────────────────────

def test_mark_up_bar_classifier():
    L = 100.0
    H_offset = 10.0
    # Bullish, body = 0.7 * range -> True
    bullish_70 = _make_bar(L + 0.15 * H_offset, L + H_offset, L, L + 0.85 * H_offset)
    assert _is_mark_up(bullish_70) is True

    # Bearish, body magnitude same but close < open -> False
    bearish_70 = _make_bar(L + 0.85 * H_offset, L + H_offset, L, L + 0.15 * H_offset)
    assert _is_mark_up(bearish_70) is False

    # Bullish but body = 0.5 * range -> False (below 2/3 threshold)
    bullish_50 = _make_bar(L + 0.25 * H_offset, L + H_offset, L, L + 0.75 * H_offset)
    assert _is_mark_up(bullish_50) is False


# ──────────────────────────────────────────────────────────────────────────
# Test 3: Ice-cream bar classifier (D-03)
# ──────────────────────────────────────────────────────────────────────────

def test_ice_cream_bar_classifier():
    L = 100.0
    H_offset = 10.0
    # Bullish: min(open,close) at L + 0.4*range (<= 0.5 midpoint),
    # close at L + 0.6*range (>= 1/3), close > open  -> ice-cream True.
    # NOTE: must also FAIL pin (open OR close < 2/3) and FAIL mark-up (body < 2/3).
    # open=0.4, close=0.6 -> body=0.2 (< 2/3), close=0.6 (< 2/3) -> not pin, not mark-up.
    ice = _make_bar(L + 0.4 * H_offset, L + H_offset, L, L + 0.6 * H_offset)
    assert _is_ice_cream(ice) is True
    assert _classify_confirmation(ice) == "ice_cream"

    # Bearish version of the same shape -> False.
    bearish = _make_bar(L + 0.6 * H_offset, L + H_offset, L, L + 0.4 * H_offset)
    assert _is_ice_cream(bearish) is False


# ──────────────────────────────────────────────────────────────────────────
# Test 4: Inside bar rule (D-04, strict inequality)
# ──────────────────────────────────────────────────────────────────────────

def test_inside_bar_rule():
    mother = _make_bar(100.0, 110.0, 100.0, 105.0)

    # Strictly inside -> True
    inside = _make_bar(102.0, 109.0, 101.0, 105.0)
    assert _inside_bar(mother, inside) is True

    # H equal to mother H -> not inside (strict)
    flat_high = _make_bar(102.0, 110.0, 101.0, 105.0)
    assert _inside_bar(mother, flat_high) is False

    # L equal to mother L -> not inside (strict)
    flat_low = _make_bar(102.0, 109.0, 100.0, 105.0)
    assert _inside_bar(mother, flat_low) is False


# ──────────────────────────────────────────────────────────────────────────
# Test 5: Wilder ATR(14)
# ──────────────────────────────────────────────────────────────────────────

def test_atr14_wilder(synthetic_ohlc):
    rng = np.random.default_rng(0)
    rows = []
    base = 100.0
    for _ in range(30):
        o = base + rng.uniform(-1, 1)
        h = max(o, base) + rng.uniform(0.5, 2.0)
        l = min(o, base) - rng.uniform(0.5, 2.0)
        c = base + rng.uniform(-1, 1)
        rows.append((o, h, l, c))
        base = c
    df = synthetic_ohlc(rows)
    atr = _compute_atr(df, 14)

    # First 13 values are NaN (min_periods=14).
    assert atr.iloc[:13].isna().all()
    # Subsequent values are finite numbers.
    assert atr.iloc[13:].notna().all()

    # Reference Wilder recursion: ATR_14 = SMA of TR over first 14 bars.
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    # ewm(alpha=1/14, adjust=False, min_periods=14) yields the recursive Wilder ATR.
    # Validate by computing the same recursion by hand on bars 14..29.
    ref = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    pd.testing.assert_series_equal(atr, ref, check_names=False)


# ──────────────────────────────────────────────────────────────────────────
# Test 6: Swing pivots (5-bar fractals)
# ──────────────────────────────────────────────────────────────────────────

def test_swing_pivots(synthetic_ohlc):
    # Construct a 9-bar series with one obvious swing high at index 4 and one
    # obvious swing low at index 4 (different rows because two of the columns
    # define different fractals).  We engineer two separate cases:
    #   highs that ascend then descend around index 4
    #   lows that descend then ascend around index 4
    rows = [
        # (Open, High, Low, Close)
        (10, 11, 9, 10),    # 0
        (10, 12, 8, 10),    # 1
        (10, 13, 7, 10),    # 2
        (10, 14, 6, 10),    # 3
        (10, 20, 1, 10),    # 4 — peak high AND lowest low
        (10, 14, 6, 10),    # 5
        (10, 13, 7, 10),    # 6
        (10, 12, 8, 10),    # 7
        (10, 11, 9, 10),    # 8
    ]
    df = synthetic_ohlc(rows)
    sh, sl = _swing_pivots(df)
    assert sh == [4]
    assert sl == [4]


# ──────────────────────────────────────────────────────────────────────────
# Test 7: SMA cluster filter (D-07)
# ──────────────────────────────────────────────────────────────────────────

def test_sma_cluster(synthetic_ohlc):
    # Build a 60-bar flat series so SMA20 == SMA50 == 100.0; ATR is small.
    # Then a mother bar with low close to 100.0 -> cluster True.
    flat_rows = [(100.0, 101.0, 99.0, 100.0)] * 60
    # Mother bar with low at 100.5 (within ±1 ATR ≈ 2 of SMA50 == 100)
    mother_row = (100.5, 101.5, 100.5, 100.5)
    rows = flat_rows + [mother_row]
    df = synthetic_ohlc(rows)
    assert _sma_cluster(df, mother_idx=60) is True

    # Mother bar with low far from SMA -> False.
    far_mother = (200.0, 205.0, 200.0, 200.0)
    rows_far = flat_rows + [far_mother]
    df_far = synthetic_ohlc(rows_far)
    assert _sma_cluster(df_far, mother_idx=60) is False


# ──────────────────────────────────────────────────────────────────────────
# Test 8: detect() returns a Detection list on a hand-engineered setup
# ──────────────────────────────────────────────────────────────────────────

def _build_uptrend(n: int, start: float = 100.0) -> list:
    """Build a HH/HL uptrend of `n` bars with multiple visible swing pivots.

    Generates explicit zig-zag legs of 6-7 bars each (3 up, 3 down) with a net
    upward drift. This guarantees the 5-bar fractal pivot detector finds at
    least 2 swing highs and 2 swing lows, all ascending, by bar `n`.
    """
    rows: List[Tuple[float, float, float, float]] = []
    price = start
    leg_up_bars = 4
    leg_down_bars = 3
    leg_up_step = 1.5
    leg_down_step = 0.8
    leg_total = leg_up_bars + leg_down_bars
    for i in range(n):
        phase = i % leg_total
        if phase < leg_up_bars:
            o = price
            c = price + leg_up_step
            h = c + 0.4
            l = o - 0.2
        else:
            o = price
            c = price - leg_down_step
            h = o + 0.2
            l = c - 0.4
        rows.append((o, h, l, c))
        price = c
    return rows


def _spring_setup_rows():
    """Build a non-spring (5-bar) setup where break-below at offset 2 and
    confirmation at offset 3.

    Returns (rows, mother_idx, conf_idx, mother_low, mother_high).
    """
    trend = _build_uptrend(70)
    last_close = trend[-1][3]

    # Mother bar with low close to recent SMA20 (cluster filter).
    mother_low = last_close - 0.5
    mother_high = last_close + 4.0
    mother_open = last_close
    mother_close = last_close + 1.0
    mother = (mother_open, mother_high, mother_low, mother_close)

    # Inside bar at mother + 1 (strictly inside).
    inside = (
        mother_open,
        mother_high - 0.5,
        mother_low + 0.3,
        mother_close,
    )

    # Offset 2: break-below bar that is NOT a confirmation (close stays BELOW
    # mother_low, which fails the "close back inside mother range" test).
    bb_low_a = mother_low - 1.5
    bb_close_a = mother_low - 0.4  # below mother_low -> not a valid confirmation
    bb_open_a = mother_low - 0.2
    bb_high_a = mother_low + 0.3
    break_bar = (bb_open_a, bb_high_a, bb_low_a, bb_close_a)

    # Offset 3: actual confirmation — mark-up bar closing back inside mother range.
    cb_low = mother_low - 0.5
    cb_high = mother_low + 1.5
    cb_open = cb_low + 0.05 * (cb_high - cb_low)
    cb_close = cb_low + 0.95 * (cb_high - cb_low)
    confirm_bar = (cb_open, cb_high, cb_low, cb_close)

    rows = trend + [mother, inside, break_bar, confirm_bar]
    mother_idx = len(trend)             # 70
    conf_idx = mother_idx + 3           # 73 (break_idx is 72, so is_spring False)
    return rows, mother_idx, conf_idx, mother_low, mother_high


def _spring_setup_same_bar_rows():
    """Setup where break-below == confirmation (offset 2): true spring case."""
    trend = _build_uptrend(70)
    last_close = trend[-1][3]
    mother_low = last_close - 0.5
    mother_high = last_close + 4.0
    mother_open = last_close
    mother_close = last_close + 1.0
    mother = (mother_open, mother_high, mother_low, mother_close)
    inside = (
        mother_open,
        mother_high - 0.5,
        mother_low + 0.3,
        mother_close,
    )
    # Bar at offset 2 from mother: break-below AND confirmation in one bar.
    # Code requires break_offset >= 2 for break-below; offset 2 is the earliest.
    # But spring per CONTEXT D-13 requires break_idx == conf_idx, which the
    # implementation handles when conf_idx starts at break_idx.
    bb_low = mother_low - 1.5
    bb_high = mother_low + 1.5
    bb_open = bb_low + 0.05 * (bb_high - bb_low)
    bb_close = bb_low + 0.95 * (bb_high - bb_low)
    spring_bar = (bb_open, bb_high, bb_low, bb_close)

    # Pad with one more trend bar so the 5-bar window has enough room.
    pad = (bb_close, bb_close + 1.0, bb_close - 0.5, bb_close + 0.5)

    rows = trend + [mother, inside, spring_bar, pad]
    mother_idx = len(trend)             # 70
    conf_idx = mother_idx + 2           # 72 (same as break_idx == 72)
    return rows, mother_idx, conf_idx, mother_low, mother_high


def test_detect_returns_detection_list(synthetic_ohlc):
    rows, mother_idx, conf_idx, _, _ = _spring_setup_rows()
    df = synthetic_ohlc(rows)

    detections = detect(df, "TEST")
    matched = [
        d for d in detections
        if d.mother_bar_index == mother_idx and d.confirmation_bar_index == conf_idx
    ]
    assert matched, f"No detection at expected indices; got {detections}"

    d = matched[0]
    assert d.confirmation_type in {"pin", "mark_up", "ice_cream"}
    assert isinstance(d.is_spring, bool)
    assert d.ticker == "TEST"
    assert len(d.bars) >= 4  # at least mother..confirmation
    assert d.is_spring is False  # break_idx != conf_idx in this fixture


# ──────────────────────────────────────────────────────────────────────────
# Test 9: Spring case (break_idx == conf_idx) sets is_spring=True
# ──────────────────────────────────────────────────────────────────────────

def test_spring_same_bar(synthetic_ohlc):
    rows, mother_idx, conf_idx, _, _ = _spring_setup_same_bar_rows()
    df = synthetic_ohlc(rows)

    detections = detect(df, "SPRING")
    spring_hits = [d for d in detections if d.is_spring]
    assert spring_hits, f"No spring detection found; got {detections}"

    sd = next(d for d in spring_hits if d.confirmation_bar_index == conf_idx)
    assert sd.mother_bar_index == mother_idx
    assert sd.is_spring is True


# ──────────────────────────────────────────────────────────────────────────
# Test 10: No look-ahead — truncation invariance (DET-03)
# ──────────────────────────────────────────────────────────────────────────

def test_no_lookahead_truncation_invariance(synthetic_ohlc):
    rows, _, conf_idx, _, _ = _spring_setup_rows()
    # Add tail bars beyond the confirmation so we can truncate.
    tail = [
        (rows[-1][3], rows[-1][3] + 1.0, rows[-1][3] - 0.5, rows[-1][3] + 0.5)
    ] * 10
    rows_full = rows + tail
    df = synthetic_ohlc(rows_full)

    full = detect(df, "INV")
    k = conf_idx  # truncate at the confirmation bar
    truncated = detect(df.iloc[: k + 1], "INV")

    # Every detection in `truncated` whose confirmation_bar_index <= k must also
    # appear (with same key fields) in `full`.
    full_keyed = {
        (d.mother_bar_index, d.confirmation_bar_index, d.confirmation_type): d
        for d in full
    }
    for d in truncated:
        key = (d.mother_bar_index, d.confirmation_bar_index, d.confirmation_type)
        assert key in full_keyed, (
            f"Detection {key} present on truncated frame but missing on full frame"
        )
        full_d = full_keyed[key]
        assert d.is_spring == full_d.is_spring
        assert d.filters == full_d.filters
        assert d.confirmation_date == full_d.confirmation_date


# ──────────────────────────────────────────────────────────────────────────
# Test 11: Detection record schema (DET-04)
# ──────────────────────────────────────────────────────────────────────────

def test_detection_record_schema():
    d = Detection(
        ticker="AAPL",
        confirmation_date="2024-06-03",
        confirmation_type="pin",
        is_spring=False,
        bars=[
            {"date": "2024-06-01", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5},
        ],
        mother_bar_index=10,
        confirmation_bar_index=14,
        filters={"hh_hl": True, "above_50sma": True, "sma_cluster": True},
        sma_levels={"sma20": 100.0, "sma50": 95.0, "atr14": 1.5},
    )
    payload = d.to_dict()
    expected_keys = {
        "ticker",
        "confirmation_date",
        "confirmation_type",
        "is_spring",
        "bars",
        "mother_bar_index",
        "confirmation_bar_index",
        "filters",
        "sma_levels",
    }
    assert expected_keys.issubset(payload.keys())

    # Round-trip via json.dumps -> json.loads must preserve structure.
    encoded = json.dumps(payload, default=str)
    decoded = json.loads(encoded)
    assert decoded["ticker"] == "AAPL"
    assert decoded["confirmation_type"] == "pin"
    assert decoded["filters"]["hh_hl"] is True

    # Frozen dataclass: assigning a field must raise.
    with pytest.raises(Exception):
        d.ticker = "MSFT"  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────
# Test 12: CLI ticker validation (T-07-01 mitigation)
# ──────────────────────────────────────────────────────────────────────────

def test_cli_ticker_validation(monkeypatch, synthetic_ohlc):
    """The module's main() must reject non-conforming tickers BEFORE any fetch."""
    import scripts.pattern_scanner.detector as det

    # Spy on _fetch_ohlc — must NEVER be called for an invalid ticker.
    fetch_calls = {"count": 0}

    def fake_fetch(ticker, period="10y"):
        fetch_calls["count"] += 1
        # Return a small empty frame to keep detect() happy if reached.
        return synthetic_ohlc([(1.0, 2.0, 0.5, 1.5)])

    monkeypatch.setattr(det, "_fetch_ohlc", fake_fetch)

    # Bogus ticker with a space + slash + special chars -> reject, no fetch.
    rc_bad = det.main(["detector.py", "rm -rf /"])
    assert rc_bad != 0
    assert fetch_calls["count"] == 0

    # Valid ticker -> fetch invoked (we mocked it). Exit 0 because detect() on a
    # tiny frame returns []; main() prints "[]" and returns 0.
    rc_good = det.main(["detector.py", "AAPL"])
    assert rc_good == 0
    assert fetch_calls["count"] == 1
