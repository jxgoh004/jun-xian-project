"""BT-01: simulate_trade resolution paths (D-01..D-05)."""
import pytest

from scripts.pattern_scanner.backtest import simulate_trade
from scripts.pattern_scanner.detector import Detection


def _make_detection(mother_idx: int, conf_idx: int, *,
                    confirmation_type: str = "pin",
                    is_spring: bool = False,
                    bars: list[dict] | None = None,
                    confirmation_date: str = "2024-01-03",
                    ticker: str = "TEST") -> Detection:
    """Inline helper — builds a Detection without running detect()."""
    if bars is None:
        bars = [{"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5, "date": "2024-01-01"}] * 5
    return Detection(
        ticker=ticker,
        confirmation_date=confirmation_date,
        confirmation_type=confirmation_type,
        is_spring=is_spring,
        mother_bar_index=mother_idx,
        confirmation_bar_index=conf_idx,
        bars=bars,
        filters={"hh_hl": True, "above_50sma": True, "sma_cluster": True},
        sma_levels={"sma20": 10.0, "sma50": 10.0, "atr14": 0.5},
    )


def test_simulate_trade_stop_first(synthetic_ohlc):
    # Bars: 0..2 = pre-confirmation; 3 = entry (open=10.0, low=9.8 > stop=9.5 — no intrabar hit);
    # 4 = stop bar (low=9.0 <= stop=9.5; high=10.5 < target=11.0).
    # synthetic_ohlc rows are (open, high, low, close).
    df = synthetic_ohlc([
        (10.0, 11.0, 9.5, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.0, 10.5, 9.8, 10.2),
        (10.0, 10.5, 9.0, 9.2),
    ])
    det = _make_detection(mother_idx=0, conf_idx=2)
    rec = simulate_trade(df, det, stop_price=9.5, target_price=11.0)
    assert rec["exit_reason"] == "stop"
    assert rec["R"] == -1.0
    assert rec["exit_date"] == "2024-01-05"
    assert rec["entry_date"] == "2024-01-04"
    assert type(rec["entry_price"]) is float
    assert type(rec["stop_price"]) is float
    assert type(rec["R"]) is float


def test_simulate_trade_target_first(synthetic_ohlc):
    # Bars: 4 hits target=11.0 first (low > stop=9.5, high >= 11.0).
    df = synthetic_ohlc([
        (10.0, 11.0, 9.5, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.0, 10.5, 9.8, 10.2),
        (10.0, 11.5, 9.8, 11.2),
    ])
    det = _make_detection(mother_idx=0, conf_idx=2)
    rec = simulate_trade(df, det, stop_price=9.5, target_price=11.0)
    assert rec["exit_reason"] == "target"
    assert rec["R"] == 2.0
    assert rec["exit_date"] == "2024-01-05"


def test_simulate_trade_intrabar_pessimistic(synthetic_ohlc):
    # D-03: bar 4 has low=9.0 <= stop AND high=11.5 >= target → stop wins.
    df = synthetic_ohlc([
        (10.0, 11.0, 9.5, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.0, 10.5, 9.8, 10.2),
        (10.0, 11.5, 9.0, 10.5),
    ])
    det = _make_detection(mother_idx=0, conf_idx=2)
    rec = simulate_trade(df, det, stop_price=9.5, target_price=11.0)
    assert rec["exit_reason"] == "stop"
    assert rec["R"] == -1.0


def test_simulate_trade_gap_down_through_stop(synthetic_ohlc):
    """D-04: entry bar gaps down THROUGH the stop (open < stop). The recorded R
    must be < -1.0 — a gap-through is strictly worse than a clean -1R stop.

    Setup:
      - confirmation bar (idx=2): close = 10.0  (pre-gap reference)
      - entry bar (idx=3): open = 8.5  (gap-down well below stop=9.5)
      - stop = 9.5, target = 12.0
      - intended_risk = conf_close - stop = 10.0 - 9.5 = 0.5
      - R = (entry_open - stop) / intended_risk = (8.5 - 9.5) / 0.5 = -2.0
    """
    df = synthetic_ohlc([
        (10.0, 11.0, 9.5, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.5, 11.0, 9.8, 10.0),   # confirmation bar — Close = 10.0
        (8.5, 9.0, 8.0, 8.2),      # entry bar gaps down through stop
        (8.5, 9.0, 8.0, 8.2),
    ])
    det = _make_detection(mother_idx=0, conf_idx=2)
    rec = simulate_trade(df, det, stop_price=9.5, target_price=12.0)
    assert rec["exit_reason"] == "stop"
    assert rec["R"] == pytest.approx(-2.0)
    assert rec["R"] < -1.0, f"gap-through must record R < -1.0, got {rec['R']}"
    assert rec["entry_price"] == 8.5
    assert rec["exit_price"] == 8.5  # exit at entry_open per D-04
    assert rec["hold_days"] == 0
    assert type(rec["R"]) is float


def test_simulate_trade_gap_down_exactly_at_stop(synthetic_ohlc):
    """D-04 boundary: entry_open == stop_price. R must equal 0.0 exactly when
    the gap lands precisely at the stop (zero realized loss vs. the planned
    1R reference). Confirms the divide-by-zero hazard from the prior code is
    gone (now uses pre-gap intended_risk, not entry_open - stop).

    Setup:
      - confirmation close = 10.5, stop = 9.5 -> intended_risk = 1.0
      - entry_open = 9.5 (gap exactly to stop) -> R = (9.5 - 9.5) / 1.0 = 0.0
    """
    df = synthetic_ohlc([
        (10.0, 11.0, 9.5, 10.5),
        (10.5, 11.0, 10.0, 10.5),
        (10.5, 11.0, 9.8, 10.5),   # confirmation close = 10.5
        (9.5, 10.0, 9.0, 9.2),     # entry_open == stop
        (9.0, 9.5, 8.5, 8.8),
    ])
    det = _make_detection(mother_idx=0, conf_idx=2)
    rec = simulate_trade(df, det, stop_price=9.5, target_price=12.5)
    assert rec["exit_reason"] == "stop"
    # entry_open == stop -> numerator zero -> R == 0.0 (no divide-by-zero)
    assert rec["R"] == pytest.approx(0.0)
    assert rec["hold_days"] == 0


def test_simulate_trade_open_outcome(synthetic_ohlc):
    # No bar hits stop=9.0 or target=12.0; ends 'open' with R = (last_close - entry) / risk.
    df = synthetic_ohlc([
        (10.0, 10.8, 9.5, 10.5),
        (10.5, 10.8, 10.0, 10.5),
        (10.5, 10.8, 10.0, 10.5),
        (10.0, 10.8, 9.8, 10.5),
        (10.0, 10.8, 9.5, 10.6),
    ])
    det = _make_detection(mother_idx=0, conf_idx=2)
    rec = simulate_trade(df, det, stop_price=9.0, target_price=12.0)
    assert rec["exit_reason"] == "open"
    expected_R = (10.6 - 10.0) / (10.0 - 9.0)
    assert rec["R"] == pytest.approx(expected_R)
    assert rec["exit_date"] == "2024-01-05"
