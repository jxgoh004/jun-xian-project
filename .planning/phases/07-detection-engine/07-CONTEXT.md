# Phase 7: Detection Engine - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

A pure-Python module at `scripts/pattern_scanner/detector.py` that takes daily OHLC for a single ticker and returns a list of structured inside bar spring detections. It encodes the full 5-bar ruleset, handles the spring case (break-below bar == confirmation bar), applies three trend filters (HH/HL, price > 50-SMA, cluster near 20/50-SMA) using only data available at the pattern-end bar, and emits detection records that downstream phases (8 training, 9 backtesting, 10 batch pipeline, 11 frontend) consume directly. Training data generation, model training, ONNX export, backtest computation, and pipeline orchestration are explicitly out of scope.

</domain>

<decisions>
## Implementation Decisions

### Confirmation Bar Definitions (D-01 — D-04)
- **D-01 — Pin Bar:** `open >= L + (2/3)*(H-L) AND close >= L + (2/3)*(H-L)`. Bar colour irrelevant. Inclusive boundary (`>=`).
- **D-02 — Mark Up Bar:** `(close - open) >= (2/3)*(H-L) AND close > open`. Strictly bullish (green) bar with body covering at least two-thirds of total range.
- **D-03 — Ice-cream Bar:** `min(open, close) <= L + 0.5*(H-L) AND close >= L + (1/3)*(H-L) AND close > open`. Long lower wick anchored at/below midpoint, bullish close in upper two-thirds.
- **D-04 — Inside Bar (vs mother bar):** `H_inside < H_mother AND L_inside > L_mother`. Strict less-than/greater-than on both sides — equality disqualifies.

### Trend Filters (D-05 — D-08)
- **D-05 — HH/HL uptrend:** Use fractal swing-pivot detection (5-bar pivots: a swing high is a bar whose two neighbours on each side have lower highs; symmetric for lows) over a 60-bar lookback ending at the pattern-end bar. Pass when the **last 2 swing highs are ascending AND the last 2 swing lows are ascending**.
- **D-06 — Price above 50-SMA:** `close[confirmation_bar] > sma_50[confirmation_bar]`. Single point check at confirmation timing. The 50-SMA is computed using closes up to and including the confirmation bar.
- **D-07 — Cluster near 20/50-SMA retracement:** `mother_bar_low` lies within ±1 × ATR(14) of either the 20-SMA OR the 50-SMA evaluated at the mother bar's index. Either SMA qualifies. ATR is the standard 14-bar Average True Range.
- **D-08 — Filter combination:** All three filters must pass (strict AND) for a detection to be emitted. Per-filter pass/fail booleans are still recorded in the detection record so downstream phases can stratify.

### Pattern Cluster Rule (locked from REQUIREMENTS / memory — for clarity only, not re-decided)
- Bar 1 = mother bar; Bar 2 = inside bar (per D-04); within the next **3 bars** a bar breaks below mother bar low; that break-below bar OR a subsequent bar (still within the 5-bar window) closes inside the mother bar range as one of the three confirmation types. Spring case: break-below bar and confirmation bar may be the **same** bar.

### Detection Record Schema (D-09 — D-11)
- **D-09 — Class label:** Single class `inside_bar_spring`. Spring vs full 5-bar variant is recorded as a boolean field `is_spring` on each detection (NOT split into two YOLO classes). Resolves the v2.0 open question. Easier to add a second class later than to merge two; keeps Phase 8 positive-sample count high.
- **D-10 — Schema fields (Detection record):**
  ```
  ticker: str
  confirmation_date: ISO date string (YYYY-MM-DD)
  confirmation_type: "pin" | "mark_up" | "ice_cream"
  is_spring: bool
  bars: list[5] of {date, open, high, low, close}  # mother → confirmation
  mother_bar_index: int   # row index in source df
  confirmation_bar_index: int
  filters: {hh_hl: bool, above_50sma: bool, sma_cluster: bool}
  sma_levels: {sma20: float, sma50: float, atr14: float}  # at confirmation bar
  ```
  Rich enough that Phase 8 can annotate, Phase 9 can backtest, and Phase 11 can render the drilldown without recomputation. NO `quality_score` in v1 — would require defining a heuristic now and would conflict with the Phase 8 model confidence which is the canonical confidence signal.
- **D-11 — Code representation:** Python `@dataclass(frozen=True)` named `Detection` with a `to_dict()` method (or `dataclasses.asdict()`) for JSON serialisation. No new dependencies (no Pydantic).

### Module API (D-12 — D-14)
- **D-12 — Public API:** Single pure function `detect(df: pd.DataFrame, ticker: str) -> list[Detection]`. `df` has columns `Open / High / Low / Close` and a `DatetimeIndex` (yfinance auto-adjusted format). Helpers (`_is_pin`, `_is_mark_up`, `_is_ice_cream`, `_inside_bar`, `_compute_sma`, `_compute_atr`, `_swing_pivots`, `_hh_hl_uptrend`, `_sma_cluster`) are private (leading underscore, snake_case per project convention).
- **D-13 — Standalone invocation:** `__main__` block accepts a CLI arg ticker: `python scripts/pattern_scanner/detector.py AAPL` fetches 10y daily bars via yfinance and prints detections (JSON or pretty-table). Phase 10 batch pipeline imports `detect()` directly and bypasses `__main__`. No fixture-loading code path in this phase.
- **D-14 — No look-ahead enforcement:** All filter computations slice the df up to and including the pattern-end bar before evaluation. Implementation must use `df.iloc[:confirmation_idx + 1]` for SMA/ATR/swing-pivot computations — never reference future bars. Tests must include a regression case that confirms an in-progress trailing pattern produces the same result as it would on the day of confirmation.

### Manual Validation Harness (D-15 — D-16)
- **D-15 — Test framework:** `tests/test_detector_known_setups.py` using `pytest`. Each test case is a `(ticker, expected_confirmation_date, expected_type, expected_is_spring)` tuple. The test fetches 10-year daily history via yfinance (or accepts a cached parquet fixture if the network call is too slow), runs `detect()`, and asserts: (a) a detection exists at `expected_confirmation_date` with matching `confirmation_type` and `is_spring`, (b) no detection is emitted on the bars immediately before and after the expected date (negative regression). The same file becomes the regression suite for any future detector tweak.
- **D-16 — Setup curation:** Claude proposes 5 candidate setups during Phase 7 execution from notable S&P 500 charts (e.g., AAPL post-COVID 2020, MSFT bottom 2022, plus three more). The proposal includes ticker, candidate confirmation_date, confirmation_type, is_spring, and a one-line chart narrative. The user reviews and approves (or adjusts) before encoding into the pytest fixture. Setups must span at least 2 distinct confirmation_types and at least 1 spring case to satisfy the success criterion.

### Claude's Discretion
- Specific helper function names beyond the public API
- Dataclass field ordering and JSON serialisation format details (snake_case keys preferred, matching existing codebase conventions)
- Internal representation of swing pivots (named tuples, lists, etc.)
- ATR formula variant (Wilder smoothing vs simple) — pick one and document
- CLI output format for `__main__` (likely JSON dump for machine readability)
- Whether to also expose a small `detect_one_window(df, end_idx, ticker)` helper for Phase 8 to call per-window during training annotation — Claude may add this if it materially simplifies Phase 8

### Folded Todos
None — no pending todos matched Phase 7.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level
- `.planning/PROJECT.md` — Milestone v2.0 vision, target features, scope guardrails.
- `.planning/REQUIREMENTS.md` §"Detection Engine" (DET-01 — DET-04) — Acceptance criteria the phase must satisfy.
- `.planning/ROADMAP.md` §"Phase 7: Detection Engine" — Goal, dependencies, success criteria.

### Research / domain knowledge
- `.planning/research/SUMMARY.md` — Stack additions (mplfinance, onnxruntime, ultralytics split), architecture decisions (no torch in CI), Watch Out For #1 (look-ahead bias in annotation), open questions.
- `C:/Users/zenng/.claude/projects/C--Users-zenng-Desktop-portfolio-jun-xian-project/memory/project_milestone2_pattern_scanner.md` — Full ruleset reference (the spring rule, confirmation bar definitions). Note: 3-day-old point-in-time observation; this CONTEXT.md is now the authoritative spec where they conflict.

### Codebase pattern references (for downstream reuse)
- `scripts/fetch_sp500.py` — Reference structure for batch script that imports a pure-Python computation module and processes the S&P 500 universe; Phase 10 will mirror this pattern for the pattern scanner.
- `yahoo_finance_fetcher.py` — Existing yfinance wrapper pattern; the detector's `__main__` block should reuse the same yfinance fetching idiom for consistency. NOTE: existing fetcher targets fundamentals; daily OHLC fetch will be a thin direct call (`yf.download(ticker, period="10y", auto_adjust=True)` or equivalent).
- `.planning/codebase/CONVENTIONS.md` — snake_case for Python files/functions, PascalCase for classes (so `Detection` dataclass), leading underscore for private helpers.
- `.planning/codebase/STRUCTURE.md` — Confirms `scripts/` is the right home for pipeline scripts; new sub-package `scripts/pattern_scanner/` is consistent with existing layout.

### Out-of-scope-but-related (do not implement here)
- mplfinance chart rendering — Phase 8.
- ONNX inference — Phase 10.
- Backtest forward-return computation — Phase 9.
- Train/test cutoff date — Phase 9 will define the shared config that Phase 8 (`data.yaml`) and Phase 9 backtester both read. Phase 7 needs no cutoff awareness because the detector is just a function over OHLC.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`scripts/fetch_sp500.py` orchestration pattern** — argparse, ticker iteration, JSON output, error handling per ticker. Phase 10 will mirror this; Phase 7 can reuse the per-ticker error-handling idiom inside the `__main__` block.
- **`yahoo_finance_fetcher.py` yfinance idiom** — Confirms the project's auto_adjust=True / yfinance version (0.2.65). Daily OHLC fetch is a simpler call than the fundamentals path but should follow the same exception-handling style.
- **Existing `tests/` patterns** — `_dev/test_yahoo_finance.py` and `_dev/test_finviz.py` show the project does pytest-style asserts. Phase 7 elevates this to a real `tests/` directory at repo root with proper pytest collection (the project does not yet have one — this phase introduces it).

### Established Patterns
- Python: `snake_case` modules and functions, `PascalCase` classes (`Detection`), leading underscore for private helpers, UPPER_CASE module constants. CONVENTIONS.md confirms.
- Frontend/backend split is irrelevant for this phase — detector is pure Python with no Flask/HTTP touch points.
- Existing `requirements.txt` already has pandas 2.3.2, numpy 2.3.3, yfinance 0.2.65 — sufficient. No new runtime deps needed for Phase 7. (mplfinance/onnxruntime arrive in later phases.)

### Integration Points
- New package directory: `scripts/pattern_scanner/` (currently does not exist). Add `__init__.py`.
- New file: `scripts/pattern_scanner/detector.py`.
- New top-level directory: `tests/` with `tests/test_detector_known_setups.py` (project's first formal pytest file at the proper location).
- Phase 10 will eventually `from scripts.pattern_scanner.detector import detect, Detection` — keep the public API stable from day one.

</code_context>

<specifics>
## Specific Ideas

- The spring case (break-below bar == confirmation bar) is the **strongest** version of the setup and must be explicitly tested with at least one case in the validation fixture.
- The `is_spring` flag matters for the portfolio narrative — eventually shows up as a badge in Phase 11. Keep the field even though we are not splitting the YOLO class.
- "60-bar lookback" for HH/HL was chosen because S&P 500 daily history has ~252 bars/year — 60 bars (~3 months) is a meaningful trend window without polluting with quarter-old structure.
- ATR-based SMA-cluster band auto-scales by volatility — explicit choice over fixed-percent so the detector works for both AAPL and small caps without per-stock tuning.

</specifics>

<deferred>
## Deferred Ideas

- **Quality score per detection** (heuristic 0–1 score combining filter strength, body/range ratios, etc.) — Phase 8 model confidence is the canonical confidence signal. Revisit only if the model trains poorly.
- **Two YOLO classes** (separate `spring` and `full_5bar`) — explicitly deferred via D-09. Re-evaluate after first training run if model performance suggests separating helps.
- **Notebook-based visual validation** of known setups — nice-to-have; pytest covers the regression need. Could be added in a later phase as part of portfolio narrative.
- **Parquet fixture caching** for the validation suite — only worth it if the live yfinance test becomes flaky/slow. Add later if it does.
- **Parameter sweeps / configurable thresholds** — locked thresholds are intentional; expose later only if backtesting shows tuning improves quality.
- **Edge case: stock splits / IPOs with <60 bars of history** — yfinance auto_adjust handles splits; tickers with insufficient history simply produce zero detections. No special-casing needed in this phase.

</deferred>

---

*Phase: 07-detection-engine*
*Context gathered: 2026-05-02*
