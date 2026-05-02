"""Headless mplfinance candlestick renderer with style randomisation.

Public API:
    render(df, style, target_size=640) -> bytes              # PNG bytes (RGB)
    compute_bbox_normalized(df, mother_idx_in_window,
                             confirmation_idx_in_window, style,
                             target_size=640) -> (cx, cy, w, h)
    STYLES                                                   # tuple[RenderStyle, ...]
    RenderStyle                                              # frozen dataclass

CLI:
    python scripts/pattern_scanner/renderer.py <CSV_PATH> <STYLE_NAME> <OUT_PNG>

Invariants:
    - matplotlib backend is FORCED to "Agg" before any mplfinance/pyplot import.
    - Pure function: no global state, no plt.show, no on-disk side effects from render().
    - target_size is always a square image (target_size x target_size RGB).
    - Right-aligned framing (CONTEXT D-03): the rightmost bar in df is the confirmation.
"""
from __future__ import annotations

# ── Backend MUST come before any pyplot/mplfinance import ───────────────────
import matplotlib
matplotlib.use("Agg")

import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt  # noqa: E402  (must come after matplotlib.use)
import mplfinance as mpf  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

# ── Module constants ────────────────────────────────────────────────────────
_BAR_COUNT = 60                  # parity with detector._LOOKBACK (D-01)
_DEFAULT_TARGET_SIZE = 640       # D-04
_FONT_FAMILY = "DejaVu Sans"     # ships with matplotlib; reduces cross-OS variance


# ── RenderStyle + STYLES (D-17 + research §Pitfall 1) ───────────────────────
@dataclass(frozen=True)
class RenderStyle:
    """Frozen rendering parameter set used by render() and compute_bbox_normalized().

    Attributes:
        name: identifier ("style_a" | "style_b" | "style_c").
        base_style: mplfinance built-in ("yahoo" | "charles" | "classic").
        figsize: (width, height) in inches passed to mpf.plot.
        dpi: savefig DPI; combined with figsize, determines pre-resize pixel dimensions.
        candle_width: per-bar candle width passed via update_width_config.
        facecolor: hex background colour.
    """

    name: str
    base_style: str
    figsize: Tuple[float, float]
    dpi: int
    candle_width: float
    facecolor: str


STYLES: Tuple[RenderStyle, ...] = (
    RenderStyle("style_a", "yahoo",   (8.0, 6.0), 100, 0.6, "#ffffff"),
    RenderStyle("style_b", "charles", (10.0, 7.0), 120, 0.5, "#fafafa"),
    RenderStyle("style_c", "classic", (6.0, 5.0),  90, 0.7, "#f5f5f5"),
)


# ── Internal helpers ────────────────────────────────────────────────────────
def _validate_frame(df: pd.DataFrame) -> None:
    """Raise ValueError if df is not a 60-bar OHLC frame."""
    if len(df) != _BAR_COUNT:
        raise ValueError(f"render() requires {_BAR_COUNT} bars; got {len(df)}")
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"render() requires columns {required}; missing: {missing}")


def _make_mpf_style(style: RenderStyle):
    """Build the mplfinance style object for a RenderStyle."""
    return mpf.make_mpf_style(
        base_mpf_style=style.base_style,
        facecolor=style.facecolor,
        rc={"font.family": _FONT_FAMILY},
    )


# ── Public API ──────────────────────────────────────────────────────────────
def render(df: pd.DataFrame, style: RenderStyle,
           target_size: int = _DEFAULT_TARGET_SIZE) -> bytes:
    """Render a 60-bar candlestick PNG to bytes, resized to target_size x target_size.

    Args:
        df: DataFrame with Open/High/Low/Close columns and a DatetimeIndex,
            exactly 60 rows (parity with detector._LOOKBACK).
        style: one of STYLES (any RenderStyle accepted).
        target_size: final square pixel dimension (default 640 per D-04).

    Returns:
        PNG bytes of the resized RGB image.

    Raises:
        ValueError: if len(df) != 60 or required columns missing.
    """
    _validate_frame(df)

    mpf_style = _make_mpf_style(style)

    buf = io.BytesIO()
    mpf.plot(
        df,
        type="candle",
        style=mpf_style,
        figsize=style.figsize,
        update_width_config={"candle_width": style.candle_width},
        axisoff=True,
        savefig=dict(
            fname=buf,
            dpi=style.dpi,
            bbox_inches="tight",
            pad_inches=0,
        ),
    )
    plt.close("all")  # critical: prevents memory growth across thousands of renders

    buf.seek(0)
    img = Image.open(buf).convert("RGB").resize(
        (target_size, target_size), Image.LANCZOS
    )

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def compute_bbox_normalized(
    df: pd.DataFrame,
    mother_idx_in_window: int,
    confirmation_idx_in_window: int,
    style: RenderStyle,
    target_size: int = _DEFAULT_TARGET_SIZE,
) -> Tuple[float, float, float, float]:
    """Compute YOLO-format normalised bbox (cx, cy, w, h) for the 5-bar cluster.

    Approach A (deterministic, RESEARCH §Code Examples planner note):
        Re-render with returnfig=True to get the axes; query
        ax.transData.transform for the four corners; map the rendered
        axes pixel rect to the post-resize target_size x target_size frame;
        return YOLO normalised (cx, cy, w, h) all in 0..1.

    Geometry (D-02):
        x0 = left edge of bar at mother_idx_in_window
        x1 = right edge of bar at confirmation_idx_in_window
        y0 = min(Low) over the 5 bars (mother..confirmation)
        y1 = max(High) over the 5 bars

    mplfinance places candles at integer x positions 0..N-1 in DATA coordinates;
    each bar at index i spans [i - candle_width/2, i + candle_width/2] in DATA x.

    Returns:
        (cx, cy, w, h) all in 0..1.

    Raises:
        ValueError: if df is invalid, indices are out of range, or the resulting
            bbox falls outside the [0, 1] normalised frame.
    """
    _validate_frame(df)
    if not (0 <= mother_idx_in_window < confirmation_idx_in_window < _BAR_COUNT):
        raise ValueError(
            f"invalid indices: mother={mother_idx_in_window}, "
            f"confirmation={confirmation_idx_in_window}; require "
            f"0 <= mother < confirmation < {_BAR_COUNT}"
        )

    mpf_style = _make_mpf_style(style)

    # returnfig=True hands back the figure + axes so we can read transData.
    fig, axes = mpf.plot(
        df,
        type="candle",
        style=mpf_style,
        figsize=style.figsize,
        update_width_config={"candle_width": style.candle_width},
        axisoff=True,
        returnfig=True,
    )
    ax = axes[0]

    # Force a draw so transData reflects final axes limits.
    fig.canvas.draw()

    cluster = df.iloc[mother_idx_in_window:confirmation_idx_in_window + 1]
    x0_data = mother_idx_in_window - style.candle_width / 2
    x1_data = confirmation_idx_in_window + style.candle_width / 2
    y0_data = float(cluster["Low"].min())
    y1_data = float(cluster["High"].max())

    # Display coords have origin at lower-left; PNG/PIL coords have origin at
    # upper-left, so the y direction inverts.
    px0, py_lo = ax.transData.transform((x0_data, y0_data))
    px1, py_hi = ax.transData.transform((x1_data, y1_data))

    fig_w_px, fig_h_px = fig.canvas.get_width_height()
    plt.close(fig)

    # Scale display pixel coords into the post-resize target_size frame.
    scale_x = target_size / float(fig_w_px)
    scale_y = target_size / float(fig_h_px)

    sx0 = px0 * scale_x
    sx1 = px1 * scale_x
    # Flip y: matplotlib display y is from bottom, image y is from top.
    sy_top = (fig_h_px - py_hi) * scale_y
    sy_bot = (fig_h_px - py_lo) * scale_y

    # Clamp to image bounds.
    sx0 = max(0.0, min(float(target_size), sx0))
    sx1 = max(0.0, min(float(target_size), sx1))
    sy_top = max(0.0, min(float(target_size), sy_top))
    sy_bot = max(0.0, min(float(target_size), sy_bot))

    cx = float(((sx0 + sx1) / 2.0) / target_size)
    cy = float(((sy_top + sy_bot) / 2.0) / target_size)
    w = float((sx1 - sx0) / target_size)
    h = float((sy_bot - sy_top) / target_size)

    for label, value in (("cx", cx), ("cy", cy), ("w", w), ("h", h)):
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"bbox component {label}={value} outside [0, 1]")

    return (cx, cy, w, h)


# ── CLI helpers ─────────────────────────────────────────────────────────────
def main(argv) -> int:
    """CLI entry: render(<csv>, <style_name>, <out_png>). Returns exit code."""
    if len(argv) < 4:
        print(
            "Usage: python scripts/pattern_scanner/renderer.py "
            "<CSV_PATH> <STYLE_NAME> <OUT_PNG>",
            file=sys.stderr,
        )
        return 1
    csv_path, style_name, out_png = argv[1], argv[2], argv[3]
    df = pd.read_csv(csv_path, parse_dates=[0], index_col=0)
    try:
        style = next(s for s in STYLES if s.name == style_name)
    except StopIteration:
        print(f"Unknown style: {style_name!r}", file=sys.stderr)
        return 2
    Path(out_png).write_bytes(render(df, style))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
