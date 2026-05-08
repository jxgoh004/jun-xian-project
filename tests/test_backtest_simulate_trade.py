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
