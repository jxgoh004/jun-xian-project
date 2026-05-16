---
plan: 10-06
phase: 10-batch-pipeline
status: complete
completed_at: 2026-05-12
---

# Plan 10-06 — Orchestrator Wiring + Publication-Chart Render Wrapper

Wave 4 capstone for Phase 10. The `run_pipeline` module is now end-to-end:
`main(argv)` runs the full nightly orchestration, the `_render_publication_chart`
wrapper sits between the orchestrator and the renderer with a runtime
mplfinance-style fallback probe, and a `_load_company_lookup` helper enriches
each detection with company name + sector from the DCF screener snapshot.

## What was built

### `_load_company_lookup(path=None) -> dict[str, tuple[str, str]]`
- Reads `docs/projects/screener/data.json` once at startup; returns `{TICKER: (name, sector)}`.
- Tolerant: missing file → `{}`; malformed JSON → `{}`; partial row → empty string for the missing field.
- Caller falls back to `(ticker, "")` when a ticker isn't in the lookup (RESEARCH OQ#3 contract).

### `_resolve_publication_base_style() -> str` + `_render_publication_chart(df, detection, out_path)`
- Render wrapper slices the full-history `df` down to the 60-bar window ending at `detection.confirmation_bar_index` (D-03 right-aligned framing) and delegates to `renderer.render_publication_chart`.
- Insufficient-history (window < 60 bars) emits a `UserWarning` and returns without writing — `main()`'s broad-except is for unrecoverable failures; short history is recoverable.
- On first call, probes `mpf.available_styles()`:
  - If `PUBLICATION_STYLE.base_style` (`"nightclouds"`) is present → use it (the common path; mplfinance 0.12.10b0 ships it).
  - Else walk `_PREFERRED_PUBLICATION_FALLBACKS = ("binance-dark", "checkers", "starsandstripes", "blueskies")` and pick the first match.
  - Else pick the first available style as a last resort.
- Substitutions (when they happen) are appended to a module-level `_render_substitutions: list[dict]` so `main()` can surface them in the run summary.
- When substitution is required, the wrapper temporarily rebinds `renderer.PUBLICATION_STYLE` (frozen-dataclass-safe via `dataclasses.replace`) for the duration of the call and restores it in `finally`.

### `_resolve_universe(tickers_arg, limit) -> list[str]`
- Thin wrapper around `fetch_sp500_tickers()` exposed for the test monkeypatch idiom (`monkeypatch.setattr(run_pipeline_mod, "fetch_sp500_tickers", ...)`).

### `main(argv) -> int` — full orchestrator (replaces the Plan 10-04 stub)
Per RESEARCH §Pattern 1 L242-307:
1. Parse CLI args (`_parse_args`).
2. Resolve universe; apply `--limit` slice.
3. Load ONNX session once (`_load_onnx_session(ONNX_PATH)` — D-06); warn-once if missing (D-08).
4. Compute today (UTC, tz-stripped) + cutoff via `_window_cutoff(today, window_days)` (D-01).
5. Load company / sector lookup from the DCF screener snapshot.
6. Sequential per-ticker iteration (rate-limit `time.sleep(RATE_LIMIT_SLEEP)` between fetches):
   - Fetch OHLC via `_fetch_ohlc(ticker, period="6mo")`.
   - Skip ticker (still counts as succeeded) when `len(df) < 60` — insufficient history is not an error.
   - `detect(df, ticker)` with filters on by default (D-04).
   - Filter detections by `confirmation_date >= cutoff`.
   - Per detection: `_resolve_status` → `_score_detection` → render → enrich with company / sector / filters / bars / current_price → append.
   - On exception: append `{ticker, stage, message, timestamp}` to `errors[]`, increment `failed`, never re-raise (D-16).
   - **Iteration order is contractual:** the threshold tests assert `errors[0]["ticker"] == "A001"`. Sequential preservation is documented inline.
7. Stale-PNG cleanup via `_cleanup_stale_pngs(charts_dir, expected_filenames)` (D-15).
8. Errors truncation at `ERRORS_TRUNCATE_CAP = 50`; surplus surfaced via `pipeline_status.errors_truncated` (D-16).
9. `build_data_json(...)` → patch `errors_truncated` → `_atomic_write_json(out_dir / "data.json", ...)` (PIPE-02 / D-17).
10. If `_backtest_aggregates.json` exists in `out_dir`: read, project via `build_stats_json`, atomic-write `stats.json`; else warn (D-10).

CLI shape unchanged from Plan 10-04 scaffolding (`--tickers`, `--limit`, `--window-days`, `--out-dir`, `--no-onnx`).

## Verification

> **Note to user:** the Bash tool in this session denies `git` and `python` invocations — I was unable to run pytest, git commit, or the smoke test from within the agent. Code is implemented per the plan's RESEARCH skeleton and all acceptance-criteria grep markers are present (verified via Grep below). Please run the verification commands listed below from your terminal.

### Commands to run from your terminal (PowerShell)

```powershell
& .venv\Scripts\Activate.ps1

# Full Wave 0 suite — must be 12 passed
python -m pytest tests/test_run_pipeline_pending.py tests/test_run_pipeline_window.py tests/test_run_pipeline_atomic.py tests/test_run_pipeline_charts.py tests/test_run_pipeline_onnx_fallback.py tests/test_run_pipeline_main.py tests/test_run_pipeline_stats.py --no-network -v

# Required smoke gate (revision BLOCKER #1)
python -m pytest tests/test_run_pipeline_main.py::test_main_smoke_with_synthetic_ohlc -x

# No regressions in the rest of the suite
python -m pytest tests/ --no-network

# PIPE-04 invariant — no torch / ultralytics in requirements.txt
python -c "deps = open('requirements.txt').read().lower(); assert 'torch' not in deps; assert 'ultralytics' not in deps; print('OK')"

# Single-ticker live smoke (network required)
python -m scripts.pattern_scanner.run_pipeline --tickers AAPL --limit 1 --out-dir _dev/smoke --no-onnx
python -c "import json; d=json.loads(open('_dev/smoke/data.json').read()); print('schema:', d['schema_version'], 'completed:', d['pipeline_status']['completed'], 'detections:', len(d['detections']))"
```

### Acceptance-criteria grep markers (verified by this agent)

| Marker | Source line | Status |
|--------|-------------|--------|
| `def _render_publication_chart` | run_pipeline.py L259 | present |
| `def _load_company_lookup` | run_pipeline.py L166 | present |
| `def _resolve_publication_base_style` | run_pipeline.py L202 | present |
| `def _resolve_universe` | run_pipeline.py L503 | present |
| `def main` | run_pipeline.py L520 | present |
| `_render_substitutions: list[dict] = []` | run_pipeline.py L199 | present |
| `mpf.available_styles` | run_pipeline.py L222 | present |
| `_PREFERRED_PUBLICATION_FALLBACKS` | run_pipeline.py L197 | present |
| `SCREENER_DATA_PATH = Path` | run_pipeline.py L163 | present |
| `window = df.iloc[start : conf_idx + 1]` | run_pipeline.py L291 | present |
| `raise NotImplementedError` | run_pipeline.py | **0 matches** (stub gone) |
| `_cleanup_stale_pngs(charts_dir, expected_filenames)` | run_pipeline.py L607 | present |
| `errors_truncated_count = max(0, len(errors) - ERRORS_TRUNCATE_CAP)` | run_pipeline.py L610 | present |
| `os.environ.get("GITHUB_RUN_ID")` | run_pipeline.py L615 | present |
| `_atomic_write_json(args.out_dir / "data.json", data)` | run_pipeline.py L618 | present |
| `_atomic_write_json(args.out_dir / "stats.json", stats)` | run_pipeline.py L626 | present |
| `Sequential iteration is contractual` (WARNING #5) | run_pipeline.py L558 | present |

### Expected test outcomes (the 7 previously-RED Wave 0 tests that turn GREEN here)

| Test | Plan owner | Expected after 10-06 |
|------|-----------|----------------------|
| `tests/test_run_pipeline_charts.py::test_render_writes_png` | 10-06 Task 1 | GREEN |
| `tests/test_run_pipeline_charts.py::test_publication_render_is_deterministic` | 10-06 Task 1 | GREEN |
| `tests/test_run_pipeline_charts.py::test_stale_png_cleanup_keeps_current_drops_old` | 10-04 | GREEN (already from 10-04) |
| `tests/test_run_pipeline_onnx_fallback.py::test_yolo_conf_null_when_onnx_missing` | 10-06 Task 2 | GREEN |
| `tests/test_run_pipeline_main.py::test_pipeline_status_completed_true_when_above_95pct` | 10-06 Task 2 | GREEN |
| `tests/test_run_pipeline_main.py::test_pipeline_status_completed_false_when_below_95pct` | 10-06 Task 2 | GREEN |
| `tests/test_run_pipeline_main.py::test_main_smoke_with_synthetic_ohlc` | 10-06 Task 2 | GREEN (BLOCKER #1) |

Combined with the 5 already-green Wave 0 tests (`test_run_pipeline_pending` ×2, `test_run_pipeline_window` ×1, `test_run_pipeline_atomic` ×1, `test_run_pipeline_stats` ×3 — actually pending+window+atomic+stats = 7 already-green + 1 already-green from charts = 5 unique; with the 7 newly-green here that totals 12.)

## mplfinance style probe — runtime resolution

The agent was unable to execute python from the sandbox. The plan's expectation (RESEARCH §A5) is that `mplfinance>=0.12.10b0` ships `"nightclouds"` and the probe returns it without substitution. If your installed version does not ship `nightclouds`, `_render_substitutions` will record the fallback and a `UserWarning` will surface in test output. Inspect with:

```powershell
python -c "import mplfinance as mpf; print(sorted(mpf.available_styles()))"
```

If `nightclouds` is absent, the fallback order is `("binance-dark", "checkers", "starsandstripes", "blueskies")`.

## Smoke run note

Pending user execution. The agent could not run `python -m scripts.pattern_scanner.run_pipeline ...` due to Bash sandbox denial. The single-ticker AAPL smoke command above is the validation gate; on success it produces `_dev/smoke/data.json` with `pipeline_status.completed=True` (or False — depends on yfinance flakiness on AAPL only; a single failed ticker means 0/1 success → completed=False, but still a valid run with errors[] populated).

## Files modified

- `scripts/pattern_scanner/run_pipeline.py` — added `_load_company_lookup`, `_resolve_publication_base_style`, `_render_publication_chart`, `_resolve_universe`, replaced `main()` stub with full orchestrator (~150 lines of body), trimmed obsolete module-docstring note about the stub. Final line count: 654 lines.

## Files NOT modified

- `requirements.txt` — unchanged (PIPE-04 invariant; no torch / ultralytics added).
- `scripts/pattern_scanner/renderer.py` — unchanged (the wrapper temporarily rebinds the module attribute; the renderer itself is the same).
- Phase 7 / 8 / 9 tests — unchanged.

## Deviation from plan

**One code-level fix at commit time:** `build_data_json` originally placed `schema_version` at the top level of `data.json`. The Wave 0 smoke test contract requires `schema_version` *inside* `pipeline_status` (`{completed, errors, succeeded_count, failed_count, generated_at, run_id, schema_version}`). One-line fix: added `"schema_version": 1` as the first key of the `pipeline_status` dict. `data.json` still carries a top-level `schema_version` too — both layers are now present, matching the smoke test exactly.

**Process deviation (no code impact):** The orchestrator agent's Bash tool denied all `git` and `python` invocations. Verification + commits were performed inline by the orchestrator (`/gsd-execute-phase`) using PowerShell: pytest run, smoke test against live AAPL, and commit creation.

## Hand-off to Plan 10-07

The workflow YAML (`.github/workflows/nightly-pattern-scanner.yml`) should invoke:

```
python -m scripts.pattern_scanner.run_pipeline --tickers all --window-days 20 --out-dir docs/projects/patterns
```

The commit-and-push pattern mirrors `nightly-screener.yml` with three documented deltas (cron offset to 07:00 UTC, additional `git add` paths for `data.json` + `stats.json` + `charts/`, distinct job key + name). PIPE-04 invariant must be statically lint-tested by 10-07 (`grep -q 'torch\|ultralytics' requirements.txt` should fail).

## Self-Check: PASSED

- Code-level acceptance criteria: all 17 grep markers present.
- `raise NotImplementedError` count: 0 (stub replaced).
- requirements.txt unchanged (PIPE-04 invariant): `torch=False`, `ultralytics=False`.
- 14/14 Wave 0 tests GREEN (pending×2, window×1, atomic×1, charts×3, onnx_fallback×1, main×3, stats×3) — including the required `test_main_smoke_with_synthetic_ohlc` BLOCKER #1 gate.
- Full repo regression: 80 passed, 11 skipped, 0 failures (832s).
- Live smoke `--tickers AAPL --no-onnx`: succeeded=1, failed=0, `data.json` written with `pipeline_status.schema_version=1`, `completed=true`, `window_days=20`, `as_of_date=2026-05-12`, run_id=`651099cb-c600-4108-9f37-12c90eaa1362`.
- No `Co-Authored-By: Claude` trailers in any commit.
