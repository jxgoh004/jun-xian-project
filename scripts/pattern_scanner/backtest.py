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
import io
import json
import time
import warnings
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
      * D-04 entry-bar gap-down: open <= stop -> recorded as 'stop' with possibly
        worse-than-1R R. The 1R reference is anchored to the *confirmation bar's
        close* (a stable pre-gap reference), so a gap that exceeds the planned
        risk-distance produces R < -1.0.
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

    # D-04: entry bar gap-down at or below stop -> recorded as 'stop' with
    # possibly worse-than-1R R. Anchor 1R to the *pre-gap* planned risk —
    # using the confirmation bar's close (a stable pre-entry reference) as
    # the intended-entry proxy. This gives R = -1.0 when the gap lands
    # exactly at the planned-1R distance below the confirmation close, and
    # R < -1.0 when the gap exceeds it. Must be evaluated BEFORE the
    # `risk <= 0` pathological guard, otherwise this branch is unreachable.
    if entry_open <= float(stop_price):
        conf_close = float(df.iloc[detection.confirmation_bar_index]["Close"])
        intended_risk = conf_close - float(stop_price)
        if intended_risk > 0:
            R = (entry_open - float(stop_price)) / intended_risk
            return {
                **_identity(detection),
                "entry_date": _iso(entry_date),
                "entry_price": entry_open,
                "stop_price": float(stop_price),
                "target_price": float(target_price),
                "risk": float(intended_risk),  # reflects pre-gap planned risk
                "exit_date": _iso(entry_date),
                "exit_price": entry_open,
                "exit_reason": "stop",
                "hold_days": 0,
                "R": float(R),
            }
        # else: even the confirmation close is at/below stop — truly pathological.
        # Fall through to the risk<=0 branch below.

    # Pathological: stop at or above entry AND no usable pre-gap reference.
    # Treat as immediate stop with R = -1.0 (sentinel; magnitude not meaningful).
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


# ── Plan 09-03 ONNX overlay helpers ─────────────────────────────────────────
def _load_onnx_session(model_path: Path):
    """D-14 graceful fallback: returns None if model file is absent. Single warning emitted.

    onnxruntime is imported INSIDE this function (Pitfall 3 — module must be importable
    without onnxruntime installed). Created ONCE per main() invocation and reused
    across all detections (RESEARCH §Pattern 3).
    """
    if not model_path.exists():
        warnings.warn(
            f"ONNX model not found at {model_path}; yolo_conf will be null for all records.",
            UserWarning,
            stacklevel=2,
        )
        return None
    try:
        import onnxruntime as ort  # deferred (Pitfall 3)
    except ImportError:
        warnings.warn(
            "onnxruntime not installed; yolo_conf will be null for all records.",
            UserWarning,
            stacklevel=2,
        )
        return None
    try:
        return ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    except Exception as exc:
        warnings.warn(
            f"Failed to create ONNX session ({exc}); yolo_conf will be null for all records.",
            UserWarning,
            stacklevel=2,
        )
        return None


def _window_for(detection: Detection, df: pd.DataFrame) -> "pd.DataFrame | None":
    """Right-aligned 60-bar window. Returns None when conf_idx < 59 (insufficient history).

    Per RESEARCH Open Question Q3: detections with confirmation_bar_index < 59 cannot
    produce a 60-bar window without left-padding, so yolo_conf is None for those.
    """
    conf_idx = detection.confirmation_bar_index
    if conf_idx < 59:
        return None
    return df.iloc[conf_idx - 59 : conf_idx + 1]


def _score_detection(window, sess) -> "float | None":
    """Render window with STYLES[0] (D-13 deterministic), run inference, return max-confidence score.

    Returns None when sess is None (D-14 fallback) or window is None (insufficient history).
    Reuses verify_onnx.py preprocessing verbatim: [1,3,640,640] float32 RGB tensor.
    Inference-level failures (single-window) emit a warning and return None for that record
    without aborting the whole run (T-9-04 mitigation).
    """
    if sess is None or window is None:
        return None
    try:
        from PIL import Image
        import numpy as np
        from scripts.pattern_scanner.renderer import render, STYLES
    except ImportError as exc:
        warnings.warn(
            f"ML overlay deps missing ({exc}); yolo_conf will be null.",
            UserWarning,
            stacklevel=2,
        )
        return None

    try:
        png_bytes = render(window, STYLES[0])
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB").resize((640, 640), Image.LANCZOS)
        arr = np.asarray(img).astype(np.float32) / 255.0
        arr = arr.transpose(2, 0, 1)[None, ...]  # [1, 3, 640, 640]
        inp_name = sess.get_inputs()[0].name
        raw = sess.run(None, {inp_name: arr})[0]
        # YOLOv8 ONNX output: (1, 4+nc, num_anchors); for nc=1 -> (1, 5, N).
        # raw[0].T -> (N, 5+) with score column at index 4 (verify_onnx.py L74-76).
        pred = raw[0].T
        scores = pred[:, 4]
        if scores.size == 0:
            return float(0.0)
        return float(scores.max())
    except Exception as exc:
        # Inference-level failure on a single detection should NOT abort the whole run.
        warnings.warn(
            f"ONNX inference failed for one window ({exc}); yolo_conf=null for this record.",
            UserWarning,
            stacklevel=2,
        )
        return None


# ── Orchestration ───────────────────────────────────────────────────────────
def _build_record(detection: Detection, df: pd.DataFrame, sess=None) -> dict:
    """Compute stop/target from D-01 rule, run simulate_trade, attach yolo_conf via _score_detection.

    The ONNX session (created ONCE in main()) is threaded through here so each detection's
    60-bar window can be scored. When sess is None (no model OR --no-onnx), yolo_conf=None.
    """
    stop = _stop_for(detection)
    entry_idx = detection.confirmation_bar_index + 1
    if entry_idx < len(df):
        entry_open_preview = float(df.iloc[entry_idx]["Open"])
    else:
        # Detection at last bar: simulate_trade returns 'open' with risk=0; target value irrelevant.
        entry_open_preview = float(df.iloc[-1]["Close"])
    target = _target_for(entry_open_preview, stop)
    rec = simulate_trade(df, detection, stop, target)
    rec["yolo_conf"] = _score_detection(_window_for(detection, df), sess)
    return rec


def _sample_block(records: list[dict]) -> dict:
    """Compose {detections, aggregates: {all, by_confirmation_type, by_is_spring, by_type_x_spring}}."""
    all_cell = aggregate(records, []).get("all", {})
    return {
        "detections": records,
        "aggregates": {
            "all": all_cell,
            "by_confirmation_type": aggregate(records, ["confirmation_type"]),
            "by_is_spring": aggregate(records, ["is_spring"]),
            "by_type_x_spring": aggregate(records, ["confirmation_type", "is_spring"]),
        },
    }


def _build_strategy_block(records: list[dict], cutoff_str: str) -> dict:
    """Compose {rule, in_sample, out_of_sample} for one strategy."""
    in_sample, out_of_sample = _partition_cutoff(records, cutoff_str)
    return {
        "rule": {
            "stop": "min(bar.low for bar in detection.bars)",
            "target_R": 2.0,
            "intrabar": "pessimistic",
            "timeout": "none",
        },
        "in_sample": _sample_block(in_sample),
        "out_of_sample": _sample_block(out_of_sample),
    }


def _sort_key(rec: dict) -> tuple:
    """Risk 6: deterministic record ordering."""
    return (rec["ticker"], rec["confirmation_date"], rec["mother_bar_index"])


def _onnx_sha256(path: Path) -> str | None:
    """Hash the ONNX file for cache-header reproducibility tuple. Returns None if absent."""
    if not path.exists():
        return None
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 on success.

    Mirrors generate_training_data argparse shape (D-16):
        --seed     required int
        --tickers  'all' (default) or comma-list (validated against _TICKER_RE)
        --limit    optional int (smoke-test slice)
        --out      Path; default _dev/backtest_cache.json
        --no-onnx  bool flag; honoured in Plan 09-03 (this plan logs intent only)

    Single-pass detection per ticker (RESEARCH §"Anti-Patterns to Avoid"):
    we call the detector once with apply_trend_filters=False and partition
    the resulting list via _is_filtered. yolo_conf is None on every record
    in this plan (Plan 09-03 wires the ONNX overlay).
    """
    parser = argparse.ArgumentParser(
        description="Backtest the inside bar spring strategy across the S&P 500."
    )
    parser.add_argument("--seed", type=int, required=True,
                        help="Deterministic seed; recorded in cache header.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N tickers (smoke-test).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="Output JSON path.")
    parser.add_argument("--no-onnx", action="store_true",
                        help="Force yolo_conf=null even if ONNX model exists "
                             "(bypass session loading entirely; no warning emitted).")
    parser.add_argument("--tickers", type=_parse_tickers_arg, default="all",
                        help="'all' for full S&P 500, or comma-separated tokens "
                             "(validated against _TICKER_RE before any yfinance call).")
    args = parser.parse_args(argv)

    if args.tickers == "all":
        tickers = _load_tickers(args.limit)
    else:
        tickers = args.tickers if args.limit is None else args.tickers[: args.limit]

    # Plan 09-03: load ONNX session ONCE per run (RESEARCH §Pattern 3).
    # --no-onnx bypasses session loading entirely (no warning, no session object).
    sess = None if args.no_onnx else _load_onnx_session(ONNX_PATH)

    total = len(tickers)
    filtered_records: list[dict] = []
    unfiltered_records: list[dict] = []

    for i, ticker in enumerate(tickers, start=1):
        try:
            df = _fetch_ohlc(ticker)
            if len(df) < 60:
                print(f"[{i}/{total}] {ticker}: insufficient history ({len(df)} bars) — skip")
            else:
                # Single detect() call — RESEARCH §Filter ablation.
                all_dets = detect(df, ticker, apply_trend_filters=False)
                f_dets = [d for d in all_dets if _is_filtered(d)]
                f_recs = [_build_record(d, df, sess=sess) for d in f_dets]
                u_recs = [_build_record(d, df, sess=sess) for d in all_dets]
                filtered_records.extend(f_recs)
                unfiltered_records.extend(u_recs)
                print(f"[{i}/{total}] {ticker}: filtered={len(f_recs)} unfiltered={len(u_recs)}")
        except Exception as exc:  # broad except — match gen_training_data.py L224-227
            print(f"[{i}/{total}] {ticker}: unexpected error — {exc}")
        if i < total:
            time.sleep(RATE_LIMIT_SLEEP)

    filtered_records.sort(key=_sort_key)
    unfiltered_records.sort(key=_sort_key)

    cache = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "train_test_cutoff": TRAIN_TEST_CUTOFF,
        "seed": int(args.seed),
        "ticker_list": list(tickers),
        "ticker_count": len(tickers),
        "onnx_sha256": (None if args.no_onnx else _onnx_sha256(ONNX_PATH)),
        "strategies": {
            STRATEGY_FILTERED: _build_strategy_block(filtered_records, TRAIN_TEST_CUTOFF),
            STRATEGY_UNFILTERED: _build_strategy_block(unfiltered_records, TRAIN_TEST_CUTOFF),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True, default=str)
        f.write("\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
