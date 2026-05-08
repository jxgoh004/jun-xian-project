# Phase 9: Backtesting Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 09-backtesting-engine
**Areas discussed:** Exit rule & hold period, Output schema, Filter ablation, ML-confidence stratification

---

## Exit rule & hold period

### Q1 — Canonical exit rule

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed N bars only | Exit at close of confirmation+1+N. Simplest; median hold trivial. | |
| Variable: stop at mother-low, profit target, OR N-bar timeout (whichever first) | Discretionary-trader style. | |
| Fixed N bars AND a parallel variable-exit run | Two stat blocks per type; 2× compute. | |
| You decide | Claude picks. | |

**User's choice (free-text "Other"):** "Stop loss at the most recent low, target a 1:2 risk reward ratio"
**Notes:** Anchors a discretionary, fixed-R:R rule. Subsequent questions disambiguated which "low" and how unresolved trades are handled.

### Q2 — Stop anchor

| Option | Description | Selected |
|--------|-------------|----------|
| Mother-bar low | Classical interpretation; risk = entry − mother_low. | |
| Lowest low across the 5-bar cluster | Equals break-below bar's low in spring cases. Tightest-but-honest. | ✓ |
| Confirmation-bar low | Tightest stop; most likely stopped on noise. | |

**User's choice:** Lowest low across the 5-bar cluster.
**Notes:** Directly readable from `Detection.bars` field — no extra computation needed.

### Q3 — Unresolved trade handling

| Option | Description | Selected |
|--------|-------------|----------|
| Hard timeout at N bars | Force-close at exit bar. | |
| No timeout — drop unresolved | Trades open at data edge excluded entirely. | |
| No timeout — mark unresolved as 'open' | Three-bucket outcome: stop / target / open. | ✓ |

**User's choice:** Three-bucket outcome.
**Notes:** Win-rate denominator excludes 'open'; N includes it. Most honest — no methodological choice hidden in dropped trades.

### Q4 — Intrabar resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Pessimistic — stop wins | Standard daily-bar convention. | ✓ |
| Optimistic — target wins | Overstates results. | |
| Pro-rata by open proximity | Heuristic; complexity for ambiguous benefit. | |
| Skip the day | Unusual; can leave trades open longer. | |

**User's choice:** Pessimistic.
**Notes:** Documented in the strategy `rule` metadata so the convention is transparent in the output JSON.

### Q5 — Return unit

| Option | Description | Selected |
|--------|-------------|----------|
| R-multiples | Stop = −1.0R; target = +2.0R. | ✓ |
| Pct return (% of entry) | BT-03 wording; mixes stop-widths. | |
| Both | Costs a few floats per record. | |

**User's choice:** R-multiples.
**Notes:** Output field `avg_return_r`. BT-03's "avg return %" is interpreted as "avg return in R" — note in Phase 9 SUMMARY.

---

## Output schema

### Q6 — Per-detection vs aggregate-only

| Option | Description | Selected |
|--------|-------------|----------|
| Aggregate-by-confirmation-type only | Smallest file. | |
| Per-detection records + aggregates | One record per detection + bucketed aggregates. | ✓ |
| Per-detection + per-ticker rollup + per-type aggregates | Most flexible; not in Phase 11 success criteria. | |
| You decide | Claude picks. | |

**User's choice:** Per-detection + aggregates.
**Notes:** Per-detection records make filter-ablation analysis and the optional yolo_conf overlay first-class.

### Q7 — In-sample vs out-of-sample

| Option | Description | Selected |
|--------|-------------|----------|
| Out-of-sample only | Strict BT-02; cleanest integrity story. | |
| Both, clearly labelled | Two parallel blocks per strategy. | ✓ |
| Out-of-sample only + pre-cutoff count for context | Compromise; metadata only. | |

**User's choice:** Both, labelled.
**Notes:** Phase 11 stat cards must read `out_of_sample`. The `in_sample` block is for transparency narrative, not the headline number.

### Q8 — Aggregate groupings

| Option | Description | Selected |
|--------|-------------|----------|
| By confirmation_type (3 rows) | Required by BT-01. | ✓ |
| By is_spring (2 rows) | Spring vs extended setup. | ✓ |
| By confirmation_type × is_spring (≤6 cells) | Cross-tab; some cells low-N. | ✓ |
| Global 'all' row | Headline for portfolio card. | ✓ |

**User's choice:** All four — namespaced under `strategies.<strategy_name>` at the top level so future strategies can be added without schema break.
**Notes:** User asked which option is best given that more strategies will be added in the future but rely on the same confirmation types. Recommendation accepted: full cross-tab + global + per-strategy namespace at the top level. Each strategy block carries its own `rule` metadata (stop / target_R / intrabar / timeout).

---

## Filter ablation

### Q9 — Run unfiltered universe in parallel?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — separate strategy keys | filtered + full unfiltered superset. | ✓ |
| Yes — per-filter-combo keys (8 cells) | Stratified by filter on/off. | |
| No — filtered only | Simplest. | |

**User's choice:** Two strategy entries, same exit rule, different detection sources.
**Notes:** `1to2_rr_cluster_low_stop` (filtered) and `1to2_rr_cluster_low_stop__unfiltered` (full superset via `apply_trend_filters=False`). Lets the portfolio narrative quantify what the trend filters add.

---

## ML-confidence stratification

### Q10 — Run ONNX per detection?

| Option | Description | Selected |
|--------|-------------|----------|
| No — model-free Phase 9 | Calibration ships from Phase 10. | |
| Yes — render + run ONNX, stratify by tier | Adds by_tier aggregate. | |
| Yes — store yolo_conf per-detection only | Defer tier thresholds to Phase 11. | ✓ |

**User asked for a recommendation.** Recommended option 3 with rationale:
1. Stores the data; defers the tier-threshold UX decision until the conf distribution is visible.
2. Honest about what `yolo_conf` means — the model mimics the algorithmic detector, so its confidence scores chart-textbook-ness, not P&L probability. Stratifying win-rate by tier risks implying causation that isn't there.
3. Cost is bounded; reuses `renderer.py` and `verify_onnx.py` infrastructure already shipped by Phase 8.
4. Composes cleanly with the strategy namespace.
5. Phase 10 doesn't have to do this work twice.

**User's choice:** Option 3 — yolo_conf per-detection only.
**Notes:** If `models/inside_bar_v1.onnx` is missing at runtime, write `yolo_conf: null` and emit a single warning. Backtest stays runnable independently.

---

## Claude's Discretion

- Runtime parallelization for 503 tickers (sequential acceptable if total wall-time < 30 min).
- Per-detection record field ordering, JSON pretty-print, sort order.
- ONNX session caching shape (load once at process start, reuse session).
- Whether `simulate_trade` returns frozen dataclass or plain dict (recommend dict for direct JSON serialisation).
- Calendar vs trading days for `median_hold_days` (recommend calendar; document choice).
- Per-ticker progress logging (recommend mirroring `generate_training_data.py`).
- Refinements to gap-down-on-entry handling beyond D-04's default.
- Exact CLI flag shape (`--seed`, `--tickers`, `--limit`, `--out` suggested).
- Whether `simulate_trade` accepts df slices ending at entry bar or full df + forward-walk loop (recommend full df).

## Deferred Ideas

- By-tier `yolo_conf` aggregation — defer until Phase 11 has post-cutoff conf-distribution histogram.
- Per-ticker rollup ("best tickers for this setup") — not in Phase 11 success criteria.
- Per-filter-combo cross-tab (8 cells of 2³ filter on/off) — finer-grained ablation; revisit if binary ablation is interesting.
- Additional strategies (`fixed_20bar_hold`, `1to3_rr_mother_low_stop`, etc.) — schema namespace already supports them.
- Variable hold with ATR-based exits.
- Slippage and commission modeling.
- Equity-curve simulation, position sizing, compounding (REQUIREMENTS Out of Scope — locked).
- Phase 9 → Phase 11 build step that transforms `_dev/backtest_cache.json` into frontend-ready `docs/projects/patterns/backtest_stats.json` (Phase 11's problem).
