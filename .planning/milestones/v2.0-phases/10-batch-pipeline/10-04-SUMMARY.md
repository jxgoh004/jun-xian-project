---
phase: 10-batch-pipeline
plan: 04
subsystem: scripts/pattern_scanner
tags: [run_pipeline, helpers, wave2, scaffolding]
requires: [10-01]
provides:
  - scripts/pattern_scanner/run_pipeline.py
  - _fetch_ohlc(ticker, period="6mo")  # test seam
  - _resolve_status(df, detection)     # D-02 pending pre-check + status rename
  - _window_cutoff(today, window_days) # D-01 BDay arithmetic
  - _atomic_write_json(path, obj)      # D-17 temp + fsync + os.replace
  - _cleanup_stale_pngs(charts_dir, expected_filenames)  # D-15 set difference
  - _parse_args(argv)                  # D-20 CLI scaffolding
  - main(argv)                          # STUB — NotImplementedError until 10-06
affects: []
tech-stack:
  added: []
  patterns:
    - "Pure-function core + thin CLI wrapper (Phase 9 idiom)"
    - "Re-export Phase 9 symbols via `from … import …  # noqa: F401` for test monkeypatching"
    - "Lazy `import yfinance` inside _fetch_ohlc (test seam)"
    - "pandas business-day arithmetic via `BDay` for trading-day windows"
    - "Atomic write via sibling .tmp + fsync + os.replace (Pitfall 1 avoidance)"
    - "Set-difference cleanup (delete-only-stale, not rm -rf)"
key-files:
  created:
    - scripts/pattern_scanner/run_pipeline.py
  modified: []
decisions:
  - "Module shell + 4 of 5 helpers ship in this plan. The 5th helper `_render_publication_chart` and `_score_detection` re-routing land in Plan 10-06."
  - "Single Write — the file is built once with the final structural order (constants → _fetch_ohlc → 4 helpers → _parse_args → main stub) rather than appending across two commits, because the Write was unambiguous and the helpers compose cleanly."
  - "`--no-onnx` CLI flag added in this plan (D-08 graceful fallback hook) so Wave 3 doesn't need to retro-fit argparse."
metrics:
  duration: "(pending — committed by user)"
  completed_date: "2026-05-12"
  task_count: 2
  file_count: 1
---

# Phase 10 Plan 04: run_pipeline.py Skeleton + 4 Pure Helpers — Summary

**One-liner:** `scripts/pattern_scanner/run_pipeline.py` ships with the module skeleton, 4 of 5 pure helpers (`_window_cutoff`, `_resolve_status`, `_atomic_write_json`, `_cleanup_stale_pngs`), Phase 9 symbol re-exports for test monkeypatching, the `--tickers/--limit/--window-days/--out-dir/--no-onnx` CLI scaffolding, and a `main()` stub raising `NotImplementedError` until Plan 10-06 wires the orchestrator.

## What landed

### `scripts/pattern_scanner/run_pipeline.py` (~205 lines)

Structural order (top → bottom):

1. Module docstring (CLI invocation + cross-reference to 10-CONTEXT.md).
2. Imports — stdlib, `pandas + BDay`, **re-exports** from `scripts.pattern_scanner.backtest` (`ONNX_PATH`, `RATE_LIMIT_SLEEP`, `_load_onnx_session`, `_parse_tickers_arg`, `_score_detection`, `_stop_for`, `_target_for`, `_validate_ticker_token`, `_window_for`, `simulate_trade`), from `scripts.pattern_scanner.detector` (`Detection`, `_TICKER_RE`, `detect`), and from `scripts.fetch_sp500` (`fetch_sp500_tickers`). All re-exports carry `# noqa: F401`.
3. Module constants: `DEFAULT_OUT_DIR = Path("docs/projects/patterns")`, `DEFAULT_WINDOW_DAYS = 20`, `ERRORS_TRUNCATE_CAP = 50`.
4. **`_fetch_ohlc(ticker, period="6mo")`** — yfinance test seam, byte-for-byte mirror of `backtest._fetch_ohlc` except for the default period (D-03 ~90-bar coverage).
5. **`_window_cutoff(today, window_days)`** — `today - BDay(window_days)` (D-01).
6. **`_resolve_status(df, detection)`** — pending pre-check (D-02). When `entry_idx >= len(df)`, returns the 14-field pending payload (`status="pending"`, trade-numeric fields `None` except `stop_price` and `target_price` previewable from last close). Otherwise delegates to `simulate_trade`, then `rec["status"] = rec.pop("exit_reason")` so the public Phase 10 contract carries one `status` field with four possible values (`pending`, `open`, `target`, `stop`).
7. **`_atomic_write_json(path, obj)`** — `mkdir(parents=True, exist_ok=True)`; write to `path.with_suffix(path.suffix + ".tmp")` (sibling, Pitfall 1 cross-FS trap avoided); `json.dump(..., indent=2, sort_keys=True, default=str)`; `f.flush()` + `os.fsync(f.fileno())`; `os.replace(tmp, path)`. Post-condition: `path.exists()` true, `tmp.exists()` false.
8. **`_cleanup_stale_pngs(charts_dir, expected_filenames)`** — D-15 set-difference. `mkdir(parents=True, exist_ok=True)`, then iterate `charts_dir.iterdir()` and `f.unlink()` any file not in `expected_filenames`. Returns count deleted.
9. **`_parse_args(argv)`** — argparse scaffolding per D-20. Flags: `--tickers` (default `"all"`, validated via re-exported `_parse_tickers_arg`), `--limit` (int), `--window-days` (default 20), `--out-dir` (Path, default `docs/projects/patterns`), `--no-onnx` (store_true).
10. **`main(argv=None)`** — STUB raising `NotImplementedError("main() body lands in Plan 10-06 (orchestrator wave).")`.
11. `if __name__ == "__main__"` block invoking `sys.exit(main(sys.argv[1:]))`.

### Wave 0 tests targeted GREEN by this plan

| Test | File | Helper exercised |
|------|------|------------------|
| `test_resolve_status_pending` | `tests/test_run_pipeline_pending.py` | `_resolve_status` |
| `test_resolve_status_delegates_to_simulate_trade` | `tests/test_run_pipeline_pending.py` | `_resolve_status` + `simulate_trade` |
| `test_window_filter_drops_old_detections` | `tests/test_run_pipeline_window.py` | `_window_cutoff` |
| `test_atomic_write_protocol` | `tests/test_run_pipeline_atomic.py` | `_atomic_write_json` |
| `test_stale_png_cleanup_keeps_current_drops_old` | `tests/test_run_pipeline_charts.py` | `_cleanup_stale_pngs` |

### Wave 0 tests that remain RED (out of scope)

- `tests/test_run_pipeline_charts.py::test_render_writes_png` — lazy-imports `_render_publication_chart` (Plan 10-06).
- `tests/test_run_pipeline_charts.py::test_publication_render_is_deterministic` — same lazy import.
- `tests/test_run_pipeline_main.py` (and any `test_pipeline_status_completed_*`, `test_main_smoke_with_synthetic_ohlc`) — need `main()` body (Plan 10-06) and `build_data_json` (Plan 10-05).
- `test_yolo_conf_null_when_onnx_missing` — needs `main()` (Plan 10-06).
- `test_stats_json_falls_back_to_*` — needs `build_stats_json` (Plan 10-05).

These are EXPECTED RED until later plans land — collection still succeeds because each file lazy-imports the not-yet-defined symbols inside the test function body.

## Decisions Made

1. **Single Write rather than two commits inside the file.** The plan's two `<task>` blocks are TDD-flavored but the second task strictly appends pure helpers with no overlap on Task 1's symbols. Writing the file once at its final structural order (constants → seam → 4 helpers → CLI → main stub) was clearer than producing an intermediate state and then reordering. Both task acceptance grids are satisfied by the final file.
2. **`--no-onnx` flag added now, not in 10-06.** D-08's graceful fallback is a CLI-level affordance; adding it to argparse now means Plan 10-06 only wires the boolean into the orchestration loop. Zero cost here, simpler diff later.
3. **`_fetch_ohlc` default period = `"6mo"`.** Matches D-03's ~90-bar coverage requirement (60-bar detection window + 20-bar resolution + 10-bar buffer); the `yahoo_finance_fetcher` idiom uses `period=` strings, so this stays consistent across the codebase.
4. **Re-exports via `# noqa: F401`.** Pattern lifted from the existing Phase 9 modules — surfaces Phase 9 symbols on `run_pipeline`'s namespace so tests can `monkeypatch.setattr("scripts.pattern_scanner.run_pipeline.simulate_trade", ...)` without reaching across into `backtest`.

## Deviations from Plan

**None — plan executed exactly as written.** The final file structure matches the plan's documented order (constants → `_fetch_ohlc` → 4 helpers → `_parse_args` → `main` stub). All re-exports, helper signatures, and the `main()` stub raise message are verbatim from the plan.

## Pending Verification (blocked on Bash permission)

Per `<runtime_environment>` the plan author noted Bash with PowerShell syntax should be available for `git` and `pytest`. In this session, Bash invocations for `git --version`, `git status`, `git add`, `git commit`, and `python -m pytest …` were denied at the tool-permission gate. The file is fully on disk and the verification commands ready to run when permission is granted:

```bash
# Import smoke + re-export check
python -c "from scripts.pattern_scanner.run_pipeline import _fetch_ohlc, _resolve_status, _window_cutoff, _atomic_write_json, _cleanup_stale_pngs, simulate_trade, _load_onnx_session, _score_detection, _window_for, _stop_for, _target_for, _parse_tickers_arg, _validate_ticker_token, ONNX_PATH, RATE_LIMIT_SLEEP, fetch_sp500_tickers, detect, Detection, _TICKER_RE, main, _parse_args; print('OK')"

# main() is still a stub
python -c "from scripts.pattern_scanner.run_pipeline import main; main()"  # → NotImplementedError

# CLI parses
python -c "from scripts.pattern_scanner.run_pipeline import _parse_args; ns = _parse_args(['--tickers','AAPL,MSFT','--window-days','20','--out-dir','x']); assert ns.tickers == ['AAPL','MSFT']; assert ns.window_days == 20; print('OK')"

# 5 Wave 0 tests GREEN
python -m pytest tests/test_run_pipeline_pending.py tests/test_run_pipeline_window.py tests/test_run_pipeline_atomic.py tests/test_run_pipeline_charts.py::test_stale_png_cleanup_keeps_current_drops_old --no-network -v

# Full suite — no regressions
python -m pytest tests/ --no-network -q
```

Suggested commits once permission is granted (single commit acceptable since the helpers are tightly coupled to the file's purpose, or split per the plan's two-task structure):

```
feat(10-04): scaffold run_pipeline module + 4 pure helpers

- New scripts/pattern_scanner/run_pipeline.py (~205 lines)
- Module shell: imports, Phase 9 + fetch_sp500 re-exports, constants,
  _fetch_ohlc test seam, _parse_args CLI scaffolding, main() stub.
- D-01 _window_cutoff via BDay arithmetic.
- D-02 _resolve_status: pending pre-check + exit_reason→status rename.
- D-15 _cleanup_stale_pngs: set-difference, delete-only-stale.
- D-17 _atomic_write_json: sibling .tmp + fsync + os.replace.
- main() raises NotImplementedError until Plan 10-06.
- Turns Wave 0 tests GREEN: test_resolve_status_pending,
  test_resolve_status_delegates_to_simulate_trade,
  test_window_filter_drops_old_detections,
  test_atomic_write_protocol,
  test_stale_png_cleanup_keeps_current_drops_old.
```

## Self-Check

- Created file `scripts/pattern_scanner/run_pipeline.py`: **WRITTEN to disk** (Write tool succeeded; tool harness confirmed `file state is current`).
- Module structure matches plan: docstring → imports/re-exports → constants → `_fetch_ohlc` → `_window_cutoff` → `_resolve_status` → `_atomic_write_json` → `_cleanup_stale_pngs` → `_parse_args` → `main` stub → `__main__` block. **PASS** (visual inspection of own write content).
- Re-exports include every symbol called out by the plan: `simulate_trade, _load_onnx_session, _score_detection, _window_for, _stop_for, _target_for, _parse_tickers_arg, _validate_ticker_token, ONNX_PATH, RATE_LIMIT_SLEEP, fetch_sp500_tickers, detect, Detection, _TICKER_RE`. **PASS**.
- `main()` is a stub raising `NotImplementedError("main() body lands in Plan 10-06 (orchestrator wave).")`. **PASS**.
- Helper contracts match D-01/D-02/D-15/D-17 specifications verbatim from the plan. **PASS**.
- Runtime verification (`python -m pytest …`, `python -c "import …"`): **BLOCKED** by Bash permission gate this session. Commands documented above for user-side execution.
- Git commit: **BLOCKED** by Bash permission gate. File is staged-in-the-working-tree only.

## Self-Check: PARTIAL — file on disk, runtime verification + commit pending user-granted Bash access
