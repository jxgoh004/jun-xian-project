---
phase: 9
slug: backtesting-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Compiled from `09-RESEARCH.md` Validation Architecture (lines 786–839).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (standard discovery) — already configured by Phase 7+8 |
| **Config file** | `tests/conftest.py` (no separate pytest.ini) |
| **Quick run command** | `pytest tests/test_backtest_simulate_trade.py tests/test_backtest_aggregate.py -x` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds (full backtest test set; unit-level only — no network) |

---

## Sampling Rate

- **After every task commit:** Run the unit tests touched by that task — e.g. `pytest tests/test_backtest_simulate_trade.py -x` after editing `simulate_trade`.
- **After every plan wave:** Run `pytest tests/test_backtest_*.py -q` (the full Phase 9 backtest test set).
- **Before `/gsd-verify-work`:** Full suite green (`pytest tests/ -q`) PLUS the one-time full-run that produces `_dev/backtest_cache.json` with N ≥ 10 evidence (Plan 09-04 deliverable).
- **Max feedback latency:** ~5 seconds for unit tests; ~15–25 minutes for the one-time empirical run.

---

## Per-Task Verification Map

> Filled in by the planner during PLAN.md generation. Each plan task gets a row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 9-01-W0 | 01 | 0 | scaffold | — | N/A | scaffold | `touch tests/test_backtest_*.py` | ❌ W0 | ⬜ pending |
| 9-01-XX | 01 | 1 | BT-01 (simulate_trade) | — | N/A | unit | `pytest tests/test_backtest_simulate_trade.py -x` | ❌ W0 | ⬜ pending |
| 9-01-XX | 01 | 1 | BT-01 (aggregate) | — | N/A | unit | `pytest tests/test_backtest_aggregate.py -x` | ❌ W0 | ⬜ pending |
| 9-02-XX | 02 | 1 | BT-02 (cutoff isolation) | — | N/A | integration (synthetic) | `pytest tests/test_backtest_cutoff.py -x` | ❌ W0 | ⬜ pending |
| 9-02-XX | 02 | 1 | BT-02 (filter ablation superset) | — | N/A | unit | `pytest tests/test_backtest_unfiltered_superset.py -x` | ❌ W0 | ⬜ pending |
| 9-02-XX | 02 | 1 | input validation | T-9-01 | reject non-`_TICKER_RE` tokens before yfinance call | unit | `pytest tests/test_backtest_cli.py::test_invalid_ticker_rejected -x` | ❌ W0 | ⬜ pending |
| 9-03-XX | 03 | 1 | BT-03 (yolo_conf fallback) | — | N/A | unit | `pytest tests/test_backtest_yolo_conf_fallback.py -x` | ❌ W0 | ⬜ pending |
| 9-04-XX | 04 (opt) | manual | BT-03 (N ≥ 10 empirical) | — | N/A | manual / one-time | `python -m scripts.pattern_scanner.backtest --seed 42 --tickers all` then inspect JSON | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_backtest_simulate_trade.py` — stubs for BT-01 (4 sub-tests: stop_first, target_first, intrabar_pessimistic, open_outcome)
- [ ] `tests/test_backtest_aggregate.py` — stubs for BT-01 aggregation (`test_aggregate_groupings`)
- [ ] `tests/test_backtest_cutoff.py` — stubs for BT-02 cutoff isolation
- [ ] `tests/test_backtest_unfiltered_superset.py` — stubs for BT-02 ablation strict-superset
- [ ] `tests/test_backtest_yolo_conf_fallback.py` — stubs for BT-03 ONNX-missing fallback

(No new framework or fixture install needed — pytest + `synthetic_ohlc` fixture from `tests/conftest.py` and `_fetch_ohlc` monkeypatch pattern from `tests/test_generate_training_data.py` are reused verbatim.)

---

## Validation Dimensions for Backtest Correctness

> Five dimensions compiled from RESEARCH.md §"Validation Dimensions for Backtest Correctness". Each dimension maps to an automated test above.

1. **Deterministic reproducibility** — Same `(seed, ticker list, cutoff, ONNX hash)` produces byte-identical `_dev/backtest_cache.json`. Test = run twice with `--limit 3 --seed 42` against monkeypatched `_fetch_ohlc`; assert byte-identical files.
2. **Cutoff isolation (BT-02)** — No `in_sample` record has `confirmation_date >= cutoff`; no `out_of_sample` record has `confirmation_date < cutoff`. Per-record assertion across the entire JSON.
3. **Aggregate math correctness (BT-01)** — Per cell: `n == target_count + stop_count + open_count`; `n_resolved == target_count + stop_count`; `win_rate == target_count / n_resolved` when `n_resolved > 0`.
4. **Outcome resolution monotonicity (BT-01)** — Once `exit_reason ∈ {stop, target}`, the forward-walk loop exits. Synthetic test asserts exit_date is the first bar where stop hit, even if a later bar would have hit target.
5. **Filter ablation strict-superset (BT-02)** — For every `(ticker, mother_idx, conf_idx)` triple in the filtered strategy, the same triple appears in the unfiltered strategy.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `out_of_sample` slice contains ≥10 detections for at least one `confirmation_type` | BT-03 | Empirical evidence from a real S&P 500 + 10y yfinance run; cannot be unit-tested deterministically | Run `python -m scripts.pattern_scanner.backtest --seed 42 --tickers all --out _dev/backtest_cache.json` then inspect JSON. Plan 09-04 deliverable. |
| Wall-time stays under 30 minutes for the full S&P 500 run | D-15 (Claude's discretion) | Depends on yfinance + ONNX inference performance | Same run; record duration in 09-04 SUMMARY. If wall-clock > 30 min, refine to `ThreadPoolExecutor` per RESEARCH risk #5. |

---

## Validation Sign-Off

- [ ] All plan tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all 5 MISSING test files
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s for unit tests
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
