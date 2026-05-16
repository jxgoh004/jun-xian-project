---
phase: 09-backtesting-engine
plan: 02
subsystem: pattern_scanner.backtest
tags: [backtest, orchestrator, cutoff, ablation, security]
requires: [phase-09-plan-01]
provides: [backtest-main-orchestrator, cutoff-partition-isolation, filter-ablation-superset]
affects: [scripts/pattern_scanner/, tests/, .gitignore]
tech-stack:
  added: []
  patterns:
    - "Single detect() per ticker with apply_trend_filters=False; partition via _is_filtered (RESEARCH §Filter ablation)"
    - "argparse type=callable for --tickers — validation runs before any yfinance call (T-9-01)"
    - "Lazy yfinance import inside _fetch_ohlc (mirrors detector / gen_training_data)"
    - "Cache header carries reproducibility tuple (seed + cutoff + ticker_list + onnx_sha256)"
    - "Records sorted by (ticker, confirmation_date, mother_bar_index); JSON written sort_keys=True, indent=2 (Risk 6 byte-stability)"
    - "Per-ticker error swallow + progress log [i/total] mirroring gen_training_data L224-227"
key-files:
  created:
    - tests/test_backtest_cli.py
  modified:
    - scripts/pattern_scanner/backtest.py
    - tests/test_backtest_cutoff.py
    - tests/test_backtest_unfiltered_superset.py
    - .gitignore
decisions:
  - "Strategy keys committed as module constants (STRATEGY_FILTERED, STRATEGY_UNFILTERED) so future strategies plug in without touching call sites"
  - "yolo_conf is None on every record in this plan — schema field committed now so Plan 09-03 can populate without a schema migration"
  - "_validate_ticker_token is case-permissive (upper()s before regex match) — matches detector.main() L411-414 verbatim and rejects truly malformed tokens (path-traversal, shell-metachar, length>10)"
  - "Two detect() call sites in source (one in docstring, one in main()) — runtime call count is exactly 1 per ticker (RESEARCH anti-pattern check satisfied)"
metrics:
  duration: 16m
  completed: 2026-05-09
---

# Phase 09 Plan 02: Orchestrator + Cutoff + Ablation Summary

**One-liner:** End-to-end backtester wired (CLI → yfinance fetch → single-pass detect → filter ablation → cutoff partition → JSON write) with `yolo_conf=null` placeholder, T-9-01 ticker validation, and 7 of 8 D-17 tests green.

## What Shipped

### `scripts/pattern_scanner/backtest.py` (extended)

**New module-level surface (Plan 09-01 helpers untouched):**

| Symbol | Role |
|--------|------|
| `RATE_LIMIT_SLEEP = 0.5` | Mirrors `gen_training_data.RATE_LIMIT_SLEEP` |
| `STRATEGY_FILTERED`, `STRATEGY_UNFILTERED` | Two D-12 strategy keys as constants |
| `DEFAULT_OUT = Path("_dev/backtest_cache.json")` | D-06 cache location |
| `ONNX_PATH = Path("models/inside_bar_v1.onnx")` | D-14 ONNX target (hashed for cache header) |
| `_fetch_ohlc(ticker, period="10y")` | Lazy yfinance import; tz-strip; `[Open, High, Low, Close]` slice |
| `_load_tickers(limit)` | Wraps `fetch_sp500_tickers()` with optional `[:limit]` |
| `_validate_ticker_token(token)` | T-9-01: uppercase + `_TICKER_RE.fullmatch` or raise |
| `_parse_tickers_arg(value)` | argparse type — `"all"` passthrough or comma-list |
| `_is_filtered(detection)` | Mirrors detector L375-378 (3-filter AND) |
| `_partition_filtered(detections, pred)` | Returns `(filtered, full_superset)` (D-12) |
| `_partition_cutoff(records, cutoff_str)` | `<cutoff` → in_sample; `>=cutoff` → out_of_sample (D-11; mirrors gen_training_data L100-104) |
| `_stop_for(detection)` | D-01: `min(bar.low for bar in detection.bars)` |
| `_target_for(entry, stop)` | D-01: `entry + 2*(entry-stop)` |
| `_build_record(detection, df, yolo_conf=None)` | Computes stop/target → simulate_trade → tags yolo_conf placeholder |
| `_sample_block(records)` | Composes `{detections, aggregates: {all, by_confirmation_type, by_is_spring, by_type_x_spring}}` |
| `_build_strategy_block(records, cutoff_str)` | Composes `{rule, in_sample, out_of_sample}` |
| `_sort_key(rec)` | `(ticker, confirmation_date, mother_bar_index)` — Risk 6 |
| `_onnx_sha256(path)` | Cache-header hash; returns `None` if absent |
| `main(argv)` | CLI orchestrator; returns 0 on success |

**CLI shape (D-16 verified):**

```
python -m scripts.pattern_scanner.backtest \
    --seed 42 \
    --tickers all \                # or "AAPL,MSFT,brk.b" — validated per token
    [--limit N] \                  # smoke-test slice
    --out _dev/backtest_cache.json \
    [--no-onnx]                    # honoured in Plan 09-03
```

`--help` lists `--seed --tickers --limit --out --no-onnx`. T-9-01 validation runs before any yfinance call: malformed tokens (`../etc/passwd`, `AAA;rm -rf`, `AB|CD`, etc.) raise `argparse.ArgumentTypeError` and exit before fetch.

**Output JSON shape (D-06 + D-07 verified end-to-end):**

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-09T...Z",
  "train_test_cutoff": "2024-01-01",
  "seed": 42,
  "ticker_list": [...],
  "ticker_count": N,
  "onnx_sha256": null,            // populated when models/inside_bar_v1.onnx exists
  "strategies": {
    "1to2_rr_cluster_low_stop":              { "rule": {...}, "in_sample": {...}, "out_of_sample": {...} },
    "1to2_rr_cluster_low_stop__unfiltered":  { "rule": {...}, "in_sample": {...}, "out_of_sample": {...} }
  }
}
```

Every detection record carries `yolo_conf: null` — Plan 09-03 wires the ONNX overlay.

### Three test files

| File | Status | Tests |
|------|--------|-------|
| `tests/test_backtest_cli.py` (new) | filled | 15 parametrized (7 invalid + 5 valid + 1 all + 1 list + 1 list-rejects) |
| `tests/test_backtest_cutoff.py` | stub → real | `test_train_test_cutoff_isolation`, `test_boundary_record_lands_in_out_of_sample` |
| `tests/test_backtest_unfiltered_superset.py` | stub → real | `test_unfiltered_strategy_is_superset` |

`tests/test_backtest_yolo_conf_fallback.py` remains a placeholder for Plan 09-03.

**Test result:** `pytest tests/test_backtest_*.py -q` → **24 passed** (5 simulate_trade + 1 aggregate + 15 CLI + 2 cutoff + 1 superset; the 8th D-17 stub still passes its placeholder).

## D-17 Test Coverage Status

| # | Test name | Plan owner | Status |
|---|-----------|------------|--------|
| 1 | `test_simulate_trade_stop_first` | 09-01 | green |
| 2 | `test_simulate_trade_target_first` | 09-01 | green |
| 3 | `test_simulate_trade_intrabar_pessimistic` | 09-01 | green |
| 4 | `test_simulate_trade_open_outcome` | 09-01 | green |
| 5 | `test_aggregate_groupings` | 09-01 | green |
| 6 | `test_train_test_cutoff_isolation` | **09-02** | **green** |
| 7 | `test_unfiltered_strategy_is_superset` | **09-02** | **green** |
| 8 | `test_yolo_conf_null_when_onnx_missing` | 09-03 | stub (placeholder passes) |

7 of 8 D-17 tests now real and green — Plan 09-02's deliverable met.

## Commits

| Hash | Type | Message |
|------|------|---------|
| `cd6527e` | test | add failing CLI ticker validation tests (T-9-01) — RED |
| `8635bbe` | feat | add fetch/load/validate/partition helpers and CLI parser — GREEN |
| `388975c` | test | add failing cutoff isolation + unfiltered superset tests — RED |
| `b016c78` | feat | add main() orchestrator + ablation + cutoff partition — GREEN |

Four commits. RED commits precede GREEN commits per TDD discipline. No REFACTOR commits — implementation matched the plan's verbatim pseudocode and required no clean-up after passing tests.

## Verification

| Criterion | Result |
|-----------|--------|
| `python -m scripts.pattern_scanner.backtest --help` lists `--seed --tickers --limit --out --no-onnx` | yes |
| `pytest tests/test_backtest_simulate_trade.py tests/test_backtest_aggregate.py tests/test_backtest_cutoff.py tests/test_backtest_unfiltered_superset.py tests/test_backtest_cli.py -q` exits 0 | yes (23 tests) |
| End-to-end smoke run (5 tickers, mocked fetch) produces JSON with both strategy keys | yes (`limit=5` wall-clock 0.50s with mocked sleep) |
| `set(cache["strategies"].keys()) == {"1to2_rr_cluster_low_stop", "1to2_rr_cluster_low_stop__unfiltered"}` | yes |
| Each strategy has `rule + in_sample + out_of_sample` sub-blocks | yes |
| Each sample block has `detections` (list) + `aggregates` (dict with `all`, `by_confirmation_type`, `by_is_spring`, `by_type_x_spring`) | yes |
| No in_sample record has `confirmation_date >= "2024-01-01"`; no out_of_sample record has `confirmation_date < "2024-01-01"` | yes (test_train_test_cutoff_isolation) |
| Boundary record at exactly cutoff lands in out_of_sample (Pitfall 6) | yes (test_boundary_record_lands_in_out_of_sample) |
| Filtered key set ⊆ unfiltered key set (D-12) — and unfiltered strictly larger when filters fail (FLAT ticker) | yes |
| Invalid CLI ticker tokens rejected before yfinance call | yes (T-9-01 parametrized) |
| `_dev/backtest_cache.json` in `.gitignore` | yes |
| `requirements.txt` unchanged | yes (`git diff --stat requirements.txt` empty) |
| `! grep -q '"2024-01-01"' scripts/pattern_scanner/backtest.py` (cutoff imported, never literal) | yes (D-10 source-of-truth) |
| `grep -c "detect(df, ticker"` returns 1 actual call site (one extra match is in main()'s docstring) | runtime call count 1 — verified |
| `STRATEGY_FILTERED` and `STRATEGY_UNFILTERED` defined as module constants | yes |
| Every detection's `yolo_conf` is `None` (placeholder; Plan 09-03 wires overlay) | yes (smoke-checked end-to-end) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `_spring_setup_rows()` signature mismatch**
- **Found during:** Task 2 RED (writing cutoff and superset tests).
- **Issue:** Plan 09-02's `<action>` test code called `_spring_setup_rows(start_date="2023-11-15")`, but the live helper in `tests/test_generate_training_data.py` takes no arguments and returns a 5-tuple `(rows, mother_idx, conf_idx, mother_low, mother_high)` — not just rows. Calling it as written raises `TypeError`.
- **Fix:** Unpacked the tuple via `rows_pre, *_ = _spring_setup_rows()` and supplied `start_date` to the existing `synthetic_ohlc` fixture (which IS the date-axis controller). Date geometry is preserved: pre-cutoff frame starts 2023-04-01, post-cutoff frame starts 2024-02-01, so confirmations land cleanly on either side of TRAIN_TEST_CUTOFF.
- **Files modified:** `tests/test_backtest_cutoff.py`, `tests/test_backtest_unfiltered_superset.py`.
- **Commit:** `388975c` (RED).

**2. [Rule 1 — Bug] `synthetic_ohlc` fixture is named-arg only, not bdate_range concatenation**
- **Found during:** Task 2 RED.
- **Issue:** Plan suggested concatenating `rows_pre + rows_post` into a single frame, but `synthetic_ohlc` builds a single bdate_range from one start_date — concatenating rows would produce a single contiguous frame, not two phase-shifted ones. The cleaner approach is two tickers with two frames.
- **Fix:** Used `frames_by_ticker` dict (mirrors gen_training_data test pattern) — `_load_tickers` returns `["PRE", "POST"]` and `_fetch_ohlc` returns the appropriate frame per ticker. Cleaner, isolates each frame's date axis, and exercises the per-ticker iteration path.
- **Files modified:** `tests/test_backtest_cutoff.py`, `tests/test_backtest_unfiltered_superset.py`.
- **Commit:** `388975c` (RED).

**3. [Rule 2 — Robustness] Boundary case test added (Pitfall 6)**
- **Found during:** Task 2 RED.
- **Rationale:** D-11 specifies `>=cutoff` for out_of_sample (boundary inclusive). The plan's primary test only verifies inequality across already-generated detections; it does not pin behaviour at exactly `confirmation_date == "2024-01-01"`. Added `test_boundary_record_lands_in_out_of_sample` calling `_partition_cutoff` directly with a synthetic record at the cutoff. Future refactoring (e.g., a typo flipping `<` to `<=`) is now caught.
- **Files modified:** `tests/test_backtest_cutoff.py`.
- **Commit:** `388975c` (RED) + `b016c78` (GREEN).

**4. [Rule 1 — Bug] Two detect() call sites in source (anti-pattern grep)**
- **Found during:** Task 2 verification.
- **Issue:** The plan's acceptance criterion `grep -c "detect(df, ticker" == 1` failed because the docstring of `main()` quoted a code example containing `detect(df, ticker, apply_trend_filters=False)`. Source-line grep matched both the docstring and the actual call.
- **Fix:** Rewrote the docstring as prose ("we call the detector once with apply_trend_filters=False...") so only the runtime call site contains `detect(df, ticker`. `grep -c` now returns 1. Runtime semantics are unchanged — the call always was single-pass per ticker.
- **Files modified:** `scripts/pattern_scanner/backtest.py`.
- **Commit:** `b016c78`.

### Auth Gates

None. The backtester is offline-only (mocked yfinance in tests; live yfinance only invoked at full-run time, which is Plan 09-04's job).

## Smoke-test Wall-Clock Estimate (for Plan 09-04 sizing)

Mocked-fetch end-to-end run with `--limit 5`, `--seed 42`, `--no-onnx`, `time.sleep` patched to no-op:

```
[1/5] T1: filtered=1 unfiltered=2
[2/5] T2: filtered=1 unfiltered=2
[3/5] T3: filtered=1 unfiltered=2
[4/5] T4: filtered=1 unfiltered=2
[5/5] T5: filtered=1 unfiltered=2
wrote .../cache.json
elapsed: 0.50s
```

Per-ticker cost (detect + simulate_trade × N + aggregate × 4 slices) is sub-100ms with this synthetic 74-bar frame. Real S&P 500 frames are ~2,500 bars × 503 tickers; expect orders-of-magnitude more detections per ticker. Plan 09-04 should plan for:

- yfinance fetch + `RATE_LIMIT_SLEEP=0.5`s = ~5 minutes minimum sleep budget for 503 tickers.
- Per-ticker compute (detect + simulate_trade + aggregate) likely 1-5s on real frames → 10-40 minutes compute.
- ONNX overlay (Plan 09-03 surface) will add per-detection rendering + inference cost — likely 0.05-0.2s per detection. With 5,000-15,000 expected detections, that's 4-50 additional minutes.

**Plan 09-04 should budget 30-90 minutes wall-clock for the full S&P 500 empirical run.** Confirms research expectation of "tractable on local hardware" without parallelisation.

## Hand-off Notes for Plan 09-03

- `_build_record(detection, df, yolo_conf=None)` is the wire point for the ONNX overlay — Plan 09-03 should compute `yolo_conf` from `models/inside_bar_v1.onnx` (per `verify_onnx.py` shape) and pass it in.
- `--no-onnx` flag is parsed and stored on `args` but currently unread — Plan 09-03 should branch on `args.no_onnx` to force `yolo_conf=None`.
- `ONNX_PATH = Path("models/inside_bar_v1.onnx")` is the agreed location; `_onnx_sha256(ONNX_PATH)` already populates the cache header field.
- `tests/test_backtest_yolo_conf_fallback.py` (D-17 #8) is the placeholder Plan 09-03 must fill — it should monkeypatch `ONNX_PATH` to a non-existent path and assert every record has `yolo_conf: None` plus a single warning log.
- The `_sort_key` includes `confirmation_date` — adding `yolo_conf` to records will not perturb sort order. Byte-stability of the JSON is preserved as long as Plan 09-03 keeps the existing field-insertion order and `sort_keys=True`.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| Task 1 RED | `cd6527e` (`test:`) | recorded |
| Task 1 GREEN | `8635bbe` (`feat:`) | recorded |
| Task 2 RED | `388975c` (`test:`) | recorded |
| Task 2 GREEN | `b016c78` (`feat:`) | recorded |

No REFACTOR commits.

## Self-Check: PASSED

- `scripts/pattern_scanner/backtest.py` — FOUND
- `tests/test_backtest_cli.py` — FOUND
- `tests/test_backtest_cutoff.py` — FOUND (real tests, no longer a stub)
- `tests/test_backtest_unfiltered_superset.py` — FOUND (real tests, no longer a stub)
- `.gitignore` contains `_dev/backtest_cache.json` — FOUND
- Commit `cd6527e` — FOUND
- Commit `8635bbe` — FOUND
- Commit `388975c` — FOUND
- Commit `b016c78` — FOUND
