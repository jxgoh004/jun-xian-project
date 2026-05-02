"""Unit-level checks on the trained ONNX artifacts — TRAIN-04 (Plan 04/05 fill these in).

The actual clean-venv inference is a CLI gate via verify_onnx.py — see Plan 05.
"""
from __future__ import annotations
import pytest

pytestmark = pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04 (opset) and Plan 05 (round-trip)")

def test_onnx_file_exists():
    """models/inside_bar_v1.onnx exists post-train."""

def test_opset_recorded():
    """models/training_summary.json contains opset == 12."""

def test_manifest_sha256_round_trip():
    """models/dataset_manifest.json concat_sha256 matches a deterministic re-run on the same seed."""
