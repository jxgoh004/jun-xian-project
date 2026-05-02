"""Unit tests for scripts.pattern_scanner.renderer — TRAIN-01 (Plan 02 fills these in)."""
from __future__ import annotations
import pytest

pytestmark = pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 02 (renderer)")

def test_render_returns_640x640_png():
    """Render of a 60-bar synthetic frame produces a 640x640 RGB PNG."""

def test_render_deterministic_same_style():
    """Two renders with the same (df, style) produce byte-identical PNG on the same machine."""

def test_render_styles_differ():
    """Rendering the same df with 3 different styles produces 3 byte-distinct PNGs."""
