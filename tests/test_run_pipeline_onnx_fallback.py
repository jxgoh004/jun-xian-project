"""Phase 10 D-08 / Phase 9 D-14: yolo_conf=null fallback when ONNX is missing.

RED (Wave 0): imports `run_pipeline` from `scripts.pattern_scanner` which
does not yet exist on disk. Plan 10-04 creates the module skeleton; Plan
10-06 wires the orchestrator `main()`. This test goes GREEN after Plan 10-06.

Template: `tests/test_backtest_yolo_conf_fallback.py` (Phase 9 D-14 analog —
identified by Phase 10 CONTEXT D-08 as the line-for-line shape to mirror).

Revision BLOCKER #3 (anti-vacuous):
  The spring-setup fixture is imported from `tests.test_detector_apply_trend_filters_kwarg`
  — the canonical 74-row sequence engineered to produce >=1 detection from
  detect(). The test asserts `len(data["detections"]) >= 1` BEFORE asserting
  every detection has `yolo_conf is None`, so the contract assertion is not
  vacuous if the fixture produces zero detections.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pattern_scanner import run_pipeline as run_pipeline_mod  # noqa: E402
# Canonical 74-row spring fixture (revision BLOCKER #3 — locked import path).
from tests.test_detector_apply_trend_filters_kwarg import _spring_setup_rows


@pytest.fixture
def patched_pipeline(monkeypatch, tmp_path, synthetic_ohlc):
    """Single-ticker patched environment with ONNX absent.

    `_spring_setup_rows()` returns a 5-tuple
    `(rows, mother_idx, conf_idx, mother_low, mother_high)` — the 74-row
    sequence is engineered to produce at least one detection from detect().

    `start_date="2026-04-15"` places confirmation_date inside the 20-BDay
    window from a 2026-05-* run-date so the detection survives D-01 filtering.
    """
    rows, _mother_idx, _conf_idx, _mother_low, _mother_high = _spring_setup_rows()
    df = synthetic_ohlc(rows, start_date="2026-04-15")
    monkeypatch.setattr(run_pipeline_mod, "fetch_sp500_tickers", lambda: ["TEST"])
    monkeypatch.setattr(run_pipeline_mod, "_fetch_ohlc", lambda t, period="6mo": df)
    monkeypatch.setattr(run_pipeline_mod.time, "sleep", lambda *a, **kw: None)
    monkeypatch.setattr(
        run_pipeline_mod, "ONNX_PATH", Path("/nonexistent/inside_bar_v1.onnx")
    )
    return tmp_path


def test_yolo_conf_null_when_onnx_missing(patched_pipeline):
    """D-08: missing ONNX model file → one UserWarning + every detection
    carries yolo_conf=None. Pipeline must still produce a valid data.json
    (return code 0) — the live screener never gates on the model.
    """
    out_dir = patched_pipeline

    with pytest.warns(UserWarning, match="ONNX model not found"):
        rc = run_pipeline_mod.main(
            [
                "--tickers",
                "TEST",
                "--window-days",
                "20",
                "--out-dir",
                str(out_dir),
            ]
        )
    assert rc == 0

    data = json.loads((out_dir / "data.json").read_text())

    # Anti-vacuous (revision BLOCKER #3): fixture MUST produce at least one
    # detection — otherwise the yolo_conf=null assertion below is meaningless.
    assert len(data["detections"]) >= 1, (
        "test fixture must produce at least one detection — "
        "otherwise yolo_conf=null assertion is vacuous"
    )
    assert all(d["yolo_conf"] is None for d in data["detections"]), (
        "every detection must have yolo_conf=null when ONNX is absent (D-08 contract)"
    )
