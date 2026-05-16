# Phase 9 — Backtesting Engine — SUMMARY

**Closed:** 2026-05-10
**Plans:** 4 (09-01, 09-02, 09-03, 09-04)
**Requirements satisfied:** BT-01, BT-02, BT-03

## Deliverables

- `scripts/pattern_scanner/backtest.py` — pure-function core (`simulate_trade`, `aggregate`) + orchestrator (`main`) + ONNX overlay (`_load_onnx_session`, `_window_for`, `_score_detection`).
- 26 backtest unit tests across 6 test files (Plans 09-01 + 09-02 + 09-03), all green:
  - `test_backtest_simulate_trade.py` (5): stop_first, target_first, intrabar_pessimistic, open_outcome (D-01..D-05).
  - `test_backtest_aggregate.py` (1): four-slice rollup (D-09).
  - `test_backtest_cli.py` (15 parametrized): T-9-01 ticker-token security gauntlet.
  - `test_backtest_cutoff.py` (2): cutoff isolation + boundary-record-into-out_of_sample (D-11 / Pitfall 6).
  - `test_backtest_unfiltered_superset.py` (1): filtered ⊆ unfiltered (D-12).
  - `test_backtest_yolo_conf_fallback.py` (3): file-missing fallback, --no-onnx bypass spy, populated-session contract (D-14).
- `_dev/backtest_cache.json` produced empirically; gitignored (D-06).
- `.gitignore` updated to exclude `_dev/backtest_cache.json` (Plan 09-02).

## Empirical Results (BT-03 acceptance evidence)

**Run details:**
- Date: 2026-05-10
- Seed: 42
- Ticker count: 503
- Wall-clock: ~27 minutes (10:55:44 → 11:22:42 UTC)
- ONNX SHA-256: `null` — run executed with `--no-onnx`; see "Methodology Notes" below for rationale (the plan's `must_haves` explicitly permits this).
- TRAIN_TEST_CUTOFF: `2024-01-01` (held; not revised)

**Out-of-sample N by confirmation_type (filtered strategy `1to2_rr_cluster_low_stop`):**

| confirmation_type | n | n_resolved | win_rate | avg_return_r |
|-------------------|---|------------|----------|--------------|
| pin | 295 | 294 | 0.296 | -0.112 |
| mark_up | 317 | 311 | 0.328 | -0.007 |
| ice_cream | 713 | 710 | 0.345 | +0.036 |

**BT-03 gate (at least one type with n >= 10):** **PASS.** All three types clear by ≥ 295.

**Filter ablation (out_of_sample, all-cell):**

| strategy | n | win_rate | avg_return_r |
|----------|---|----------|--------------|
| 1to2_rr_cluster_low_stop | 1325 | 0.330 | -0.007 |
| 1to2_rr_cluster_low_stop__unfiltered | 8841 | 0.353 | +0.061 |

**Notable empirical finding** — within this 2-year out-of-sample window, the **unfiltered** strategy slightly outperforms the **filtered** strategy on both win-rate (+2.3 pp) and avg_return_r (+0.068R). The filtered set is 6.7× smaller (more selective), but the trend filters do not appear to add value over the post-cutoff slice. In-sample numbers tell a different story (filtered avg_return_r = +0.064 vs unfiltered = +0.079, both positive). The portfolio narrative will frame this honestly: "the filters tighten selectivity but the out-of-sample stats are too thin to claim a positive edge from filters alone." Phase 11 stat cards must surface this rather than overclaim.

**In-sample numbers (transparency, not the headline):**

| strategy | sample | n | win_rate | avg_return_r |
|----------|--------|---|----------|--------------|
| filtered | in_sample | 4015 | 0.354 | +0.064 |
| filtered | out_of_sample | 1325 | 0.330 | -0.007 |
| unfiltered | in_sample | 25841 | 0.359 | +0.079 |
| unfiltered | out_of_sample | 8841 | 0.353 | +0.061 |

The in-sample → out-of-sample drop is much larger for the **filtered** strategy (−0.071R) than the **unfiltered** (−0.018R), suggesting the filter combination may have been (mildly) over-fit to the pre-2024 sample.

## Methodology Notes (must read before consuming the cache)

### R-multiples are the unit, not percent (D-05)

BT-03 says "average return %". Phase 9 reports `avg_return_r` (R-multiples) — the methodologically clean unit for a fixed 1:2 R:R rule. Stop = -1.0R, target = +2.0R. Open trades carry an unrealized R = `(last_close - entry) / risk`. This is a deliberate reinterpretation of BT-03; rationale: R-multiples normalize across ticker price levels and align with how a discretionary trader using this rule would frame returns. A flat avg_return_r ≈ 0 with a 33% win-rate at 1:2 R:R is **break-even by construction** (target_count × 2R + stop_count × -1R = 0 when win_rate = 1/3); the actual numbers are slightly worse than break-even on the filtered slice and slightly better on the unfiltered.

### Prices are dividend-adjusted (Risk 3 / Pitfall 5)

`yfinance(auto_adjust=True)` is inherited from Phase 7 / Phase 8. Absolute `entry_price`, `stop_price`, `target_price`, `exit_price` in the cache are dividend-adjusted, which differs from TradingView's default split-adjusted-only view on dividend-paying tickers. R-multiples are unaffected (ratios within the same series). When Phase 11 cross-links the drilldown to the DCF screener (UI-04), expect price labels to differ visually from TradingView for high-dividend tickers — this is correct behavior, not a bug.

### Pessimistic intrabar resolution (D-03)

When a single bar's `[low, high]` contains both stop and target, stop wins. This is the standard backtester convention without intraday data — avoids overstating win-rate. The empirical median hold_days of 3 (filtered out_of_sample resolved trades) suggests many trades resolve on the entry bar or the day after; D-03's pessimism is doing meaningful work in those cases.

### Ticker-list drift caveat (Risk 7)

The reproducibility tuple `(seed, ticker_list, TRAIN_TEST_CUTOFF, onnx_sha256)` is captured in the cache header. `ticker_list` is the live S&P 500 constituents list at run time (Wikipedia-scraped via `scripts/fetch_sp500.py`). Cross-machine determinism is guaranteed only when:
- The Wikipedia scrape returns the same constituents.
- yfinance returns identical OHLC series for those constituents.

Same caveat as Phase 8's concat_sha256 cross-machine drift. Survivor bias is also present (tickers delisted before 2026-05-10 are not in the universe); this is documented as a known limitation in REQUIREMENTS Out of Scope ("Survivor-bias-free constituent list — requires paid data").

### `yolo_conf` is a quality signal, not a P&L signal (D-13)

The model was trained to mimic the algorithmic detector. So `yolo_conf` measures chart-textbook-ness, not trade-success probability. Raw float stored per-detection (when ONNX overlay is enabled); tier thresholds (green/yellow/red badges) are a Phase 11 UI decision once the post-cutoff conf-distribution histogram is visible. **In this empirical run, `yolo_conf` is `null` on every record because of the `--no-onnx` trade-off** — see "Run anomalies" below; Phase 11 will need to score the post-cutoff filtered slice (~1325 detections) with the ONNX overlay separately.

### "open" outcomes can be very old (Risk 4)

D-02 explicitly chose no timeout. A 2014 detection still marked `open` in 2026 has `hold_days ~ 4400`. The schema field disambiguates; Phase 11 UI may want to gate "still pending" on `hold_days < some_recent_threshold`. In the empirical run, the filtered out_of_sample slice has only 10 `open` outcomes out of 1325 (0.75%) and median resolved hold_days is 3 — most trades resolve quickly because the 1:2 R:R rule is geometrically tight on daily bars.

## Phase 10 / 11 Hand-off

**For Phase 10 (Batch Pipeline):**
- Phase 10 does NOT consume `_dev/backtest_cache.json` — that file is local-only / portfolio-narrative-only.
- Phase 10's nightly inference runs detection + ONNX inference, NOT backtesting. Backtest cache is regenerated manually when methodology changes.
- The `verify_onnx.py` clean-venv pattern from Phase 8 remains the inference dependency contract: only `onnxruntime + numpy + Pillow + mplfinance + matplotlib` are needed at CI runtime; never torch/ultralytics.

**For Phase 11 (Frontend):**
- The backtest cache lives at `_dev/backtest_cache.json` LOCALLY (gitignored). Phase 11 must add a small build step (probably in the deploy script) to copy/transform it into a frontend-readable JSON at `docs/projects/patterns/backtest_stats.json` (or similar).
- Phase 11 stat cards must read from `out_of_sample`, NOT `in_sample` — the integrity story per D-11.
- **`yolo_conf` is null on every record in the empirical cache** because the run used `--no-onnx` for tractable wall-clock. Phase 11 must add a small scoring utility (~50 LoC) that loads `models/inside_bar_v1.onnx`, iterates the post-cutoff filtered detection windows (~1325 records), runs the same `_score_detection` helper from `scripts/pattern_scanner/backtest.py`, and writes `(detection_key, yolo_conf)` pairs into the frontend JSON. Estimated runtime: ~5 min on CPU.
- Confidence-tier thresholds (green/yellow/red badges): inspect that yolo_conf distribution from the Phase 11 scoring pass to choose breakpoints. RESEARCH suggests starting with the 0.3 floor from Phase 8's CONFIDENCE_FLOOR but the histogram is the source of truth.
- The "filters do not add value out-of-sample" empirical finding (above) means Phase 11 should NOT overclaim filter benefit. The honest framing: "The trend filters tighten selectivity (1325 vs 8841 detections post-cutoff) at a small cost to expected return; the unfiltered numbers are similar enough that the choice is a discretionary trader's preference."

## Risks Documented (per RESEARCH §"Risks & Gotchas")

| Risk | Status | Note |
|------|--------|------|
| Risk 1 (numpy.float64 leak) | mitigated | All numeric fields wrapped in `float()` at write-time; verified by isinstance asserts in `test_backtest_simulate_trade.py`. |
| Risk 2 (Timestamp leak) | mitigated | All date fields use `df.index[i].strftime("%Y-%m-%d")`; verified by regex assert. |
| Risk 3 (auto_adjust=True) | documented | See "Methodology Notes — Prices are dividend-adjusted" above. |
| Risk 4 (open detections walk forever) | accepted | D-02 explicit choice. Documented for Phase 11 UI. Empirically: only 10/1325 (0.75%) of filtered out_of_sample detections are `open`. |
| Risk 5 (ONNX session memory) | accepted | onnxruntime production-tested at this scale; this run bypassed via `--no-onnx` so no memory pressure observed. |
| Risk 6 (detect ordering not stable) | mitigated | Records sorted by `(ticker, confirmation_date, mother_bar_index)` before serialization (Plan 09-02). |
| Risk 7 (ticker-list drift) | documented | Cache header captures live list of 503 tickers + survivor bias caveat. |

## Cutoff Decision Log

**No revision.** TRAIN_TEST_CUTOFF held at `2024-01-01`. Empirical N comfortably clears BT-03 across all three confirmation_types in the filtered out_of_sample slice (minimum N = 295 for pin; ice_cream is 713 — the dominant type). Phase 8's training set boundary is preserved unchanged.

## Run anomalies

**`yolo_conf` is null on every record in the empirical cache.** The full ONNX-enabled run was projected at ~7-9 hours wall-clock based on observed throughput (~1 ticker/min steady-state) — substantially over the plan's 50-180 min budget. The plan's `must_haves` explicitly permits `onnx_sha256: null` when `--no-onnx` is used; we exercised that escape hatch. Trade-off:

- Lost: per-detection `yolo_conf` floats in the cache.
- Preserved: the BT-03 acceptance evidence (BT-03 is independent of `yolo_conf`), the filter ablation narrative, every per-detection trade record, the full schema contract.
- Recoverable: Phase 11 can score just the post-cutoff filtered slice (~1325 detections) with the existing `_score_detection` helper in ~5 min — that's the only slice that needs a histogram for tier-threshold calibration.

The full-ONNX path is exercised end-to-end by `tests/test_backtest_yolo_conf_fallback.py::test_yolo_conf_populated_when_session_available` and the prior smoke run (`_dev/backtest_smoke.json` retained, 388 detections all populated, ONNX SHA-256 = `c793768a988f1cb9d16cb2cd59ad21dce0614a5b095f76c50a1a87019dcc6f74`). The wiring is verified; the empirical run chose to bypass it.

**No per-ticker errors.** All 503 tickers fetched and processed cleanly; `_dev/backtest_full.err` is empty. The earliest detection in the cache is 2015-08, the latest is 2026-05 — full 10y depth confirmed.

## Open Items / Follow-ups

- **Phase 11 yolo_conf scoring utility** (~50 LoC, ~5 min runtime). Sketch: load ONNX, iterate `cache["strategies"]["1to2_rr_cluster_low_stop"]["out_of_sample"]["detections"]`, refetch each detection's 60-bar window via `_fetch_ohlc + _window_for`, call `_score_detection`, write keyed yolo_conf JSON. Defer to Phase 11.
- **ThreadPoolExecutor for full-ONNX runs.** Current per-detection ONNX overlay at ~250-350 ms is the bottleneck. RESEARCH §"ONNX Overlay Performance Estimation" notes onnxruntime sessions are thread-safe for concurrent `run` calls; an N=4 worker pool around `_score_detection` could bring the full-ONNX wall-clock from ~9h to ~2-3h. Defer until/unless Phase 11 needs the full per-detection conf floats (current plan is to score just the post-cutoff filtered slice, which doesn't need parallelization).
- **Filter ablation narrative needs care in Phase 11.** The empirical "filters add small value in-sample but do not in out-of-sample" result is the honest framing. Avoid overclaiming.

## Plan-by-plan Recap

| Plan | Outcome | Commits | Duration |
|------|---------|---------|----------|
| 09-01 | Pure-function core (`simulate_trade`, `aggregate`) + 5 of 8 D-17 tests | 5 commits (df1744b, 394b85f, 64bbba4, bb4b55e, 6226b2e) | 22 min |
| 09-02 | `main()` orchestrator + cutoff partition + filter ablation + T-9-01 CLI security; 7 of 8 D-17 tests | 4 commits (cd6527e, 8635bbe, 388975c, b016c78) | 16 min |
| 09-03 | ONNX overlay (`_load_onnx_session`, `_window_for`, `_score_detection`) + `--no-onnx` bypass; all 8 D-17 tests | 2 commits (01f20f6, 51d24c7) | 12 min |
| 09-04 | Empirical full-S&P-500 run; BT-03 PASS; phase + plan SUMMARYs | (this plan — 1 docs commit) | ~3h (incl. failed full-ONNX run; 27 min for the successful --no-onnx run) |

Phase 9 close-out: 4/4 plans complete. BT-01, BT-02, BT-03 satisfied.
