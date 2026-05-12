"""Inside-bar-spring batch pipeline (Phase 10).

Pure-function core + thin CLI wrapper. Mirrors scripts.pattern_scanner.backtest
structurally; reuses Phase 9 inference symbols verbatim via import + re-export so
tests can monkeypatch them on `run_pipeline_mod` directly.

See .planning/phases/10-batch-pipeline/10-CONTEXT.md for D-01..D-24.

CLI:
    python -m scripts.pattern_scanner.run_pipeline \
        --tickers all --window-days 20 --out-dir docs/projects/patterns
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
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

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
# ME-02: use CustomBusinessDay with the US Federal holiday calendar so months
# with Thanksgiving / Christmas don't silently shift the effective cutoff by
# 2-3 trading days. USFederalHolidayCalendar covers all NYSE-closed federal
# holidays (New Year's, MLK, Presidents', Memorial, Independence, Labor,
# Thanksgiving, Christmas) — the only NYSE-only closure it misses is Good
# Friday, which we accept as within the resolution-coverage buffer.
_US_BDAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())


def _window_cutoff(today: pd.Timestamp, window_days: int) -> pd.Timestamp:
    """Compute the cutoff timestamp: detections with confirmation_date < cutoff are dropped.

    Uses pandas CustomBusinessDay seeded with USFederalHolidayCalendar so the
    cutoff skips Saturday/Sunday AND US federal market holidays. Saturday/Sunday
    or holiday `today` is rolled back to the previous trading day before
    subtracting window_days.
    """
    return today - window_days * _US_BDAY


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
    # BL-01: normalize confirmation_date once at the boundary. The detector
    # promises YYYY-MM-DD strings (detector.py L58, L290), but the upstream
    # pipeline-window filter uses pd.Timestamp() to coerce, which means an
    # accidental Timestamp leaking in would produce "2024-01-10 00:00:00" —
    # a filesystem-hostile filename containing a space and colons.
    # Normalize defensively so chart_path / out_png are always safe.
    conf_date_str = pd.Timestamp(detection.confirmation_date).strftime("%Y-%m-%d")
    assert " " not in conf_date_str and ":" not in conf_date_str, (
        f"confirmation_date {conf_date_str!r} contains space/colon — filesystem-hostile"
    )
    if entry_idx >= len(df):
        # PENDING: entry has not happened yet (today IS the confirmation day, or
        # there is no next bar in the fetched slice yet). Compute a "would-be"
        # target_price from the last close so the frontend can preview the setup.
        last_close = float(df.iloc[-1]["Close"])
        target_price = _target_for(last_close, stop_price)
        return {
            "ticker": str(detection.ticker),
            "confirmation_date": conf_date_str,
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
    # BL-01: force the same shape on the delegated path as well, so both
    # branches of _resolve_status emit a path-safe YYYY-MM-DD string.
    rec["confirmation_date"] = conf_date_str
    return rec


# ── HI-03: strict JSON serializer ───────────────────────────────────────────
def _json_default(obj):
    """Strict serializer for JSON dump. Explicitly handles known types; raises
    TypeError on anything else.

    HI-03: the previous `default=str` was a silent type-coercion footgun — it
    would happily turn a `pd.Timestamp` into `'2024-01-10 00:00:00'`
    (path-hostile, masked BL-01 in testing). The replacement fails loudly on
    unexpected types so the bad value is caught at write time.
    """
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(
        f"Unexpected type {type(obj).__name__} in data.json payload: {obj!r}"
    )


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
    # HI-02: clean up the .tmp sibling if json.dump / fsync raises, so a
    # failed write doesn't leave disk-litter that future readers can mistake
    # for diagnostics. The `with` block already closes the file handle; we
    # additionally unlink the tmp path on any exception before re-raising.
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True, default=_json_default)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())  # durability hygiene (not load-bearing for atomicity)
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


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
        # BL-03: only consider .png files — never touch .gitkeep, README,
        # thumbnails, or any other artefact placed in charts/. The previous
        # implementation deleted any file not in expected_filenames, which
        # would silently kill .gitkeep on every nightly run.
        if not (f.is_file() and f.suffix.lower() == ".png"):
            continue
        if f.name not in expected_filenames:
            f.unlink()
            deleted += 1
    return deleted


# ── Company / sector enrichment from the DCF screener snapshot (RESEARCH OQ#3) ──
SCREENER_DATA_PATH = Path("docs/projects/screener/data.json")


def _load_company_lookup(path: Path | None = None) -> dict[str, tuple[str, str]]:
    """Build {ticker: (company_name, sector)} from the DCF screener snapshot.

    D-19 enrichment per RESEARCH Open Question #3:
        - Reads docs/projects/screener/data.json (the existing committed snapshot
          from Phase 5's screener pipeline; refreshed nightly by nightly-screener.yml
          at 06:00 UTC — Phase 10 runs at 07:00 UTC, so the data is fresh).
        - Returns {} on any IO / JSON failure (caller defaults to (ticker, "")).
        - Tolerant of partial rows: a row missing company_name or sector yields ""
          for the missing field.
    """
    target = path or SCREENER_DATA_PATH
    if not target.exists():
        return {}
    # HI-04: defensively validate the top-level shape and each row before
    # calling .get / .upper. The previous implementation caught only
    # json.JSONDecodeError + OSError, so a future schema change in the DCF
    # screener (e.g. top-level list instead of dict, or rows missing keys)
    # would raise AttributeError mid-iteration and abort the entire
    # pattern-scanner run.
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            warnings.warn(
                f"{target}: expected dict at top level, got "
                f"{type(data).__name__}; company/sector enrichment skipped.",
                UserWarning,
            )
            return {}
        stocks = data.get("stocks", [])
        if not isinstance(stocks, list):
            warnings.warn(
                f"{target}: 'stocks' is {type(stocks).__name__}, expected list; "
                f"company/sector enrichment skipped.",
                UserWarning,
            )
            return {}
        lookup: dict[str, tuple[str, str]] = {}
        for row in stocks:
            if not isinstance(row, dict):
                continue
            ticker = row.get("ticker")
            if not ticker or not isinstance(ticker, str):
                continue
            lookup[ticker.upper()] = (
                str(row.get("company_name") or ""),
                str(row.get("sector") or ""),
            )
        return lookup
    except (json.JSONDecodeError, OSError, AttributeError, TypeError) as exc:
        warnings.warn(
            f"Failed to load company lookup from {target}: {exc}",
            UserWarning,
        )
        return {}


# ── D-14 + D-15: publication-chart render wrapper with style-fallback probe ───
_PREFERRED_PUBLICATION_FALLBACKS = ("binance-dark", "checkers", "starsandstripes", "blueskies")
_resolved_publication_base_style: str | None = None
_render_substitutions: list[dict] = []


def _resolve_publication_base_style() -> str:
    """Probe mpf.available_styles() once per process. Returns the base_style to use.

    Strategy:
        1. If PUBLICATION_STYLE.base_style is in mpf.available_styles() -> use it
           (the common case; nightclouds is documented in mplfinance 0.12.10b0).
        2. Otherwise, walk _PREFERRED_PUBLICATION_FALLBACKS and pick the first match.
        3. If none matches (extremely unlikely — mplfinance ships ~14 named styles),
           pick the FIRST entry in mpf.available_styles() and record a loud warning.

    Records the substitution to _render_substitutions for SUMMARY surfacing.
    Caches the result globally so the probe runs ONCE per process.
    """
    global _resolved_publication_base_style
    if _resolved_publication_base_style is not None:
        return _resolved_publication_base_style

    from scripts.pattern_scanner.renderer import PUBLICATION_STYLE
    import mplfinance as mpf

    available = set(mpf.available_styles())
    wanted = PUBLICATION_STYLE.base_style
    if wanted in available:
        _resolved_publication_base_style = wanted
        return wanted

    for candidate in _PREFERRED_PUBLICATION_FALLBACKS:
        if candidate in available:
            _render_substitutions.append({
                "requested": wanted,
                "substituted": candidate,
                "reason": "preferred fallback (nightclouds absent from this mplfinance install)",
            })
            warnings.warn(
                f"mplfinance base_style {wanted!r} not available; substituting {candidate!r}.",
                UserWarning,
            )
            _resolved_publication_base_style = candidate
            return candidate

    # Last-resort: pick whatever exists. Order is implementation-defined but
    # mplfinance always exposes >=1 style.
    fallback = sorted(available)[0]
    _render_substitutions.append({
        "requested": wanted,
        "substituted": fallback,
        "reason": "no preferred fallback matched — picked first available style",
    })
    warnings.warn(
        f"mplfinance base_style {wanted!r} not available AND none of preferred fallbacks "
        f"{_PREFERRED_PUBLICATION_FALLBACKS} matched; using {fallback!r}.",
        UserWarning,
    )
    _resolved_publication_base_style = fallback
    return fallback


def _render_publication_chart(df: pd.DataFrame, detection, out_path: Path) -> bool:
    """Wrapper: slice the 60-bar window, probe style, delegate to renderer.

    Reads detection.confirmation_bar_index and slices df.iloc[conf-59 : conf+1].
    If the slice is shorter than 60 (insufficient history), logs warning and
    returns False WITHOUT raising — main()'s broad-except is for failures the
    renderer cannot recover from; short history is recoverable by skipping the
    chart. Returns True on successful render (PNG written to out_path).

    On the first call, probes mplfinance for style availability. If
    PUBLICATION_STYLE.base_style is absent, picks a fallback and records the
    substitution (visible to main() for the SUMMARY).

    Args:
        df: full OHLC dataframe (NOT yet sliced to 60 bars).
        detection: Detection-like object with .confirmation_bar_index.
        out_path: target PNG path. Parent dirs are created.

    Returns:
        True if the PNG was rendered; False if the render was skipped
        (insufficient history or anomalous slice). The caller MUST gate
        `chart_path` assignment on this return value (BL-02): writing
        chart_path into data.json for a skipped render produces frontend 404s.
    """
    from scripts.pattern_scanner.renderer import (
        render_publication_chart as _render_impl,
        PUBLICATION_STYLE,
    )

    conf_idx = detection.confirmation_bar_index
    start = conf_idx - 59
    if start < 0:
        warnings.warn(
            f"_render_publication_chart: insufficient history "
            f"(conf_idx={conf_idx}, need 60 bars; only {conf_idx + 1} available); "
            f"skipping {out_path.name}.",
            UserWarning,
        )
        return False
    window = df.iloc[start : conf_idx + 1]
    if len(window) != 60:
        warnings.warn(
            f"_render_publication_chart: window slice produced {len(window)} bars "
            f"(expected 60); skipping {out_path.name}.",
            UserWarning,
        )
        return False

    # Probe + cache style fallback on first call.
    resolved = _resolve_publication_base_style()

    # ME-07: pass the resolved style EXPLICITLY rather than rebinding
    # renderer.PUBLICATION_STYLE for the duration of the call. The previous
    # rebind approach was correct for sequential single-threaded use, but a
    # parallel renderer.render_publication_chart call (pytest-xdist, future
    # ThreadPoolExecutor) would see the mutated module-level constant. The
    # explicit-arg form is concurrency-safe.
    if resolved == PUBLICATION_STYLE.base_style:
        _render_impl(window, detection, out_path)
        return True

    from dataclasses import replace

    resolved_style = replace(PUBLICATION_STYLE, base_style=resolved)
    _render_impl(window, detection, out_path, style=resolved_style)
    return True


# ── PIPE-02: build_data_json — assemble the atomic-write payload ─────────────
def build_data_json(
    detections: list[dict],
    errors: list[dict],
    run_id: str,
    succeeded: int,
    failed: int,
    window_days: int,
    now_utc: datetime | None = None,
    style_substitutions: list[dict] | None = None,
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
        now_utc: ME-01 — the run's single anchor timestamp. When None, falls
            back to `datetime.now(timezone.utc)` (kept for back-compat with
            unit tests that call build_data_json directly). main() threads its
            own anchor through so generated_at, as_of_date, and the window
            cutoff all share one moment in time.

    Returns:
        dict matching the RESEARCH §Schema Designs L781-826 shape.
    """
    total = succeeded + failed
    success_rate = succeeded / max(total, 1)
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    generated_at = now_utc.isoformat()
    as_of_date = now_utc.strftime("%Y-%m-%d")

    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "window_days": int(window_days),
        "as_of_date": as_of_date,
        "pipeline_status": {
            "schema_version": 1,
            "completed": bool(success_rate >= 0.95),
            "succeeded_count": int(succeeded),
            "failed_count": int(failed),
            "errors": list(errors),
            "errors_truncated": 0,  # truncation, if any, happened in the caller
            "run_id": str(run_id),
            "generated_at": generated_at,
            # ME-04: persist style substitutions so a thin-mplfinance install
            # (no `nightclouds`) is visible in the committed data.json instead
            # of being trapped in 90-day CI log retention.
            "style_substitutions": list(style_substitutions or []),
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


# ── Universe resolver — tests monkeypatch fetch_sp500_tickers on this module ───
def _resolve_universe(tickers_arg, limit: int | None) -> list[str]:
    """Resolve the --tickers argparse output into a concrete list of symbols.

    `tickers_arg` is the output of _parse_tickers_arg: either the literal string
    "all" or a list[str] (already token-validated). When "all", call
    fetch_sp500_tickers() (which tests can monkeypatch on run_pipeline_mod).
    Apply --limit slicing AFTER resolving the universe.
    """
    if tickers_arg == "all":
        tickers = list(fetch_sp500_tickers())
    else:
        tickers = list(tickers_arg)
    if limit is not None:
        tickers = tickers[:limit]
    return tickers


def main(argv: list[str] | None = None) -> int:
    """Orchestrate the nightly pattern-scanner pipeline (D-19).

    Sequence (RESEARCH §Pattern 1 L242-307):
        1. Parse CLI.
        2. Resolve universe; apply --limit slice.
        3. Load ONNX session once (D-06); warn-once if absent (D-08).
        4. Compute today + cutoff via BDay (D-01).
        5. Load company / sector lookup from the DCF screener snapshot.
        6. Iterate tickers with 0.5s rate-limit:
            - fetch OHLC, detect (filtered default, D-04), window-filter, resolve status,
              score with ONNX, render chart, attach company_name + sector + filters + bars.
            - On exception: append to errors[], increment failed, never re-raise.
        7. Stale-PNG cleanup via set-difference (D-15).
        8. Truncate errors at ERRORS_TRUNCATE_CAP (D-16 / Claude's Discretion).
        9. build_data_json + atomic write data.json.
       10. Read _backtest_aggregates.json, build_stats_json, atomic write stats.json.
    """
    args = _parse_args(argv)
    tickers = _resolve_universe(args.tickers, args.limit)
    # D-08 / D-06: load ONNX session once (warn-once if missing).
    # --no-onnx forces graceful-fallback path without attempting to load.
    if args.no_onnx:
        # LO-02: noisy startup notice so an operator who passed --no-onnx for
        # debugging cannot silently ship a `yolo_conf: null`-everywhere
        # data.json to production. The only previous signal was the absence
        # of yolo_conf values, which is invisible until inspection.
        print(
            "[run_pipeline] --no-onnx: ONNX scoring disabled; "
            "yolo_conf will be null on every detection row."
        )
        sess = None
    else:
        sess = _load_onnx_session(ONNX_PATH)
    # ME-01: capture ONE anchor timestamp for the entire run so generated_at,
    # as_of_date, and the window cutoff cannot land on different sides of
    # midnight UTC during a slow run. Threaded through build_data_json below.
    now_utc = datetime.now(timezone.utc)
    today = pd.Timestamp(now_utc).tz_convert("UTC").normalize().tz_localize(None)
    cutoff = _window_cutoff(today, args.window_days)
    # LO-01: lazy-load the screener company lookup on first hit. The full
    # screener data.json is ~<500KB but parsing it for a 1-ticker smoke test
    # is wasted I/O. Wrapping in a 1-element cache avoids touching disk until
    # we actually need a name/sector for a detection-bearing ticker.
    _company_lookup_cache: dict | None = None

    def _get_company_lookup() -> dict[str, tuple[str, str]]:
        nonlocal _company_lookup_cache
        if _company_lookup_cache is None:
            _company_lookup_cache = _load_company_lookup()
        return _company_lookup_cache
    # Reset module-level substitutions per run so SUMMARY doesn't accumulate stale state.
    _render_substitutions.clear()
    # HI-05: also reset the cached style probe so back-to-back `main()` calls
    # in the same process (typically tests) re-probe mpf.available_styles()
    # rather than reusing a value computed under a different monkeypatch.
    global _resolved_publication_base_style
    _resolved_publication_base_style = None

    rows: list[dict] = []
    errors: list[dict] = []
    succeeded = failed = 0
    total = len(tickers)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = args.out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    # Sequential iteration is contractual: tests assert errors[0].ticker == "A001".
    # Preserve insertion order on errors[] — do NOT parallelize without updating
    # tests/test_run_pipeline_main.py.
    for i, ticker in enumerate(tickers, start=1):
        try:
            df = _fetch_ohlc(ticker, period="6mo")
            if len(df) < 60:
                print(f"[{i}/{total}] {ticker}: insufficient history ({len(df)} bars) — skip")
                succeeded += 1  # not an error — just no data this run
                if i < total:
                    time.sleep(RATE_LIMIT_SLEEP)
                continue

            dets = detect(df, ticker)  # D-04 — filtered default
            dets_in_window = [
                d for d in dets
                if pd.Timestamp(d.confirmation_date) >= cutoff
            ]
            # HI-01: accumulate per-ticker rows in a local list and extend
            # the master `rows` only after this ticker completes. If a later
            # detection raises mid-ticker, the broad-except below will record
            # the ticker as `failed` WITHOUT polluting `rows` with the earlier
            # partial detections (which would skew the 95% completion
            # threshold and leave inconsistent state in data.json).
            ticker_rows: list[dict] = []
            for d in dets_in_window:
                rec = _resolve_status(df, d)  # D-02 wrapper
                rec["yolo_conf"] = _score_detection(_window_for(d, df), sess)
                rec["current_price"] = float(df.iloc[-1]["Close"])
                rec["filters"] = dict(getattr(d, "filters", None) or {})
                rec["bars"] = [dict(b) for b in (d.bars or [])]
                company_name, sector = _get_company_lookup().get(ticker.upper(), (ticker, ""))
                rec["company_name"] = company_name
                rec["sector"] = sector
                # BL-02: only set chart_path AFTER a successful render. If the
                # render is skipped (insufficient history, anomalous slice),
                # leave chart_path None so the frontend renders a placeholder
                # instead of fetching a non-existent PNG (404 on the live site).
                out_png = charts_dir / f"{rec['ticker']}_{rec['confirmation_date']}.png"
                rendered = _render_publication_chart(df, d, out_png)
                rec["chart_path"] = f"charts/{out_png.name}" if rendered else None
                ticker_rows.append(rec)
            rows.extend(ticker_rows)  # atomic per-ticker append (HI-01)
            succeeded += 1
            print(f"[{i}/{total}] {ticker}: {len(dets_in_window)} in-window")
        except Exception as exc:  # noqa: BLE001 — D-16 broad except; never re-raise
            failed += 1
            # ME-06: cap message at 500 chars but append a sentinel when
            # truncation actually happens, so a downstream reader can tell
            # "this is the whole error" from "this is the head of a longer
            # error". Cheap and forensically useful.
            msg = str(exc)
            if len(msg) > 500:
                msg = msg[:497] + "..."
            errors.append({
                "ticker": ticker,
                "stage": "fetch_or_detect",
                "message": msg,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            print(f"[{i}/{total}] {ticker}: ERROR — {exc}")
        if i < total:
            time.sleep(RATE_LIMIT_SLEEP)

    # D-15 stale-PNG cleanup. BL-02: only count rows whose render succeeded
    # (chart_path is not None) as "expected" — a skipped render means no PNG
    # exists for that detection, and we should not pretend one is expected.
    expected_filenames = {
        f"{r['ticker']}_{r['confirmation_date']}.png"
        for r in rows
        if r.get("chart_path") is not None
    }
    deleted_count = _cleanup_stale_pngs(charts_dir, expected_filenames)

    # D-16 errors truncation
    errors_truncated_count = max(0, len(errors) - ERRORS_TRUNCATE_CAP)
    if errors_truncated_count > 0:
        errors = errors[:ERRORS_TRUNCATE_CAP]

    # Build + atomic write data.json (PIPE-02)
    run_id = os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4())
    data = build_data_json(
        rows, errors, run_id, succeeded, failed, args.window_days,
        now_utc=now_utc,
        style_substitutions=list(_render_substitutions),
    )
    data["pipeline_status"]["errors_truncated"] = errors_truncated_count
    _atomic_write_json(args.out_dir / "data.json", data)

    # Build + atomic write stats.json (D-09 / D-10)
    aggregates_path = args.out_dir / "_backtest_aggregates.json"
    if aggregates_path.exists():
        try:
            aggregates = json.loads(aggregates_path.read_text(encoding="utf-8"))
            stats = build_stats_json(aggregates)
            _atomic_write_json(args.out_dir / "stats.json", stats)
        except (json.JSONDecodeError, OSError) as exc:
            warnings.warn(
                f"Failed to build stats.json from {aggregates_path}: {exc}; "
                f"stats.json not written.",
                UserWarning,
            )
    else:
        warnings.warn(
            f"_backtest_aggregates.json not found at {aggregates_path}; "
            f"stats.json not written.",
            UserWarning,
        )

    # Final-line summary for human + log greppability
    print(
        f"[run_pipeline] complete: "
        f"succeeded={succeeded} failed={failed} "
        f"detections={len(rows)} stale_pngs_deleted={deleted_count} "
        f"errors_truncated={errors_truncated_count} "
        f"style_substitutions={len(_render_substitutions)}"
    )
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
