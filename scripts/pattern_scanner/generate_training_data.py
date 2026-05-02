"""Offline-only training data generator (CONTEXT D-20).

Outputs (under _dev/training_dataset/, gitignored per CONTEXT D-14):
    images/{train,val}/<sample_id>.png
    labels/{train,val}/<sample_id>.txt   (positive: "0 cx cy w h"; negative: empty)
    data.yaml                             (YOLOv8 dataset config)
    dataset_manifest.json                 (gitignored copy)

Also writes:
    models/dataset_manifest.json          (committed copy per CONTEXT D-15)

Public API:
    main(argv) -> int                     CLI entry
    _fetch_ohlc(ticker, period="10y") -> pd.DataFrame   (monkeypatchable for tests)

Domain logic:
    Positives = detect(df, ticker)              (filtered, Phase 7 default)
    Hard negatives = detect(df, ticker, apply_trend_filters=False)
                       MINUS positives, keyed on
                       (ticker, mother_bar_index, confirmation_bar_index)
                       (CONTEXT D-10 + RESEARCH §Pitfall 7)
    Both sets exclude detections with confirmation_date >= TRAIN_TEST_CUTOFF.
    Negatives are globally capped at 10:1 vs positives (CONTEXT D-09).
    If positives < MIN_POSITIVES (D-08), multi-style augmentation re-emits
    each positive across STYLES until the floor is met.

CLI:
    python scripts/pattern_scanner/generate_training_data.py --seed 42
    python scripts/pattern_scanner/generate_training_data.py --seed 42 --limit 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

# Add project root to sys.path so this script resolves siblings when invoked directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.pattern_scanner.detector import Detection, detect  # noqa: E402
from scripts.pattern_scanner.renderer import (  # noqa: E402
    STYLES,
    RenderStyle,
    compute_bbox_normalized,
    render,
)
from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF  # noqa: E402

# ── Module constants ────────────────────────────────────────────────────────
DATASET_ROOT = Path("_dev/training_dataset")
MODELS_ROOT = Path("models")
MIN_POSITIVES = 1000        # D-08
NEG_POS_RATIO = 10          # D-09
VAL_FRACTION = 0.20         # D-18 (random 80/20)
RATE_LIMIT_SLEEP = 0.5      # match scripts/fetch_sp500.py cadence
WINDOW_SIZE = 60            # D-01 / parity with detector._LOOKBACK


# ── Public helpers (test seam) ──────────────────────────────────────────────
def _fetch_ohlc(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Fetch daily OHLC via yfinance. Monkeypatched in tests.

    Mirrors `scripts.pattern_scanner.detector._fetch_ohlc` byte-for-byte so the
    train and inference paths consume identically-shaped frames.
    """
    import yfinance as yf  # noqa: WPS433 — deferred by design

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def _load_tickers(limit) -> List[str]:
    """Load S&P 500 ticker list via scripts.fetch_sp500.fetch_sp500_tickers().

    `limit` may be an int (truncate) or None (full list). Monkeypatched in tests.
    """
    from scripts.fetch_sp500 import fetch_sp500_tickers
    tickers = fetch_sp500_tickers()
    if limit:
        tickers = tickers[:limit]
    return tickers


# ── Domain logic ────────────────────────────────────────────────────────────
def _detect_positives(df: pd.DataFrame, ticker: str) -> List[Detection]:
    """Run filtered detector; drop detections at or after TRAIN_TEST_CUTOFF."""
    cutoff = pd.Timestamp(TRAIN_TEST_CUTOFF)
    return [
        d for d in detect(df, ticker)
        if pd.Timestamp(d.confirmation_date) < cutoff
    ]


def _detect_hard_negatives(df: pd.DataFrame, ticker: str,
                            positives: List[Detection]) -> List[Detection]:
    """Hard-negative pool = (filters-disabled detect) MINUS real positives.

    Keyed on (ticker, mother_bar_index, confirmation_bar_index) per
    RESEARCH §Pitfall 7. Also drops candidates at or after TRAIN_TEST_CUTOFF.
    """
    cutoff = pd.Timestamp(TRAIN_TEST_CUTOFF)
    all_candidates = detect(df, ticker, apply_trend_filters=False)
    positive_keys = {
        (d.ticker, d.mother_bar_index, d.confirmation_bar_index)
        for d in positives
    }
    return [
        c for c in all_candidates
        if (c.ticker, c.mother_bar_index, c.confirmation_bar_index) not in positive_keys
        and pd.Timestamp(c.confirmation_date) < cutoff
    ]


def _slice_window(df: pd.DataFrame, conf_idx: int) -> pd.DataFrame | None:
    """60-bar window ending AT confirmation bar (D-03 right-aligned).

    Returns None if the confirmation index has insufficient leading history.
    """
    start = conf_idx - (WINDOW_SIZE - 1)
    if start < 0:
        return None
    return df.iloc[start:conf_idx + 1]


# ── File I/O ────────────────────────────────────────────────────────────────
def _write_sample(png_bytes: bytes, label_line, dataset_root: Path,
                  split: str, sample_id: str) -> str:
    """Write image + label files. Returns sha256 of the PNG."""
    img_path = dataset_root / "images" / split / f"{sample_id}.png"
    lbl_path = dataset_root / "labels" / split / f"{sample_id}.txt"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    lbl_path.parent.mkdir(parents=True, exist_ok=True)
    img_path.write_bytes(png_bytes)
    lbl_path.write_text(label_line if label_line is not None else "")
    return hashlib.sha256(png_bytes).hexdigest()


def _write_data_yaml(dataset_root: Path) -> None:
    """Emit YOLOv8 dataset config (single class: inside_bar_spring)."""
    text = (
        f"path: {dataset_root.resolve()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "nc: 1\n"
        "names:\n"
        "  0: inside_bar_spring\n"
    )
    (dataset_root / "data.yaml").write_text(text)


# ── Sample materialisation ──────────────────────────────────────────────────
def _augment_to_floor(positives: list, floor: int) -> list:
    """Multi-style augmentation when positives < floor (D-08).

    Each input record is (ticker, df, det). On output, each record is
    (ticker, df, det, style) with the same (ticker, det) cycled across STYLES
    in deterministic round-robin order.
    """
    if len(positives) >= floor or not positives:
        return positives
    styles = list(STYLES)
    out = []
    idx = 0
    while len(out) < floor:
        base = positives[idx % len(positives)]
        style = styles[idx % len(styles)]
        out.append((*base, style))
        idx += 1
    return out


# ── Orchestration ───────────────────────────────────────────────────────────
def main(argv=None) -> int:
    """CLI entry. Returns 0 on success."""
    p = argparse.ArgumentParser(
        description="Generate YOLOv8 training dataset from algorithmic detections."
    )
    p.add_argument("--seed", type=int, required=True,
                   help="Deterministic seed for style choice + train/val + neg subsample.")
    p.add_argument("--limit", type=int, default=None,
                   help="Process only the first N tickers (testing).")
    p.add_argument("--dataset-root", type=Path, default=DATASET_ROOT,
                   help="Where to write images/, labels/, data.yaml, manifest.")
    p.add_argument("--models-root", type=Path, default=MODELS_ROOT,
                   help="Where to write the committed dataset_manifest.json copy.")
    args = p.parse_args(argv)

    rng = random.Random(args.seed)
    # np_rng reserved for future numpy-random use; keep seeded for parity.
    _ = np.random.default_rng(args.seed)

    tickers = _load_tickers(args.limit)
    total = len(tickers)

    positives_all: list = []  # each: (ticker, df, det)
    negatives_all: list = []

    for i, t in enumerate(tickers, start=1):
        try:
            df = _fetch_ohlc(t)
            if len(df) < WINDOW_SIZE:
                print(f"[{i}/{total}] {t}: insufficient history ({len(df)} bars) — skip")
                continue
            pos = _detect_positives(df, t)
            neg = _detect_hard_negatives(df, t, pos)
            for d in pos:
                positives_all.append((t, df, d))
            for d in neg:
                negatives_all.append((t, df, d))
            print(f"[{i}/{total}] {t}: pos={len(pos)} neg={len(neg)}")
        except Exception as exc:  # broad except — match fetch_sp500.py pattern
            print(f"[{i}/{total}] {t}: unexpected error — {exc}")
        if i < total:
            time.sleep(RATE_LIMIT_SLEEP)

    print(f"[summary] raw positives={len(positives_all)} raw negatives={len(negatives_all)}")

    # 1000-positive gate (D-08)
    if len(positives_all) < MIN_POSITIVES:
        print(f"[gate] positives < {MIN_POSITIVES} — applying multi-style augmentation")
        positives_all = _augment_to_floor(positives_all, MIN_POSITIVES)
    else:
        # Tag each positive with a single rng-chosen style so the write loop is uniform.
        positives_all = [(*item, rng.choice(STYLES)) for item in positives_all]

    # Tag each negative with a single rng-chosen style.
    negatives_all = [(*item, rng.choice(STYLES)) for item in negatives_all]

    # Cap negatives at 10:1 (D-09)
    cap = NEG_POS_RATIO * len(positives_all)
    if len(negatives_all) > cap:
        rng.shuffle(negatives_all)
        negatives_all = negatives_all[:cap]

    # 80/20 train/val split (D-18)
    all_samples = (
        [("pos", item) for item in positives_all]
        + [("neg", item) for item in negatives_all]
    )
    rng.shuffle(all_samples)
    if len(all_samples) == 0:
        n_val = 0
    else:
        n_val = max(1, int(len(all_samples) * VAL_FRACTION))
    val, train = all_samples[:n_val], all_samples[n_val:]

    # Ensure dataset root + standard subdirs exist even if no samples produced.
    for split in ("train", "val"):
        (args.dataset_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (args.dataset_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    # Write samples + accumulate concat sha256.
    sha_concat = hashlib.sha256()
    styles_seen: set = set()
    written_positives = 0
    written_negatives = 0
    for split, items in (("train", train), ("val", val)):
        for kind, payload in items:
            ticker, df, det, style = payload
            window = _slice_window(df, det.confirmation_bar_index)
            if window is None:
                continue
            styles_seen.add(style.name)
            try:
                png = render(window, style)
            except Exception as exc:
                print(f"[render] {ticker} {det.confirmation_date} {kind}: {exc}")
                continue
            label_line = None
            if kind == "pos":
                # Translate absolute bar indices into in-window indices.
                # Window spans df.iloc[conf - 59 : conf + 1].
                window_start = det.confirmation_bar_index - (WINDOW_SIZE - 1)
                mother_in_window = det.mother_bar_index - window_start
                confirmation_in_window = WINDOW_SIZE - 1
                try:
                    cx, cy, w, h = compute_bbox_normalized(
                        window,
                        mother_idx_in_window=mother_in_window,
                        confirmation_idx_in_window=confirmation_in_window,
                        style=style,
                    )
                except Exception as exc:
                    print(f"[bbox] {ticker} {det.confirmation_date}: {exc}")
                    continue
                label_line = f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
            sample_id = (
                f"{ticker}_{det.confirmation_date}_{kind}_{style.name}_"
                f"{det.mother_bar_index}_{det.confirmation_bar_index}"
            )
            sha = _write_sample(png, label_line, args.dataset_root, split, sample_id)
            sha_concat.update(bytes.fromhex(sha))
            if kind == "pos":
                written_positives += 1
            else:
                written_negatives += 1

    _write_data_yaml(args.dataset_root)

    manifest = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": args.seed,
        "tickers": tickers,
        "date_range": {"period": "10y", "train_test_cutoff": TRAIN_TEST_CUTOFF},
        "positives": written_positives,
        "negatives": written_negatives,
        "neg_pos_ratio": (
            written_negatives / max(written_positives, 1)
        ),
        "renderer_styles_seen": sorted(styles_seen),
        "concat_sha256": sha_concat.hexdigest(),
    }
    args.dataset_root.mkdir(parents=True, exist_ok=True)
    (args.dataset_root / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    args.models_root.mkdir(parents=True, exist_ok=True)
    (args.models_root / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )
    print(f"[done] manifest written: {args.models_root / 'dataset_manifest.json'}")
    print(
        f"[done] positives={written_positives} negatives={written_negatives} "
        f"ratio={manifest['neg_pos_ratio']:.2f} "
        f"concat_sha256={manifest['concat_sha256'][:12]}..."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
