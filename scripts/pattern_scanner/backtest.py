"""Inside-bar-spring backtester (Phase 9).

Pure-function core + thin CLI wrapper.
See .planning/phases/09-backtesting-engine/09-CONTEXT.md for D-01..D-17.

Plan 09-01 added: simulate_trade, aggregate.
Plan 09-02 adds: _fetch_ohlc, _load_tickers, _validate_ticker_token,
                 _parse_tickers_arg, _partition_filtered, _is_filtered,
                 _partition_cutoff, _stop_for, _target_for,
                 main(argv) orchestrator.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Callable

import pandas as pd

# Note: yfinance is imported lazily inside _fetch_ohlc to mirror
# detector._fetch_ohlc / generate_training_data._fetch_ohlc.
from scripts.fetch_sp500 import fetch_sp500_tickers
from scripts.pattern_scanner.detector import Detection, _TICKER_RE, detect
from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF

RATE_LIMIT_SLEEP = 0.5  # seconds between yfinance fetches; matches gen_training_data L65

STRATEGY_FILTERED = "1to2_rr_cluster_low_stop"
STRATEGY_UNFILTERED = "1to2_rr_cluster_low_stop__unfiltered"
DEFAULT_OUT = Path("_dev/backtest_cache.json")
ONNX_PATH = Path("models/inside_bar_v1.onnx")


def _identity(detection: Detection) -> dict:
    """Identity fields copied from Detection onto every record."""
    return {
        "ticker": str(detection.ticker),
        "confirmation_date": str(detection.confirmation_date),  # already YYYY-MM-DD per detector.py L289
        "confirmation_type": str(detection.confirmation_type),
        "is_spring": bool(detection.is_spring),
        "mother_bar_index": int(detection.mother_bar_index),
        "confirmation_bar_index": int(detection.confirmation_bar_index),
    }


def _iso(ts) -> str:
    """Coerce a pandas.Timestamp (or datetime-like) to YYYY-MM-DD string. Mirrors detector.py L289."""
    return ts.strftime("%Y-%m-%d")


def simulate_trade(
    df: pd.DataFrame,
    detection: Detection,
    stop_price: float,
    target_price: float,
) -> dict:
    """Forward-walk a trade entered at open of confirmation_bar_index+1 until stop/target/end.

    D-01..D-05 enforced:
      * Entry = open of conf+1 bar.
      * D-02 three-bucket outcome: {stop, target, open}; no timeout.
      * D-03 pessimistic intrabar: same-bar stop+target -> stop wins.
      * D-04 entry-bar gap-down: open <= stop -> recorded as 'stop' with possibly worse-than-1R R.
      * D-05 R-multiples: stop = -1.0R, target = +2.0R, open = (last_close - entry) / risk.

    All numeric fields are coerced via float(); all dates are YYYY-MM-DD strings (Pitfall 1, 2, 7).
    """
    entry_idx = detection.confirmation_bar_index + 1

    # No entry possible — detection is at the last bar.
    if entry_idx >= len(df):
        last_close = float(df.iloc[-1]["Close"])
        return {
            **_identity(detection),
            "entry_date": _iso(df.index[-1]),
            "entry_price": last_close,
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "risk": float(0.0),
            "exit_date": _iso(df.index[-1]),
            "exit_price": last_close,
            "exit_reason": "open",
            "hold_days": 0,
            "R": float(0.0),
        }

    entry_open = float(df.iloc[entry_idx]["Open"])
    entry_date = df.index[entry_idx]
    risk = entry_open - float(stop_price)

    # Pathological: stop at or above entry. Treat as immediate stop with R from gap.
    if risk <= 0:
        R = (entry_open - float(stop_price)) / max(abs(entry_open - float(stop_price)), 1e-9)
        return {
            **_identity(detection),
            "entry_date": _iso(entry_date),
            "entry_price": entry_open,
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "risk": float(risk),
            "exit_date": _iso(entry_date),
            "exit_price": entry_open,
            "exit_reason": "stop",
            "hold_days": 0,
            "R": float(R),
        }

    # D-04: entry bar gap-down at or below stop -> recorded as 'stop' (R can be < -1.0).
    if entry_open <= float(stop_price):
        R = (entry_open - float(stop_price)) / risk
        return {
            **_identity(detection),
            "entry_date": _iso(entry_date),
            "entry_price": entry_open,
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "risk": float(risk),
            "exit_date": _iso(entry_date),
            "exit_price": entry_open,
            "exit_reason": "stop",
            "hold_days": 0,
            "R": float(R),
        }

    # D-04 + D-03: entry bar's [low, high] contains stop -> pessimistic same-day stop.
    entry_low = float(df.iloc[entry_idx]["Low"])
    if entry_low <= float(stop_price):
        return {
            **_identity(detection),
            "entry_date": _iso(entry_date),
            "entry_price": entry_open,
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "risk": float(risk),
            "exit_date": _iso(entry_date),
            "exit_price": float(stop_price),
            "exit_reason": "stop",
            "hold_days": 0,
            "R": float(-1.0),
        }

    # Forward walk bars conf+2 .. end.
    for j in range(entry_idx + 1, len(df)):
        bar_low = float(df.iloc[j]["Low"])
        bar_high = float(df.iloc[j]["High"])
        hit_stop = bar_low <= float(stop_price)
        hit_target = bar_high >= float(target_price)

        # D-03: same-bar conflict -> stop wins.
        if hit_stop and hit_target:
            return {
                **_identity(detection),
                "entry_date": _iso(entry_date),
                "entry_price": entry_open,
                "stop_price": float(stop_price),
                "target_price": float(target_price),
                "risk": float(risk),
                "exit_date": _iso(df.index[j]),
                "exit_price": float(stop_price),
                "exit_reason": "stop",
                "hold_days": int((df.index[j] - entry_date).days),
                "R": float(-1.0),
            }
        if hit_stop:
            return {
                **_identity(detection),
                "entry_date": _iso(entry_date),
                "entry_price": entry_open,
                "stop_price": float(stop_price),
                "target_price": float(target_price),
                "risk": float(risk),
                "exit_date": _iso(df.index[j]),
                "exit_price": float(stop_price),
                "exit_reason": "stop",
                "hold_days": int((df.index[j] - entry_date).days),
                "R": float(-1.0),
            }
        if hit_target:
            return {
                **_identity(detection),
                "entry_date": _iso(entry_date),
                "entry_price": entry_open,
                "stop_price": float(stop_price),
                "target_price": float(target_price),
                "risk": float(risk),
                "exit_date": _iso(df.index[j]),
                "exit_price": float(target_price),
                "exit_reason": "target",
                "hold_days": int((df.index[j] - entry_date).days),
                "R": float(2.0),
            }

    # End of data — neither hit. D-02 'open'.
    last_close = float(df.iloc[-1]["Close"])
    R_open = (last_close - entry_open) / risk
    return {
        **_identity(detection),
        "entry_date": _iso(entry_date),
        "entry_price": entry_open,
        "stop_price": float(stop_price),
        "target_price": float(target_price),
        "risk": float(risk),
        "exit_date": _iso(df.index[-1]),
        "exit_price": last_close,
        "exit_reason": "open",
        "hold_days": int((df.index[-1] - entry_date).days),
        "R": float(R_open),
    }


def aggregate(records: list[dict], group_keys: list[str]) -> dict:
    """Single-pass groupby. Empty group_keys -> returns {'all': cell}.

    For multi-key grouping, key is "_".join(str(r[k]) for k in group_keys).
    Cells with n < 1 are omitted on output (D-09).

    Each cell carries: n, n_resolved, win_rate, avg_return_r, median_hold_days,
    target_count, stop_count, open_count.
    """
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if not group_keys:
            key = "all"
        elif len(group_keys) == 1:
            key = str(r[group_keys[0]])
        else:
            key = "_".join(str(r[k]) for k in group_keys)
        buckets[key].append(r)

    out: dict[str, Any] = {}
    for key in sorted(buckets):
        rs = buckets[key]
        n = len(rs)
        if n < 1:
            continue
        resolved = [r for r in rs if r["exit_reason"] != "open"]
        n_resolved = len(resolved)
        target_count = sum(1 for r in rs if r["exit_reason"] == "target")
        stop_count = sum(1 for r in rs if r["exit_reason"] == "stop")
        open_count = sum(1 for r in rs if r["exit_reason"] == "open")
        win_rate = (target_count / n_resolved) if n_resolved > 0 else None
        avg_return_r = sum(r["R"] for r in rs) / n
        median_hold_days = median(r["hold_days"] for r in resolved) if n_resolved > 0 else None
        out[key] = {
            "n": int(n),
            "n_resolved": int(n_resolved),
            "win_rate": (float(win_rate) if win_rate is not None else None),
            "avg_return_r": float(avg_return_r),
            "median_hold_days": (int(median_hold_days) if median_hold_days is not None else None),
            "target_count": int(target_count),
            "stop_count": int(stop_count),
            "open_count": int(open_count),
        }
    return out


# ── Plan 09-02 helpers ──────────────────────────────────────────────────────
def _fetch_ohlc(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Fetch daily OHLC via yfinance with auto_adjust=True. Lazy import for testability.

    Mirrors generate_training_data._fetch_ohlc / detector._fetch_ohlc byte-for-byte.
    """
    import yfinance as yf  # noqa: WPS433 — deferred by design

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def _load_tickers(limit: int | None) -> list[str]:
    """Mirror generate_training_data._load_tickers."""
    tickers = fetch_sp500_tickers()
    if limit is not None:
        tickers = tickers[:limit]
    return tickers


def _validate_ticker_token(token: str) -> str:
    """T-9-01 mitigation. Mirrors detector.main() L411-414.

    Returns upper-cased token iff _TICKER_RE matches; raises argparse.ArgumentTypeError otherwise.
    """
    upper = token.strip().upper()
    if not _TICKER_RE.fullmatch(upper):
        raise argparse.ArgumentTypeError(
            f"Invalid ticker token {token!r}: must match {_TICKER_RE.pattern}"
        )
    return upper


def _parse_tickers_arg(value: str) -> str | list[str]:
    """argparse type for --tickers. 'all' passes through; comma-list is validated per token."""
    if value == "all":
        return "all"
    return [_validate_ticker_token(tok) for tok in value.split(",")]


def _is_filtered(detection: Detection) -> bool:
    """Mirror detector.py L375-378: all three filter booleans must pass."""
    f = detection.filters
    return bool(f.get("hh_hl") and f.get("above_50sma") and f.get("sma_cluster"))


def _partition_filtered(detections: list, filter_pred: Callable[[Any], bool]) -> tuple[list, list]:
    """Returns (filtered, unfiltered_superset).

    The unfiltered list IS the input list (full superset, D-12) — not the rejects.
    """
    filtered = [d for d in detections if filter_pred(d)]
    return filtered, list(detections)


def _partition_cutoff(records: list[dict], cutoff_str: str) -> tuple[list[dict], list[dict]]:
    """Mirrors generate_training_data.py L100-104.

    in_sample      = [r for r in records if pd.Timestamp(r['confirmation_date']) <  cutoff]
    out_of_sample  = [r for r in records if pd.Timestamp(r['confirmation_date']) >= cutoff]
    """
    cutoff = pd.Timestamp(cutoff_str)
    in_sample = [r for r in records if pd.Timestamp(r["confirmation_date"]) < cutoff]
    out_of_sample = [r for r in records if pd.Timestamp(r["confirmation_date"]) >= cutoff]
    return in_sample, out_of_sample


def _stop_for(detection: Detection) -> float:
    """D-01: stop = min(bar.low for bar in detection.bars). float-coerced."""
    return float(min(b["low"] for b in detection.bars))


def _target_for(entry_open: float, stop: float) -> float:
    """D-01: target = entry + 2 * (entry - stop). float-coerced."""
    return float(entry_open + 2.0 * (entry_open - stop))
