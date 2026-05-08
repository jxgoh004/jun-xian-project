---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: — Inside Bar Pattern Scanner
status: in_progress
stopped_at: Phase 9 Plan 03 complete
last_updated: "2026-05-09T02:30:00.000Z"
last_activity: 2026-05-09
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 4
  completed_plans: 3
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-01)

**Core value:** Visitors quickly understand who I am as a developer and interact with my working projects in a professional, accessible, single-page experience.
**Current focus:** Phase 09 — Backtesting Engine (v2.0)

## Current Position

Phase: 09
Plan: 04 (next)
Status: Phase 9 Plan 03 complete (ONNX yolo_conf overlay wired: _load_onnx_session lazy-imports onnxruntime, _window_for slices the right-aligned 60-bar window, _score_detection uses STYLES[0] + verify_onnx.py preprocessing, --no-onnx bypasses session loading entirely; all 8 D-17 tests green; full suite 56 passed). Plan 04 is the empirical full-S&P-500 run + BT-03 N>=10 verification + Phase 9 SUMMARY (autonomous: false).
Last activity: 2026-05-09

```
Milestone v2.0 progress:
Phase 7  [##########] Complete (2026-05-01)
Phase 8  [##########] Complete (2026-05-08)
Phase 9  [########  ] 3/4 plans complete
Phase 10 [          ] Not started
Phase 11 [          ] Not started
```

## Performance Metrics

**Velocity (v1.0 reference):**

- Total plans completed: 12 (v1.0)
- Average duration: multi-session
- Total execution time: 2026-03-18 → 2026-05-01

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | multi-session | — |
| 02 | 1 | multi-session | — |
| 03 | 2 | multi-session | — |
| 04 | 2 | multi-session | — |
| 05 | 2 | multi-session | — |
| 06 | 3 | multi-session | — |
| 07 | 2 | - | - |

**By Phase (v2.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 07 | TBD | — | — |
| 08 | TBD | — | — |
| 09 | TBD | — | — |
| 10 | TBD | — | — |
| 11 | TBD | — | — |

**Recent Trend:**

- Last 5 plans: — (v2.0 not started)
- Trend: —

*Updated after each plan completion*
| Phase 01-static-foundation P01 | 2 | 2 tasks | 4 files |
| Phase 01-static-foundation P02 | 5 days | 2 tasks | 1 files |
| Phase 02-portfolio-shell P01 | multi-session | 2 tasks | 1 files |
| Phase 03-calculator-integration P01 | multi-session | 2 tasks | 1 files |
| Phase 03-calculator-integration P02 | multi-session | 2 tasks | 0 files |
| Phase 04 P04-02 | 2m | 2 tasks | 2 files |
| Phase 04 P04-02 | multi-session | 3 tasks | 2 files |
| Phase 05 P01 | 25 | 2 tasks | 3 files |
| Phase 09 P01 | 22m | 3 tasks | 6 files |
| Phase 09 P02 | 16m | 2 tasks | 4 files |
| Phase 09 P03 | 12m | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- GitHub Pages for hosting — free, static-only, integrates with git workflow
- Keep intrinsic value calculator API on Render — calculator needs Python backend; GitHub Pages is static-only
- Vanilla JavaScript (no framework) — consistency with existing calculator, simplicity for small site
- Single-page navigation — clean UX, fast transitions, no full page reloads
- Cards/grid layout for projects — modern portfolio standard, scales as projects are added
- [Phase 01-static-foundation]: Calculator frontend copied verbatim — API constant already handles localhost vs Render correctly
- [Phase 01-static-foundation]: Extensibility pattern: add new project by creating docs/projects/{name}/ and one card entry in docs/index.html
- [Phase 01-static-foundation]: CORS(app) allow-all on Render is sufficient for current scale — no origin allowlist needed
- [Phase 01-static-foundation]: GitHub Pages enabled via gh CLI serving docs/ from main branch — deployment pipeline confirmed live
- [Phase 02-portfolio-shell]: Single h2 per page: hero name is only h2; Projects label uses h3.section-label to avoid duplicate landmark
- [Phase 02-portfolio-shell]: CSS thumbnail placeholder div instead of broken img tag — swap to img when screenshot available
- [Phase 03-calculator-integration]: On-demand iframe: created on navigate-to, destroyed on return home — avoids loading calculator assets until requested
- [Phase 03-calculator-integration]: Card converted from <a href> to <div data-project> — prevents full-page navigation, enables hash routing
- [Phase 03-calculator-integration]: CORS(app) allow-all on Render confirmed sufficient for GitHub Pages domain — no origin-specific allowlist needed
- [Phase 04]: WebP quality=80 for thumbnail conversion — balances file size reduction with visual fidelity
- [Phase 04]: picture element pattern: WebP source + PNG fallback with loading=lazy and explicit dimensions for CLS prevention
- [Phase 05]: Wikipedia 403 fix: download HTML via requests with Chrome UA before pd.read_html
- [Phase 05]: DCF uses cumulative discount factor (prev_df/(1+r)) matching JS computeIV exactly
- [v2.0 Roadmap]: Training is offline only — ultralytics never in requirements.txt; ONNX is the CI deliverable
- [v2.0 Roadmap]: ONNX model stored in repo at models/inside_bar_v1.onnx (6-12 MB, well under 100 MB limit)
- [v2.0 Roadmap]: Annotated chart PNGs in docs/projects/patterns/charts/ — not base64 in data.json
- [v2.0 Roadmap]: Single GitHub Actions job (sequential), scheduled 07:00 UTC weekdays — 1h after DCF screener at 06:00 UTC
- [v2.0 Roadmap]: data.json schema uses detections array (only tickers with active setups, typically 5-30)
- [v2.0 Roadmap]: Hard train/test split date defined in single shared config — used by data.yaml and backtester
- [Phase 09-01]: simulate_trade encodes D-01..D-05 (entry=open of conf+1, three-bucket outcome, pessimistic intrabar, gap-down handling, R-multiples)
- [Phase 09-01]: aggregate uses str-coerced composite keys ('pin_True') for D-09 four-slice rollup; cells with n<1 omitted
- [Phase 09-01]: Pure-function core (simulate_trade + aggregate) committed without TRAIN_TEST_CUTOFF import — cutoff wiring deferred to Plan 09-02
- [Phase 09-02]: main() orchestrator runs detect() ONCE per ticker with apply_trend_filters=False, partitions via _is_filtered (D-12 superset semantics enforced)
- [Phase 09-02]: Strategy keys committed as module constants (STRATEGY_FILTERED, STRATEGY_UNFILTERED) — schema is forward-compatible with future strategies
- [Phase 09-02]: T-9-01 ticker validation runs before any yfinance call via argparse type=callable; mirrors detector.main() L411-414
- [Phase 09-03]: onnxruntime is imported lazily INSIDE _load_onnx_session — backtest module remains importable without onnxruntime installed (Pitfall 3)
- [Phase 09-03]: ONNX session created ONCE per main() invocation and threaded through _build_record (RESEARCH §Pattern 3 — sessions are thread-safe but construction is expensive)
- [Phase 09-03]: STYLES[0] used at inference time for D-13 deterministic rendering; verify_onnx.py preprocessing reused verbatim ([1,3,640,640] tensor recipe)
- [Phase 09-03]: Three-layer ONNX load fallback (file-missing → ImportError → InferenceSession-construction-failure) plus per-window try/except; corrupt model never aborts the run (T-9-04)
- [Phase 09-03]: --no-onnx forces both yolo_conf=null on every record AND onnx_sha256=null in cache header (intentional bypass advertises itself)

### Open Questions (v2.0)

- Spring (3-bar) vs full (5-bar) pattern: one class label or two? Decide before generating training data.
- Confidence threshold for screener display: sub-threshold detections shown with "unconfirmed" badge or excluded entirely?
- numpy 2.4.4 + onnxruntime compatibility: needs live round-trip test before locking pin.
- How many positive training samples? YOLOv8n needs 1,000-5,000; verify count after dataset generation.

### Roadmap Evolution

- Phase 5 added (v1.0): S&P 500 Stock Screener Page
- Phases 7-11 added (v2.0): Inside Bar Pattern Scanner

### Pending Todos

None yet.

### Blockers/Concerns

None at roadmap stage. See open questions above.

## Session Continuity

Last session: 2026-05-09T02:30:00.000Z
Stopped at: Phase 9 Plan 03 complete
Resume file: .planning/phases/09-backtesting-engine/09-04-PLAN.md
Next action: /gsd-execute-plan 09-04
