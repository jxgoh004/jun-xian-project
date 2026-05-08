"""BT-02 / D-11: cutoff partition isolation (no leakage across TRAIN_TEST_CUTOFF)."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.pattern_scanner import backtest as backtest_mod
from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF
from tests.test_generate_training_data import _spring_setup_rows


@pytest.fixture
def patched_environment(monkeypatch, tmp_path, synthetic_ohlc):
    """Two synthetic tickers — one with confirmation_date pre-cutoff, one post-cutoff.

    `_spring_setup_rows()` returns (rows, mother_idx, conf_idx, mother_low, mother_high).
    The 74 bars span ~110 calendar days; we pick start_dates so the confirmation bar
    (index 73) lands clearly on either side of TRAIN_TEST_CUTOFF (2024-01-01).
    """
    rows_pre, _m_pre, _c_pre, *_ = _spring_setup_rows()
    rows_post, _m_post, _c_post, *_ = _spring_setup_rows()
    df_pre = synthetic_ohlc(rows_pre, start_date="2023-04-01")    # conf lands ~2023-07-12
    df_post = synthetic_ohlc(rows_post, start_date="2024-02-01")  # conf lands ~2024-05-13

    frames_by_ticker = {"PRE": df_pre, "POST": df_post}

    def fake_fetch(ticker, period="10y"):
        return frames_by_ticker[ticker]

    monkeypatch.setattr(backtest_mod, "_load_tickers", lambda limit: ["PRE", "POST"])
    monkeypatch.setattr(backtest_mod, "_fetch_ohlc", fake_fetch)
    monkeypatch.setattr(backtest_mod.time, "sleep", lambda *a, **kw: None)
    return tmp_path / "backtest_cache.json"


def test_train_test_cutoff_isolation(patched_environment):
    """No in_sample record has confirmation_date >= cutoff; no out_of_sample record < cutoff."""
    out_path = patched_environment
    rc = backtest_mod.main([
        "--seed", "42",
        "--tickers", "all",
        "--out", str(out_path),
        "--no-onnx",
    ])
    assert rc == 0

    cache = json.loads(out_path.read_text())
    cutoff = TRAIN_TEST_CUTOFF  # "2024-01-01" — string compare safe (ISO YYYY-MM-DD)

    # Header sanity
    assert cache["schema_version"] == 1
    assert cache["train_test_cutoff"] == cutoff
    assert cache["seed"] == 42
    assert set(cache["strategies"].keys()) == {
        "1to2_rr_cluster_low_stop",
        "1to2_rr_cluster_low_stop__unfiltered",
    }

    saw_pre = saw_post = False
    for strategy_name, strategy in cache["strategies"].items():
        for rec in strategy["in_sample"]["detections"]:
            assert rec["confirmation_date"] < cutoff, (
                f"{strategy_name} in_sample contains record with "
                f"confirmation_date {rec['confirmation_date']} >= cutoff {cutoff}"
            )
            saw_pre = True
        for rec in strategy["out_of_sample"]["detections"]:
            assert rec["confirmation_date"] >= cutoff, (
                f"{strategy_name} out_of_sample contains record with "
                f"confirmation_date {rec['confirmation_date']} < cutoff {cutoff}"
            )
            saw_post = True

    # Both partitions must be exercised — guard against vacuous-truth pass.
    assert saw_pre, "expected at least one pre-cutoff (in_sample) detection"
    assert saw_post, "expected at least one post-cutoff (out_of_sample) detection"


def test_boundary_record_lands_in_out_of_sample(patched_environment, monkeypatch):
    """Pitfall 6: a record with confirmation_date == cutoff must land in out_of_sample (>=)."""
    out_path = patched_environment

    # Patch _partition_cutoff via a probe: feed a synthetic record at cutoff exactly.
    cutoff = TRAIN_TEST_CUTOFF
    boundary_rec = {"confirmation_date": cutoff}
    in_sample, out_of_sample = backtest_mod._partition_cutoff([boundary_rec], cutoff)
    assert boundary_rec not in in_sample
    assert boundary_rec in out_of_sample
