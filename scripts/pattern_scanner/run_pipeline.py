"""Inside-bar-spring batch pipeline (Phase 10).

Pure-function core + thin CLI wrapper. Mirrors scripts.pattern_scanner.backtest
structurally; reuses Phase 9 inference symbols verbatim via import + re-export so
tests can monkeypatch them on `run_pipeline_mod` directly.

See .planning/phases/10-batch-pipeline/10-CONTEXT.md for D-01..D-24.

CLI:
    python -m scripts.pattern_scanner.run_pipeline \
        --tickers all --window-days 20 --out-dir docs/projects/patterns

main() body lives in Plan 10-06; this module currently exposes the helpers
and the CLI scaffolding.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.tseries.offsets import BDay

# ── Re-exports from Phase 9 (D-06 single inference session + D-08 fallback) ──
# Imported here so tests can monkeypatch on this module's namespace.
from scripts.pattern_scanner.backtest import (  # noqa: F401  (re-exports)
    ONNX_PATH,
    RATE_LIMIT_SLEEP,
    _load_onnx_session,
    _parse_tickers_arg,
    _score_detection,
    _stop_for,
    _target_for,
    _validate_ticker_token,
    _window_for,
    simulate_trade,
)
from scripts.pattern_scanner.detector import Detection, _TICKER_RE, detect  # noqa: F401
from scripts.fetch_sp500 import fetch_sp500_tickers  # noqa: F401

DEFAULT_OUT_DIR = Path("docs/projects/patterns")
DEFAULT_WINDOW_DAYS = 20
ERRORS_TRUNCATE_CAP = 50  # D-16 Claude's discretion / RESEARCH recommendation


# ── Test seam ───────────────────────────────────────────────────────────────
def _fetch_ohlc(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch daily OHLC via yfinance with auto_adjust=True. Lazy import for testability.

    Mirrors backtest._fetch_ohlc / detector._fetch_ohlc byte-for-byte except for the
    default period (D-03: ~90 bars covers 60-bar detection window + 20-bar resolution
    coverage + safety buffer).
    """
    import yfinance as yf  # noqa: WPS433 — deferred by design (test seam)

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


# ── D-01: 20-trading-day window cutoff ──────────────────────────────────────
def _window_cutoff(today: pd.Timestamp, window_days: int) -> pd.Timestamp:
    """Compute the cutoff timestamp: detections with confirmation_date < cutoff are dropped.

    Uses pandas business-day offsets (BDay). Saturday/Sunday `today` is rolled back to
    the previous business day before subtracting window_days. Does NOT account for US
    market holidays — within resolution-coverage buffer (RESEARCH §A6).
    """
    return today - BDay(window_days)


# ── D-02: pending pre-check wrapper for simulate_trade ──────────────────────
def _resolve_status(df: pd.DataFrame, detection) -> dict:
    """Wrap simulate_trade with a `pending` pre-check (D-02).

    Phase 9's contract returns exit_reason ∈ {stop, target, open}. Phase 10 adds a
    fourth state `pending`: the entry bar (confirmation_bar_index + 1) has not yet
    opened on the live OHLC frame. Phase 9's simulate_trade is NOT modified.

    Returns a dict matching the data.json `detections[]` schema — `exit_reason` is
    renamed to `status` so the public API carries one field with four possible values.
    """
    entry_idx = detection.confirmation_bar_index + 1
    stop_price = _stop_for(detection)
    if entry_idx >= len(df):
        # PENDING: entry has not happened yet (today IS the confirmation day, or
        # there is no next bar in the fetched slice yet). Compute a "would-be"
        # target_price from the last close so the frontend can preview the setup.
        last_close = float(df.iloc[-1]["Close"])
        target_price = _target_for(last_close, stop_price)
        return {
            "ticker": str(detection.ticker),
            "confirmation_date": str(detection.confirmation_date),
            "confirmation_type": str(detection.confirmation_type),
            "is_spring": bool(detection.is_spring),
            "status": "pending",
            "entry_date": None,
            "entry_price": None,
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "risk": None,
            "exit_date": None,
            "exit_price": None,
            "hold_days": None,
            "R": None,
        }

    # Entry is possible — delegate to Phase 9 simulate_trade.
    entry_open = float(df.iloc[entry_idx]["Open"])
    target_price = _target_for(entry_open, stop_price)
    rec = simulate_trade(df, detection, stop_price, target_price)
    # Public Phase 10 contract: status replaces exit_reason (D-02).
    rec["status"] = rec.pop("exit_reason")
    return rec


# ── D-17: atomic JSON write (temp + fsync + os.replace) ─────────────────────
def _atomic_write_json(path: Path, obj: dict) -> None:
    """Write JSON atomically. A reader sees either the previous file or the complete
    new file, never a partial write.

    Pitfall 1 (RESEARCH L474-482): tmp MUST be a sibling of the final path so
    os.replace operates within one filesystem (atomic). Cross-FS replace silently
    falls back to copy+unlink — NOT atomic.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())  # durability hygiene (not load-bearing for atomicity)
    os.replace(tmp, path)


# ── D-15: stale-PNG cleanup via set difference ──────────────────────────────
def _cleanup_stale_pngs(charts_dir: Path, expected_filenames: set[str]) -> int:
    """Delete PNG files in charts_dir whose basename is NOT in expected_filenames.

    D-15 set-difference idiom — preserves byte-identical recurring PNGs so git sees
    no change for unchanged detections. NOT `rm -rf` (which would force every PNG
    to be regenerated and committed).

    Returns the count of files deleted. Creates charts_dir if it does not exist
    (returns 0 in that case).
    """
    charts_dir.mkdir(parents=True, exist_ok=True)
    deleted = 0
    for f in charts_dir.iterdir():
        if f.is_file() and f.name not in expected_filenames:
            f.unlink()
            deleted += 1
    return deleted


# ── CLI scaffolding (D-20) ──────────────────────────────────────────────────
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Nightly batch pipeline: detect + ONNX-score + render across S&P 500.",
    )
    p.add_argument(
        "--tickers", type=_parse_tickers_arg, default="all",
        help="'all' for full S&P 500, or comma-separated tokens validated against _TICKER_RE.",
    )
    p.add_argument(
        "--limit", type=int, default=None,
        help="Process only the first N tickers (smoke-test).",
    )
    p.add_argument(
        "--window-days", type=int, default=DEFAULT_WINDOW_DAYS,
        help=f"Trading-day window for 'current detection' (D-01, default {DEFAULT_WINDOW_DAYS}).",
    )
    p.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT_DIR,
        help="Output dir for data.json, stats.json, charts/ (default %(default)s).",
    )
    p.add_argument(
        "--no-onnx", action="store_true",
        help="Force-skip ONNX scoring (D-08 graceful fallback); yolo_conf will be null on every row.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    raise NotImplementedError("main() body lands in Plan 10-06 (orchestrator wave).")


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
