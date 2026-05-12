"""Phase 10 D-16 / PIPE-01: pipeline_status threshold + end-to-end smoke.

RED (Wave 0): imports `run_pipeline` from `scripts.pattern_scanner` which
does not yet exist. Plan 10-04 scaffolds the module; Plan 10-06 wires
`main()`. These tests GREEN after Plan 10-06.

Contract this file locks:
  - 20 tickers, 1 yfinance failure -> succeeded=19, failed=1, completed=True
    (19/20 = 95.0% — the threshold IS >= 95%, boundary inclusive).
  - 20 tickers, 2 yfinance failures -> succeeded=18, failed=2, completed=False.
  - main() smoke: data.json contains a `detections` list and `pipeline_status`
    object with the required keys {completed, errors, succeeded_count,
    failed_count, generated_at, run_id, schema_version}.

Revision BLOCKER #1: `test_main_smoke_with_synthetic_ohlc` is REQUIRED
(not optional). It is the load-bearing assertion for 10-VALIDATION.md row 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pattern_scanner import run_pipeline as run_pipeline_mod  # noqa: E402


@pytest.fixture
def patched_universe(monkeypatch, tmp_path):
    """Universe loader + sleep + ONNX_PATH patches shared across all three tests.

    `fetch_sp500_tickers` is imported into run_pipeline_mod's namespace, so we
    patch it on `run_pipeline_mod` itself (not on `scripts.fetch_sp500`).
    """
    tickers = [f"A{i:03d}" for i in range(1, 21)]  # 20 tickers
    monkeypatch.setattr(run_pipeline_mod, "fetch_sp500_tickers", lambda: tickers)
    monkeypatch.setattr(run_pipeline_mod.time, "sleep", lambda *a, **kw: None)
    monkeypatch.setattr(run_pipeline_mod, "ONNX_PATH", Path("/nonexistent/onnx"))
    return tickers, tmp_path


def _normal_df(synthetic_ohlc):
    """60-bar synthetic OHLC frame with confirmation_date inside the 20-BDay window."""
    rows = [
        (100.0 + i * 0.1, 102.0 + i * 0.1, 99.0 + i * 0.1, 101.0 + i * 0.1)
        for i in range(60)
    ]
    return synthetic_ohlc(rows, start_date="2026-04-15")


def test_pipeline_status_completed_true_when_above_95pct(
    patched_universe, monkeypatch, synthetic_ohlc
):
    """D-16: 19/20 success (95.0%) -> completed=True (boundary inclusive).

    1 yfinance failure on A001; remaining 19 tickers return the normal df.
    """
    _tickers, tmp_path = patched_universe
    df = _normal_df(synthetic_ohlc)

    def _fetch(t, period="6mo"):
        if t == "A001":
            raise RuntimeError("yfinance test flake")
        return df

    monkeypatch.setattr(run_pipeline_mod, "_fetch_ohlc", _fetch)

    with pytest.warns(UserWarning):  # ONNX missing
        rc = run_pipeline_mod.main(
            [
                "--tickers",
                "all",
                "--window-days",
                "20",
                "--out-dir",
                str(tmp_path),
            ]
        )
    assert rc == 0
    data = json.loads((tmp_path / "data.json").read_text())
    assert data["pipeline_status"]["completed"] is True
    assert data["pipeline_status"]["succeeded_count"] == 19
    assert data["pipeline_status"]["failed_count"] == 1
    assert len(data["pipeline_status"]["errors"]) == 1
    assert data["pipeline_status"]["errors"][0]["ticker"] == "A001"


def test_pipeline_status_completed_false_when_below_95pct(
    patched_universe, monkeypatch, synthetic_ohlc
):
    """D-16: 18/20 success (90.0%) -> completed=False.

    2 yfinance failures on A001/A002.
    """
    _tickers, tmp_path = patched_universe
    df = _normal_df(synthetic_ohlc)

    def _fetch(t, period="6mo"):
        if t in {"A001", "A002"}:
            raise RuntimeError("yfinance test flake")
        return df

    monkeypatch.setattr(run_pipeline_mod, "_fetch_ohlc", _fetch)

    with pytest.warns(UserWarning):
        rc = run_pipeline_mod.main(
            [
                "--tickers",
                "all",
                "--window-days",
                "20",
                "--out-dir",
                str(tmp_path),
            ]
        )
    assert rc == 0
    data = json.loads((tmp_path / "data.json").read_text())
    assert data["pipeline_status"]["completed"] is False
    assert data["pipeline_status"]["succeeded_count"] == 18
    assert data["pipeline_status"]["failed_count"] == 2


def test_main_smoke_with_synthetic_ohlc(
    patched_universe, monkeypatch, synthetic_ohlc
):
    """REQUIRED smoke test (revision BLOCKER #1).

    Validates that main() runs end-to-end against a fully-synthetic universe,
    produces a data.json with the expected top-level pipeline_status keys,
    and exits cleanly. Does NOT exercise the threshold logic (that is covered
    by the two tests above). This test is the load-bearing assertion that
    10-VALIDATION.md row 1 references.
    """
    _tickers, tmp_path = patched_universe
    df = _normal_df(synthetic_ohlc)
    monkeypatch.setattr(run_pipeline_mod, "_fetch_ohlc", lambda t, period="6mo": df)

    with pytest.warns(UserWarning):  # ONNX missing
        rc = run_pipeline_mod.main(
            [
                "--tickers",
                "all",
                "--limit",
                "5",
                "--out-dir",
                str(tmp_path),
            ]
        )
    assert rc == 0

    data_path = tmp_path / "data.json"
    assert data_path.exists() is True

    data = json.loads(data_path.read_text())
    assert isinstance(data["detections"], list)
    # LO-03: lock the empty-detections contract for THIS fixture. The
    # synthetic OHLC at line ~45 above is monotonic-rising and will not
    # produce a pin/mark_up/ice_cream pattern; if a future detector change
    # starts emitting detections here, the test will fail loudly and we
    # know to either swap to a setup-bearing fixture or update the
    # assertion. Without this, the smoke test silently validates the
    # empty-path rather than the populated-path.
    assert len(data["detections"]) == 0, (
        f"smoke fixture unexpectedly produced {len(data['detections'])} "
        "detections; pick a setup-bearing fixture to exercise the populated "
        "path, or update this assertion."
    )

    ps = data["pipeline_status"]
    required_keys = {
        "completed",
        "errors",
        "succeeded_count",
        "failed_count",
        "generated_at",
        "run_id",
        "schema_version",
    }
    missing = required_keys - set(ps.keys())
    assert not missing, f"pipeline_status missing keys: {missing}"
    assert isinstance(ps["completed"], bool)
