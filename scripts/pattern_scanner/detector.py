"""Inside bar spring detector — pure-Python rule-based candlestick pattern detection.

Public API:
    detect(df: pd.DataFrame, ticker: str) -> list[Detection]

Encodes the locked 5-bar inside bar spring ruleset (CONTEXT D-01..D-14):
    Bar 1 = mother bar
    Bar 2 = inside bar (strict: H_inside < H_mother AND L_inside > L_mother)
    Within next 3 bars (bars 3..5): one bar breaks below mother low (Low < mother_low).
    The break-below bar OR a later bar in the 5-bar window closes inside the mother
    range as a Pin / Mark-up / Ice-cream confirmation.
    Spring case: break-below bar == confirmation bar.

Trend filters (all must pass; per-filter booleans always recorded):
    HH/HL uptrend     — last 2 swing highs ascending AND last 2 swing lows ascending
                        (5-bar fractal pivots over 60-bar lookback ending at confirmation)
    Above 50-SMA      — close[conf] > sma_50 evaluated on df.iloc[:conf+1]
    SMA cluster       — mother_low within +/- 1 * ATR(14) of either 20-SMA or 50-SMA
                        evaluated on df.iloc[:mother_idx + 1]

No-look-ahead invariant:
    All filter computations slice df via df.iloc[:k+1] BEFORE computing indicators.
    Negative-offset Series shifts are BANNED in this module (canonical look-ahead operator).

CLI:
    python scripts/pattern_scanner/detector.py AAPL

The CLI ticker arg is validated against `^[A-Z0-9.-]{1,10}$` before being passed
to yfinance (T-07-01 mitigation).
"""
from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── Module constants ────────────────────────────────────────────────────────
_LOOKBACK = 60
_ATR_PERIOD = 14
_SMA20 = 20
_SMA50 = 50
_TICKER_RE = re.compile(r"^[A-Z0-9.-]{1,10}$")


# ── Detection record (D-10, D-11) ───────────────────────────────────────────
@dataclass(frozen=True)
class Detection:
    """Frozen detection record. Fields per CONTEXT D-10."""

    ticker: str
    confirmation_date: str          # ISO YYYY-MM-DD
    confirmation_type: str          # "pin" | "mark_up" | "ice_cream"
    is_spring: bool
    bars: List[Dict]                # 5 dicts {date, open, high, low, close} mother -> conf
    mother_bar_index: int
    confirmation_bar_index: int
    filters: Dict[str, bool]        # {hh_hl, above_50sma, sma_cluster}
    sma_levels: Dict[str, float]    # {sma20, sma50, atr14}

    def to_dict(self) -> Dict:
        """Return a plain-dict representation suitable for json.dumps."""
        return asdict(self)


# ── Confirmation classifiers (D-01..D-03) ───────────────────────────────────
def _is_pin(bar) -> bool:
    """Pin bar (D-01): open >= L + (2/3)*range AND close >= L + (2/3)*range.

    Returns native Python bool (not numpy.bool_) so callers can rely on `is True`.
    """
    rng = float(bar["High"]) - float(bar["Low"])
    if rng <= 0:
        return False
    upper_third = float(bar["Low"]) + (2.0 / 3.0) * rng
    return bool(float(bar["Open"]) >= upper_third and float(bar["Close"]) >= upper_third)


def _is_mark_up(bar) -> bool:
    """Mark-up bar (D-02): bullish bar with body >= 2/3 of range."""
    rng = float(bar["High"]) - float(bar["Low"])
    if rng <= 0:
        return False
    body = float(bar["Close"]) - float(bar["Open"])
    return bool(body >= (2.0 / 3.0) * rng and float(bar["Close"]) > float(bar["Open"]))


def _is_ice_cream(bar) -> bool:
    """Ice-cream bar (D-03): long lower wick at/below midpoint, bullish close in upper 2/3."""
    rng = float(bar["High"]) - float(bar["Low"])
    if rng <= 0:
        return False
    body_low = min(float(bar["Open"]), float(bar["Close"]))
    midpoint = float(bar["Low"]) + 0.5 * rng
    upper_third = float(bar["Low"]) + (1.0 / 3.0) * rng
    return bool(
        body_low <= midpoint
        and float(bar["Close"]) >= upper_third
        and float(bar["Close"]) > float(bar["Open"])
    )


def _classify_confirmation(bar) -> Optional[str]:
    """Return 'pin' | 'mark_up' | 'ice_cream' | None.

    Precedence on overlap: pin -> mark_up -> ice_cream.
    """
    if _is_pin(bar):
        return "pin"
    if _is_mark_up(bar):
        return "mark_up"
    if _is_ice_cream(bar):
        return "ice_cream"
    return None


# ── Inside bar (D-04) ───────────────────────────────────────────────────────
def _inside_bar(mother, child) -> bool:
    """Inside bar (D-04): strict less-than/greater-than on both sides.

    Returns native Python bool.
    """
    return bool(
        float(child["High"]) < float(mother["High"])
        and float(child["Low"]) > float(mother["Low"])
    )


# ── Indicators (slice-first idiom) ──────────────────────────────────────────
def _compute_sma(close: pd.Series, period: int) -> pd.Series:
    """Simple moving average. Caller must pre-slice the closing-price series."""
    return close.rolling(window=period, min_periods=period).mean()


def _compute_atr(view: pd.DataFrame, period: int = _ATR_PERIOD) -> pd.Series:
    """Wilder-smoothed ATR. Caller must pre-slice the OHLC frame.

    True Range = max(H - L, |H - prev_close|, |L - prev_close|).
    Wilder smoothing == EMA with alpha = 1/period and adjust=False.
    """
    high = view["High"]
    low = view["Low"]
    prev_close = view["Close"].shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return atr


# ── Swing pivots (D-05) ─────────────────────────────────────────────────────
def _swing_pivots(view: pd.DataFrame) -> Tuple[List[int], List[int]]:
    """5-bar fractal swing pivots inside `view` (positional indices).

    Returns (swing_high_idx_list, swing_low_idx_list). Strict > / < on neighbours.
    Pivots within 2 bars of either edge are inherently un-confirmable and are
    therefore omitted — this is past-only logic, NOT a look-ahead violation.
    """
    highs = view["High"].values
    lows = view["Low"].values
    n = len(view)
    swing_highs: List[int] = []
    swing_lows: List[int] = []
    for i in range(2, n - 2):
        if (
            highs[i] > highs[i - 1]
            and highs[i] > highs[i - 2]
            and highs[i] > highs[i + 1]
            and highs[i] > highs[i + 2]
        ):
            swing_highs.append(i)
        if (
            lows[i] < lows[i - 1]
            and lows[i] < lows[i - 2]
            and lows[i] < lows[i + 1]
            and lows[i] < lows[i + 2]
        ):
            swing_lows.append(i)
    return swing_highs, swing_lows


def _hh_hl_uptrend(view: pd.DataFrame) -> bool:
    """HH/HL filter (D-05): last 2 swing highs ascending AND last 2 swing lows ascending."""
    sh, sl = _swing_pivots(view)
    if len(sh) < 2 or len(sl) < 2:
        return False
    last_high = float(view["High"].iloc[sh[-1]])
    prev_high = float(view["High"].iloc[sh[-2]])
    last_low = float(view["Low"].iloc[sl[-1]])
    prev_low = float(view["Low"].iloc[sl[-2]])
    return bool(last_high > prev_high and last_low > prev_low)


# ── SMA cluster (D-07) ──────────────────────────────────────────────────────
def _sma_cluster(df: pd.DataFrame, mother_idx: int) -> bool:
    """Mother-bar low within +/- 1 * ATR(14) of either 20-SMA or 50-SMA at mother_idx.

    Slice-first idiom: compute on df.iloc[:mother_idx + 1], then read .iloc[-1].
    """
    view = df.iloc[: mother_idx + 1]
    if len(view) < _SMA50:
        return False
    sma20 = _compute_sma(view["Close"], _SMA20).iloc[-1]
    sma50 = _compute_sma(view["Close"], _SMA50).iloc[-1]
    atr14 = _compute_atr(view, _ATR_PERIOD).iloc[-1]
    if any(_is_nan(v) for v in (sma20, sma50, atr14)):
        return False
    mother_low = float(df.iloc[mother_idx]["Low"])
    sma20_f = float(sma20)
    sma50_f = float(sma50)
    atr14_f = float(atr14)
    return bool(
        abs(mother_low - sma20_f) <= atr14_f
        or abs(mother_low - sma50_f) <= atr14_f
    )


def _is_nan(v) -> bool:
    """math.isnan that also tolerates non-floats (returns True for non-numeric)."""
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return True


# ── Detection assembly ──────────────────────────────────────────────────────
def _build_detection(
    df: pd.DataFrame,
    ticker: str,
    mother_idx: int,
    break_idx: int,
    conf_idx: int,
    conf_type: str,
) -> Detection:
    """Build a Detection record. Always evaluates ALL THREE filter booleans (D-08)."""
    view = df.iloc[: conf_idx + 1]

    # Per-filter booleans — always evaluated regardless of short-circuit (D-08).
    hh_hl = _hh_hl_uptrend(view)

    sma50_series = _compute_sma(view["Close"], _SMA50)
    sma50_at_conf = sma50_series.iloc[-1]
    close_at_conf = float(df.iloc[conf_idx]["Close"])
    above_50sma = (
        not _is_nan(sma50_at_conf) and close_at_conf > float(sma50_at_conf)
    )

    sma_cluster_ok = _sma_cluster(df, mother_idx)

    # SMA levels at confirmation (informational; D-10 sma_levels dict)
    sma20_at_conf = _compute_sma(view["Close"], _SMA20).iloc[-1]
    atr14_at_conf = _compute_atr(view, _ATR_PERIOD).iloc[-1]

    sma_levels: Dict[str, float] = {
        "sma20": float(sma20_at_conf) if not _is_nan(sma20_at_conf) else float("nan"),
        "sma50": float(sma50_at_conf) if not _is_nan(sma50_at_conf) else float("nan"),
        "atr14": float(atr14_at_conf) if not _is_nan(atr14_at_conf) else float("nan"),
    }

    # 5-bar window mother..mother+4 truncated to length of df.
    bars: List[Dict] = []
    end = min(mother_idx + 5, len(df))
    for i in range(mother_idx, end):
        idx_label = df.index[i]
        bars.append(
            {
                "date": idx_label.strftime("%Y-%m-%d"),
                "open": float(df.iloc[i]["Open"]),
                "high": float(df.iloc[i]["High"]),
                "low": float(df.iloc[i]["Low"]),
                "close": float(df.iloc[i]["Close"]),
            }
        )

    is_spring = (break_idx == conf_idx)

    return Detection(
        ticker=ticker,
        confirmation_date=df.index[conf_idx].strftime("%Y-%m-%d"),
        confirmation_type=conf_type,
        is_spring=is_spring,
        bars=bars,
        mother_bar_index=int(mother_idx),
        confirmation_bar_index=int(conf_idx),
        filters={
            "hh_hl": bool(hh_hl),
            "above_50sma": bool(above_50sma),
            "sma_cluster": bool(sma_cluster_ok),
        },
        sma_levels=sma_levels,
    )


# ── Public API ──────────────────────────────────────────────────────────────
def detect(df: pd.DataFrame, ticker: str,
           apply_trend_filters: bool = True) -> List[Detection]:
    """Detect bullish inside bar spring setups in daily OHLC data.

    Args:
        df: DataFrame with flat columns Open/High/Low/Close and a tz-naive
            DatetimeIndex (yfinance auto_adjust + tz_localize(None) format).
        ticker: uppercase symbol; included in each Detection record.
        apply_trend_filters: when True (default — Phase 7 contract), only
            emit detections whose three trend filters all pass. When False
            (Phase 8 hard-negative pool — D-10), emit every detection that
            passes the cluster shape rules regardless of filter state.
            Per-filter booleans are still recorded in either mode.

    Returns:
        List of Detection records, one per emitted setup. Empty list if the
        input frame is shorter than the 60-bar minimum or no setups match.
    """
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"detect() requires columns {required}; missing: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("detect() requires a DatetimeIndex on df.")
    if df.index.tz is not None:
        raise ValueError("detect() requires a tz-naive DatetimeIndex; got tz-aware.")

    detections: List[Detection] = []
    n = len(df)
    if n < _LOOKBACK:
        return detections

    # Earliest mother bar must satisfy: 60-bar history available at the confirmation bar.
    # The mandatory bar after mother is the inside bar at mother + 1; the
    # break-bar offsets (2..4) are bounds-checked inside the inner loop, which
    # naturally accommodates the spring case where confirmation can land as
    # early as mother + 2.
    for mother_idx in range(_LOOKBACK, n - 1):
        if not _inside_bar(df.iloc[mother_idx], df.iloc[mother_idx + 1]):
            continue
        mother_low = float(df.iloc[mother_idx]["Low"])
        mother_high = float(df.iloc[mother_idx]["High"])

        # Scan bars (mother+2)..(mother+4) for first break-below.
        for break_offset in range(2, 5):
            break_idx = mother_idx + break_offset
            if break_idx >= n:
                break
            if float(df.iloc[break_idx]["Low"]) >= mother_low:
                continue  # not a break-below; keep scanning offsets

            # Try break_idx and any later bar within the 5-bar window as confirmation.
            for conf_idx in range(break_idx, min(mother_idx + 5, n)):
                conf_type = _classify_confirmation(df.iloc[conf_idx])
                if conf_type is None:
                    continue
                conf_close = float(df.iloc[conf_idx]["Close"])
                # Confirmation must close back inside mother range.
                if not (mother_low < conf_close < mother_high):
                    continue
                detection = _build_detection(
                    df=df,
                    ticker=ticker,
                    mother_idx=mother_idx,
                    break_idx=break_idx,
                    conf_idx=conf_idx,
                    conf_type=conf_type,
                )
                if not apply_trend_filters:
                    detections.append(detection)
                elif (
                    detection.filters["hh_hl"]
                    and detection.filters["above_50sma"]
                    and detection.filters["sma_cluster"]
                ):
                    detections.append(detection)
                break  # one confirmation per break-below
            break  # one break-below window per mother bar

    return detections


# ── CLI helpers ─────────────────────────────────────────────────────────────
def _fetch_ohlc(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Fetch daily OHLC via yfinance. Deferred import keeps unit tests fast."""
    import yfinance as yf  # noqa: WPS433 — deferred by design

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def main(argv: List[str]) -> int:
    """CLI entry point. Returns process exit code.

    argv mimics sys.argv (argv[0] is the program name). Validates the ticker
    against `_TICKER_RE` BEFORE invoking yfinance (T-07-01 mitigation).
    """
    if len(argv) < 2:
        print(
            "Usage: python scripts/pattern_scanner/detector.py <TICKER>",
            file=sys.stderr,
        )
        return 1
    ticker = argv[1].upper()
    if not _TICKER_RE.match(ticker):
        print(f"Invalid ticker: {ticker!r}", file=sys.stderr)
        return 2
    df = _fetch_ohlc(ticker)
    detections = detect(df, ticker)
    print(json.dumps([d.to_dict() for d in detections], indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
