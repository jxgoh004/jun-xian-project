# Phase 7: Detection Engine — Research

**Researched:** 2026-05-02
**Domain:** Pure-Python rule-based candlestick pattern detection with no-look-ahead trend filters; first formal pytest harness for the repo
**Confidence:** HIGH

---

## Summary

Phase 7 builds a single-file detection module `scripts/pattern_scanner/detector.py` exposing one public function `detect(df, ticker) -> list[Detection]`. The CONTEXT.md document already locks every algorithmic threshold (D-01 through D-16): pin / mark-up / ice-cream confirmation rules, inside-bar definition, 60-bar HH/HL filter via 5-bar fractal pivots, 20-/50-SMA cluster within ±1·ATR(14), and the 5-bar window with the spring case (break-below bar == confirmation bar). Research therefore concentrates on the *implementation-level* discretionary choices — ATR variant, pivot iteration style, no-look-ahead enforcement idioms, the new `tests/` harness, and yfinance offline fallback — plus the Validation Architecture and security sections required by GSD.

The dominant technical risk is silent look-ahead leakage. pandas `.rolling()` is forward-anchored by default and is correct here, but any computation that touches `df` *outside* the `df.iloc[:end_idx + 1]` slice — including helpers that compute "the SMA at the mother bar" by indexing the full-frame SMA series — will leak future bars in subtle ways. The prescriptive rule is: **slice first, compute on the slice, read the last value.** Tests must include a regression that re-runs `detect()` on a truncated frame and asserts the same set of detections is emitted up to that cutoff.

**Primary recommendation:** Use `yf.Ticker(ticker).history(period="10y", auto_adjust=True)` for the `__main__` fetch (returns flat-column DataFrame, unlike `yf.download` which returns a MultiIndex). Use Wilder-smoothed ATR(14) (industry-standard "true ATR"). Use `pytest>=8.4,<9` with a `network` marker that auto-skips when a `--no-network` flag or an offline env var is set. Compute SMA/ATR vectorised on the truncated slice; iterate bar-by-bar only for swing pivots, mother-bar identification, and confirmation-window scanning.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Confirmation bar definitions (D-01 — D-04):**
- D-01 Pin: `open >= L + (2/3)*(H-L) AND close >= L + (2/3)*(H-L)`. Colour irrelevant. Inclusive `>=`.
- D-02 Mark-up: `(close - open) >= (2/3)*(H-L) AND close > open`. Strictly bullish, body ≥ 2/3 of range.
- D-03 Ice-cream: `min(open, close) <= L + 0.5*(H-L) AND close >= L + (1/3)*(H-L) AND close > open`.
- D-04 Inside bar: `H_inside < H_mother AND L_inside > L_mother`. Strict inequality on both sides.

**Trend filters (D-05 — D-08):**
- D-05 HH/HL: 5-bar fractal swing-pivots over 60-bar lookback ending at pattern-end bar; pass when last 2 swing highs ascending **AND** last 2 swing lows ascending.
- D-06 Above 50-SMA: `close[confirmation_bar] > sma_50[confirmation_bar]` (single point check at confirmation timing).
- D-07 SMA cluster: `mother_bar_low` within ±1·ATR(14) of either 20-SMA OR 50-SMA evaluated at the mother-bar index.
- D-08 All three filters strict-AND for emission; per-filter booleans still recorded.

**Pattern cluster rule:** Bar 1 = mother bar; Bar 2 = inside bar; within next 3 bars a bar breaks below mother low; that break-below bar OR a subsequent bar (still within 5-bar window) closes inside the mother range as one of the three confirmation types. Spring case: break-below and confirmation may be the **same** bar.

**Schema (D-09 — D-11):**
- D-09 Single class `inside_bar_spring` with `is_spring: bool` field (NOT split into two classes).
- D-10 Detection record fields: `ticker, confirmation_date, confirmation_type ("pin"|"mark_up"|"ice_cream"), is_spring, bars[5] (date/O/H/L/C, mother→confirmation), mother_bar_index, confirmation_bar_index, filters{hh_hl,above_50sma,sma_cluster}, sma_levels{sma20,sma50,atr14}`. NO quality_score.
- D-11 `@dataclass(frozen=True)` named `Detection` with `to_dict()` (or `dataclasses.asdict()`). No new dependencies.

**API (D-12 — D-14):**
- D-12 Public: `detect(df: pd.DataFrame, ticker: str) -> list[Detection]`. Helpers leading-underscore snake_case.
- D-13 `__main__`: `python scripts/pattern_scanner/detector.py AAPL` fetches 10y daily via yfinance and prints detections.
- D-14 No-look-ahead: All computations must use `df.iloc[:confirmation_idx + 1]`; tests must include a regression on trailing in-progress patterns.

**Validation harness (D-15 — D-16):**
- D-15 `tests/test_detector_known_setups.py` with pytest. Each case: `(ticker, expected_confirmation_date, expected_type, expected_is_spring)`. Assert: detection exists at the expected date with matching type+spring; no detection on adjacent bars.
- D-16 Claude proposes 5 candidate setups during execution; user reviews/approves; ≥ 2 distinct types and ≥ 1 spring case.

### Claude's Discretion

- Specific helper function names beyond the public API
- Dataclass field ordering and JSON serialisation format details (snake_case keys preferred)
- Internal representation of swing pivots (named tuples, lists, etc.)
- ATR formula variant (Wilder vs simple) — pick one and document
- CLI output format for `__main__` (likely JSON dump for machine readability)
- Whether to also expose `detect_one_window(df, end_idx, ticker)` helper for Phase 8 per-window training annotation

### Deferred Ideas (OUT OF SCOPE)

- Quality score per detection (Phase 8 model confidence is canonical)
- Two YOLO classes (spring vs full 5-bar) — re-evaluate after first training run
- Notebook visual validation
- Parquet fixture caching (only if live yfinance test becomes flaky)
- Parameter sweeps / configurable thresholds
- Edge case: stock splits / IPOs with <60 bars — yfinance auto_adjust handles splits; insufficient history → zero detections, no special-casing

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-01 | Detect bullish inside bar spring setups using the 5-bar ruleset (mother → inside → break-below within 3 → confirmation as Pin / Mark-up / Ice-cream) | Confirmation predicates encoded per D-01..D-03; inside-bar per D-04; window scan in §"Pattern scan loop" below |
| DET-02 | Handle the spring case (break-below bar == confirmation bar) | §"Pattern scan loop" treats the break-below bar as a candidate confirmation; `is_spring = (break_idx == confirmation_idx)` |
| DET-03 | Trend filters evaluated at pattern-end bar with no look-ahead | §"No-look-ahead enforcement"; `df.iloc[:confirmation_idx + 1]` slice + read last value pattern |
| DET-04 | Output structured detections with ticker, confirmation date, confirmation type, and 5-bar OHLC context | `Detection` dataclass per D-10; `to_dict()` for JSON |

---

## Project Constraints (from CLAUDE.md)

Extracted directives the planner MUST honor:

| Directive | Source | Implication for Phase 7 |
|-----------|--------|--------------------------|
| Python 3, snake_case modules and functions | CLAUDE.md tech stack + CONVENTIONS.md | `scripts/pattern_scanner/detector.py`, `_is_pin()`, `_compute_atr()`, etc. |
| PascalCase classes | CONVENTIONS.md | `Detection` dataclass |
| No AI co-author in commits | MEMORY.md `feedback_git_attribution.md` | Use git-attribution-guard before committing; **no `Co-Authored-By: Claude` trailers** |
| Use `.venv` for Python | MEMORY.md `feedback_venv.md` | All `python`/`pip`/`pytest` commands must run inside `.venv` (Windows: `source .venv/Scripts/activate`) |
| Existing `requirements.txt` is sufficient | CONTEXT.md code_context | No new runtime deps; pytest is dev-only |
| `_dev/` is research artefacts; `tests/` is the new formal home | CONTEXT.md code_context | First `tests/` directory at repo root; not in `_dev/` |
| MCP tools (code-review-graph) preferred over Grep/Glob/Read in agents | CLAUDE.md MCP table | Implementation agent should use `query_graph` / `semantic_search_nodes` when navigating existing code |

---

## Standard Stack

### Core (already pinned in `requirements.txt`)

| Library | Verified version | Purpose | Why standard |
|---------|------------------|---------|--------------|
| pandas | 3.0.2 (verified in `.venv` 2026-05-02) | DataFrame operations, `.rolling()`, `.iloc[]` slicing | Existing project dep; the rule "slice df then compute" is a one-liner in pandas |
| numpy | 2.4.4 (verified) | Vectorised arithmetic for True Range / band checks | Existing project dep |
| yfinance | 0.2.65 (verified) | Daily OHLC for `__main__` and tests | Existing project dep; matches `yahoo_finance_fetcher.py` idiom |

### Supporting (NEW dev-only dependencies)

| Library | Version | Purpose | When to use |
|---------|---------|---------|-------------|
| pytest | `>=8.4,<9` (latest 8.x stable as of May 2026 is 8.4.2) | Test runner for `tests/test_detector_known_setups.py` | Dev-only; goes in a new `requirements-dev.txt`, NOT `requirements.txt` |

[VERIFIED: `pip index versions pytest` shows 9.0.3 latest; pytest 8.4.2 published 2025-09-04 (Sep 4 2025) per pytest changelog] [CITED: https://docs.pytest.org/en/stable/changelog.html]

**Why pin to 8.x (not 9.x):** pytest 9.0 was released ~April 2026 (one month before this research). Pinning to 8.x avoids any 9.0 breaking-change risk while keeping a recent stable line. If the planner prefers 9.x, document the choice; the test patterns used here (markers, skipif, conftest) are stable across 8.x and 9.x.

**No other new deps.** The detector is pure pandas/numpy/dataclasses/`json`. mplfinance, onnxruntime, ultralytics arrive in Phase 8+.

### Alternatives Considered

| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| Plain `@dataclass` | Pydantic `BaseModel` | Pydantic adds runtime validation but introduces a new dependency for a problem dataclasses already solve. CONTEXT D-11 explicitly rules it out. |
| `pytest` | `unittest` (stdlib, no install) | unittest works but has weaker fixtures/markers; project intent in D-15 is pytest; weight of community + GSD ecosystem favours pytest. |
| `pandas-ta` / `ta-lib` for ATR | hand-rolled Wilder ATR (~15 lines) | New dependency for a 15-line function; ta-lib has C-extension install pain on Windows. Reject. |
| `yf.download(ticker, ...)` | `yf.Ticker(ticker).history(...)` | `yf.download` returns **MultiIndex columns** even for a single ticker (verified empirically — columns become `[('Close','AAPL'), ...]`). `Ticker.history()` returns flat columns. Use `Ticker.history()`. |

**Installation (planner action — Wave 0):**
```bash
# Inside .venv
pip install "pytest>=8.4,<9"
# Add to NEW file requirements-dev.txt — do NOT add to requirements.txt
```

**Version verification (HIGH confidence):**
- pandas 3.0.2 — verified `python -c "import pandas; print(pandas.__version__)"` in `.venv` on 2026-05-02
- numpy 2.4.4 — same
- yfinance 0.2.65 — same; matches `requirements.txt` pin
- pytest 8.4.2 — latest stable in 8.x line per pytest changelog [CITED: https://docs.pytest.org/en/stable/changelog.html]

---

## Architecture Patterns

### Recommended Project Structure

```
scripts/
└── pattern_scanner/
    ├── __init__.py             # empty (or re-export Detection, detect)
    └── detector.py             # ~250-350 lines; the whole phase

tests/
├── __init__.py                 # empty — makes pytest treat as package (optional)
├── conftest.py                 # shared fixtures: pytest_addoption(--no-network), yfinance fetch helper, network skip
└── test_detector_known_setups.py   # the 5 known-setup regression cases + a no-look-ahead regression case

requirements-dev.txt             # NEW — pytest>=8.4,<9
pytest.ini                       # NEW — registers `network` marker, sets testpaths=tests
```

### Pattern 1: One-frame slice, vectorised compute, scalar read

The single most important idiom for Phase 7. Every filter that needs "value at index `k`" must:

1. Slice the frame: `view = df.iloc[:k + 1]` (history up to and **including** bar `k`).
2. Compute the indicator vectorised on `view`: `sma20 = view["Close"].rolling(20).mean()`.
3. Read the last value: `sma20_at_k = sma20.iloc[-1]`.

Never compute the indicator on the full `df` and then index `[k]` — even though pandas `.rolling()` is past-only by default and would give the same numeric answer here, the slice-first habit eliminates the entire class of look-ahead bugs and makes every reviewer's job trivial. [ASSUMED: pandas `.rolling().mean()` is past-anchored; verified by reading pandas docs — see Sources]

```python
# Source: pattern derived from pandas .rolling() docs
def _compute_sma(close: pd.Series, period: int) -> pd.Series:
    """SMA over a closing-price series. Caller must pre-slice."""
    return close.rolling(window=period, min_periods=period).mean()
```

### Pattern 2: Wilder ATR(14)

[CITED: https://www.macroption.com/atr-calculation/] Wilder's ATR uses a recursive smoothing:
- Bar 1: `ATR_1 = TR_1`
- Bar 2..13: bootstrap as simple mean of TR so far, OR define `ATR_14 = mean(TR[0:14])` and recurse from there
- Bar n ≥ 15: `ATR_n = (ATR_{n-1} * 13 + TR_n) / 14`

This is the **industry-standard** "true ATR" — it's what TradingView, Bloomberg, and most charting platforms emit when a user requests "ATR(14)". A simple 14-bar rolling mean of TR is a defensible alternative but is *not* what most practitioners mean by ATR. **Recommendation: use Wilder.** Document the choice in a docstring.

True Range formula:
```
TR = max(
    H - L,
    abs(H - prev_close),
    abs(L - prev_close)
)
```

```python
# Source: Wilder's New Concepts in Technical Trading Systems (1978), as encoded in macroption.com & tulipindicators.org
def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder-smoothed ATR(14). Caller must pre-slice df to the desired endpoint."""
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Wilder smoothing == EMA with alpha = 1/period (adjust=False)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return atr
```

The `ewm(alpha=1/period, adjust=False)` form is mathematically equivalent to Wilder's recursion and is one line. [VERIFIED: pandas docs `DataFrame.ewm` — `adjust=False` selects the recursive form; `alpha=1/N` matches Wilder's smoothing factor 1/N.] [CITED: https://www.macroption.com/atr-calculation/]

### Pattern 3: 5-bar fractal swing pivot detection

A swing high at bar `i` requires bars `i-2, i-1, i+1, i+2` all to have lower highs. Symmetric for lows. Iterate bar by bar — there is no clean vectorised form because each pivot needs 2 bars on **each** side, and at the lookback window's right edge we naturally have only 0-1 bars on the right (those bars cannot yet be pivots and that is **correct** — confirming a swing requires 2 bars of forward confirmation, which is **inherent past-only logic and is NOT a look-ahead violation** when scanning historical data up to bar `k`).

```python
# Source: standard Bill Williams fractal pattern, well documented in TA literature
def _swing_pivots(view: pd.DataFrame) -> tuple[list[int], list[int]]:
    """Return (swing_high_idx_list, swing_low_idx_list) within view (positional indices)."""
    highs = view["High"].values
    lows = view["Low"].values
    n = len(view)
    swing_highs, swing_lows = [], []
    for i in range(2, n - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] \
           and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            swing_highs.append(i)
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] \
           and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            swing_lows.append(i)
    return swing_highs, swing_lows


def _hh_hl_uptrend(view: pd.DataFrame) -> bool:
    """Pass when the last 2 swing highs ascending AND last 2 swing lows ascending (D-05)."""
    sh, sl = _swing_pivots(view)
    if len(sh) < 2 or len(sl) < 2:
        return False
    return (view["High"].iloc[sh[-1]] > view["High"].iloc[sh[-2]]
            and view["Low"].iloc[sl[-1]] > view["Low"].iloc[sl[-2]])
```

**On strict vs non-strict comparisons:** Use strict `>` / `<`. Equal highs/lows do not constitute pivots. This matches the inside-bar definition's strict inequality (D-04).

### Pattern 4: Pattern scan loop with spring handling

```python
# Pseudocode — final implementation will replace these comments with real code
def detect(df: pd.DataFrame, ticker: str) -> list[Detection]:
    detections = []
    n = len(df)
    if n < 60:                              # need 60 bars for HH/HL filter (D-05)
        return detections

    # Iterate candidate mother-bar indices; need room for 5-bar window AND 60-bar history.
    # Earliest mother bar must satisfy: 60-bar history available at the confirmation bar.
    # Confirmation bar = mother + (1..4); minimum is mother + 1 (spring shares the inside bar — actually mother+2 minimum after inside bar, see below).
    for mother_idx in range(60, n - 4):     # leave 4 bars of forward window
        if not _inside_bar(df.iloc[mother_idx], df.iloc[mother_idx + 1]):
            continue
        mother_low = df.iloc[mother_idx]["Low"]

        # Scan bars (mother+2) .. (mother+4): look for first break-below.
        # Spring case: break-below bar IS the confirmation bar.
        # Full case: break-below bar is followed by a confirmation bar still inside the 5-bar window.
        for break_offset in range(2, 5):
            break_idx = mother_idx + break_offset
            if break_idx >= n:
                break
            if df.iloc[break_idx]["Low"] >= mother_low:
                continue                     # not a break-below; keep scanning
            # Try this bar as confirmation (spring case)
            for conf_idx in range(break_idx, min(mother_idx + 5, n)):
                conf_type = _classify_confirmation(df.iloc[conf_idx])
                if conf_type is None:
                    continue
                # Confirmation must close back inside mother range
                if not (mother_low < df.iloc[conf_idx]["Close"] < df.iloc[mother_idx]["High"]):
                    continue
                # Apply trend filters with no-look-ahead slice ending at conf_idx
                detection = _build_detection(
                    df=df, ticker=ticker,
                    mother_idx=mother_idx, break_idx=break_idx, conf_idx=conf_idx,
                    conf_type=conf_type,
                    is_spring=(break_idx == conf_idx),
                )
                if detection.filters["hh_hl"] and detection.filters["above_50sma"] and detection.filters["sma_cluster"]:
                    detections.append(detection)
                break    # one confirmation per break-below; move on
            break        # one break-below window per mother bar; move on
    return detections
```

**Note on the 5-bar window minimum:** Bar 1 = mother, Bar 2 = inside. So the earliest break-below is bar 3 (offset 2 from mother). The earliest spring-case confirmation is bar 3 (break_idx == conf_idx). The latest confirmation is bar 5 (offset 4). Code uses `range(2, 5)` for break offsets and `range(break_idx, min(mother_idx + 5, n))` for confirmation scan.

### Anti-Patterns to Avoid

- **Computing SMA/ATR on the full frame and indexing into the result.** Even though pandas `.rolling()` is past-only and the *value* at bar `k` is correct, this disguises look-ahead in the codebase mental model and makes any *future* refactor (centred rolling, lookahead helpers) silently catastrophic. Slice first, always.
- **Using `.shift(-1)` anywhere.** Negative shift is the canonical look-ahead operator. There is zero legitimate use of negative shift in this module. A grep for `shift(-` should be a CI fail.
- **Mutating `df` in place.** `detect()` is pure. Any internal sort/dropna must operate on a copy.
- **Catching broad `Exception` and swallowing.** Existing codebase has this pattern in fetchers (acceptable for optional data sources). The detector is deterministic — let exceptions propagate. Only the `__main__` CLI block should catch and pretty-print.
- **Hard-coding fixture file paths in tests.** Use pytest tmp_path / `Path(__file__).parent` for any fixture files; never absolute paths.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Wilder ATR smoothing | Custom recursive loop with bootstrap | `series.ewm(alpha=1/14, adjust=False, min_periods=14).mean()` on the True Range series | One pandas line, mathematically equivalent, no off-by-one risk |
| Rolling mean (SMA) | Manual sliding-window loop | `series.rolling(window=N, min_periods=N).mean()` | Vectorised, NaN-aware, the obvious choice |
| Date arithmetic for ISO confirmation_date | Manual string manipulation | `df.index[conf_idx].strftime("%Y-%m-%d")` | DatetimeIndex already exposes strftime |
| MultiIndex column unwrapping | Manual `df.columns.get_level_values(0)` | Use `yf.Ticker(t).history()` instead of `yf.download(t)` | The flat-column variant exists; just use it |
| Test fixtures with cached data | Hand-rolled CSV/parquet caching | yfinance live fetch in tests; cache only if proven flaky (CONTEXT defers parquet caching) | Network calls are 1-2s for a single 10y fetch; acceptable for 5 test cases |

**Key insight:** The detector is rule-based and the rules are locked. The single most common mistake is reaching for an indicator library (pandas-ta, ta-lib, talib-binary) for ATR — but ATR via `.ewm()` is one line and adds zero dependency surface.

---

## Runtime State Inventory

> Phase 7 is greenfield (creates new files). No rename / migration / refactor of existing runtime state.

| Category | Items found | Action required |
|----------|-------------|-----------------|
| Stored data | None — verified by Glob `scripts/pattern_scanner/**`, no existing module | None |
| Live service config | None — pure-Python module, no external service registration | None |
| OS-registered state | None — no Task Scheduler / systemd / pm2 entries created in this phase (Phase 10 handles GH Actions cron) | None |
| Secrets/env vars | None — yfinance is unauthenticated; no API keys | None |
| Build artifacts / installed packages | New `tests/` and `scripts/pattern_scanner/` packages — no compiled artifacts; pytest installs into `.venv` only | After `pip install pytest`, no further action; rerunning `pip install -r requirements.txt` will not affect dev deps |

---

## Common Pitfalls

### Pitfall 1: yfinance MultiIndex columns from `yf.download`
**What goes wrong:** Code written as `df["Close"]` works locally with `Ticker.history()` but fails (KeyError or unexpected MultiIndex behaviour) when someone swaps in `yf.download()`.
**Why it happens:** `yf.download(ticker, ...)` returns MultiIndex columns even for a single ticker — verified empirically: columns are `[('Close','AAPL'), ('High','AAPL'), ...]`.
**How to avoid:** Use `yf.Ticker(ticker).history(period="10y", auto_adjust=True)` in `__main__`. Document the contract: `detect(df, ticker)` requires flat columns named exactly `Open / High / Low / Close`. Add a defensive assert at the top of `detect()`.
**Warning signs:** Test fails with KeyError on `df["Close"]` or returns empty results because comparison `df["Close"] > sma` returns an unexpected DataFrame.
[VERIFIED: empirical probe in `.venv` on 2026-05-02]

### Pitfall 2: Look-ahead via full-frame indicator computation
**What goes wrong:** Developer computes `df["sma_50"] = df["Close"].rolling(50).mean()` once, then indexes `df["sma_50"].iloc[mother_idx]` inside the loop. Numerically correct *today*, but invisibly couples filter values to assumptions about how the frame was constructed.
**Why it happens:** It's the obvious vectorised idiom and 99% of the time it gives the right answer. The 1% where it doesn't (e.g., a future refactor adding `.rolling(window=N, center=True)`, or a test that prepends future bars) is silent.
**How to avoid:** Always `view = df.iloc[:end_idx + 1]; sma = view["Close"].rolling(50).mean().iloc[-1]`. Add a regression test: detect on `df` produces the same detection at date `D` as detect on `df.loc[:D]`.
**Warning signs:** Different detections appear when the input frame has different right-edge truncation.

### Pitfall 3: NaN handling at series start
**What goes wrong:** First 50 bars have NaN SMA; first 14 have NaN ATR; first 4 cannot have pivots. Comparisons like `close > sma_50` against NaN return False, but `mother_bar_low - atr14` returns NaN and a band-membership check `(sma20 - atr14) <= mother_low <= (sma20 + atr14)` against NaN is silently False.
**Why it happens:** pandas/numpy NaN semantics; arithmetic with NaN produces NaN, comparisons with NaN return False.
**How to avoid:** Skip mother indices < 60 (CONTEXT D-05 already requires 60-bar HH/HL history; this is also enough for SMA-50 and ATR-14 to be defined). Add an explicit `if math.isnan(sma_50) or math.isnan(atr14): continue` guard before applying filters.
**Warning signs:** Detections never emit on tickers with < 60-bar history (correct — see Deferred Ideas in CONTEXT). Tickers with adequate history but NaN issues at the edge are a bug, not a config gap.

### Pitfall 4: Weekend/holiday gap behaviour
**What goes wrong:** Tester expects "5 calendar days after the mother bar" but yfinance returns trading days only.
**Why it happens:** yfinance daily bars are trading days; Mon-Fri excluding US holidays.
**How to avoid:** Treat "5 bars" as "5 trading bars" throughout — that is what CONTEXT means. Document in the dataclass docstring: "5-bar window = 5 consecutive trading bars (no calendar-day interpretation)." Test fixture confirmation_date assertions use the actual yfinance trading-day index value.
**Warning signs:** Tests fail because the expected confirmation_date falls on a weekend or holiday in the user's mental model.

### Pitfall 5: Filter coupling — emission depends on AND, but record stores per-filter booleans
**What goes wrong:** Developer mis-reads D-08 ("strict AND for emission") and short-circuits filter computation, so the `filters` dict has `{hh_hl: True, above_50sma: False, sma_cluster: None}` because the third was never evaluated.
**Why it happens:** Premature optimisation; "if any filter fails, skip the rest" feels efficient.
**How to avoid:** Always evaluate all three filters before deciding emission. Record all three booleans. Only the emission decision uses AND. Per-filter booleans are persisted (D-10) so Phase 8/9/11 can stratify; missing or `None` values defeat that purpose.
**Warning signs:** Detection records have any `None` or missing key in the `filters` dict.

### Pitfall 6: pytest discovery in a project with `_dev/test_*.py`
**What goes wrong:** Running `pytest` from repo root tries to collect `_dev/test_yahoo_finance.py` and `_dev/test_finviz.py` (older non-pytest scripts) and fails or runs unintended tests.
**Why it happens:** pytest's default discovery walks the whole tree.
**How to avoid:** Create `pytest.ini` (or `pyproject.toml [tool.pytest.ini_options]`) with `testpaths = tests`. This restricts collection to the new `tests/` directory. Also register the `network` marker to suppress the unknown-marker warning.
**Warning signs:** `pytest` from repo root collects more tests than the file count in `tests/` or emits "PytestUnknownMarkWarning".

### Pitfall 7: yfinance flakiness in CI / first run
**What goes wrong:** Live yfinance call returns rate-limit error or empty frame; test fails with cryptic message.
**Why it happens:** Yahoo rate-limits aggressive access; yfinance does its own retry but not always enough.
**How to avoid:** Use `pytest.mark.network` on tests that hit yfinance. Add a `--no-network` CLI option (or `PYTEST_OFFLINE=1` env var) to `conftest.py` that auto-skips network-marked tests. Tests run live by default in dev; local devs can `pytest --no-network` for offline iteration. Phase 10 CI will use offline fixtures (out of scope here, deferred per CONTEXT).
**Warning signs:** Tests fail with empty DataFrame, KeyError on Close, or HTTPError 429.
[CITED: https://docs.pytest.org/en/stable/example/markers.html on custom marker registration; https://docs.pytest.org/en/stable/how-to/skipping.html on conditional skip]

---

## Code Examples

Verified patterns ready for the planner to translate into tasks.

### Example 1: Confirmation classifier (D-01..D-03)

```python
# Source: encoded directly from CONTEXT D-01..D-03
def _is_pin(bar) -> bool:
    rng = bar["High"] - bar["Low"]
    if rng <= 0:
        return False
    upper_third = bar["Low"] + (2.0 / 3.0) * rng
    return bar["Open"] >= upper_third and bar["Close"] >= upper_third


def _is_mark_up(bar) -> bool:
    rng = bar["High"] - bar["Low"]
    if rng <= 0:
        return False
    body = bar["Close"] - bar["Open"]
    return body >= (2.0 / 3.0) * rng and bar["Close"] > bar["Open"]


def _is_ice_cream(bar) -> bool:
    rng = bar["High"] - bar["Low"]
    if rng <= 0:
        return False
    body_low = min(bar["Open"], bar["Close"])
    midpoint = bar["Low"] + 0.5 * rng
    upper_third = bar["Low"] + (1.0 / 3.0) * rng
    return (body_low <= midpoint
            and bar["Close"] >= upper_third
            and bar["Close"] > bar["Open"])


def _classify_confirmation(bar) -> Optional[str]:
    """Return 'pin' | 'mark_up' | 'ice_cream' | None. Order matters only if a bar matches multiple — document precedence in tests."""
    if _is_pin(bar):
        return "pin"
    if _is_mark_up(bar):
        return "mark_up"
    if _is_ice_cream(bar):
        return "ice_cream"
    return None
```

### Example 2: Inside bar (D-04)

```python
# Source: CONTEXT D-04 — strict less-than/greater-than on both sides
def _inside_bar(mother, child) -> bool:
    return child["High"] < mother["High"] and child["Low"] > mother["Low"]
```

### Example 3: Detection dataclass (D-10, D-11)

```python
# Source: CONTEXT D-10 / D-11 — frozen dataclass with to_dict()
from dataclasses import dataclass, asdict, field
from typing import List, Dict


@dataclass(frozen=True)
class Detection:
    ticker: str
    confirmation_date: str          # ISO YYYY-MM-DD
    confirmation_type: str          # "pin" | "mark_up" | "ice_cream"
    is_spring: bool
    bars: List[Dict]                # [{date, open, high, low, close}, ...] mother → confirmation
    mother_bar_index: int
    confirmation_bar_index: int
    filters: Dict[str, bool]        # {hh_hl, above_50sma, sma_cluster}
    sma_levels: Dict[str, float]    # {sma20, sma50, atr14}

    def to_dict(self) -> Dict:
        return asdict(self)
```

### Example 4: yfinance fetch in `__main__` (D-13)

```python
# Source: matches yahoo_finance_fetcher.py idiom; uses Ticker.history (flat columns)
import sys
import json
import yfinance as yf


def _fetch_ohlc(ticker: str, period: str = "10y") -> "pd.DataFrame":
    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]   # drop Volume / Dividends / Stock Splits
    df.index = df.index.tz_localize(None)        # strip America/New_York → naive datetime
    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/pattern_scanner/detector.py <TICKER>", file=sys.stderr)
        sys.exit(1)
    ticker = sys.argv[1].upper()
    df = _fetch_ohlc(ticker)
    detections = detect(df, ticker)
    print(json.dumps([d.to_dict() for d in detections], indent=2, default=str))
```

[VERIFIED 2026-05-02: `yf.Ticker('AAPL').history(period='10d', auto_adjust=True)` returned a 7-column flat-column DataFrame with `DatetimeIndex` tz=America/New_York. The tz_localize(None) line normalises to naive timestamps consistent with `confirmation_date` formatting downstream.]

### Example 5: pytest `conftest.py` with network marker

```python
# tests/conftest.py
# Source: pytest custom marker pattern from official docs
import os
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--no-network",
        action="store_true",
        default=False,
        help="Skip tests that require live yfinance / network access.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "network: marks tests that require live network access (yfinance fetch).",
    )


def pytest_collection_modifyitems(config, items):
    no_network = config.getoption("--no-network") or os.environ.get("PYTEST_OFFLINE") == "1"
    if not no_network:
        return
    skip_marker = pytest.mark.skip(reason="--no-network or PYTEST_OFFLINE=1 set")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_marker)
```

```ini
# pytest.ini
[pytest]
testpaths = tests
markers =
    network: tests that require live yfinance / network access
```

[CITED: https://docs.pytest.org/en/stable/example/markers.html — `pytest_addoption`, `pytest_collection_modifyitems`, `pytest_configure` are the canonical pytest hooks for adding CLI options and registering markers.]

### Example 6: Test case shape (D-15)

```python
# tests/test_detector_known_setups.py
# Source: encoded from CONTEXT D-15
import pytest
import yfinance as yf

from scripts.pattern_scanner.detector import detect


KNOWN_SETUPS = [
    # (ticker, expected_confirmation_date, expected_type, expected_is_spring)
    # Filled in by Claude during execution per D-16, then user-approved.
    # ("AAPL", "2020-04-02", "mark_up", False),
    # ...
]


@pytest.mark.network
@pytest.mark.parametrize("ticker, expected_date, expected_type, expected_spring", KNOWN_SETUPS)
def test_known_setup_is_detected(ticker, expected_date, expected_type, expected_spring):
    df = yf.Ticker(ticker).history(period="10y", auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    df.index = df.index.tz_localize(None)
    detections = detect(df, ticker)

    matched = [d for d in detections if d.confirmation_date == expected_date]
    assert matched, f"No detection found at {expected_date} for {ticker}"
    d = matched[0]
    assert d.confirmation_type == expected_type
    assert d.is_spring is expected_spring


@pytest.mark.network
@pytest.mark.parametrize("ticker, expected_date, _t, _s", KNOWN_SETUPS)
def test_no_detection_on_adjacent_bars(ticker, expected_date, _t, _s):
    # ... adjacent-bar negative regression
    pass


@pytest.mark.network
def test_no_lookahead_truncation_invariance():
    """detect(df) on truncated df reproduces the same detections up to the truncation date."""
    df = yf.Ticker("AAPL").history(period="2y", auto_adjust=True)[["Open","High","Low","Close"]]
    df.index = df.index.tz_localize(None)
    full = detect(df, "AAPL")
    cutoff = df.index[-30]
    truncated = detect(df.loc[:cutoff], "AAPL")
    expected = [d for d in full if d.confirmation_date <= cutoff.strftime("%Y-%m-%d")]
    # Filter expected to those with conf_idx + 4 <= cutoff_idx so the 5-bar window was complete on cutoff day
    # ... assertion
```

---

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| `yf.download(ticker, ...)` (returns MultiIndex columns since yfinance 0.2.x) | `yf.Ticker(ticker).history(...)` for single-ticker | yfinance ~0.2.20+ | Use `Ticker.history()` to get flat columns; saves a column-flattening step |
| ATR via TA-Lib C extension | ATR via pandas `ewm(alpha=1/14, adjust=False)` | pandas 1.0+ | One-line vectorised; no C extension to install on Windows |
| Manual rolling loops | `series.rolling(N, min_periods=N).mean()` | pandas 0.18+ | Default for SMA |
| `pytest --strict-markers` opt-in | Same — still opt-in but recommended | pytest 4.0+ | Adding `--strict-markers` to `pytest.ini` makes typos in `@pytest.mark.foo` immediate errors |

**Deprecated/outdated:**
- `pandas.DataFrame.append()` (removed in pandas 2.0) — use `pd.concat`. Not a concern here since the detector returns a `list[Detection]`, not a DataFrame.
- `yf.pdr_override()` (yfinance helper for pandas-datareader) — not used in this project; ignore.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | pytest `.rolling().mean()` is past-anchored (right-aligned) by default | Pattern 1 | LOW — universally documented pandas behaviour; would invalidate the "slice-first is equivalent to full-frame index" equivalence claim. Mitigation: the slice-first habit is correct regardless. |
| A2 | yfinance auto_adjust=True on `Ticker.history(period="10y")` returns split- and dividend-adjusted OHLC consistent across re-fetches for old dates | Code Example 4 | MEDIUM — yfinance occasionally back-revises for late corporate-action notices. Practical impact: a known-setup test fixture may need to re-anchor to a different date if yfinance updates an adjustment. CONTEXT D-15 already accepts this risk by allowing a parquet fixture if live calls become flaky. |
| A3 | Wilder ATR is the "right" choice over simple ATR | Pattern 2 | LOW — both produce valid filter behaviour; CONTEXT explicitly grants Claude discretion. Wilder is the conventional choice and is documented. |
| A4 | The first time-zone-naive `confirmation_date` representation in `Detection.confirmation_date` is the right format for downstream phases | Code Example 3 | LOW — D-10 specifies ISO YYYY-MM-DD string; tz-naive after `.strftime` is the natural fit. Phase 10 batch and Phase 11 frontend both consume strings. |
| A5 | The 5 known setups can be discovered from public S&P 500 history without exotic data sources | Validation Architecture | MEDIUM — relies on Claude's training data + chart-reading. CONTEXT D-16 explicitly puts user review in the loop, mitigating. |

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3 | All phase work | ✓ | (project venv) | — |
| pandas | Detector | ✓ | 3.0.2 | — |
| numpy | Detector | ✓ | 2.4.4 | — |
| yfinance | Detector `__main__`, tests | ✓ | 0.2.65 | If network unavailable in CI: `--no-network` flag skips tests; offline fixture (parquet) deferred per CONTEXT |
| pytest | Validation harness | ✗ | — | Install via `pip install pytest>=8.4,<9` in `.venv` (Wave 0 task) |
| Network access (Yahoo Finance) | yfinance live tests | likely ✓ in dev | — | `pytest --no-network` for offline iteration |

**Missing dependencies with no fallback:** None — pytest is installable on demand.

**Missing dependencies with fallback:** pytest (install in Wave 0).

[VERIFIED: probed `.venv` 2026-05-02 — pandas/numpy/yfinance present; pytest absent.]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.x (latest 8.x stable) |
| Config file | `pytest.ini` at repo root (NEW — Wave 0) |
| Quick run command | `pytest tests/ -x` (fail-fast; runs in `.venv`) |
| Full suite command | `pytest tests/ -v` |
| Offline run | `pytest tests/ --no-network` or `PYTEST_OFFLINE=1 pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|--------|----------|-----------|-------------------|--------------|
| DET-01 | 5-bar inside-bar spring detected with correct confirmation type | integration (live yfinance) | `pytest tests/test_detector_known_setups.py::test_known_setup_is_detected -x` | ❌ Wave 0 |
| DET-02 | Spring case (break == confirmation) detected; `is_spring=True` flagged | integration (live yfinance) | `pytest tests/test_detector_known_setups.py::test_known_setup_is_detected -x -k spring` (parametrized cases include ≥1 spring per D-16) | ❌ Wave 0 |
| DET-03 | No look-ahead — truncated frame reproduces same detections up to cutoff | integration (live yfinance) | `pytest tests/test_detector_known_setups.py::test_no_lookahead_truncation_invariance -x` | ❌ Wave 0 |
| DET-04 | Detection record contains all D-10 fields (ticker, confirmation_date, confirmation_type, is_spring, bars, indices, filters, sma_levels) | unit (no network — synthesises a tiny df) | `pytest tests/test_detector_schema.py::test_detection_has_required_fields -x` | ❌ Wave 0 |

**Negative regression** (covers D-15 second assertion): adjacent-bar non-detection — `pytest tests/test_detector_known_setups.py::test_no_detection_on_adjacent_bars`.

### Sampling rate

- **Per task commit:** `pytest tests/ -x --no-network` (unit tests only; <5s)
- **Per wave merge:** `pytest tests/ -v` (full live network suite; ~5-15s for 5 setups)
- **Phase gate:** Full suite green (`pytest tests/ -v` exit 0) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `requirements-dev.txt` — `pytest>=8.4,<9`
- [ ] `pytest.ini` — `testpaths = tests` and `network` marker registration
- [ ] `tests/__init__.py` — empty file (optional but conventional)
- [ ] `tests/conftest.py` — `--no-network` option, `network` marker auto-skip, shared `_fetch_ohlc` fixture
- [ ] `tests/test_detector_known_setups.py` — parametrized fixture; live yfinance integration tests
- [ ] `tests/test_detector_schema.py` — pure-unit test of `Detection` shape on a synthesised tiny DataFrame (no network) — covers DET-04 schema lock
- [ ] Framework install: `pip install -r requirements-dev.txt` inside `.venv`

---

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json`, so include this section. The detector is a pure-Python module with no network listeners and one user-controlled input: the CLI ticker arg.

### Applicable ASVS L1 Categories

| ASVS Category | Applies | Standard control |
|---------------|---------|-------------------|
| V2 Authentication | no | yfinance is unauthenticated; no project secrets touched |
| V3 Session Management | no | no sessions |
| V4 Access Control | no | no access boundaries |
| V5 Input Validation | yes | CLI ticker arg → must be uppercase alphanumeric (with allowed `-` and `.`) before being passed to yfinance |
| V6 Cryptography | no | no crypto operations; no secrets |
| V8 Data Protection | no | no PII; OHLC is public market data |
| V14 Configuration | yes | New `pytest.ini`, `requirements-dev.txt`; ensure no secrets baked in |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---------|--------|----------------------|
| Ticker arg shell injection | Tampering | yfinance accepts a string and constructs an HTTPS URL internally; no shell call. Still: in `__main__`, validate ticker matches `^[A-Z0-9.-]{1,10}$` and raise on mismatch. Defence in depth. |
| Dependency CVEs in yfinance / pandas / numpy | Tampering / Supply chain | All three are pinned (yfinance==0.2.65) or floor-pinned in `requirements.txt`. Run `pip-audit` quarterly; not a Phase 7 task but document. |
| Path traversal via fixture filename | Tampering | Tests use `Path(__file__).parent` for any local fixture access; never accept fixture paths from env / args |
| Network-call DoS in tests | Denial of Service | yfinance has built-in rate limiting; `--no-network` flag allows offline iteration |
| pytest plugin malicious package | Supply chain | Pin pytest to `>=8.4,<9` in `requirements-dev.txt`; only top-level pytest is added (no third-party plugins in this phase) |

**Net assessment:** Phase 7 attack surface is minimal (one CLI arg, well-known dependencies). The single concrete control to add is **ticker arg validation in `__main__`** with a clear regex and an early raise. No other ASVS-L1 controls apply.

---

## Open Questions

1. **Should `detect()` validate the input frame's index timezone?**
   - What we know: yfinance returns tz-aware DatetimeIndex (`America/New_York`); the example fetch normalises to tz-naive.
   - What's unclear: Should `detect()` accept tz-aware frames and normalise, or require tz-naive?
   - Recommendation: Require tz-naive (assert in detect()'s preamble); document in docstring. Phase 10 batch will normalise once at fetch time.

2. **Tie-breaker when one bar matches multiple confirmation types**
   - What we know: A bar could in principle match both `_is_pin` and `_is_mark_up` (e.g., a strongly bullish bar with a tiny lower wick — pin's lower-third condition fails, but combinations exist). Code Example 1 shows precedence pin → mark_up → ice_cream.
   - What's unclear: CONTEXT D-01..D-03 do not specify precedence on overlap.
   - Recommendation: Encode precedence pin → mark_up → ice_cream in `_classify_confirmation` and document with a unit test capturing the overlap case. Surface to user during /gsd-discuss-phase if it has not already been settled.

3. **What is `__main__` output format — pretty table or JSON?**
   - What we know: CONTEXT discretion area; D-13 does not lock format.
   - What's unclear: Phase 10 imports `detect()` directly so doesn't read `__main__` output. Output is dev-facing only.
   - Recommendation: JSON (machine-readable), with `--pretty` flag for human-readable tabular output. JSON is the default per the discretion comment in CONTEXT.

---

## Sources

### Primary (HIGH confidence)
- `.planning/phases/07-detection-engine/07-CONTEXT.md` — locked decisions D-01..D-16
- `.planning/REQUIREMENTS.md` — DET-01..DET-04 acceptance criteria
- `.planning/ROADMAP.md` — Phase 7 success criteria
- `.planning/research/SUMMARY.md` — Watch Out For #1 (look-ahead), stack additions deferred to Phase 8+
- `.planning/codebase/CONVENTIONS.md` — snake_case, PascalCase, leading underscore for private helpers
- `./CLAUDE.md` — project-level instructions
- `MEMORY.md` — `feedback_venv.md`, `feedback_git_attribution.md`
- `scripts/fetch_sp500.py` — orchestration / per-ticker error handling pattern
- `yahoo_finance_fetcher.py` — yfinance idiom + retry pattern
- pytest changelog — pytest 8.4.2 release date and stability [CITED: https://docs.pytest.org/en/stable/changelog.html]
- pytest custom markers + skipping docs [CITED: https://docs.pytest.org/en/stable/example/markers.html, https://docs.pytest.org/en/stable/how-to/skipping.html]

### Secondary (MEDIUM confidence)
- ATR Wilder vs simple comparison [CITED: https://www.macroption.com/atr-calculation/]
- Wilder smoothing as EMA with alpha=1/N [CITED: https://www.macroption.com/atr-excel-wilder/, https://tulipindicators.org/wilders]
- Empirical probe in `.venv` 2026-05-02: `pandas 3.0.2`, `numpy 2.4.4`, `yfinance 0.2.65`, pytest absent. Verified `yf.download` returns MultiIndex columns; `yf.Ticker.history()` returns flat columns.

### Tertiary (LOW confidence)
- pytest 9.0.x ecosystem stability — released ~April 2026, recommendation pins to 8.4.x for 1-2 month stability buffer.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pandas/numpy/yfinance versions empirically verified in `.venv`; pytest version traced to changelog
- Architecture patterns: HIGH — directly derived from CONTEXT locked decisions; Wilder ATR is industry-standard
- Pitfalls: HIGH — the look-ahead, MultiIndex, NaN, and pytest-discovery pitfalls are concrete and reproducible
- Security: HIGH — minimal surface; one input validation control documented
- Validation Architecture: HIGH — test framework, command, sampling rate, and Wave 0 gaps are unambiguous

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (30 days; stable domain — pure-Python rule encoding with no external service exposure)

---

## Key Findings (TL;DR for the planner)

1. **Use `yf.Ticker(t).history(period="10y", auto_adjust=True)`** — NOT `yf.download(t, ...)`. The latter returns MultiIndex columns even for a single ticker (empirically verified).
2. **Wilder ATR via `series.ewm(alpha=1/14, adjust=False, min_periods=14).mean()`** — one line, industry standard, no new dep.
3. **Always slice-first for filters:** `view = df.iloc[:k+1]; sma = view["Close"].rolling(50).mean().iloc[-1]`. Add a truncation-invariance regression test.
4. **pytest 8.4.x in a NEW `requirements-dev.txt`** — keep `requirements.txt` runtime-only. Register a `network` marker and a `--no-network` CLI option in `conftest.py`.
5. **Wave 0 gaps:** `requirements-dev.txt`, `pytest.ini`, `tests/conftest.py`, `tests/test_detector_known_setups.py`, `tests/test_detector_schema.py`. All net-new files.
6. **Security control:** validate the CLI ticker arg with `^[A-Z0-9.-]{1,10}$` regex in `__main__` before passing to yfinance.
7. **5 known setups (D-16):** must be Claude-proposed during execution, user-approved before encoding into the parametrize list. ≥ 2 distinct types and ≥ 1 spring case.

---

*Phase: 07-detection-engine*
*Research: 2026-05-02*
