# Phase 9: Backtesting Engine - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

A pure-Python, **offline** backtester that runs Phase 7's `detect()` across the S&P 500 over 10 years of daily OHLC and writes a structured `_dev/backtest_cache.json` containing per-detection records and aggregate forward-return statistics. Concretely the phase delivers:

1. `scripts/pattern_scanner/backtest.py` — orchestrator that iterates the S&P 500 universe, fetches 10y OHLC, runs the algorithmic detector, simulates a fixed entry/exit rule per detection, and writes the cache.
2. **Two strategy entries side by side** (filter ablation): `1to2_rr_cluster_low_stop` (filtered detections — Phase 7 default) and `1to2_rr_cluster_low_stop__unfiltered` (full superset via `apply_trend_filters=False`). Identical exit rule; different detection sources.
3. **Hard train/test split** sourced from `scripts.pattern_scanner.split_config.TRAIN_TEST_CUTOFF` — same constant the training-data generator imports. Output carries parallel `in_sample` (pre-cutoff) and `out_of_sample` (post-cutoff) blocks for narrative honesty without diluting the integrity story.
4. **Optional ONNX overlay**: each per-detection record carries a `yolo_conf` field obtained by rendering the detection's 60-bar window via `scripts/pattern_scanner/renderer.py` and running `models/inside_bar_v1.onnx` (reuses the inference shape from `verify_onnx.py`). If the ONNX is missing at runtime, `yolo_conf: null` + warning — backtest stays runnable independently of Phase 8 artifacts.
5. **Pytest suite** following the Phase 8 pattern: synthetic OHLC fixtures + monkeypatched `_fetch_ohlc` so tests run in milliseconds without yfinance.

**Explicitly out of scope:**
- Nightly orchestration / GitHub Actions / atomic write protocol — Phase 10.
- Frontend rendering of stat cards / drilldown — Phase 11.
- P&L simulation, equity curves, position sizing, compounding — locked out by REQUIREMENTS Out of Scope.
- Real-time / streaming — daily bars only.
- Tier-threshold setting for confidence badges — that's a Phase 11 UI decision once the post-cutoff `yolo_conf` distribution is visible.

</domain>

<decisions>
## Implementation Decisions

### Exit Rule & Outcome Resolution (D-01 — D-05)

- **D-01 — Strategy name & rule:** The single strategy this phase ships is `1to2_rr_cluster_low_stop`. Entry = open of `confirmation_bar_index + 1`. Stop = `min(bar.low for bar in detection.bars)` — the lowest low across the 5-bar cluster, directly readable from the `Detection` record. Target = `entry + 2 × (entry − stop)` (1:2 R:R). Risk distance `R = entry − stop`.

- **D-02 — Three-bucket outcome:** Each trade resolves as exactly one of `{stop, target, open}`. **No timeout.** A trade that reaches neither stop nor target by the last available bar in the 10y series is marked `open` and **excluded from the win-rate denominator** but counted in N. Open trades carry an unrealized `R = (last_close − entry) / risk` so per-detection records still report a return for analysis.

- **D-03 — Intrabar resolution (pessimistic):** When a single daily bar's `[low, high]` range contains both the stop and the target levels, **stop wins**. This is the standard backtester convention for daily-bar simulation without intraday data — avoids overstating win-rate.

- **D-04 — Stop-touched-on-entry-bar edge case (Claude's discretion, with default):** If the entry bar (= `confirmation_bar_index + 1`) gaps down so its open is at or below the stop, the trade is recorded as `stop` with `R = (entry_open − stop) / risk` (negative, possibly worse than −1.0R). If the entry bar's `[low, high]` already contains the stop intrabar but open is above, apply D-03 (pessimistic — stop wins same day). Researcher / planner may refine; default is conservative.

- **D-05 — Return unit (R-multiples):** The output stat called "avg return" by REQUIREMENTS BT-03 is reported in **R-multiples**, not percent of entry. Stop = −1.0R; target = +2.0R; open = `(last_close − entry) / risk`. This is the methodologically clean unit for a 1:2 R:R rule and makes stats comparable across tickers regardless of price level. Output JSON field name: `avg_return_r`. The `R` choice is a deliberate reinterpretation of BT-03's "return %" — note this in the Phase 9 SUMMARY so the requirement is traceable.

### Output Schema (D-06 — D-09)

- **D-06 — File location:** `_dev/backtest_cache.json` (BT-03). Add `_dev/backtest_cache.json` to `.gitignore` alongside the existing `_dev/training_dataset/` entry. Cache regenerable from `(seed, ticker list, TRAIN_TEST_CUTOFF, ONNX artifact hash)` — same reproducibility convention as Phase 8.

- **D-07 — Top-level structure (strategies namespace):** The output JSON has a top-level `strategies` map keyed on `strategy_name`. This phase populates exactly two keys (D-01 + D-08). The schema is forward-compatible with future strategies (e.g., `fixed_20bar_hold`, `1to3_rr_mother_low_stop`) — they can be added without breaking existing readers.

  ```json
  {
    "schema_version": 1,
    "generated_at": "...",
    "train_test_cutoff": "2024-01-01",
    "seed": 42,
    "strategies": {
      "<strategy_name>": {
        "rule": { "stop": "...", "target_R": 2.0, "intrabar": "pessimistic", "timeout": "none" },
        "in_sample":     { "detections": [...], "aggregates": { "all": {...}, "by_confirmation_type": {...}, "by_is_spring": {...}, "by_type_x_spring": {...} } },
        "out_of_sample": { "detections": [...], "aggregates": { ... same shape ... } }
      }
    }
  }
  ```

- **D-08 — Per-detection record shape:** Each entry under `detections` carries:
  - Identity: `ticker`, `confirmation_date`, `confirmation_type`, `is_spring`
  - Trade: `entry_date`, `entry_price`, `stop_price`, `target_price`, `risk`
  - Resolution: `exit_date`, `exit_price`, `exit_reason ∈ {stop, target, open}`, `hold_days` (calendar days from entry to exit), `R`
  - ML overlay: `yolo_conf` (float in [0,1] or `null` if model unavailable — D-12)
  - Composite key derivable as `f"{ticker}_{confirmation_date}_{confirmation_type}"` — no separate ID field needed.

- **D-09 — Aggregate groupings (per sample-block, per strategy):** Always emit four slices:
  - `all` — global headline row (single object)
  - `by_confirmation_type` — keys: `pin`, `mark_up`, `ice_cream`
  - `by_is_spring` — keys: `spring`, `extended` (where `extended = is_spring == False`)
  - `by_type_x_spring` — up to 6 keys: `pin_spring`, `pin_extended`, `mark_up_spring`, ...

  Each aggregate cell carries: `n` (total detections), `n_resolved` (excludes `open`), `win_rate` (target_count / n_resolved), `avg_return_r`, `median_hold_days` (computed over resolved trades only), `target_count`, `stop_count`, `open_count`. Cells with `n < 1` are omitted (not emitted as zero rows).

### Train/Test Split & Sample Blocks (D-10 — D-11)

- **D-10 — Cutoff source-of-truth:** `from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF`. This is the same constant `generate_training_data.py` reads (Phase 8 D-07). **Phase 9 may revise this date** — the file lives in one place precisely so revision is safe. Researcher should evaluate whether `2024-01-01` leaves enough out-of-sample N for at least one confirmation_type to clear N ≥ 10 (BT-03 acceptance criterion); if the post-cutoff slice is too thin, propose a revised cutoff and update `split_config.py`. **Caveat:** revising the cutoff changes the training-data manifest's train/test boundary retroactively. If revised, document the rationale and either (a) accept that the trained model was trained on slightly more data than the new cutoff suggests, or (b) flag a Phase 8 retrain.

- **D-11 — Two parallel sample blocks:** Output emits both `in_sample` (detections with `confirmation_date < TRAIN_TEST_CUTOFF`) and `out_of_sample` (`>= TRAIN_TEST_CUTOFF`) blocks per strategy, with identical `detections + aggregates` shape. **The `out_of_sample` block is the integrity number** — Phase 11 stat cards must read from `out_of_sample`. The `in_sample` block exists for the portfolio-narrative angle "here is how the rule held up on data the model was trained on AND on data it never saw". BT-02 strict enforcement ("no detections from training period appear in backtest results") is satisfied because the `out_of_sample` block is well-defined and labelled separately.

### Filter Ablation (D-12)

- **D-12 — Two strategy entries, same exit rule:** Run the full backtest **twice**, with the only delta being the detection source:
  - `1to2_rr_cluster_low_stop` — detections from `detect(df, ticker)` (filtered, Phase 7 default).
  - `1to2_rr_cluster_low_stop__unfiltered` — detections from `detect(df, ticker, apply_trend_filters=False)` (the full candidate pool, which is a strict superset of filtered — Phase 8 D-10 confirms the `apply_trend_filters` kwarg surface). **Not just the rejects** — the full superset, so the comparison is "filtered universe vs total universe", not "filtered vs failed-only".

  Per Phase 8 D-10 + D-20 the kwarg is already implemented and stable. Cost: ~10× detection volume for the unfiltered run; still tractable on local hardware (Phase 7 detector is pure-Python and fast). The portfolio narrative payoff is "the trend filters lift win-rate from X% to Y%" — quantified, not asserted.

### ML-Confidence Overlay (D-13 — D-14)

- **D-13 — `yolo_conf` per-detection only (no by-tier aggregate):** Render each detection's 60-bar right-aligned window via `scripts/pattern_scanner/renderer.py` (reuse the same `STYLES[0]` deterministic style — not randomised; this is inference, not training) and run `models/inside_bar_v1.onnx` via the inference shape implemented in `scripts/pattern_scanner/verify_onnx.py`. Write the resulting confidence float on the per-detection record. **Do NOT** emit a `by_yolo_tier` aggregate slice — tier thresholds are a Phase 11 UI decision once the conf distribution is visible.

  **Rationale (recorded so the decision survives review):** The model was trained to mimic the algorithmic detector. So `yolo_conf` for an algorithmic-positive detection scores *chart-textbook-ness*, not *trade success probability*. Stratifying win-rate by tier risks implying a causation that isn't there. Storing the raw float defers the tier-threshold call to a moment when the histogram is visible.

- **D-14 — Graceful ONNX-absence fallback:** If `models/inside_bar_v1.onnx` does not exist at backtest runtime, `yolo_conf` is set to `null` on every record and a single warning is logged. The backtest must remain runnable independently of Phase 8 artifacts (e.g., for fast iteration on the exit rule or filter-ablation analysis).

### Module Surface & Conventions (D-15 — D-17)

- **D-15 — New file:** `scripts/pattern_scanner/backtest.py` — pure-function core + thin CLI wrapper, mirroring `detector.py` and `generate_training_data.py`. Public API:
  - `_fetch_ohlc(ticker, period="10y") -> pd.DataFrame` (test seam, monkeypatchable; mirrors `generate_training_data._fetch_ohlc` byte-for-byte).
  - `simulate_trade(df, detection, stop_price, target_price) -> dict` (pure; given OHLC and entry rule, returns the resolution record). The key testable unit.
  - `aggregate(detections: list[dict], group_keys: list[str]) -> dict` (pure; the stats-rollup helper).
  - `main(argv) -> int` (CLI orchestrator).

- **D-16 — CLI shape (suggested; researcher may refine):** `python -m scripts.pattern_scanner.backtest --seed 42 --tickers all --out _dev/backtest_cache.json`. Same `--limit N` smoke-test arg as `generate_training_data.py` for fast local iteration. Same `RATE_LIMIT_SLEEP = 0.5` cadence for yfinance fetches.

- **D-17 — Test scaffold (`tests/test_backtest_*.py`):** Synthetic OHLC fixture + monkeypatched `_fetch_ohlc` (Phase 8 pattern; see `tests/conftest.py` and `test_generate_training_data.py`). Required tests:
  - `test_simulate_trade_stop_first` — deterministic stop hit before target.
  - `test_simulate_trade_target_first` — deterministic target hit before stop.
  - `test_simulate_trade_intrabar_pessimistic` — D-03 enforcement (single bar contains both → stop wins).
  - `test_simulate_trade_open_outcome` — neither hit by data edge.
  - `test_aggregate_groupings` — D-09 four-slice rollup correctness.
  - `test_train_test_cutoff_isolation` — no `confirmation_date >= cutoff` in `in_sample`; no `< cutoff` in `out_of_sample`.
  - `test_unfiltered_strategy_is_superset` — every filtered detection appears in the unfiltered detection set; the unfiltered set may have more.
  - `test_yolo_conf_null_when_onnx_missing` — D-14 graceful fallback.
  - All run in milliseconds, no network.

### Claude's Discretion

- Exact runtime parallelization for 503 tickers (process pool, async, or sequential — match whatever shape is fastest to verify; sequential is acceptable if total wall-time is < 30 min).
- Per-detection record field ordering, JSON indent / pretty-print decision, sort order of `detections` list (suggest `(ticker, confirmation_date)`).
- ONNX session caching: load once at process start, run inference per detection. Reuse the input-shape preprocessing from `verify_onnx.py` verbatim.
- Whether `simulate_trade` returns a frozen dataclass or plain dict (suggest dict for direct JSON serialisation).
- Whether to include the median entry-to-exit calendar-day gap or trading-day gap in `median_hold_days` (suggest calendar days for portfolio readability; record the choice in the SUMMARY).
- Whether to log progress per ticker the way `generate_training_data.py` does (recommended — long runs without progress feedback are a UX miss).
- Whether `simulate_trade` accepts `df` slices ending at the entry bar or full df (suggest full df with a forward-walk loop starting at `confirmation_bar_index + 1`).
- Exact gap-down-on-entry handling refinements beyond D-04's default.

### Folded Todos

None — no pending todos matched Phase 9.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level
- `.planning/PROJECT.md` — Milestone v2.0 vision; v2.0 Out of Scope list (no P&L sim, no equity curve, no signals/targets, no real-time).
- `.planning/REQUIREMENTS.md` §"Backtesting Engine" — BT-01, BT-02, BT-03 acceptance criteria. Note that BT-01's "fixed hold period" is reinterpreted as "fixed exit rule" (1:2 R:R with three-bucket outcome) per D-01..D-05.
- `.planning/ROADMAP.md` §"Phase 9: Backtesting Engine" — Goal, dependencies (Phase 7), success criteria 1–3.

### Upstream phase contracts
- `.planning/phases/07-detection-engine/07-CONTEXT.md` — Detection record schema (D-10), `detect(df, ticker)` public API, no-look-ahead invariants. Phase 9 consumes Detection records as the input to `simulate_trade`.
- `scripts/pattern_scanner/detector.py` — The `Detection` dataclass (`bars` field is the source of `min(bar.low)` for the stop) and the `detect()` function. **`apply_trend_filters: bool = True` kwarg is in place** (Phase 8 D-10) — Phase 9 backtester uses both `True` (filtered strategy) and `False` (unfiltered strategy).
- `.planning/phases/08-training-pipeline/08-CONTEXT.md` — Training pipeline decisions; D-07 establishes the shared `split_config.TRAIN_TEST_CUTOFF`, D-15 establishes the seed+manifest reproducibility pattern.
- `.planning/phases/08-training-pipeline/08-05-SUMMARY.md` — **Phase 9 hand-off notes (must read):** detector contract, ML confidence threshold = 0.3 calibration, dataset_manifest.json contents (Phase 9 can subtract these to verify out-of-sample isolation), inference dep lock (`onnxruntime>=1.19`, `Pillow`, `numpy<2.0`, `mplfinance`, `matplotlib` — NEVER torch/ultralytics).
- `scripts/pattern_scanner/split_config.py` — Single source of truth for `TRAIN_TEST_CUTOFF`. Phase 9 imports it. Phase 9 may revise the value (D-10).

### Codebase pattern references (for downstream reuse)
- `scripts/pattern_scanner/generate_training_data.py` — Closest analog: same orchestrator shape (S&P 500 iteration, monkeypatchable `_fetch_ohlc`, seeded determinism, manifest writing). `backtest.py` should mirror its argparse, ticker iteration, per-ticker error handling, JSON output idioms.
- `scripts/pattern_scanner/renderer.py` — **Reused** for the ML overlay (D-13). Use a single deterministic style at inference time (e.g., `STYLES[0]`), not the training-time randomisation.
- `scripts/pattern_scanner/verify_onnx.py` — Reference for the ONNX inference shape (input tensor `[1, 3, 640, 640]`, RGB preprocessing, output parsing). Phase 9 reuses the inference call directly; it does NOT re-run the clean-venv subprocess test (that's Phase 8's gate).
- `scripts/fetch_sp500.py` — Source of `fetch_sp500_tickers()`. Phase 9 imports it via the same path Phase 8 used (`from scripts.fetch_sp500 import fetch_sp500_tickers`).
- `yahoo_finance_fetcher.py` — Yfinance idiom reference (auto_adjust=True, version 0.2.65).
- `tests/conftest.py`, `tests/test_generate_training_data.py` — Synthetic OHLC fixtures + monkeypatched fetcher. Phase 9 test files mirror this.
- `.planning/codebase/CONVENTIONS.md` — snake_case files/functions, PascalCase classes, leading underscore for private helpers, UPPER_SNAKE_CASE module constants.
- `.planning/codebase/STRUCTURE.md` — `scripts/pattern_scanner/` package; `tests/` at repo root.
- `requirements.txt` — Already includes `onnxruntime`, `Pillow`, `numpy`, `mplfinance`, `matplotlib`, `pandas`, `yfinance` (per Phase 8 D-20). Phase 9 should add nothing new to `requirements.txt`. **Must NOT** add torch or ultralytics.

### ML artifacts (read at runtime; not committed by Phase 9)
- `models/inside_bar_v1.onnx` — Inference target for the `yolo_conf` overlay (D-13). If absent → `yolo_conf: null` + warning (D-14).
- `models/dataset_manifest.json` — Records which detections were in the training set; useful for cross-checking that no in-sample leakage exists in the `out_of_sample` block.

### Out-of-scope-but-related (do not implement here)
- Nightly inference orchestration & GitHub Actions workflow — Phase 10.
- Atomic `data.json` write protocol (temp + rename) for the production scanner — Phase 10 PIPE-02.
- Confidence-tier thresholds (green / yellow / red badges) — Phase 11 UI decision; Phase 9 only writes the raw `yolo_conf` floats that will inform that decision.
- Frontend stat cards / drilldown rendering — Phase 11.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`scripts/pattern_scanner/detector.detect(df, ticker, apply_trend_filters=True)`** — The detection source for both strategy entries. The `Detection` dataclass exposes `bars` (5-element list of OHLC dicts), `confirmation_bar_index`, `confirmation_type`, `is_spring`, and `confirmation_date` — every field the backtester needs.
- **`scripts/pattern_scanner.split_config.TRAIN_TEST_CUTOFF`** — Single source of truth. Backtester imports it; uses it to partition detections into `in_sample` / `out_of_sample` blocks.
- **`scripts/fetch_sp500.fetch_sp500_tickers()`** — Universe loader. Same call site Phase 8's `_load_tickers` uses.
- **`scripts/pattern_scanner/renderer.py`** — 60-bar 640×640 PNG renderer. Pass `STYLES[0]` for deterministic inference rendering.
- **`scripts/pattern_scanner/verify_onnx.py`** — ONNX inference reference. Reuse session-creation + `[1, 3, 640, 640]` preprocessing + output parsing.
- **`tests/conftest.py` `synthetic_ohlc` fixture + `_fetch_ohlc` monkeypatch pattern** — Phase 8's deterministic test scaffold. Phase 9 tests follow the same shape.

### Established Patterns
- **Pure-function core, thin CLI wrapper** — every `scripts/pattern_scanner/*.py` module exposes a pure function (`detect`, `_render`, `_emit_sample`, `verify_onnx`) plus an `if __name__ == "__main__"` argparse CLI. `backtest.py` follows the same split.
- **Seeded, monkeypatchable, no-network tests** — `test_generate_training_data.py` is the template. yfinance is never called in unit tests; the synthetic OHLC fixture provides deterministic input.
- **`_fetch_ohlc` mirrors byte-for-byte across modules** — `detector._fetch_ohlc` and `generate_training_data._fetch_ohlc` are identical. `backtest._fetch_ohlc` follows.
- **Deterministic seeded outputs** — `--seed` flag produces bit-for-bit reproducible JSON given the same yfinance data revision. Document the seed used in the cache header (D-07).
- **Per-ticker progress logging** — `generate_training_data.py` logs `[i/total] TICKER: ...`. Long backtests are a UX miss without it; mirror the pattern.

### Integration Points
- **New file:** `scripts/pattern_scanner/backtest.py`.
- **New tests:** `tests/test_backtest_simulate_trade.py`, `tests/test_backtest_aggregate.py`, `tests/test_backtest_cutoff.py`, `tests/test_backtest_unfiltered_superset.py`, `tests/test_backtest_yolo_conf_fallback.py` (or one consolidated `tests/test_backtest.py` — researcher's choice).
- **Updated `.gitignore`:** add one line — `_dev/backtest_cache.json`.
- **Read-only consumers:** Phase 10's nightly pipeline does NOT consume `_dev/backtest_cache.json`. Phase 11's frontend reads it (probably via a small build step that copies/transforms it into `docs/projects/patterns/backtest_stats.json` — out of scope for Phase 9).
- **Possible revision target:** `scripts/pattern_scanner/split_config.py`'s `TRAIN_TEST_CUTOFF` (D-10) — only if the post-cutoff slice is too thin for BT-03's `N ≥ 10` gate. Document any change in Phase 9 SUMMARY.

</code_context>

<specifics>
## Specific Ideas

- **The 1:2 R:R rule encodes a finance-domain claim.** The portfolio narrative is that this is how a discretionary trader would actually use the inside bar spring setup — defend the cluster low, target a 2× move. Output stats answer "does the rule produce positive expectancy out-of-sample?" with R-multiples, the natural unit for fixed-R:R rules. Reporting in % would obscure the methodology.
- **Why "lowest low across the 5-bar cluster" (D-01) is the right stop anchor:** The break-below bar's low (which equals or is below mother_low by definition of the spring case) is the level that "should have held" for the setup to be considered active. Stopping there means "the setup failed" in the same sense the rule defines a setup. Mother-low alone would let spring-case stops trigger on noise that's already part of the pattern; confirmation-bar low would be too tight. Cluster-low is the methodologically tight-but-honest choice.
- **The `strategies` namespace (D-07) is a deliberate forward-compatibility move.** Today this phase ships exactly two strategy entries (filtered + unfiltered, same rule). Future strategies (different stop rules, different R:R, different hold semantics) plug in as additional keys without breaking existing readers — Phase 11 / future phases iterate by adding keys, never by reshaping the schema.
- **In-sample stats are for transparency, not the headline.** Phase 11 stat cards must read `out_of_sample` (D-11). The `in_sample` block lets the portfolio narrative add: "and here's how the same rule held up over the 8 years before that, where N is much higher." It is a transparency move, not a credibility move — separation enforced by the labelled JSON keys.
- **`yolo_conf` is a quality signal, not a P&L signal (D-13 rationale).** The model was trained to mimic the algorithmic detector. So a high `yolo_conf` means "the chart looks textbook" — useful for filtering visually messy detections, not for predicting trade success. The decision to store the raw float without by-tier aggregation preserves both options for Phase 11 UI: tier badges if the histogram supports clean cuts, or no tiering if it doesn't.
- **Filter ablation is the most important narrative deliverable beyond the headline stats.** "We claim our trend filters add value" → "here are the numbers, computed honestly". This is the difference between a portfolio piece that asserts methodology and one that demonstrates it.
- **The cutoff `2024-01-01` is a placeholder Phase 8 inherited.** Phase 9 has standing permission to revise (D-10). The researcher should evaluate post-cutoff N early — if any confirmation_type clears N ≥ 10 with `2024-01-01`, leave it alone; if not, propose a revision that does, and document the trade-off (revising the cutoff retroactively reframes Phase 8's training set).

</specifics>

<deferred>
## Deferred Ideas

- **By-tier `yolo_conf` aggregation** — defer until Phase 11 has the post-cutoff conf-distribution histogram visible (D-13). The raw floats are stored per-detection from day one so this can be added later as a notebook study or a Phase 11 sub-task.
- **Per-ticker rollup** ("best tickers for this setup") — not in Phase 11's success criteria. Easy to add later if a future iteration wants a leaderboard view.
- **Per-filter-combo cross-tab (8 cells of 2³ filter on/off)** — a finer-grained ablation than D-12's filtered-vs-superset split. Revisit only if D-12's binary ablation result is interesting enough to warrant decomposition.
- **Additional strategies** (`fixed_20bar_hold`, `1to3_rr_mother_low_stop`, `mother_low_stop_with_atr_target`) — schema namespace already supports them (D-07). Add as future-phase or future-iteration work.
- **Variable hold with ATR-based exits** — considered (e.g., target = entry + 2×ATR) and deferred. Cluster-low + R-multiple is cleaner.
- **Slippage and commission modeling** — defaults to zero this phase. Real-world friction can be added as a strategy `rule` field if a future iteration cares.
- **Equity-curve simulation, position sizing, compounding** — explicitly out of scope (REQUIREMENTS Out of Scope). Will not be added without milestone re-scoping.
- **Phase 9 → Phase 11 build step** that transforms `_dev/backtest_cache.json` into a frontend-ready `docs/projects/patterns/backtest_stats.json` — that's Phase 11's problem.

### Reviewed Todos (not folded)

None — no pending todos were reviewed in this discussion.

</deferred>

---

*Phase: 09-backtesting-engine*
*Context gathered: 2026-05-08*
