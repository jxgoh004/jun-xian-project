"""Live yfinance integration regression suite for the inside bar spring detector.

Provenance (D-15 / D-16, Phase 7 success criterion #4):
    The KNOWN_SETUPS fixture below is a curated, user-reviewed list of
    historical S&P 500 inside-bar-spring setups. Each entry was proposed by
    Claude from a detector dump under `_dev/phase07_proposal/`, then approved
    verbatim by the user on 2026-05-02 per the D-16 checkpoint in
    `.planning/phases/07-detection-engine/07-02-PLAN.md`. The fixture is the
    regression contract for Phase 7: any future detector tweak — or upstream
    yfinance data revision — that breaks one of these assertions surfaces here
    immediately.

    The fixture spans three distinct `confirmation_type` values
    (mark_up, pin, ice_cream) and contains four spring cases, exceeding the
    D-16 minima of >=2 types and >=1 spring.

Tests:
    1. test_known_setup_is_detected (parametrized) — DET-01, DET-02, DET-04:
       fetches 10y daily history via yfinance, runs `detect()`, asserts that a
       detection lands at the approved confirmation_date with matching
       `confirmation_type` and `is_spring`, and validates the schema shape.
    2. test_no_detection_on_adjacent_bars (parametrized) — D-15 negative
       regression: confirms NO detection emits on the trading day immediately
       before or after each approved confirmation_date.
    3. test_no_lookahead_truncation_invariance — DET-03 at integration scale:
       runs detect on full 10y AAPL history vs a frame truncated 30 bars
       earlier and verifies the truncated detections are a subset of full
       detections (no look-ahead leak under real data).

All tests are decorated `@pytest.mark.network` and auto-skip when pytest is
invoked with `--no-network` or `PYTEST_OFFLINE=1` (see `tests/conftest.py`,
Plan 01).

This file is the success-criterion-#4 evidence for Phase 7 — see
`.planning/phases/07-detection-engine/07-01-SUMMARY.md` for the offline
unit-test layer this complements.
"""
from __future__ import annotations

import pandas as pd
import pytest
import yfinance as yf

from scripts.pattern_scanner.detector import Detection, detect


# ── User-approved fixture (D-16, 2026-05-02) ────────────────────────────────
KNOWN_SETUPS = [
    # User-approved per D-16 on 2026-05-02. Provenance: detector dump in _dev/phase07_proposal/.
    # (ticker, expected_confirmation_date, expected_type, expected_is_spring)
    ("NVDA", "2020-04-13", "mark_up",   True),   # Post-COVID V-recovery; spring break-and-reclaim into 50-SMA cluster
    ("MSFT", "2023-04-13", "mark_up",   False),  # Full 5-bar setup; AI rally start; break-below day 3, mark-up day 5
    ("JPM",  "2020-06-15", "mark_up",   True),   # Q2 2020 bank recovery; spring break to $81.83, reclaim to $86.42
    ("META", "2020-11-30", "pin",       True),   # Post-election Q4 pin; wick below mother low, body upper third
    ("V",    "2024-02-13", "ice_cream", True),   # Late-Q1 2024 pullback-reclaim; long lower wick, close upper two-thirds
]


# ── Fetch helper (mirrors detector._fetch_ohlc) ─────────────────────────────
def _fetch(ticker: str) -> pd.DataFrame:
    """Fetch 10y daily OHLC via yfinance with the same normalisation as the detector CLI."""
    df = yf.Ticker(ticker).history(period="10y", auto_adjust=True)[
        ["Open", "High", "Low", "Close"]
    ]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


# ── Test 1 — primary positive assertion (DET-01, DET-02, DET-04) ────────────
@pytest.mark.network
@pytest.mark.parametrize(
    "ticker, expected_date, expected_type, expected_spring", KNOWN_SETUPS
)
def test_known_setup_is_detected(
    ticker: str,
    expected_date: str,
    expected_type: str,
    expected_spring: bool,
) -> None:
    """Each user-approved setup must produce a detection on the approved date with matching type + is_spring."""
    df = _fetch(ticker)
    detections = detect(df, ticker)
    matched = [d for d in detections if d.confirmation_date == expected_date]
    assert matched, (
        f"No detection at {expected_date} for {ticker} "
        f"(got {[d.confirmation_date for d in detections]})"
    )
    d = matched[0]
    assert isinstance(d, Detection)
    assert d.confirmation_type == expected_type, (
        f"{ticker} {expected_date}: expected {expected_type}, got {d.confirmation_type}"
    )
    assert d.is_spring is expected_spring, (
        f"{ticker} {expected_date}: expected is_spring={expected_spring}, got {d.is_spring}"
    )
    # DET-04 schema sanity
    assert d.ticker == ticker
    assert set(d.filters.keys()) == {"hh_hl", "above_50sma", "sma_cluster"}
    assert set(d.sma_levels.keys()) == {"sma20", "sma50", "atr14"}
    assert len(d.bars) == 5


# ── Test 2 — adjacent-bar negative regression (D-15) ────────────────────────
@pytest.mark.network
@pytest.mark.parametrize(
    "ticker, expected_date, _t, _s", KNOWN_SETUPS
)
def test_no_detection_on_adjacent_bars(
    ticker: str,
    expected_date: str,
    _t: str,
    _s: bool,
) -> None:
    """No detection may fire on the trading day immediately before or after each approved date."""
    df = _fetch(ticker)
    detections = detect(df, ticker)
    idx = df.index
    pos = idx.get_indexer([pd.Timestamp(expected_date)])[0]
    assert pos != -1, f"{expected_date} not in {ticker} index"
    prev_date = idx[pos - 1].strftime("%Y-%m-%d") if pos - 1 >= 0 else None
    next_date = idx[pos + 1].strftime("%Y-%m-%d") if pos + 1 < len(idx) else None
    detection_dates = {d.confirmation_date for d in detections}
    if prev_date is not None:
        assert prev_date not in detection_dates, (
            f"{ticker}: spurious detection on {prev_date} (day before approved {expected_date})"
        )
    if next_date is not None:
        assert next_date not in detection_dates, (
            f"{ticker}: spurious detection on {next_date} (day after approved {expected_date})"
        )


# ── Test 3 — truncation invariance (DET-03 at integration scale) ────────────
@pytest.mark.network
def test_no_lookahead_truncation_invariance() -> None:
    """detect() on a truncated frame must produce a subset of full-frame detections.

    Confirms no look-ahead leak under real yfinance data: any detection whose
    entire 5-bar window completes before the cutoff must appear identically in
    both runs. Uses AAPL 10y as a high-volume reference.
    """
    df = _fetch("AAPL")
    full = detect(df, "AAPL")
    cutoff_pos = len(df) - 30
    truncated_df = df.iloc[: cutoff_pos + 1]
    truncated = detect(truncated_df, "AAPL")

    # Every detection in `truncated` must appear identically in `full`.
    full_keys = {(d.confirmation_date, d.confirmation_type, d.is_spring) for d in full}
    for d in truncated:
        assert (d.confirmation_date, d.confirmation_type, d.is_spring) in full_keys, (
            f"Truncated frame produced detection not present in full: {d}"
        )

    # Every full detection whose confirmation_idx <= cutoff_pos must appear in `truncated`.
    full_in_window = [d for d in full if d.confirmation_bar_index <= cutoff_pos]
    truncated_keys = {
        (d.confirmation_date, d.confirmation_type, d.is_spring) for d in truncated
    }
    for d in full_in_window:
        assert (d.confirmation_date, d.confirmation_type, d.is_spring) in truncated_keys, (
            f"Full detection {d.confirmation_date} missing from truncated frame "
            f"(look-ahead leak suspected)"
        )
