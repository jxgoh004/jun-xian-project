"""Phase 10 D-15 / PIPE-03: stale-PNG cleanup + publication-render determinism.

RED (Wave 0): imports from `scripts.pattern_scanner.run_pipeline` which does
not yet exist. Plan 10-04 will land `_cleanup_stale_pngs` (top-level import,
collection-safe). Plan 10-06 will land `_render_publication_chart` (lazy-
imported inside the render-test function bodies so collection still succeeds
between 10-04 and 10-06).

Revision BLOCKER #2 import structure:
  - Top level: only `_cleanup_stale_pngs` (defined by Plan 10-04).
  - Inside render-test bodies: `_render_publication_chart` (Plan 10-06).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

# TOP-LEVEL: defined by Plan 10-04. After 10-04 lands, collection succeeds.
from scripts.pattern_scanner.run_pipeline import _cleanup_stale_pngs  # noqa: E402


@dataclass(frozen=True)
class FakeDet:
    """Minimal Detection stand-in for `_render_publication_chart`.

    Uses indices 55 / 59 inside a 60-bar window — the only viable indices
    given renderer._validate_frame's hard requirement `len(df) == 60`
    (PATTERNS L283).
    """

    ticker: str = "TEST"
    confirmation_date: str = "2024-04-01"
    confirmation_type: str = "pin"
    is_spring: bool = True
    mother_bar_index: int = 55
    confirmation_bar_index: int = 59
    bars: list = field(
        default_factory=lambda: [
            {"low": 100.0, "high": 105.0, "open": 102.0, "close": 103.0, "date": "2024-03-25"}
        ]
        * 5
    )


def test_stale_png_cleanup_keeps_current_drops_old(tmp_path):
    """D-15: set-difference cleanup. PNGs in `expected_filenames` survive;
    everything else in the charts directory is deleted. The return value is
    the count of deleted files (1 here).

    Uses `_cleanup_stale_pngs` (top-level import) — GREEN after Plan 10-04.
    """
    charts = tmp_path / "charts"
    charts.mkdir()
    (charts / "AAPL_2024-01-01.png").write_bytes(b"\x89PNG_stub_aapl")
    (charts / "MSFT_2024-01-01.png").write_bytes(b"\x89PNG_stub_msft")
    (charts / "STALE_2023-01-01.png").write_bytes(b"\x89PNG_stub_stale")

    deleted = _cleanup_stale_pngs(
        charts, {"AAPL_2024-01-01.png", "MSFT_2024-01-01.png"}
    )

    assert deleted == 1
    assert (charts / "AAPL_2024-01-01.png").exists()
    assert (charts / "MSFT_2024-01-01.png").exists()
    assert not (charts / "STALE_2023-01-01.png").exists()


def test_render_writes_png(tmp_path, synthetic_ohlc):
    """PIPE-03: `_render_publication_chart` writes a non-trivial PNG.

    LAZY-IMPORT (revision BLOCKER #2): `_render_publication_chart` is defined
    by Plan 10-06. The import lives inside the function body so module
    collection succeeds after Plan 10-04 (when `_cleanup_stale_pngs` exists)
    even if the render symbol does not yet.
    """
    from scripts.pattern_scanner.run_pipeline import _render_publication_chart

    # renderer._validate_frame requires exactly 60 bars (PATTERNS L283).
    rows = [(100.0 + i, 105.0 + i, 99.0 + i, 102.0 + i) for i in range(60)]
    df = synthetic_ohlc(rows)
    out = tmp_path / "out.png"

    _render_publication_chart(df, FakeDet(), out)

    assert out.exists()
    assert out.stat().st_size > 1000
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_publication_render_is_deterministic(tmp_path, synthetic_ohlc):
    """D-15 prerequisite: same input -> byte-identical PNG.

    Determinism is what makes set-difference cleanup commit-friendly:
    PNGs that recur night-to-night are byte-equal, so git sees no change
    for them. Only churned files (new detections + aged-out detections)
    appear in the diff.

    LAZY-IMPORT (revision BLOCKER #2) — see test_render_writes_png.
    """
    from scripts.pattern_scanner.run_pipeline import _render_publication_chart

    rows = [(100.0 + i, 105.0 + i, 99.0 + i, 102.0 + i) for i in range(60)]
    df = synthetic_ohlc(rows)
    p1 = tmp_path / "run1.png"
    p2 = tmp_path / "run2.png"

    _render_publication_chart(df, FakeDet(), p1)
    _render_publication_chart(df, FakeDet(), p2)

    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2
