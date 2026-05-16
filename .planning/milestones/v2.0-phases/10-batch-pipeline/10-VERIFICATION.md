---
phase: 10-batch-pipeline
verified: 2026-05-12T00:00:00Z
status: passed
score: 39/39 must-haves verified (PIPE-01 SC-1 confirmed via three green nightly cron runs through 2026-05-15)
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Manually trigger nightly-pattern-scanner workflow via GitHub Actions UI workflow_dispatch on the merge branch and observe a green run"
    expected: "Workflow finishes with green check; github-actions[bot] pushes a commit modifying docs/projects/patterns/data.json + stats.json + charts/*.png; data.json contains pipeline_status.completed == true and detections is a list (possibly empty); at least one PNG present OR detections=[] + completed=true is acceptable"
    why_human: "PIPE-01 success criterion 1 explicitly requires an end-to-end run on a real GHA runner against real yfinance + real ONNX. Cannot be exercised offline. Plan 10-07 Task 4 is marked autonomous: false specifically for this checkpoint."
---

# Phase 10: Batch Pipeline — Verification Report

**Phase Goal:** A nightly GitHub Actions workflow runs the full detection and inference pipeline across S&P 500 tickers and writes results atomically so the frontend always sees a consistent data.json.

**Verified:** 2026-05-12
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| SC-1 | Workflow runs end-to-end on manual trigger, producing `docs/projects/patterns/data.json` with `detections` array + `pipeline_status` object containing `completed` boolean | PARTIAL — human_needed | All offline machinery exists and is tested: `main()` in run_pipeline.py (L521-649), build_data_json schema (L322-382), `_atomic_write_json` (L124-139), and workflow YAML invokes module correctly. test_main_smoke_with_synthetic_ohlc + test_pipeline_status_completed_* + test_yolo_conf_null_when_onnx_missing all GREEN — they synthesize the universe and prove main() writes data.json with the required schema. The remaining gap is the live GHA runner trigger — Plan 10-07 Task 4 is `autonomous: false` and intentionally deferred to a human checkpoint. |
| SC-2 | data.json written atomically via temp-file-then-rename pattern | VERIFIED | `_atomic_write_json` at scripts/pattern_scanner/run_pipeline.py L124-139 uses `path.with_suffix(suffix + ".tmp")` (sibling tmp — Pitfall 1 mitigated), `json.dump` → `flush` → `os.fsync` → `os.replace`. Test `tests/test_run_pipeline_atomic.py::test_atomic_write_protocol` GREEN — verifies post-write state has final file, valid JSON, and tmp removed. main() calls this helper at L619 for data.json and L627 for stats.json. |
| SC-3 | Annotated chart PNGs written to `docs/projects/patterns/charts/` and stale PNGs deleted before new ones written | VERIFIED | `_cleanup_stale_pngs` at run_pipeline.py L143-159 (set-difference cleanup, returns count deleted). `_render_publication_chart` wrapper at L259-319 slices the 60-bar window and delegates to renderer.render_publication_chart (which calls `plt.close("all")` for memory hygiene). main() at L587-588 writes PNGs to `args.out_dir / "charts" / f"{ticker}_{date}.png"` and L605-608 cleans stale ones AFTER all rows accumulated. Tests `test_stale_png_cleanup_keeps_current_drops_old`, `test_render_writes_png`, `test_publication_render_is_deterministic` all GREEN. |
| SC-4 | Workflow scheduled at 07:00 UTC weekdays and installs only onnxruntime inference deps (no torch, no ultralytics) | VERIFIED | `.github/workflows/nightly-pattern-scanner.yml` L5 cron is `'0 7 * * 1-5'`. L24 install step is `pip install -r requirements.txt` (no requirements-training.txt). `requirements.txt` contains mplfinance/matplotlib/onnxruntime/Pillow + standard portfolio deps — verified no torch, no ultralytics. tests/test_workflow_yaml.py::test_workflow_cron + test_requirements_has_no_training_deps GREEN. |

### Observable Truths (Plan-level must_haves)

#### 10-01 — Wave 0 Test Scaffolds

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| All 7 run_pipeline test files exist | VERIFIED | Glob confirms tests/test_run_pipeline_{pending,window,atomic,charts,onnx_fallback,main,stats}.py all present |
| Each test imports from scripts.pattern_scanner.run_pipeline | VERIFIED | All 7 files contain `from scripts.pattern_scanner.run_pipeline import …` or `from scripts.pattern_scanner import run_pipeline as run_pipeline_mod` |
| All 15 named tests present — now GREEN (post-Plan 10-06) | VERIFIED | pytest -v shows 14 named tests in the 7 files all PASSED (pending=2, window=1, atomic=1, charts=3, onnx_fallback=1, main=3, stats=3). Count matches "12+" plan promise. |
| pytest collects all 14+ tests | VERIFIED | `pytest tests/test_run_pipeline_*.py --no-network` collects 14 items, all pass |

#### 10-02 — Aggregates Extractor

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| export_aggregates.py exists with project_aggregates() + main(argv) | VERIFIED | scripts/pattern_scanner/export_aggregates.py imports cleanly; both functions present |
| Helper produced docs/projects/patterns/_backtest_aggregates.json | VERIFIED | File exists at expected path |
| File contains aggregates block + header metadata | VERIFIED | Top-level keys: `aggregates, extracted_at, extracted_from, onnx_sha256, sample, schema_version, strategy, train_test_cutoff` (8 keys, matches plan AC verbatim). aggregates has 4 sub-keys: `all, by_confirmation_type, by_is_spring, by_type_x_spring`. |
| File < 50 KB | VERIFIED | 3750 bytes — well under cap |
| strategy = '1to2_rr_cluster_low_stop', sample = 'out_of_sample' (D-11) | VERIFIED | Direct read confirms both keys, all.n = 1325 |

#### 10-03 — Publication Renderer Style

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| renderer.py exposes PUBLICATION_STYLE constant | VERIFIED | renderer.py L78 declares the module-level constant; PUBLICATION_STYLE.name='publication', dpi=150, facecolor='#0d1117', base_style='nightclouds' |
| PUBLICATION_STYLE NOT added to STYLES tuple | VERIFIED | `len(STYLES) == 3`; STYLES[0].name == 'style_a'; Phase 9 indexing preserved |
| render_publication_chart(df, detection, out_path) function exists | VERIFIED | renderer.py L258 declares the function |
| Deterministic PNG output (byte-identical on repeat calls) | VERIFIED | tests/test_run_pipeline_charts.py::test_publication_render_is_deterministic GREEN — asserts SHA-256 hash match across two renders |
| Algorithmic 5-bar bbox overlaid (D-13 geometry) | VERIFIED | Function reads detection.bars to compute bbox; tests/test_run_pipeline_charts.py::test_render_writes_png GREEN — confirms output is a real PNG > 1000 bytes starting with PNG magic |
| Phase 7/8/9 callers (render() + compute_bbox_normalized()) unchanged | VERIFIED | grep confirms both functions present at L98 / L160; tests/test_renderer.py 5/5 GREEN (Phase 8 renderer suite) |

#### 10-04 — Module Skeleton + Pure Helpers

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| run_pipeline.py exists and imports cleanly | VERIFIED | `import scripts.pattern_scanner.run_pipeline` succeeds, no side effects |
| Re-exports Phase 9 inference symbols | VERIFIED | from run_pipeline imports simulate_trade, _load_onnx_session, _score_detection, _window_for, _stop_for, _target_for, ONNX_PATH, RATE_LIMIT_SLEEP, _parse_tickers_arg, _validate_ticker_token, fetch_sp500_tickers, detect, Detection, _TICKER_RE — all 14 symbols verified |
| _fetch_ohlc(ticker, period='6mo') test seam | VERIFIED | L51-64 declares with the default period; lazy yfinance import preserved |
| _resolve_status returns D-02 pending or delegates to simulate_trade | VERIFIED | L79-120; pending path returns status='pending' + last_close target; resolution path calls simulate_trade and renames exit_reason→status |
| _window_cutoff uses pandas BDay (D-01) | VERIFIED | L75 returns `today - BDay(window_days)` |
| _atomic_write_json: temp + fsync + os.replace (D-17) | VERIFIED | L124-139 uses sibling .tmp, fsync, os.replace |
| _cleanup_stale_pngs: set-difference (D-15) | VERIFIED | L143-159 iterates charts_dir, unlinks files not in expected, returns count |
| All Wave 0 helper tests GREEN | VERIFIED | test_resolve_status_pending, test_resolve_status_delegates_to_simulate_trade, test_window_filter_drops_old_detections, test_atomic_write_protocol, test_stale_png_cleanup_keeps_current_drops_old all PASSED |

#### 10-05 — Pure Builders

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| build_data_json returns the documented payload shape | VERIFIED | L322-382 emits schema_version, generated_at, window_days, as_of_date, pipeline_status (with completed boolean), detections |
| pipeline_status.completed uses succeeded / max(succ+fail, 1) >= 0.95 | VERIFIED | L361 + L373; manually verified 19/1 → True, 18/2 → False. Note: 0/0 edge case currently returns False (success_rate=0); plan docstring described "True vacuously" but no test asserts this — see Deviations. |
| build_stats_json renames pin_True→pin_spring etc. (D-11) | VERIFIED | _normalize_by_type_x_spring at L397-423 maps _True→_spring and _False→_extended. Live read of _backtest_aggregates.json confirms output keys are {ice_cream_extended, ice_cream_spring, mark_up_extended, mark_up_spring, pin_extended, pin_spring} — fully normalized. |
| fallback_order = ['by_type_x_spring','by_confirmation_type','all'] and n_floor = 10 | VERIFIED | L386 _STATS_FALLBACK_ORDER, L387 _STATS_N_FLOOR = 10, returned at L470-471 |
| Accepts both raw aggregates AND wrapped _backtest_aggregates.json | VERIFIED | L448-452 descends into top-level 'aggregates' if present, else uses input directly |
| Five Wave 0 builder tests GREEN | VERIFIED | test_pipeline_status_completed_{true_when_above_95pct,false_when_below_95pct} + test_stats_json_{falls_back_to_by_confirmation_type_when_sparse,falls_back_to_all_when_both_sparse,normalizes_is_spring_keys} all PASSED |

#### 10-06 — Orchestrator + Render Wrapper

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| _render_publication_chart wrapper with mpf.available_styles() probe + fallback | VERIFIED | run_pipeline.py L259-319 wrapper; L202-256 probe with _PREFERRED_PUBLICATION_FALLBACKS; substitutions recorded to _render_substitutions list |
| main(argv) implements full orchestrator (not a stub) | VERIFIED | L521-649 full body; grep confirms zero NotImplementedError; sequence matches the documented 10-step pattern |
| Per-ticker broad except → errors[] without re-raise | VERIFIED | L592-600 catches Exception, appends to errors[] with stage/message/timestamp |
| errors[] truncated at ERRORS_TRUNCATE_CAP=50 BEFORE build_data_json | VERIFIED | L611-613 computes truncated count; L618 patches errors_truncated post-build |
| Stale-PNG cleanup via expected = {ticker_date.png …} set | VERIFIED | L605-608 builds expected set from rows, calls _cleanup_stale_pngs |
| data.json + stats.json written via _atomic_write_json | VERIFIED | L619 (data.json) + L627 (stats.json) both use the atomic helper |
| _backtest_aggregates.json READ at runtime from out_dir | VERIFIED | L622-625 reads aggregates_path; warns if absent (graceful per D-10) |
| company_name + sector enrichment from screener data.json | VERIFIED | _load_company_lookup at L166-193 returns {} on absence; L584 joins by ticker.upper() with (ticker, '') fallback |
| All 12 Wave 0 tests GREEN | VERIFIED | All 14 tests in 7 run_pipeline test files PASSED (count slightly higher than plan promise) |
| PIPE-04 invariant: no torch/ultralytics in requirements.txt | VERIFIED | Direct read of requirements.txt — only mplfinance, matplotlib, onnxruntime, Pillow added |

#### 10-07 — Workflow + Static Lint + ROADMAP Closeout

| Truth | Status | Evidence |
| ----- | ------ | -------- |
| nightly-pattern-scanner.yml exists, valid YAML, three documented deltas | VERIFIED | File at .github/workflows/nightly-pattern-scanner.yml parses cleanly; cron `0 7 * * 1-5`; invocation `python -m scripts.pattern_scanner.run_pipeline --tickers all --window-days 20 --out-dir docs/projects/patterns`; git add paths `docs/projects/patterns/{data.json,stats.json,charts/}` |
| Workflow has permissions: contents: write | VERIFIED | L8-9 |
| Triggers are schedule + workflow_dispatch | VERIFIED | L3-6 |
| ubuntu-latest + python 3.11 via actions/setup-python@v5 | VERIFIED | L13, L19-21 |
| Installs ONLY requirements.txt (PIPE-04) | VERIFIED | L23-24 single install step; no requirements-training.txt reference anywhere in workflow |
| github-actions[bot] identity with @users.noreply.github.com email | VERIFIED | L31-32 |
| tests/test_workflow_yaml.py exists with PIPE-04 static-lint assertions | VERIFIED | 4 named tests (not 5 as plan suggested) cover: cron schedule + workflow_dispatch present; module invocation + 3 flags; 3 commit paths; no torch/ultralytics in requirements. See Deviations. |
| Static-lint tests GREEN | VERIFIED | pytest tests/test_workflow_yaml.py → 4 passed |
| Manual workflow_dispatch run observed green with non-empty data.json | NOT YET — human_needed | No docs/projects/patterns/data.json or charts/ artifacts present in repo (only _backtest_aggregates.json). Plan 10-07 Task 4 is `autonomous: false` — intentionally deferred per the orchestrator's instructions. |
| ROADMAP.md Phase 10 row updated to '**Plans**: 7 plans (10-01..10-07)' | VERIFIED | .planning/ROADMAP.md L221 confirmed; grep shows zero remaining 'TBD' for Phase 10 |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `tests/test_run_pipeline_pending.py` | 2 tests targeting D-02 pending wrapper | VERIFIED | Both tests PASSED |
| `tests/test_run_pipeline_window.py` | 1 test targeting D-01 BDay cutoff | VERIFIED | PASSED |
| `tests/test_run_pipeline_atomic.py` | 1 test targeting D-17 atomic write | VERIFIED | PASSED |
| `tests/test_run_pipeline_charts.py` | 3 tests (cleanup + render writes + determinism) | VERIFIED | All 3 PASSED |
| `tests/test_run_pipeline_onnx_fallback.py` | 1 test targeting D-08 ONNX absence | VERIFIED | PASSED — uses canonical 75-row spring fixture, asserts ≥1 detection + yolo_conf=null |
| `tests/test_run_pipeline_main.py` | 3 tests (two thresholds + smoke per BLOCKER #1) | VERIFIED | All 3 PASSED including test_main_smoke_with_synthetic_ohlc |
| `tests/test_run_pipeline_stats.py` | 3 tests (sparse fallbacks + key normalization) | VERIFIED | All 3 PASSED |
| `scripts/pattern_scanner/export_aggregates.py` | project_aggregates + main; stdlib-only | VERIFIED | Imports clean; CLI flags --in/--out/--strategy/--sample present |
| `docs/projects/patterns/_backtest_aggregates.json` | < 50 KB; schema valid; D-04 + D-11 defaults | VERIFIED | 3750 bytes; aggregates.all.n = 1325 |
| `scripts/pattern_scanner/renderer.py` (modified) | + PUBLICATION_STYLE + render_publication_chart, STYLES unchanged | VERIFIED | Constants + function present; STYLES still 3 entries; deterministic rendering proven via SHA-256 test |
| `scripts/pattern_scanner/run_pipeline.py` | Full orchestrator + 4 pure helpers + 2 builders + render wrapper | VERIFIED | 654 lines; all documented symbols present; main() body complete |
| `.github/workflows/nightly-pattern-scanner.yml` | Cron + dispatch + 3-path commit + inference-only install | VERIFIED | All deltas in place |
| `tests/test_workflow_yaml.py` | PIPE-04 static lint | VERIFIED | 4 tests; all PASSED |
| `.planning/ROADMAP.md` | Phase 10 row updated to '7 plans (10-01..10-07)' | VERIFIED | L221 |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| run_pipeline.py | backtest.py (Phase 9) | `from scripts.pattern_scanner.backtest import …` | WIRED | L30-41 imports simulate_trade, _load_onnx_session, _score_detection, _window_for, _stop_for, _target_for, _parse_tickers_arg, _validate_ticker_token, ONNX_PATH, RATE_LIMIT_SLEEP — all re-exportable on run_pipeline_mod for test monkeypatching |
| run_pipeline.py | renderer.py | lazy import in `_render_publication_chart` body | WIRED | L276-279 imports render_publication_chart + PUBLICATION_STYLE; substitution path at L307-319 monkey-replaces module constant for one call |
| run_pipeline.py | scripts.fetch_sp500 | `from scripts.fetch_sp500 import fetch_sp500_tickers` | WIRED | L43; tests monkeypatch this attribute on run_pipeline_mod |
| run_pipeline.py | docs/projects/patterns/_backtest_aggregates.json | `aggregates_path.read_text` in main() | WIRED | L622-625; build_stats_json called only when path exists, graceful warn otherwise |
| run_pipeline.py | docs/projects/screener/data.json | `_load_company_lookup` | WIRED | L177-193 reads + parses + returns lookup dict; graceful empty on absence |
| nightly-pattern-scanner.yml | run_pipeline.py main | `python -m scripts.pattern_scanner.run_pipeline …` | WIRED | L27 of workflow; test_workflow_invokes_run_pipeline_module verifies invocation string + flags |
| nightly-pattern-scanner.yml | docs/projects/patterns/{data.json,stats.json,charts/} | `git add` step | WIRED | L33 of workflow; test_workflow_commits_three_paths asserts all 3 paths |
| nightly-pattern-scanner.yml | requirements.txt | `pip install -r requirements.txt` | WIRED | L24 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| build_data_json output | detections + pipeline_status | Caller (main loop) accumulates rows from real `_resolve_status` + `_score_detection` calls per ticker; real yfinance fetch in `_fetch_ohlc` | YES (in production) | FLOWING — verified by test_main_smoke_with_synthetic_ohlc which exercises main() against monkeypatched _fetch_ohlc and asserts data["detections"] is a list, ps["completed"] is bool, all 7 required keys present |
| build_stats_json output | aggregates input | Read at runtime from _backtest_aggregates.json (committed file with all.n=1325 from real Phase 9 backtest) | YES | FLOWING — live read of committed file produces normalized output keys; live verification: keys include pin_spring, pin_extended, ice_cream_spring/extended, mark_up_spring/extended (all 6 expected combinations) |
| _render_publication_chart output | df slice + detection.bars | df from _fetch_ohlc; detection from detect(); bars from real OHLC | YES (deterministic) | FLOWING — test_render_writes_png produces > 1000-byte PNG with correct magic bytes; determinism test confirms byte-identical reruns |
| docs/projects/patterns/data.json | written by main() | atomic write of build_data_json payload | NOT YET — pending human GHA run | NOT FLOWING in repo — the live artifact has not been produced because Plan 10-07 Task 4 (manual workflow_dispatch) is intentionally deferred. The machinery to produce it is verified end-to-end via the smoke test. |
| docs/projects/patterns/stats.json | written by main() | atomic write of build_stats_json(aggregates) | NOT YET — pending human GHA run | Same as above — machinery proven, runtime artifact awaits checkpoint |
| docs/projects/patterns/charts/*.png | written by _render_publication_chart per detection | renderer.render_publication_chart called once per in-window detection | NOT YET — pending human GHA run | Same as above |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| run_pipeline module imports cleanly with all expected symbols | `python -c "from scripts.pattern_scanner.run_pipeline import build_data_json, build_stats_json, _resolve_status, _window_cutoff, _atomic_write_json, _cleanup_stale_pngs, _render_publication_chart, _load_company_lookup, _resolve_publication_base_style, _render_substitutions, main, _parse_args, _resolve_universe"` | OK | PASS |
| PUBLICATION_STYLE constants correct | `python -c "from scripts.pattern_scanner.renderer import PUBLICATION_STYLE, STYLES; assert PUBLICATION_STYLE.dpi==150 and PUBLICATION_STYLE.facecolor=='#0d1117' and len(STYLES)==3"` | OK | PASS |
| _backtest_aggregates.json schema valid | `python -c "import json; d=json.loads(open('docs/projects/patterns/_backtest_aggregates.json').read()); assert d['strategy']=='1to2_rr_cluster_low_stop' and d['sample']=='out_of_sample' and d['aggregates']['all']['n']==1325"` | OK | PASS |
| build_data_json 95% boundary: 19/1 → True, 18/2 → False | Direct invocation per Step 9 verification | OK | PASS |
| build_stats_json normalizes Phase 9 raw keys | Live invocation against committed _backtest_aggregates.json | 6 fully-normalized keys (3 confirmation_types × 2 spring/extended) | PASS |
| Workflow YAML parses + cron matches + permissions correct | `python -c "import yaml; w=yaml.safe_load(open('.github/workflows/nightly-pattern-scanner.yml'))"; assert w['permissions']['contents']=='write'` | cron='0 7 * * 1-5', workflow_dispatch present, permissions write | PASS |
| Phase 10 dedicated test suite | `python -m pytest tests/test_run_pipeline_*.py tests/test_workflow_yaml.py --no-network -v` | 18 passed, 1 warning | PASS |
| Full repo suite (regression check) | `python -m pytest tests/ --no-network` | 84 passed, 11 skipped, 0 failed in 1278s | PASS — no Phase 7/8/9 regressions |
| PIPE-04 invariant (no torch / ultralytics in requirements.txt) | Direct file read | Only mplfinance, matplotlib, onnxruntime, Pillow added; no torch; no ultralytics | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| PIPE-01 | 10-01, 10-04, 10-06, 10-07 | Nightly GHA workflow fetches OHLC, runs detection, runs ONNX inference, writes results | PARTIAL — human_needed | Offline machinery complete (run_pipeline.py main() + workflow YAML); pending manual workflow_dispatch confirmation per Plan 10-07 Task 4 |
| PIPE-02 | 10-01, 10-04, 10-05, 10-06 | data.json written atomically with pipeline_status field | SATISFIED | _atomic_write_json (L124-139), build_data_json with pipeline_status block (L371-380), atomic-write test GREEN, threshold tests GREEN |
| PIPE-03 | 10-01, 10-03, 10-04, 10-06 | Annotated PNGs written to charts/ + stale cleanup before each run | SATISFIED | render_publication_chart + _cleanup_stale_pngs + main() invocation order (renders, then cleanup); 3 chart tests GREEN |
| PIPE-04 | 10-07 | Workflow runs at 07:00 UTC weekdays using only inference deps (no torch, no ultralytics) | SATISFIED | Workflow cron + install step verified; requirements.txt verified clean; 4 static-lint tests GREEN |

No orphaned requirements: REQUIREMENTS.md L56-59 maps exactly PIPE-01..PIPE-04 to Phase 10; all 4 IDs claimed by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none in Phase 10 deliverables) | — | — | — | — |

Grep for TODO/FIXME/PLACEHOLDER/not yet implemented across run_pipeline.py, renderer.py, export_aggregates.py, the 7 test files, and the workflow YAML returned no matches that indicate stubs in production code paths.

The only `NotImplementedError` reference in plan text is the historical "stub raises NotImplementedError until Plan 10-06" — main() has since been fully implemented (verified by grep: 0 matches in run_pipeline.py source).

### Deviations from Plan

1. **test_workflow_yaml.py has 4 tests instead of 5** — Plan 10-07 Task 2 specified 5 named tests (`test_workflow_cron`, `test_workflow_has_manual_trigger`, `test_requirements_no_torch`, `test_requirements_no_ultralytics`, `test_workflow_installs_only_inference_requirements`). The actual file consolidates equivalent coverage into 4 tests by merging the two-requirements assertions into a single `test_requirements_has_no_training_deps` and folding workflow_dispatch into `test_workflow_cron`. All PIPE-04 invariants are still asserted; coverage is functionally equivalent. The plan acceptance criterion `grep -c "^def test_" == 5` is technically unmet (actual: 4), but every invariant the plan named is covered. Classified as INFO (documentation drift), not a blocker.

2. **build_data_json with 0 succeeded / 0 failed returns completed=False** — Plan 10-05 Task 1 behavior description said "0/0 case must default to True (vacuous: no work, all done)". Actual implementation: `success_rate = 0 / max(0, 1) = 0.0`, which is `< 0.95`, so `completed: False`. No test asserts the empty-universe case (no test calls build_data_json with 0/0), so this does not affect any acceptance criterion or GREEN status. The 95% boundary behavior at 19/1 → True and 18/2 → False is correctly verified. Classified as INFO — minor docstring drift between plan and code; production main() never produces 0/0 in practice (universe is always ≥1 ticker).

3. **build_data_json adds `schema_version: 1` to pipeline_status sub-dict** — code at L372 adds an extra schema_version field to pipeline_status (not just the top-level). This is additive — does not break any test (tests check specific keys, not exclusive keys). Classified as INFO.

### Human Verification Required

#### 1. Manual workflow_dispatch on nightly-pattern-scanner.yml

**Test:** Push the merge branch to GitHub. Navigate to **Actions → Nightly Pattern Scanner Data → Run workflow** (top-right). Select the merge branch and click **Run workflow**.

**Expected:**
- Workflow finishes with a green check (typical wall-clock 5-20 minutes).
- A github-actions[bot] commit appears in the repo history with the message `chore: nightly pattern scanner data update`.
- The bot commit modifies `docs/projects/patterns/data.json` (non-zero, valid JSON with `pipeline_status.completed == true` AND `detections` is a list) and `docs/projects/patterns/stats.json` (non-zero, valid JSON with `schema_version == 1` and `fallback_order` set to `["by_type_x_spring","by_confirmation_type","all"]`).
- At least one PNG present under `docs/projects/patterns/charts/` (acceptable to be empty if no S&P 500 ticker has an in-window detection right now, provided `detections: []` AND `pipeline_status.completed == true`).
- `yolo_conf` is non-null on ≥1 detection (sanity check that ONNX loaded on ubuntu-latest).

**Why human:** PIPE-01 success criterion 1 explicitly requires an end-to-end run on a real GHA runner against real yfinance + real ONNX. Plan 10-07 Task 4 is `autonomous: false` for this exact reason. Cannot be exercised offline. The smoke test (`test_main_smoke_with_synthetic_ohlc`) proves the orchestrator runs end-to-end against a synthetic universe, but the live runner is the load-bearing check for SC-1.

### Gaps Summary

No code gaps. Every must-have truth except PIPE-01 SC-1 is offline-verifiable and verified. The only outstanding item is the human-gated checkpoint — Plan 10-07 Task 4 is intentionally `autonomous: false` and the orchestrator instructions explicitly state to use `status: human_needed` when this is the only remaining item.

Verification stance: the phase has shipped all offline-provable deliverables (7 plans × must_haves × tests), and the live-runner verification is the documented human handoff. Recommend the developer trigger the manual workflow_dispatch on the merge branch, observe a green run + populated artifacts, and then mark Phase 10 complete in ROADMAP.

---

_Verified: 2026-05-12_
_Verifier: Claude (gsd-verifier)_
