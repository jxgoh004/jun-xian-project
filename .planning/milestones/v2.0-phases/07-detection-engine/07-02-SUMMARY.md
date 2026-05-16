---
phase: 07-detection-engine
plan: 02
subsystem: pattern-scanner
tags: [python, detection, pytest, finance, integration, network, yfinance, regression]

# Dependency graph
requires:
  - phase: 07-detection-engine
    provides: scripts/pattern_scanner/detector.py (detect public API), Detection dataclass, tests/conftest.py network marker auto-skip, synthetic_ohlc unit-test layer (07-01-SUMMARY.md)
provides:
  - "tests/test_detector_known_setups.py — live yfinance regression suite over 5 user-approved historical inside-bar-spring setups"
  - "KNOWN_SETUPS fixture (5 entries spanning 3 confirmation_types and 4 spring cases) — locked-in regression contract for any future detector tweak"
  - "Three integration tests: positive (parametrized), adjacent-bar negative regression (parametrized), truncation-invariance (AAPL 10y vs 30-bar truncation)"
  - "Phase 7 success criterion #4 evidence: >=5 known setups confirmed flagged, adjacent bars not flagged"
affects:
  - phase 08-training-data-generation (annotation script will rely on the same KNOWN_SETUPS as ground-truth seeds)
  - phase 09-backtesting (regression contract guards against silent detector drift)
  - phase 10-batch-pipeline (nightly job will inherit @pytest.mark.network gating pattern)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Live yfinance regression suite gated by @pytest.mark.network — auto-skips under --no-network or PYTEST_OFFLINE=1"
    - "User-approved historical fixture provenance: comment-block dating + per-setup chart narrative"
    - "Truncation-invariance test pattern: full vs df.iloc[:cutoff_pos+1] comparison on confirmation_bar_index <= cutoff_pos subset"

key-files:
  created:
    - "tests/test_detector_known_setups.py"
    - ".planning/phases/07-detection-engine/07-02-SUMMARY.md"
  modified: []

key-decisions:
  - "KNOWN_SETUPS encodes the user-approved 5 setups verbatim (D-16 checkpoint, 2026-05-02): NVDA 2020-04-13, MSFT 2023-04-13, JPM 2020-06-15, META 2020-11-30, V 2024-02-13"
  - "Fixture spans 3 confirmation_types (mark_up, pin, ice_cream) and 4 spring cases — both D-16 minima exceeded"
  - "No assertion loosening on yfinance back-revision — failure must be re-curated with the user (T-07-07 accept disposition)"
  - "Adjacent-bar negative regression covers both prior and next trading day per setup (10 negative assertions across 5 entries)"
  - "Truncation-invariance verified at integration scale on AAPL 10y vs 30-bar cutoff — complements unit-level no-look-ahead checks from Plan 01"

patterns-established:
  - "@pytest.mark.network as the single integration-test gate; conftest auto-skip is the only environment-aware mechanism"
  - "yfinance fetch helper inlined in test file mirrors detector._fetch_ohlc — keeps test self-sufficient without hidden dependency on private helpers"
  - "User-review provenance recorded inline (comment with date) so future readers can trace fixture authority"

requirements-completed: [DET-01, DET-02, DET-03, DET-04]

# Metrics
duration: 12min
completed: 2026-05-02
---

# Phase 7 Plan 02: Known-Setup Regression Suite Summary

**Live yfinance regression suite locking the inside-bar-spring detector against 5 user-approved historical S&P 500 setups (NVDA, MSFT, JPM, META, V) spanning 3 confirmation_types and 4 spring cases — Phase 7 success criterion #4 satisfied.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 1 of 1 (Task 1 was a proposal-only checkpoint, approved by user; Task 2 implemented here)
- **Files created:** 1 (tests/test_detector_known_setups.py)
- **Files modified:** 0

## Accomplishments

- Encoded user-approved KNOWN_SETUPS verbatim (D-16 checkpoint, 2026-05-02 approval) — 5 entries, 3 distinct confirmation_types, 4 spring cases.
- Three @pytest.mark.network integration tests:
  - `test_known_setup_is_detected` (parametrized × 5) — DET-01, DET-02, DET-04: asserts a detection lands at the approved confirmation_date with matching `confirmation_type` + `is_spring` + Detection schema shape.
  - `test_no_detection_on_adjacent_bars` (parametrized × 5) — D-15 negative regression: confirms no spurious detection on the trading day immediately before or after each approved date (10 negative assertions total).
  - `test_no_lookahead_truncation_invariance` — DET-03 at integration scale: runs detect on full 10y AAPL history vs `df.iloc[:cutoff_pos+1]` for cutoff = len(df)-30, and verifies the truncated detection set is a subset of full-frame detections (no look-ahead leak under real data).
- All 11 parametrized + truncation cases green with network on; all 11 cleanly SKIPPED with `--no-network`; full suite (12 schema unit tests from Plan 01 + 11 integration tests from Plan 02) green at 23 passed.
- Phase 7 success criterion #4 satisfied: ">=5 known setups confirmed flagged, adjacent bars not flagged."

## Task Commits

Task 1 was a proposal-only checkpoint (no commits — `approve` reply by user).

1. **Task 2: Encode approved setups into live regression suite** — `d46627e` (test)

**Plan metadata commit:** (this SUMMARY)

## Files Created/Modified

- `tests/test_detector_known_setups.py` — live yfinance regression suite. Contains:
  - Module docstring with D-15/D-16 provenance and 2026-05-02 user-approval date.
  - `KNOWN_SETUPS` list (5 user-approved tuples, comment block citing detector dump under `_dev/phase07_proposal/`).
  - `_fetch(ticker)` helper mirroring `detector._fetch_ohlc`.
  - Three `@pytest.mark.network`-decorated test functions described above.

## Approved KNOWN_SETUPS (D-16, 2026-05-02)

| Ticker | Confirmation Date | Type       | Spring | Narrative |
|--------|-------------------|------------|--------|-----------|
| NVDA   | 2020-04-13        | mark_up    | True   | Post-COVID V-recovery; spring break-and-reclaim into 50-SMA cluster |
| MSFT   | 2023-04-13        | mark_up    | False  | Full 5-bar setup; AI rally start; break-below day 3, mark-up day 5 |
| JPM    | 2020-06-15        | mark_up    | True   | Q2 2020 bank recovery; spring break to $81.83, reclaim to $86.42 |
| META   | 2020-11-30        | pin        | True   | Post-election Q4 pin; wick below mother low, body upper third |
| V      | 2024-02-13        | ice_cream  | True   | Late-Q1 2024 pullback-reclaim; long lower wick, close upper two-thirds |

Coverage: 3 confirmation_types (mark_up × 3, pin × 1, ice_cream × 1), 4 spring cases. Both D-16 minima (≥2 types, ≥1 spring) exceeded.

## Decisions Made

- **No assertion loosening policy:** if yfinance back-revises an OHLC value invalidating one of these setups, the test must fail and be re-curated with the user — never weakened. T-07-07 accept disposition documented in PLAN.md threat register.
- **Inlined fetch helper:** `_fetch(ticker)` is a copy of `detector._fetch_ohlc`'s normalisation idiom, kept in the test file rather than imported from `detector` so a refactor of the private helper cannot silently change test fetch behaviour.
- **Adjacent-bar coverage on both sides:** prior and next trading day are both checked per setup, yielding 10 negative assertions across the 5 entries (defends against both early- and late-classification regressions).

## Deviations from Plan

None — plan executed exactly as written. The approved KNOWN_SETUPS list, the three test signatures, the @pytest.mark.network decoration on every test, and the assertion shapes all match `07-02-PLAN.md` Task 2 verbatim.

## Issues Encountered

- The worktree branch was created from commit `35840f5` (pre-Phase-7), so the Plan 01 artifacts (`scripts/pattern_scanner/detector.py`, `tests/conftest.py`, `tests/test_detector_schema.py`, `pytest.ini`, `requirements-dev.txt`) were absent at the start of this task. Resolved by `git merge` of main HEAD `b69b685` into the worktree branch — clean fast-forward, no conflicts. After merge, Plan 01 schema tests confirmed passing (12/12) before Plan 02 work began.

## Verification

- `python -m pytest tests/test_detector_known_setups.py -q` (network on) — **11 passed in 14.74s**.
- `python -m pytest tests/test_detector_known_setups.py -q --no-network` — **11 skipped in 0.84s** (validates Plan 01 conftest auto-skip).
- `python -m pytest tests/ -q` (network on) — **23 passed in 13.81s** (12 schema + 11 integration).

## Phase 7 Success Criterion #4

> "A manually reviewed sample of at least 5 known setups from historical data confirms the detector flags them and does not flag the bars immediately adjacent."

**Satisfied.** 5 user-approved setups detected at the approved confirmation_date with matching `confirmation_type` and `is_spring`; no spurious detection on the prior or next trading day for any of the 5 entries; truncation-invariance verified at integration scale on AAPL 10y. See 07-01-SUMMARY.md for the complementary offline unit-test layer (DET-01..DET-04 schema lock, 12 tests).

## Next Phase Readiness

- Phase 7 detection engine is fully gated: rules locked by Plan 01 unit tests, real-data behaviour locked by Plan 02 integration tests.
- Phase 8 (training-data-generation) can call `detect()` per window and use these 5 known setups as ground-truth seeds for annotation.
- Any future detector edit (or upstream yfinance back-revision) will surface immediately in this regression suite — re-curate with the user per T-07-07 disposition rather than loosening assertions.

---
*Phase: 07-detection-engine*
*Plan: 02*
*Completed: 2026-05-02*

## Self-Check: PASSED

- FOUND: tests/test_detector_known_setups.py
- FOUND commit: d46627e (test 07-02 add live yfinance regression suite)
- VERIFIED: pytest network-on (11 passed), pytest --no-network (11 skipped), full suite (23 passed)
- VERIFIED: KNOWN_SETUPS contains 5 entries, 3 confirmation_types, 4 spring cases (both D-16 minima exceeded)
- VERIFIED: 3 @pytest.mark.network-decorated test functions (`test_known_setup_is_detected`, `test_no_detection_on_adjacent_bars`, `test_no_lookahead_truncation_invariance`)
