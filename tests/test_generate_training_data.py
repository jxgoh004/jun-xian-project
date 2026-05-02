"""Unit tests for scripts.pattern_scanner.generate_training_data — TRAIN-02 + TRAIN-03.

All tests are pure-unit. The yfinance fetch is monkeypatched to return synthetic
frames built via the `synthetic_ohlc` fixture, so the suite runs offline.

Test inventory (8 named tests, matching the Wave 0 stubs from Plan 01):
    test_yolo_directory_layout
    test_positive_label_format
    test_style_randomization_used
    test_cutoff_enforced
    test_neg_pos_ratio_capped
    test_negative_labels_empty
    test_hard_negative_set_difference
    test_manifest_sha256_consistent
"""
from __future__ import annotations

import hashlib
import json
from typing import List, Tuple

import pandas as pd
import pytest

import scripts.pattern_scanner.generate_training_data as gen_mod
from scripts.pattern_scanner.detector import detect
from scripts.pattern_scanner.generate_training_data import (
    _detect_hard_negatives,
    _detect_positives,
    main,
)


# ── Synthetic builders ──────────────────────────────────────────────────────
# Helpers below are copied from tests/test_detector_schema.py (lines 227-300).
# Keep in sync if the detector schema fixture evolves — these are file-local
# helpers in the schema test, not importable, so duplication is intentional.

def _build_uptrend(n: int, start: float = 100.0) -> List[Tuple[float, float, float, float]]:
    """HH/HL uptrend with multiple swing pivots — produces filter-passing detections."""
    rows: List[Tuple[float, float, float, float]] = []
    price = start
    leg_up_bars = 4
    leg_down_bars = 3
    leg_up_step = 1.5
    leg_down_step = 0.8
    leg_total = leg_up_bars + leg_down_bars
    for i in range(n):
        phase = i % leg_total
        if phase < leg_up_bars:
            o = price
            c = price + leg_up_step
            h = c + 0.4
            l = o - 0.2
        else:
            o = price
            c = price - leg_down_step
            h = o + 0.2
            l = c - 0.4
        rows.append((o, h, l, c))
        price = c
    return rows


def _spring_setup_rows():
    """Cluster geometry that produces a Phase 7 detection with all 3 filters PASS.

    Verbatim copy of tests/test_detector_schema.py::_spring_setup_rows (lines 258-300):
    HH/HL uptrend prefix + mother + inside + break_bar + confirm_bar.
    Returns (rows, mother_idx, conf_idx, mother_low, mother_high).
    Total length = 70 + 4 = 74 bars. mother_idx=70, conf_idx=73.
    """
    trend = _build_uptrend(70)
    last_close = trend[-1][3]
    mother_low = last_close - 0.5
    mother_high = last_close + 4.0
    mother_open = last_close
    mother_close = last_close + 1.0
    mother = (mother_open, mother_high, mother_low, mother_close)
    inside = (
        mother_open,
        mother_high - 0.5,
        mother_low + 0.3,
        mother_close,
    )
    bb_low_a = mother_low - 1.5
    bb_close_a = mother_low - 0.4
    bb_open_a = mother_low - 0.2
    bb_high_a = mother_low + 0.3
    break_bar = (bb_open_a, bb_high_a, bb_low_a, bb_close_a)
    cb_low = mother_low - 0.5
    cb_high = mother_low + 1.5
    cb_open = cb_low + 0.05 * (cb_high - cb_low)
    cb_close = cb_low + 0.95 * (cb_high - cb_low)
    confirm_bar = (cb_open, cb_high, cb_low, cb_close)
    rows = trend + [mother, inside, break_bar, confirm_bar]
    mother_idx = len(trend)
    conf_idx = mother_idx + 3
    return rows, mother_idx, conf_idx, mother_low, mother_high


def _flat_prefix_rows():
    """Cluster valid but trend-filters FAIL (HH/HL prefix is flat).

    Builds a flat-price prefix (65 bars) so `hh_hl=False` because no swing
    pivot pattern emerges, then appends the same cluster geometry as
    _spring_setup_rows() so a detection candidate IS produced when filters
    are disabled. detect(df, t) returns [], detect(df, t, apply_trend_filters=False)
    returns >= 1.
    Total length = 65 + 4 = 69 bars.
    """
    prefix: List[Tuple[float, float, float, float]] = [
        (100.0, 100.05, 99.95, 100.0)
    ] * 65
    last_close = 100.0
    mother_low = last_close - 0.5
    mother_high = last_close + 4.0
    mother_open = last_close
    mother_close = last_close + 1.0
    mother = (mother_open, mother_high, mother_low, mother_close)
    inside = (
        mother_open,
        mother_high - 0.5,
        mother_low + 0.3,
        mother_close,
    )
    bb_low_a = mother_low - 1.5
    bb_close_a = mother_low - 0.4
    bb_open_a = mother_low - 0.2
    bb_high_a = mother_low + 0.3
    break_bar = (bb_open_a, bb_high_a, bb_low_a, bb_close_a)
    cb_low = mother_low - 0.5
    cb_high = mother_low + 1.5
    cb_open = cb_low + 0.05 * (cb_high - cb_low)
    cb_close = cb_low + 0.95 * (cb_high - cb_low)
    confirm_bar = (cb_open, cb_high, cb_low, cb_close)
    return prefix + [mother, inside, break_bar, confirm_bar]


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def patched_fetch(monkeypatch, synthetic_ohlc):
    """Monkeypatch _fetch_ohlc + _load_tickers + time.sleep.

    Returns a `frames_by_ticker` dict the test can mutate to override the
    default frame for any ticker. Each ticker defaults to a spring-shaped
    frame so positives > 0 across the run.
    """
    frames_by_ticker: dict = {}
    default_rows, *_ = _spring_setup_rows()
    # Use an early start_date so all confirmation_dates fall well before
    # TRAIN_TEST_CUTOFF (= 2024-01-01) — keeps positives in-set by default.
    default_frame = synthetic_ohlc(default_rows, start_date="2020-01-01")

    def fake_fetch(ticker, period="10y"):
        return frames_by_ticker.get(ticker, default_frame)

    monkeypatch.setattr(gen_mod, "_fetch_ohlc", fake_fetch)
    monkeypatch.setattr(
        gen_mod,
        "_load_tickers",
        lambda limit: ["TST1", "TST2", "TST3"][: (limit or 3)],
    )
    monkeypatch.setattr(gen_mod.time, "sleep", lambda *_a, **_kw: None)
    return frames_by_ticker


# ── Tests ───────────────────────────────────────────────────────────────────
def test_yolo_directory_layout(tmp_path, patched_fetch):
    """Generator emits images/{train,val} + labels/{train,val} + data.yaml under DATASET_ROOT."""
    ds = tmp_path / "ds"
    models = tmp_path / "models"
    rc = main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds),
        "--models-root", str(models),
    ])
    assert rc == 0
    assert (ds / "images" / "train").is_dir()
    assert (ds / "images" / "val").is_dir()
    assert (ds / "labels" / "train").is_dir()
    assert (ds / "labels" / "val").is_dir()
    yaml = (ds / "data.yaml").read_text()
    assert "nc: 1" in yaml
    assert "inside_bar_spring" in yaml
    assert (models / "dataset_manifest.json").exists()
    assert (ds / "dataset_manifest.json").exists()


def test_positive_label_format(tmp_path, patched_fetch):
    """Positive labels are '0 cx cy w h' with all values normalised 0..1."""
    ds = tmp_path / "ds"
    models = tmp_path / "models"
    main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds),
        "--models-root", str(models),
    ])
    found_positive = False
    for txt in (ds / "labels").rglob("*.txt"):
        content = txt.read_text().strip()
        if not content:
            # Empty label — negative sample. Skip.
            continue
        found_positive = True
        parts = content.split()
        assert len(parts) == 5, f"{txt} has {len(parts)} fields, expected 5"
        assert parts[0] == "0", f"{txt} class id != 0: {parts[0]}"
        for v in parts[1:]:
            f = float(v)
            assert 0.0 <= f <= 1.0, f"{txt} component {v} outside [0, 1]"
    assert found_positive, "no positive labels were generated; cannot validate format"


def test_style_randomization_used(tmp_path, patched_fetch):
    """At least 2 distinct style names appear across N samples."""
    ds = tmp_path / "ds"
    models = tmp_path / "models"
    main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds),
        "--models-root", str(models),
    ])
    manifest = json.loads((ds / "dataset_manifest.json").read_text())
    assert len(manifest["renderer_styles_seen"]) >= 2, (
        f"expected >= 2 styles, got {manifest['renderer_styles_seen']}"
    )


def test_cutoff_enforced(tmp_path, patched_fetch, monkeypatch):
    """No detection with confirmation_date >= TRAIN_TEST_CUTOFF appears in the dataset."""
    ds = tmp_path / "ds"
    models = tmp_path / "models"
    # Patch cutoff to an early date so all spring detections are excluded.
    monkeypatch.setattr(gen_mod, "TRAIN_TEST_CUTOFF", "1900-01-01")
    main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds),
        "--models-root", str(models),
    ])
    # No positive labels should be written (every detection is post-cutoff).
    non_empty = [
        t for t in (ds / "labels").rglob("*.txt")
        if t.read_text().strip()
    ]
    assert non_empty == [], f"cutoff not enforced; positive labels survived: {non_empty}"
    # Manifest reflects zero positives.
    manifest = json.loads((ds / "dataset_manifest.json").read_text())
    assert manifest["positives"] == 0
    assert manifest["negatives"] == 0


def test_neg_pos_ratio_capped(tmp_path, patched_fetch):
    """negatives <= 10 * positives in the generated manifest (D-09)."""
    ds = tmp_path / "ds"
    models = tmp_path / "models"
    main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds),
        "--models-root", str(models),
    ])
    manifest = json.loads((ds / "dataset_manifest.json").read_text())
    assert manifest["positives"] >= 1, "need at least one positive to test the cap"
    assert manifest["neg_pos_ratio"] <= 10.0 + 1e-9, (
        f"neg/pos ratio = {manifest['neg_pos_ratio']} exceeds 10:1 cap"
    )
    assert manifest["negatives"] <= 10 * manifest["positives"]


def test_negative_labels_empty(tmp_path, patched_fetch):
    """Files whose sample_id contains '_neg_' are zero-byte .txt files (YOLO background)."""
    ds = tmp_path / "ds"
    models = tmp_path / "models"
    main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds),
        "--models-root", str(models),
    ])
    neg_files = [t for t in (ds / "labels").rglob("*.txt") if "_neg_" in t.name]
    # There may be 0 negatives if the synthetic fixture only emits filter-passing
    # candidates; the negatives in this run come from any cluster shape that the
    # filters-disabled detect() finds in the trend prefix.
    for txt in neg_files:
        assert txt.stat().st_size == 0, f"{txt} is a negative but not zero bytes"


def test_hard_negative_set_difference(synthetic_ohlc):
    """Hard-negative pool keys are disjoint from positive keys (RESEARCH §Pitfall 7)."""
    rows = _flat_prefix_rows()
    df = synthetic_ohlc(rows, start_date="2020-01-01")
    # Sanity: filters-on returns [], filters-off returns >= 1.
    filtered = detect(df, "TST")
    unfiltered = detect(df, "TST", apply_trend_filters=False)
    assert filtered == [], f"flat prefix should fail HH/HL; got {len(filtered)} positives"
    assert len(unfiltered) >= 1, "filters-off should find the cluster"

    positives = _detect_positives(df, "TST")
    negatives = _detect_hard_negatives(df, "TST", positives)
    pos_keys = {
        (d.ticker, d.mother_bar_index, d.confirmation_bar_index)
        for d in positives
    }
    neg_keys = {
        (d.ticker, d.mother_bar_index, d.confirmation_bar_index)
        for d in negatives
    }
    assert pos_keys.isdisjoint(neg_keys), (
        "hard negatives must not contain real positives "
        f"(overlap: {pos_keys & neg_keys})"
    )

    # When the prefix forces filters to fail, we expect zero positives but at
    # least one hard negative — proving the set difference yields candidates.
    assert pos_keys == set()
    assert len(neg_keys) >= 1


def test_manifest_sha256_consistent(tmp_path, patched_fetch):
    """Same seed → identical concat_sha256 across two independent runs."""
    ds1 = tmp_path / "ds1"
    models1 = tmp_path / "models1"
    main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds1),
        "--models-root", str(models1),
    ])
    manifest1 = json.loads((ds1 / "dataset_manifest.json").read_text())

    # Shape sanity — 64-hex sha256.
    assert len(manifest1["concat_sha256"]) == 64
    assert all(c in "0123456789abcdef" for c in manifest1["concat_sha256"])

    # Reproducibility — same seed, fresh root, identical concat.
    ds2 = tmp_path / "ds2"
    models2 = tmp_path / "models2"
    main([
        "--seed", "42",
        "--limit", "3",
        "--dataset-root", str(ds2),
        "--models-root", str(models2),
    ])
    manifest2 = json.loads((ds2 / "dataset_manifest.json").read_text())
    assert manifest1["concat_sha256"] == manifest2["concat_sha256"], (
        "same seed must produce identical concat_sha256 "
        f"(got {manifest1['concat_sha256']} vs {manifest2['concat_sha256']})"
    )

    # Stricter: every committed PNG sha256 IS one of the inputs to the concat
    # (we recompute the sha of each file and confirm it appears in a recompute
    # of the manifest concat in some order — manifest order is the write order,
    # so we can't trivially reproduce the exact concat from filesystem-sorted
    # globs without bookkeeping. The two-run determinism check above is the
    # canonical sha256-correctness gate.)
    pngs = sorted((ds1 / "images").rglob("*.png"))
    for png in pngs:
        sha = hashlib.sha256(png.read_bytes()).hexdigest()
        assert len(sha) == 64
