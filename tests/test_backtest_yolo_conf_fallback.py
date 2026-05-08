"""BT-03 / D-14: yolo_conf=null fallback when ONNX model is missing.

Three scenarios covered:
1. ONNX model file absent -> exactly one UserWarning + every record yolo_conf=None.
2. --no-onnx flag -> no warning, _load_onnx_session never called, every record yolo_conf=None.
3. Real (mocked) session present -> records carry yolo_conf as float in [0.0, 1.0].
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pattern_scanner import backtest as backtest_mod
from tests.test_generate_training_data import _spring_setup_rows


@pytest.fixture
def patched_environment(monkeypatch, tmp_path, synthetic_ohlc):
    """Single ticker producing >= 1 detection so we have records to inspect.

    `_spring_setup_rows()` returns (rows, mother_idx, conf_idx, mother_low, mother_high);
    we pass the rows to `synthetic_ohlc` with a post-cutoff start_date so the cluster
    geometry resolves to a detection (conf_idx=73 > 59, so the 60-bar window is valid).
    """
    rows, *_ = _spring_setup_rows()
    df = synthetic_ohlc(rows, start_date="2024-02-01")  # post-cutoff for clarity
    monkeypatch.setattr(backtest_mod, "_load_tickers", lambda limit: ["TEST"])
    monkeypatch.setattr(backtest_mod, "_fetch_ohlc", lambda t, period="10y": df)
    monkeypatch.setattr(backtest_mod.time, "sleep", lambda *a, **kw: None)
    return tmp_path / "backtest_cache.json"


def _all_records(cache: dict) -> list[dict]:
    out = []
    for strat in cache["strategies"].values():
        for sample in ("in_sample", "out_of_sample"):
            out.extend(strat[sample]["detections"])
    return out


def test_yolo_conf_null_when_onnx_missing(patched_environment, monkeypatch):
    """D-14: missing ONNX file -> single UserWarning + every record yolo_conf=None."""
    out_path = patched_environment
    # Force ONNX_PATH to a non-existent location
    monkeypatch.setattr(backtest_mod, "ONNX_PATH", Path("/nonexistent/inside_bar_v1.onnx"))

    with pytest.warns(UserWarning, match="ONNX model not found"):
        rc = backtest_mod.main(["--seed", "42", "--tickers", "all", "--out", str(out_path)])
    assert rc == 0

    cache = json.loads(out_path.read_text())
    records = _all_records(cache)
    assert len(records) >= 1, "Test fixture must produce at least one detection"
    for rec in records:
        assert rec["yolo_conf"] is None, (
            f"Expected yolo_conf=None when ONNX missing; got {rec['yolo_conf']} on {rec['ticker']}"
        )

    # Cache header onnx_sha256 must also be null when model is absent
    assert cache["onnx_sha256"] is None


def test_yolo_conf_null_when_no_onnx_flag(patched_environment, monkeypatch):
    """--no-onnx bypasses session loading entirely (no warning, _load_onnx_session not called)."""
    out_path = patched_environment

    # Spy on _load_onnx_session to assert it is NOT called when --no-onnx is set
    calls: list = []
    real_loader = backtest_mod._load_onnx_session

    def spy(path):
        calls.append(path)
        return real_loader(path)

    monkeypatch.setattr(backtest_mod, "_load_onnx_session", spy)

    rc = backtest_mod.main(["--seed", "42", "--tickers", "all", "--out", str(out_path), "--no-onnx"])
    assert rc == 0
    assert calls == [], "_load_onnx_session must not be called when --no-onnx is set"

    cache = json.loads(out_path.read_text())
    records = _all_records(cache)
    for rec in records:
        assert rec["yolo_conf"] is None
    assert cache["onnx_sha256"] is None  # forced None when --no-onnx


def test_yolo_conf_populated_when_session_available(patched_environment, monkeypatch):
    """When _load_onnx_session returns a (mocked) session, yolo_conf must be a float in [0,1]."""
    out_path = patched_environment

    # Stub _load_onnx_session to return a sentinel non-None object so _build_record
    # passes a non-None sess into _score_detection.
    sentinel_session = object()
    monkeypatch.setattr(backtest_mod, "_load_onnx_session", lambda p: sentinel_session)

    # Stub _score_detection itself to bypass renderer + PIL + ONNX inference, but
    # respect the same None-returning contract for sess is None / window is None.
    def fake_score(window, sess):
        if sess is None or window is None:
            return None
        return 0.42

    monkeypatch.setattr(backtest_mod, "_score_detection", fake_score)

    rc = backtest_mod.main(["--seed", "42", "--tickers", "all", "--out", str(out_path)])
    assert rc == 0

    cache = json.loads(out_path.read_text())
    records = _all_records(cache)
    assert len(records) >= 1
    populated = [r for r in records if r["yolo_conf"] is not None]
    assert len(populated) >= 1, "Expected at least one record with non-null yolo_conf"
    for rec in populated:
        assert isinstance(rec["yolo_conf"], float)
        assert 0.0 <= rec["yolo_conf"] <= 1.0
