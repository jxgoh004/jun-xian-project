"""BT-02 / D-12: unfiltered strategy is a strict superset of the filtered strategy."""
from __future__ import annotations

import json

import pytest

from scripts.pattern_scanner import backtest as backtest_mod
from tests.test_generate_training_data import _flat_prefix_rows, _spring_setup_rows


@pytest.fixture
def patched_environment(monkeypatch, tmp_path, synthetic_ohlc):
    """Two tickers:
       - 'FILT' uses _spring_setup_rows (HH/HL prefix → all filters PASS → both strategies emit).
       - 'FLAT' uses _flat_prefix_rows (flat prefix → filters FAIL → only unfiltered emits).
    Together they prove: filtered ⊆ unfiltered AND unfiltered may have extra (D-12).
    """
    rows_filt, *_ = _spring_setup_rows()
    rows_flat = _flat_prefix_rows()
    df_filt = synthetic_ohlc(rows_filt, start_date="2020-01-01")
    df_flat = synthetic_ohlc(rows_flat, start_date="2020-01-01")
    frames_by_ticker = {"FILT": df_filt, "FLAT": df_flat}

    def fake_fetch(ticker, period="10y"):
        return frames_by_ticker[ticker]

    monkeypatch.setattr(backtest_mod, "_load_tickers", lambda limit: ["FILT", "FLAT"])
    monkeypatch.setattr(backtest_mod, "_fetch_ohlc", fake_fetch)
    monkeypatch.setattr(backtest_mod.time, "sleep", lambda *a, **kw: None)
    return tmp_path / "backtest_cache.json"


def _all_keys(strategy_block) -> set[tuple]:
    keys = set()
    for sample in ("in_sample", "out_of_sample"):
        for r in strategy_block[sample]["detections"]:
            keys.add(
                (r["ticker"], r["mother_bar_index"], r["confirmation_bar_index"])
            )
    return keys


def test_unfiltered_strategy_is_superset(patched_environment):
    out_path = patched_environment
    rc = backtest_mod.main([
        "--seed", "42",
        "--tickers", "all",
        "--out", str(out_path),
        "--no-onnx",
    ])
    assert rc == 0

    cache = json.loads(out_path.read_text())
    filtered_keys = _all_keys(cache["strategies"]["1to2_rr_cluster_low_stop"])
    unfiltered_keys = _all_keys(cache["strategies"]["1to2_rr_cluster_low_stop__unfiltered"])

    assert filtered_keys.issubset(unfiltered_keys), (
        f"D-12 superset violated. In filtered but not unfiltered: "
        f"{filtered_keys - unfiltered_keys}"
    )
    assert len(unfiltered_keys) >= len(filtered_keys), (
        "Unfiltered must have >= filtered count"
    )
    # Strict-superset evidence: FLAT ticker contributes only to unfiltered.
    flat_in_unfiltered = any(k[0] == "FLAT" for k in unfiltered_keys)
    flat_in_filtered = any(k[0] == "FLAT" for k in filtered_keys)
    assert flat_in_unfiltered, "FLAT ticker should appear in unfiltered (filters bypassed)"
    assert not flat_in_filtered, "FLAT ticker should NOT appear in filtered (filters fail)"
