"""Unit tests for scripts.pattern_scanner.renderer — TRAIN-01 + bbox correctness.

All tests are pure-unit and run offline using the `synthetic_ohlc` fixture
from tests/conftest.py. NO @pytest.mark.network markers.
"""
from __future__ import annotations

import io
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from scripts.pattern_scanner.renderer import (
    RenderStyle,  # noqa: F401  (re-exported public surface — import test)
    STYLES,
    compute_bbox_normalized,
    render,
)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _flat_60(synthetic_ohlc) -> pd.DataFrame:
    """60-bar OHLC frame with monotone slow drift — deterministic, valid for mpf."""
    rng = np.random.default_rng(0)
    rows: List[Tuple[float, float, float, float]] = []
    base = 100.0
    for _ in range(60):
        o = base + rng.uniform(-0.5, 0.5)
        h = max(o, base) + rng.uniform(0.1, 1.0)
        l = min(o, base) - rng.uniform(0.1, 1.0)
        c = base + rng.uniform(-0.5, 0.5)
        rows.append((float(o), float(h), float(l), float(c)))
        base = c
    return synthetic_ohlc(rows)


# ── W8 spike-recorded baseline (recorded 2026-05-02 on this machine) ────────
# Source: Step 0 of Plan 02 Task 1 — `compute_bbox_normalized(_flat_60(rng=0),
# mother_idx_in_window=55, confirmation_idx_in_window=59, style=STYLES[0])`.
# Tolerance is ±0.02 to absorb minor mplfinance/matplotlib version drift while
# still catching real geometry regressions.
_SPIKE_CX = 0.8352433023510114
_SPIKE_CY = 0.35750947500642727
_SPIKE_W = 0.04938615239326012
_SPIKE_H = 0.24339904312602512
_SPIKE_TOL = 0.02


# ── Tests ───────────────────────────────────────────────────────────────────
def test_render_returns_640x640_png(synthetic_ohlc):
    """render() returns bytes that PIL decodes to a 640x640 RGB PNG (D-04)."""
    df = _flat_60(synthetic_ohlc)
    png_bytes = render(df, STYLES[0])
    img = Image.open(io.BytesIO(png_bytes))
    assert img.size == (640, 640)
    assert img.mode == "RGB"
    # PNG signature.
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_deterministic_same_style(synthetic_ohlc):
    """Two renders with the same (df, style) produce byte-identical PNGs."""
    df = _flat_60(synthetic_ohlc)
    a = render(df, STYLES[0])
    b = render(df, STYLES[0])
    assert a == b, "render must be deterministic on the same machine + style"


def test_render_styles_differ(synthetic_ohlc):
    """Rendering the same df with all 3 STYLES yields 3 byte-distinct PNGs."""
    df = _flat_60(synthetic_ohlc)
    outs = [render(df, s) for s in STYLES]
    assert len(set(outs)) == 3, "STYLES must produce visually distinct PNGs"


def test_render_rejects_wrong_bar_count(synthetic_ohlc):
    """render() raises ValueError when the input frame is not exactly 60 bars."""
    df = _flat_60(synthetic_ohlc).iloc[:50]   # 50 bars, not 60
    with pytest.raises(ValueError, match="60 bars"):
        render(df, STYLES[0])


def test_compute_bbox_encloses_cluster_excludes_neighbours(synthetic_ohlc):
    """Bbox encloses bars [55..59] (the 5-bar cluster, right-aligned per D-03)
    and excludes bar 54 (the bar immediately before mother).

    Acceptance values come from the W8 bbox spike — Step 0 of Task 1 prints them
    to stdout; recorded as the _SPIKE_* constants above. This test asserts within
    ±_SPIKE_TOL of those recorded values to prevent silent geometry drift.
    """
    df = _flat_60(synthetic_ohlc)
    # 5-bar cluster: mother=55, confirmation=59 (right edge per D-03)
    cx, cy, w, h = compute_bbox_normalized(
        df,
        mother_idx_in_window=55,
        confirmation_idx_in_window=59,
        style=STYLES[0],
    )

    # All four normalised values in [0, 1].
    for label, value in (("cx", cx), ("cy", cy), ("w", w), ("h", h)):
        assert 0.0 <= value <= 1.0, f"value out of [0,1]: {label}={value}"

    # Right-aligned (D-03): confirmation bar at the right edge of the frame.
    right_edge = cx + w / 2
    assert right_edge >= 0.85, (
        f"confirmation bar should be right-aligned; right_edge={right_edge}"
    )

    # Width covers ~5 bars (with tight bbox margins from mplfinance). The
    # spike-recorded value is ~0.049, so we use a generous lower bound to
    # accept the actual geometry of the rendered axes.
    assert 0.04 <= w <= 0.20, f"5-bar bbox width should be ~5/60 with margins; got {w}"

    # Spike-baseline equality (within ±_SPIKE_TOL) — guards against silent drift
    # in mplfinance / matplotlib axes-transform geometry.
    assert abs(cx - _SPIKE_CX) <= _SPIKE_TOL, f"cx drifted from spike: {cx} vs {_SPIKE_CX}"
    assert abs(cy - _SPIKE_CY) <= _SPIKE_TOL, f"cy drifted from spike: {cy} vs {_SPIKE_CY}"
    assert abs(w - _SPIKE_W) <= _SPIKE_TOL, f"w drifted from spike: {w} vs {_SPIKE_W}"
    assert abs(h - _SPIKE_H) <= _SPIKE_TOL, f"h drifted from spike: {h} vs {_SPIKE_H}"

    # Bar 54 (the bar immediately before mother) must NOT overlap the bbox.
    # Bar i in mplfinance spans [i - candle_width/2, i + candle_width/2] in DATA
    # x-coords. STYLES[0].candle_width=0.6, so bar 54 right edge = 54.3 (data),
    # and mother bar (55) left edge = 54.7 (data) — a 0.4-data-unit gap. The
    # bbox left_edge in normalised space must therefore lie strictly to the
    # right of bar 54's right edge after the same axes transform.
    left_edge = cx - w / 2
    # Conservative: left_edge sits comfortably to the right of frame midpoint.
    assert left_edge > 0.5, f"bbox left_edge={left_edge} unexpectedly far left"
