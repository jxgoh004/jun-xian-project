"""Unit checks on the trained ONNX artifacts — TRAIN-04.

The actual clean-venv inference round-trip lives in scripts/pattern_scanner/verify_onnx.py
(Plan 05) — it requires creating a temp venv, which is too slow / brittle for the unit suite.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ONNX_PATH = Path("models/inside_bar_v1.onnx")
SUMMARY_PATH = Path("models/training_summary.json")


def test_onnx_file_exists():
    assert ONNX_PATH.exists(), f"{ONNX_PATH} not committed — run train.py first"
    size = ONNX_PATH.stat().st_size
    assert 1_000_000 <= size <= 50_000_000, f"unexpected size {size} for YOLOv8n ONNX"


def test_opset_recorded():
    assert SUMMARY_PATH.exists(), f"{SUMMARY_PATH} not committed — run train.py first"
    payload = json.loads(SUMMARY_PATH.read_text())
    assert payload["opset"] == 12, f"opset != 12: {payload['opset']}"
    assert payload["imgsz"] == 640
    assert payload["fliplr"] == 0.0


@pytest.mark.skip(reason="Implemented in Plan 05 (clean-venv subprocess round-trip)")
def test_manifest_sha256_round_trip():
    """Re-run generator with same seed; manifest concat_sha256 matches."""
