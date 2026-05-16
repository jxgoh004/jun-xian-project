# Phase 7: Detection Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 07-detection-engine
**Areas discussed:** Confirmation bar precision, Trend filter parameterisation, Detection record schema, Module API + manual validation harness

---

## Confirmation bar precision

### Pin Bar threshold

| Option | Description | Selected |
|--------|-------------|----------|
| open & close ≥ L + (2/3)*(H-L) | Both must sit in upper third. Inclusive (≥). Bar colour irrelevant. | ✓ |
| Same threshold but use bar body (min/max of o,c) | Equivalent when open ≠ close; explicit doji handling. | |
| Configurable threshold (default 2/3) in config dict | Adds a tunable surface. | |

**User's choice:** open & close ≥ L + (2/3)*(H-L), bar colour irrelevant.

### Mark Up Bar definition

| Option | Description | Selected |
|--------|-------------|----------|
| (close − open) ≥ (2/3)*(H−L), close > open required | Strictly bullish bar with dominant body. | ✓ |
| abs(close − open) ≥ (2/3)*(H−L), close > open required | Same outcome when close > open enforced. | |
| (close − open) ≥ (2/3)*(H−L), no colour requirement | Allows close == open with dominant body. | |

**User's choice:** strictly bullish + body ≥ 2/3 of range.

### Ice-cream Bar definition

| Option | Description | Selected |
|--------|-------------|----------|
| min(o,c) ≤ L + 0.5*(H−L) AND close ≥ L + (1/3)*(H−L) AND close > open | Lower wick at/below midpoint, bullish close upper two-thirds. | ✓ |
| Same but drop close>open | Allows doji-shaped ice-cream. | |
| Lower-wick formulation: (min(o,c) − L) ≥ (1/3)*(H−L) | Different math, same intent. | |

**User's choice:** combined wick + close + bullish triple-condition.

### Inside bar (bar 2 vs mother bar)

| Option | Description | Selected |
|--------|-------------|----------|
| Strict: H_inside < H_mother AND L_inside > L_mother | Equality disqualifies. | ✓ |
| Inclusive on both sides | Allows exact matches. | |
| Asymmetric (strict one side, inclusive other) | No principled reason. | |

**User's choice:** strict on both sides.

---

## Trend filter parameterisation

### HH/HL uptrend detection

| Option | Description | Selected |
|--------|-------------|----------|
| Fractal 5-bar swing pivots, last 2 swing highs and last 2 swing lows ascending, 60-bar lookback | Standard fractal pivot. | ✓ |
| Slope of 20-SMA > 0 over last 10 bars | Smoother, lower fidelity. | |
| Both: swing-based gate + 20-SMA slope tag | Adds metadata in record. | |

**User's choice:** swing-based, 60-bar lookback.

### SMA cluster definition

| Option | Description | Selected |
|--------|-------------|----------|
| Mother bar low within ±1 ATR(14) of 20-SMA or 50-SMA | Auto-scales by volatility. | ✓ |
| Mother bar low within ±3% of 20-SMA or 50-SMA | Fixed band. | |
| Any of 5 bars overlaps SMA geometrically | Bar/SMA overlap test. | |

**User's choice:** ATR-based band on mother bar low.

### Filter combination

| Option | Description | Selected |
|--------|-------------|----------|
| Strict AND, all 3 must pass; record per-filter pass/fail | Strict gate with debugging metadata. | ✓ |
| Scored: emit if ≥ 2 pass | More detections, lower precision. | |
| Strict AND, no per-filter breakdown | Cleanest schema, less analytic depth. | |

**User's choice:** strict AND with per-filter booleans recorded.

### Above 50-SMA timing

| Option | Description | Selected |
|--------|-------------|----------|
| Close of confirmation bar > 50-SMA at confirmation index | Single-point check at detection moment. | ✓ |
| All 5 bars' closes > 50-SMA | Stricter; rejects pullback springs. | |
| Mother bar close > 50-SMA only | Anchors at pattern start. | |

**User's choice:** check at confirmation bar.

---

## Detection record schema

### Spring vs full pattern class label

| Option | Description | Selected |
|--------|-------------|----------|
| Single class with `is_spring: bool` field | One YOLO class, metadata flag. | ✓ |
| Two classes: spring and full_5bar | Doubles per-class sample requirement. | |
| Single class, no spring metadata | Loses domain distinction. | |

**User's choice:** single class + boolean. Resolves the v2.0 open question.

### Schema fields per detection

| Option | Description | Selected |
|--------|-------------|----------|
| Core + per-filter flags + 5-bar OHLC + dates + indices + sma/atr levels | Rich; serves Phases 8/9/11 without recomputation. | ✓ |
| Minimal: ticker, confirmation_date, type, is_spring, 5 OHLC tuples | Forces downstream recomputation. | |
| Full + a `quality_score` (0–1) | Pre-computed confidence signal; conflicts with model confidence. | |

**User's choice:** full + per-filter flags. No quality_score (deferred).

### Code representation

| Option | Description | Selected |
|--------|-------------|----------|
| Python `@dataclass(frozen=True)` Detection + to_dict() | Type-safe, no new deps. | ✓ |
| Plain dict throughout | Simplest, no type safety. | |
| Pydantic BaseModel | Adds dependency; overkill for internal schema. | |

**User's choice:** frozen dataclass.

---

## Module API + manual validation harness

### Public API shape

| Option | Description | Selected |
|--------|-------------|----------|
| Single pure function `detect(df, ticker) → list[Detection]` | Pure, easy to test, easy to import. | ✓ |
| Class `InsideBarDetector` with config + .scan() | Stateful, supports parameter sweeps. | |
| Function + DetectorConfig dataclass (default singleton) | Compromise; tunable when needed. | |

**User's choice:** pure function.

### Standalone data source

| Option | Description | Selected |
|--------|-------------|----------|
| yfinance live in `__main__` block, ticker via CLI arg | Simple; reuses yfinance idiom. | ✓ |
| Cached parquet fixtures in `_dev/pattern_fixtures/` | Deterministic, no network. | |
| Both: --ticker (live) or --fixture (parquet) | Most flexible; two code paths. | |

**User's choice:** yfinance live via CLI; no fixture path in this phase.

### Validation harness

| Option | Description | Selected |
|--------|-------------|----------|
| pytest file `tests/test_detector_known_setups.py` with 5 hand-curated cases | Reproducible regression suite. | ✓ |
| Standalone script printing pass/fail | Lower ceremony; easy to forget to run. | |
| Jupyter notebook with annotated charts | Visual; not automatable. | |

**User's choice:** pytest file. Notebook deferred as nice-to-have.

### Setup curation

| Option | Description | Selected |
|--------|-------------|----------|
| User curates 5 picks now | Most reliable ground truth. | |
| Claude proposes 5 candidates from notable S&P 500 charts; user confirms | Faster; user is final gate. | ✓ |
| Run detector on all S&P 500 over 10y; eyeball top 5 | Bootstraps; circular validation. | |

**User's choice:** Claude proposes; user approves before encoding.

---

## Claude's Discretion

- Helper function names beyond the public API.
- ATR formula variant (Wilder vs simple) — pick one and document.
- Optional `detect_one_window(df, end_idx, ticker)` helper if it simplifies Phase 8 annotation.
- CLI output format for `__main__` (JSON dump assumed).

## Deferred Ideas

- Quality-score field on detections (Phase 8 model confidence supersedes).
- Two YOLO classes (revisit if training underperforms).
- Visual notebook-based validation.
- Parquet fixture caching for tests.
- Configurable thresholds / parameter sweeps.
