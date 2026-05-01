---
phase: 7
slug: detection-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.x |
| **Config file** | `pytest.ini` (Wave 0 creates) |
| **Quick run command** | `python -m pytest tests/test_detector_schema.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~20 seconds offline; ~60 seconds with live yfinance |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_detector_schema.py -q --no-network`
- **After every plan wave:** Run `python -m pytest tests/ -q --no-network`
- **Before `/gsd-verify-work`:** Full suite must be green WITH live yfinance (network on)
- **Max feedback latency:** 30 seconds offline

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-W0 | 01 | 0 | — | — | N/A | infra | `python -m pytest --collect-only` exits 0 | ❌ W0 | ⬜ pending |
| 07-01-01 | 01 | 1 | DET-01 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_pin_bar_classifier -q` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | DET-01 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_mark_up_bar_classifier -q` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | DET-01 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_ice_cream_bar_classifier -q` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | DET-01 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_inside_bar_rule -q` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 2 | DET-03 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_swing_pivots -q` | ❌ W0 | ⬜ pending |
| 07-01-06 | 01 | 2 | DET-03 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_atr14_wilder -q` | ❌ W0 | ⬜ pending |
| 07-01-07 | 01 | 2 | DET-03 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_sma_cluster -q` | ❌ W0 | ⬜ pending |
| 07-01-08 | 01 | 3 | DET-01, DET-02 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_detect_returns_detection_list -q` | ❌ W0 | ⬜ pending |
| 07-01-09 | 01 | 3 | DET-02 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_spring_same_bar -q` | ❌ W0 | ⬜ pending |
| 07-01-10 | 01 | 3 | DET-03 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_no_lookahead_truncation_invariance -q` | ❌ W0 | ⬜ pending |
| 07-01-11 | 01 | 3 | DET-04 | — | N/A | unit | `pytest tests/test_detector_schema.py::test_detection_record_schema -q` | ❌ W0 | ⬜ pending |
| 07-01-12 | 01 | 4 | — | T-07-01 | CLI ticker arg matches `^[A-Z0-9.-]{1,10}$` or exits non-zero | unit | `pytest tests/test_detector_schema.py::test_cli_ticker_validation -q` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 5 | DET-01..DET-04 | — | N/A | integration (network) | `pytest tests/test_detector_known_setups.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `requirements-dev.txt` — `pytest>=8.4,<9`
- [ ] `pytest.ini` — testpaths=tests, markers (network), addopts
- [ ] `tests/__init__.py` — package marker
- [ ] `tests/conftest.py` — `--no-network` flag, network marker autoskip, shared fixtures (synthetic OHLC builders)
- [ ] `tests/fixtures/` — directory for cached parquet/CSV setups (created on first network run)
- [ ] `tests/test_detector_schema.py` — stubs for DET-01..DET-04 (unit-level)
- [ ] `tests/test_detector_known_setups.py` — stubs marked `@pytest.mark.network`
- [ ] `scripts/pattern_scanner/__init__.py` — package marker
- [ ] `scripts/pattern_scanner/detector.py` — module skeleton (Detection dataclass + detect signature)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Curated 5-setup pytest fixture (≥2 confirmation_types, ≥1 spring) is realistic and matches chart context | DET-04, success criterion #4 | Requires human chart-reading judgement to confirm setups are visually correct on TradingView/yfinance plots before encoding | Reviewer opens each setup's chart at `confirmation_date`, confirms bar pattern matches `confirmation_type`, approves before encoding into `tests/test_detector_known_setups.py` parametrize list |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
