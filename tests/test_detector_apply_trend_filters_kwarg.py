"""Regression coverage for the Phase 8 `apply_trend_filters` kwarg on detect().

Two tests:
  1. test_default_kwarg_matches_phase7 — proves Phase 7 contract is preserved
     when the kwarg is omitted vs. passed explicitly as True.
  2. test_unfiltered_is_superset — proves apply_trend_filters=False emits a
     strict superset of the filtered run, AND at least one extra detection has
     a failing per-filter boolean (so the unfiltered branch is the hard-negative
     pool source, not just a no-op).
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest

from scripts.pattern_scanner.detector import Detection, detect


# Copied from tests/test_detector_schema.py — keep in sync if either changes.
def _build_uptrend(n: int, start: float = 100.0) -> list:
    """HH/HL uptrend of `n` bars with multiple visible swing pivots."""
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


# Copied from tests/test_detector_schema.py — keep in sync if either changes.
def _spring_setup_rows():
    """Non-spring (5-bar) setup; break-below at offset 2, confirmation at offset 3."""
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

    bb_low_a = mother_low - 1.5
    bb_close_a = mother_low - 0.4
    bb_open_a = mother_low - 0.2
    bb_high_a = mother_low + 0.3
    break_bar = (bb_open_a, bb_high_a, bb_low_a, bb_close_a)

    cb_low = mother_low - 0.5
    cb_high = mother_low + 1.5
    cb_open = cb_low + 0.05 * (cb_high - cb_low)
    cb_close = cb_low + 0.95 * (cb_high - cb_low)
    confirm_bar = (cb_open, cb_high, cb_low, cb_close)

    rows = trend + [mother, inside, break_bar, confirm_bar]
    mother_idx = len(trend)             # 70
    conf_idx = mother_idx + 3           # 73
    return rows, mother_idx, conf_idx, mother_low, mother_high


# ──────────────────────────────────────────────────────────────────────────
# Test 1: Default kwarg behavior is byte-identical to omitting the kwarg.
# ──────────────────────────────────────────────────────────────────────────

def test_default_kwarg_matches_phase7(synthetic_ohlc):
    rows, _mother_idx, _conf_idx, _, _ = _spring_setup_rows()
    df = synthetic_ohlc(rows)

    a = detect(df, "TEST")
    b = detect(df, "TEST", apply_trend_filters=True)

    assert a == b
    assert len(a) >= 1, "fixture should produce at least one Phase 7 detection"


# ──────────────────────────────────────────────────────────────────────────
# Test 2: apply_trend_filters=False yields a strict superset, and at least
# one element of the difference has a failing per-filter boolean.
# ──────────────────────────────────────────────────────────────────────────

def _spring_setup_rows_flat_prefix():
    """Same cluster geometry as _spring_setup_rows() but with a flat prefix
    so HH/HL fails. Cluster filter still passes because mother_low sits near
    the flat-price SMAs; above_50sma may or may not pass — the test only
    asserts AT LEAST ONE filter is False in the difference set.
    """
    flat_price = 100.0
    # 70 flat bars: O=H=L=C ≈ flat_price with negligible range so no swing pivots ascend.
    flat_rows: List[Tuple[float, float, float, float]] = []
    for _ in range(70):
        flat_rows.append((flat_price, flat_price + 0.05, flat_price - 0.05, flat_price))

    last_close = flat_rows[-1][3]  # 100.0

    # Mother low sits within ±1 ATR of the flat SMA (cluster shape valid).
    mother_low = last_close - 0.3
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

    bb_low_a = mother_low - 1.5
    bb_close_a = mother_low - 0.4
    bb_open_a = mother_low - 0.2
    bb_high_a = mother_low + 0.3
    break_bar = (bb_open_a, bb_high_a, bb_low_a, bb_close_a)

    cb_low = mother_low - 0.5
    cb_high = mother_low + 1.5
    cb_open = cb_low + 0.05 * (cb_high - cb_low)
    cb_close = cb_low + 0.95 * (cb_high - cb_low)
    confirm_bar = (cb_open, cb_high, cb_low, cb_close)

    return flat_rows + [mother, inside, break_bar, confirm_bar]


def test_unfiltered_is_superset(synthetic_ohlc):
    rows_flat_prefix = _spring_setup_rows_flat_prefix()
    df = synthetic_ohlc(rows_flat_prefix)

    filtered = detect(df, "TEST")
    unfiltered = detect(df, "TEST", apply_trend_filters=False)

    # Superset: every filtered detection appears in unfiltered.
    for d in filtered:
        assert d in unfiltered

    # Difference must contain at least one detection with at least one failing
    # per-filter boolean — proving the False branch is the hard-negative pool.
    diff = [d for d in unfiltered if d not in filtered]
    assert len(diff) >= 1, (
        f"Expected at least one detection emitted only when filters disabled; "
        f"got filtered={filtered!r}, unfiltered={unfiltered!r}"
    )
    assert any(
        (not d.filters["hh_hl"])
        or (not d.filters["above_50sma"])
        or (not d.filters["sma_cluster"])
        for d in diff
    )
