"""Phase 10 D-02: `_resolve_status` wrapper for the `pending` state.

RED (Wave 0): these tests import from `scripts.pattern_scanner.run_pipeline`,
a module that does not yet exist on disk. Plan 10-04 creates it.

Until then `pytest --collect-only` may either:
  - Collect these tests (if collection deferral applies), or
  - Error at collection with ModuleNotFoundError.

Both states are valid RED. The contract this file locks is:
  _resolve_status(df, detection) -> dict with keys:
    {ticker, confirmation_date, confirmation_type, is_spring, status,
     entry_date, entry_price, stop_price, target_price, risk,
     exit_date, exit_price, hold_days, R}
  status ∈ {"pending", "open", "target", "stop"} (the `pending` state is new
  in Phase 10; the other three flow through verbatim from Phase 9's
  simulate_trade with the `exit_reason` key renamed to `status`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import pytest

# Import will fail until Plan 04 lands — this is the expected Wave 0 RED state.
from scripts.pattern_scanner.run_pipeline import _resolve_status  # noqa: E402


@dataclass(frozen=True)
class FakeDet:
    """Minimal Detection stand-in for `_resolve_status`.

    Mirrors the field surface that simulate_trade + _resolve_status read off
    `scripts.pattern_scanner.detector.Detection` (RESEARCH §Example 6 L715-742).
    """

    ticker: str = "TEST"
    confirmation_date: str = "2024-01-10"
    confirmation_type: str = "pin"
    is_spring: bool = True
    mother_bar_index: int = 7
    confirmation_bar_index: int = 9
    bars: list = field(
        default_factory=lambda: [
            {"low": 99.0, "high": 105.0, "open": 100.0, "close": 102.0, "date": "2024-01-10"}
        ]
        * 5
    )
    filters: dict = field(default_factory=dict)
    sma_levels: dict = field(default_factory=dict)


def test_resolve_status_pending(synthetic_ohlc):
    """D-02: when entry_idx >= len(df), status MUST be `pending` and trade
    fields MUST be null. Stop/target are still pre-computable (cluster low +
    1:2 R off last close) so the UI can show "if filled tomorrow at ~X, stop
    ~Y, target ~Z" without claiming the trade has begun.
    """
    rows = [(100.0 + i, 105.0 + i, 99.0 + i, 102.0 + i) for i in range(10)]
    df = synthetic_ohlc(rows)
    # confirmation_bar_index = 9 (LAST bar), so entry_idx = 10 >= len(df) = 10.
    fake = FakeDet(confirmation_bar_index=9)

    rec = _resolve_status(df, fake)

    assert rec["status"] == "pending"
    assert rec["entry_date"] is None
    assert rec["entry_price"] is None
    assert rec["R"] is None
    # Stop and target are knowable even before entry (cluster low + 1:2 R).
    assert isinstance(rec["stop_price"], float)
    assert isinstance(rec["target_price"], float)
    # `exit_reason` is renamed to `status` at the run_pipeline boundary
    # (RESEARCH L425-426: `rec["status"] = rec.pop("exit_reason")`); the
    # old key MUST be absent in the returned dict.
    assert "exit_reason" not in rec


def test_resolve_status_delegates_to_simulate_trade(synthetic_ohlc):
    """D-02 sanity check: when entry IS possible (entry_idx < len(df)), the
    wrapper delegates to Phase 9's simulate_trade and surfaces its three
    outcome buckets — `target`, `stop`, or `open`. Never `pending`.
    """
    # 15-bar df, confirmation_bar_index = 9 → entry_idx = 10 < 15 = len(df).
    rows = [(100.0 + i, 105.0 + i, 99.0 + i, 102.0 + i) for i in range(15)]
    df = synthetic_ohlc(rows)
    fake = FakeDet(confirmation_bar_index=9)

    rec = _resolve_status(df, fake)

    assert rec["status"] in {"target", "stop", "open"}
    # Per-row payload contract (D-02). Every key MUST be present.
    required_keys = {
        "ticker",
        "confirmation_date",
        "confirmation_type",
        "is_spring",
        "status",
        "entry_date",
        "entry_price",
        "stop_price",
        "target_price",
        "risk",
        "exit_date",
        "exit_price",
        "hold_days",
        "R",
    }
    missing = required_keys - set(rec.keys())
    assert not missing, f"_resolve_status missing keys: {missing}"
    # Rename invariant: the legacy `exit_reason` key from Phase 9 must NOT
    # leak into Phase 10's output (RESEARCH L425-426).
    assert "exit_reason" not in rec
