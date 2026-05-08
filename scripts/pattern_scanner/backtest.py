"""Inside-bar-spring backtester (Phase 9).

Pure-function core (this module) + thin CLI wrapper (Plan 09-02 Task: main).
See .planning/phases/09-backtesting-engine/09-CONTEXT.md for D-01..D-17.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

import pandas as pd

from scripts.pattern_scanner.detector import Detection


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
