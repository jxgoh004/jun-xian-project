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


# ── PIPE-02: build_data_json — assemble the atomic-write payload ─────────────
def build_data_json(
    detections: list[dict],
    errors: list[dict],
    run_id: str,
    succeeded: int,
    failed: int,
    window_days: int,
) -> dict:
    """Pure: assemble the data.json payload per RESEARCH §Schema Designs L781-826.

    Phase boundary: this builder is pure — no I/O, no filesystem effects. The
    atomic write happens in Plan 10-06's main loop via
    `_atomic_write_json(out_dir / "data.json", data)`.

    D-02: each detection dict in `detections` already carries `status` (renamed
        from exit_reason in `_resolve_status`); no further transformation here.
    D-16: pipeline_status.completed = succeeded / max(succeeded+failed, 1) >= 0.95.
        The denominator guard avoids ZeroDivisionError on empty universes
        (e.g., `--tickers TEST` with no usable data — return True vacuously so
        the frontend doesn't show a "stale" banner on a single-ticker smoke).
    D-17: payload caller (Plan 10-06) writes this dict via _atomic_write_json.

    Args:
        detections: list of detection dicts (already shaped by Plan 10-06's loop
            with status, entry_*, stop_price, target_price, risk, exit_*, hold_days,
            R, yolo_conf, chart_path, current_price, company_name, sector, filters,
            bars, ticker, confirmation_date, confirmation_type, is_spring).
        errors: list of {ticker, stage, message, timestamp} dicts (already truncated
            to ERRORS_TRUNCATE_CAP by the caller per D-16 / Claude's Discretion).
        run_id: string from GITHUB_RUN_ID env var or uuid4() fallback.
        succeeded: count of tickers processed without exception.
        failed: count of tickers that raised.
        window_days: int, from CLI --window-days (D-01).

    Returns:
        dict matching the RESEARCH §Schema Designs L781-826 shape.
    """
    total = succeeded + failed
    success_rate = succeeded / max(total, 1)
    now_utc = datetime.now(timezone.utc)
    generated_at = now_utc.isoformat()
    as_of_date = pd.Timestamp.now(tz="UTC").normalize().strftime("%Y-%m-%d")

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "window_days": int(window_days),
        "as_of_date": as_of_date,
        "pipeline_status": {
            "completed": bool(success_rate >= 0.95),
            "succeeded_count": int(succeeded),
            "failed_count": int(failed),
            "errors": list(errors),
            "errors_truncated": 0,  # truncation, if any, happened in the caller
            "run_id": str(run_id),
            "generated_at": generated_at,
        },
        "detections": list(detections),
    }


# ── D-11: build_stats_json — project _backtest_aggregates.json for the frontend ──
_STATS_FALLBACK_ORDER = ["by_type_x_spring", "by_confirmation_type", "all"]
_STATS_N_FLOOR = 10
_STATS_RULE = {
    "stop": "min(bar.low for bar in detection.bars)",
    "target_R": 2.0,
    "intrabar": "pessimistic",
    "timeout": "none",
}
_STATS_SOURCE = "out_of_sample, strategy=1to2_rr_cluster_low_stop"


def _normalize_by_type_x_spring(raw: dict) -> dict:
    """Rename Phase 9 raw keys to D-11 frontend-ready keys.

    Phase 9 aggregate() builds keys as f"{ct}_{is_spring}" where is_spring
    Python-str-coerces a bool → "True" / "False". For example:
      - "pin_True"  → "pin_spring"
      - "pin_False" → "pin_extended"
      - "mark_up_True" → "mark_up_spring"
      - "ice_cream_False" → "ice_cream_extended"

    If the input already uses the normalized form (idempotent on re-call),
    pass through unchanged.
    """
    out: dict = {}
    for key, cell in raw.items():
        # Idempotency: if already normalized, copy as-is.
        if key.endswith("_spring") or key.endswith("_extended"):
            out[key] = cell
            continue
        if key.endswith("_True"):
            out[key[: -len("_True")] + "_spring"] = cell
        elif key.endswith("_False"):
            out[key[: -len("_False")] + "_extended"] = cell
        else:
            # Unknown suffix — preserve the key so future schema changes don't drop data silently.
            out[key] = cell
    return out


def build_stats_json(aggregates: dict) -> dict:
    """Pure: project _backtest_aggregates.json into the frontend-ready shape (D-11).

    Accepts either:
        (a) the raw `aggregates` block (keys: all / by_confirmation_type /
            by_is_spring / by_type_x_spring), OR
        (b) the full _backtest_aggregates.json dict (top-level "aggregates" key).
    Returns the dict matching RESEARCH §Schema Designs L838-865.

    D-11 contract:
        - Emits raw cuts for `all`, `by_confirmation_type`, `by_type_x_spring`.
        - Renames by_type_x_spring keys via _normalize_by_type_x_spring.
        - Documents the fallback chain (`fallback_order` + `n_floor`) — the
          walk itself happens client-side per RESEARCH Open Question #1.

    Args:
        aggregates: dict in either shape (a) or (b) above.

    Returns:
        dict with keys: schema_version, generated_at, source, rule, stats,
        fallback_order, n_floor.
    """
    # Accept both shape (a) and shape (b) per the docstring.
    if "aggregates" in aggregates and isinstance(aggregates["aggregates"], dict):
        agg = aggregates["aggregates"]
    else:
        agg = aggregates

    # Defensive: if any of the four expected slices is missing, default to {}.
    # This keeps build_stats_json total — never raises on partial input.
    all_cell = agg.get("all", {})
    by_ct = agg.get("by_confirmation_type", {})
    by_x = _normalize_by_type_x_spring(agg.get("by_type_x_spring", {}))

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": _STATS_SOURCE,
        "rule": dict(_STATS_RULE),
        "stats": {
            "by_type_x_spring": by_x,
            "by_confirmation_type": dict(by_ct),
            "all": dict(all_cell),
        },
        "fallback_order": list(_STATS_FALLBACK_ORDER),
        "n_floor": _STATS_N_FLOOR,
    }


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
