"""Phase 10 D-01: 20-business-day cutoff on `confirmation_date`.

RED (Wave 0): imports `_window_cutoff` from `scripts.pattern_scanner.run_pipeline`
which does not yet exist on disk. Plan 10-04 creates it.

The contract this file locks:
  _window_cutoff(today: pd.Timestamp, window_days: int) -> pd.Timestamp
  Returns today - BDay(window_days). The pipeline then keeps detections
  whose confirmation_date >= cutoff.
"""
from __future__ import annotations

import pandas as pd

# Import will fail until Plan 04 lands — this is the expected Wave 0 RED state.
from scripts.pattern_scanner.run_pipeline import _window_cutoff  # noqa: E402


def test_window_filter_drops_old_detections():
    """D-01: detections with confirmation_date < today - BDay(20) are dropped.

    Fixed `today = 2026-05-11` (a Monday). 20 business days back lands on
    `2026-04-13`. The five in-window dates straddle that cutoff on the
    recent side; the five out-of-window dates sit comfortably before it.
    """
    today = pd.Timestamp("2026-05-11")
    cutoff = _window_cutoff(today, 20)

    in_window = [
        "2026-05-08",  # 1 BDay back
        "2026-05-01",  # 6 BDays back
        "2026-04-25",  # ~10 BDays back (Saturday — still > cutoff)
        "2026-04-20",  # ~14 BDays back
        "2026-04-15",  # ~17 BDays back
    ]
    out_window = [
        "2026-04-01",  # ~28 BDays back
        "2026-03-15",
        "2026-02-28",
        "2026-01-15",
        "2025-12-01",
    ]

    all_dates = in_window + out_window
    survivors = [d for d in all_dates if pd.Timestamp(d) >= cutoff]

    assert len(survivors) == 5
    assert set(survivors) == set(in_window)
