---
phase: 10
slug: batch-pipeline
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-11
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `10-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing; reused from Phase 7/8/9) |
| **Config file** | none — `tests/conftest.py` carries shared fixtures and `--no-network` flag |
| **Quick run command** | `python -m pytest tests/test_run_pipeline*.py --no-network -x` |
| **Full suite command** | `python -m pytest tests/ --no-network` |
| **Estimated runtime** | < 5 seconds for run_pipeline tests; ~30 seconds for full suite |
| **Markers** | `network` (defined in conftest.py); run_pipeline tests must NOT use this marker |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_run_pipeline*.py --no-network -x`
- **After every plan wave:** Run `python -m pytest tests/ --no-network`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| PIPE-01 | Nightly workflow runs detect + ONNX + writes data.json | unit + smoke | `python -m pytest tests/test_run_pipeline_main.py::test_main_smoke_with_synthetic_ohlc -x` | ❌ W0 | ⬜ pending |
| PIPE-02 | data.json atomic write | unit | `python -m pytest tests/test_run_pipeline_atomic.py::test_atomic_write_protocol -x` | ❌ W0 | ⬜ pending |
| PIPE-02 | data.json carries pipeline_status with completed boolean | unit | `python -m pytest tests/test_run_pipeline_main.py::test_pipeline_status_completed_true_when_above_95pct -x` | ❌ W0 | ⬜ pending |
| PIPE-02 | pipeline_status detects partial runs (95% threshold) | unit | `python -m pytest tests/test_run_pipeline_main.py::test_pipeline_status_completed_false_when_below_95pct -x` | ❌ W0 | ⬜ pending |
| PIPE-03 | Annotated chart PNGs written | unit | `python -m pytest tests/test_run_pipeline_charts.py::test_render_writes_png -x` | ❌ W0 | ⬜ pending |
| PIPE-03 | Stale PNGs cleaned (D-15 set-difference) | unit | `python -m pytest tests/test_run_pipeline_charts.py::test_stale_png_cleanup_keeps_current_drops_old -x` | ❌ W0 | ⬜ pending |
| PIPE-03 | Publication render is byte-deterministic | unit | `python -m pytest tests/test_run_pipeline_charts.py::test_publication_render_is_deterministic -x` | ❌ W0 | ⬜ pending |
| PIPE-04 | Workflow runs at 07:00 UTC weekdays | static (YAML lint) | `python -c "import yaml; w = yaml.safe_load(open('.github/workflows/nightly-pattern-scanner.yml')); assert w['on']['schedule'][0]['cron'] == '0 7 * * 1-5'"` | ❌ W0 | ⬜ pending |
| PIPE-04 | Only inference deps installed (no torch / ultralytics) | static (grep) | `python -c "deps = open('requirements.txt').read().lower(); assert 'torch' not in deps; assert 'ultralytics' not in deps"` | ❌ W0 | ⬜ pending |
| D-02 | `pending` status when entry bar not yet present | unit | `python -m pytest tests/test_run_pipeline_pending.py::test_resolve_status_pending -x` | ❌ W0 | ⬜ pending |
| D-02 | `_resolve_status` delegates to simulate_trade when entry possible | unit | `python -m pytest tests/test_run_pipeline_pending.py::test_resolve_status_delegates_to_simulate_trade -x` | ❌ W0 | ⬜ pending |
| D-01 | 20-day window cutoff enforced | unit | `python -m pytest tests/test_run_pipeline_window.py::test_window_filter_drops_old_detections -x` | ❌ W0 | ⬜ pending |
| D-08 | yolo_conf=null when ONNX missing | unit | `python -m pytest tests/test_run_pipeline_onnx_fallback.py::test_yolo_conf_null_when_onnx_missing -x` | ❌ W0 | ⬜ pending |
| D-11 | stats.json fallback to by_confirmation_type when n<10 | unit | `python -m pytest tests/test_run_pipeline_stats.py::test_stats_json_falls_back_to_by_confirmation_type_when_sparse -x` | ❌ W0 | ⬜ pending |
| D-11 | stats.json ultimate fallback to `all` when both sparse | unit | `python -m pytest tests/test_run_pipeline_stats.py::test_stats_json_falls_back_to_all_when_both_sparse -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_run_pipeline_pending.py` — D-02 coverage
- [ ] `tests/test_run_pipeline_window.py` — D-01 coverage
- [ ] `tests/test_run_pipeline_atomic.py` — D-17 / PIPE-02 coverage
- [ ] `tests/test_run_pipeline_charts.py` — D-15 / PIPE-03 coverage
- [ ] `tests/test_run_pipeline_onnx_fallback.py` — D-08 coverage (template: `tests/test_backtest_yolo_conf_fallback.py`)
- [ ] `tests/test_run_pipeline_main.py` — D-16 / PIPE-01 / PIPE-02 coverage
- [ ] `tests/test_run_pipeline_stats.py` — D-11 coverage
- [ ] No new `conftest.py` needed — reuse `synthetic_ohlc` fixture and `--no-network` machinery
- [ ] No framework install — pytest already in project

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Workflow runs successfully end-to-end on `workflow_dispatch` | PIPE-01 (success criterion 1) | Real GHA runner + real yfinance + real ONNX cannot be reproduced offline | Push branch, trigger `nightly-pattern-scanner.yml` via Actions UI, confirm green check + `docs/projects/patterns/data.json` updated with non-empty `detections[]` and `pipeline_status.completed == true` |
| Frontend (Phase 11) reads data.json without partial-write races | PIPE-02 | OS-level atomicity guarantee — cannot be unit-tested with single-process pytest | Run workflow under load (manual trigger 3x in 10 minutes); confirm no JSONDecodeError in `docs/projects/patterns/data.json` reads |
| 1h offset from nightly-screener.yml is honored on cron schedule | PIPE-04 | Cron timing is the GHA scheduler's responsibility — only verifiable by observation | After first scheduled run, confirm `nightly-pattern-scanner` ran ~1h after `nightly-screener` in Actions history |

---

## Atomic Write Test Strategy (D-21)

`test_atomic_write_protocol` cannot literally simulate "writer killed mid-write" in pytest. Instead, test the invariant: writer leaves no `.tmp` file behind and the final file is valid JSON. See RESEARCH.md § Atomic Write Test Strategy for full skeleton.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (7 new test files)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter after planner closes coverage

**Approval:** pending

> **Flag flip rationale (audit v2.0, 2026-05-16):** All Phase 10 success criteria verified per 10-VERIFICATION.md; Nyquist sign-off retroactively recorded.
