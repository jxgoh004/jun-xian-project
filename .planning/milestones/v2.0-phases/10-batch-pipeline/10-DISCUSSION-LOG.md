# Phase 10: Batch Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 10-batch-pipeline
**Areas discussed:** Scan window, ONNX role, Backtest stats integration, Charts + failure handling

---

## Scan window ("current detection")

### Q1 — What counts as a "current detection"?

| Option | Description | Selected |
|--------|-------------|----------|
| Confirmed in last N trading days | confirmation_date within last N days. Aligns with discretionary "what just confirmed?" question. | ✓ |
| Active trade window | Entered, not yet exited. Reuses simulate_trade on live data. | |
| Pre-entry pending only | 5-bar cluster confirmed yesterday, entry-bar hasn't opened yet. | |
| All detections in last 60 bars | All; let frontend filter by stage. | |

**User's choice:** Confirmed in last N trading days
**Notes:** User reframed the screener's purpose mid-discussion: "what if I want users to see the most recent confirmation in the last N days so that they can also monitor the accuracy of the strategy?" — turning it from a "what to trade tomorrow" tool into an "audit-the-rule-in-motion" tool. This reframing drove the next two questions.

### Q2 — What value of N (after reframing)?

| Option | Description | Selected |
|--------|-------------|----------|
| 20 trading days (~1 month) | Most detections (~95%) have resolved; mix of fresh + resolved on any given day. | ✓ |
| 10 trading days (~2 weeks) | Tighter; more in-flight. | |
| 60 trading days (~3 months) | Fully retrospective. | |
| Make N a CLI flag, default 20 | Lock 20 with --window-days override. | (folded — D-01 captures the CLI-flag knob) |

**User's choice:** 20 trading days, with the CLI-flag retunability folded into D-01.
**Notes:** Phase 9's median hold was ~3 trading days for filtered out_of_sample, so 20 days bracketed the actionable + resolved window without going stale.

### Q3 — Per-row resolution payload schema?

| Option | Description | Selected |
|--------|-------------|----------|
| Full simulate_trade output | status, entry/stop/target prices, exit info, hold_days, R. | ✓ |
| Status + R only | Minimal; recomputed on drilldown. | |
| Status only, no numbers | Badge only, no R-multiples. | |

**User's choice:** Full simulate_trade output

### Q4 — OHLC fetch depth per ticker?

| Option | Description | Selected |
|--------|-------------|----------|
| ~90 bars | 60 detection + 20 resolution + 10 buffer. | ✓ |
| 1 year | Conservative ample coverage. | |
| 10 years (match Phase 9) | Heaviest, no upside for nightly. | |

**User's choice:** ~90 bars

### Q5 — Filter strategy on the public screener?

| Option | Description | Selected |
|--------|-------------|----------|
| Filtered only | apply_trend_filters=True (Phase 7 default). Defends methodology. | ✓ |
| Both, tagged per row | Filtered + unfiltered, frontend toggle. | |
| Unfiltered only | apply_trend_filters=False. | |

**User's choice:** Filtered only

---

## ONNX role in the pipeline

### Q1 — How does YOLO inference relate to algorithmic detection?

| Option | Description | Selected |
|--------|-------------|----------|
| Quality overlay (Phase 9 D-13) | Algo finds; ONNX scores. yolo_conf attached per row. | ✓ |
| Gate (both must agree) | Both required for row to appear. | |
| Independent + reconciliation | Run both; tag source. | |
| Algorithmic only, no ONNX | Skip ONNX. Conflicts with PIPE-01. | |

**User's choice:** Quality overlay (Phase 9 D-13 pattern)

### Q2 — Inference runtime / caching strategy?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline per detection | Single session loaded once; score per row. No cache. | ✓ |
| Persistent yolo_conf cache | Incremental; only score new detections each night. | |
| Skip ONNX in nightly, run weekly | Decoupled jobs. | |

**User's choice:** Inline per detection

### Q3 — yolo_conf format (raw / tier / both)?

| Option | Description | Selected |
|--------|-------------|----------|
| Raw float per row | yolo_conf: 0–1 float. Tier thresholds deferred to Phase 11. | ✓ |
| Raw float + tier label | Both written backend-side. | |
| Tier label only | Bucketed badge only. | |

**User's choice:** Raw float per row

### Q4 — Pre-flight ONNX gate?

| Option | Description | Selected |
|--------|-------------|----------|
| Trust committed ONNX | verify_onnx.py is the commit-time gate. | ✓ |
| Quick smoke test inline | Single-fixture inference at workflow start. | |
| Full clean-venv check every run | Most paranoid. | |

**User's choice:** Trust committed ONNX

---

## Backtest stats integration

### Q1 — Where does the join from _dev/backtest_cache.json happen?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 10 pipeline produces stats.json | Pipeline owns the join; writes a separate stats.json. | ✓ |
| Pipeline embeds stats inline in data.json | One file, but stats duplicated per row. | |
| Stats stay frontend-side (Phase 11 join) | Phase 11 fetches both files and joins. | |

**User's choice:** Phase 10 pipeline produces stats.json

### Q2 — How does the GHA runner get the (gitignored) backtest cache?

| Option | Description | Selected |
|--------|-------------|----------|
| Commit a slimmed _backtest_aggregates.json | A few KB, just aggregates blocks. | ✓ |
| Workflow regenerates the cache nightly | Always-fresh; +27 min per run. | |
| Commit the full 27.8 MB cache | Repo bloat. | |

**User's choice:** Commit a slimmed stats source file

### Q3 — Which cuts ship in the live stats?

| Option | Description | Selected |
|--------|-------------|----------|
| Out-of-sample, by_type_x_spring | Most specific; fall back to by_confirmation_type when sparse. | ✓ |
| Out-of-sample, by_confirmation_type only | Larger n per cell; loses spring distinction. | |
| Both in_sample and out_of_sample | Two columns; more cognitive load. | |

**User's choice:** Out-of-sample, by_type_x_spring (with fallback chain)

### Q4 — Algorithmic-only stats acceptable, or re-run ONNX-aware backtest first?

| Option | Description | Selected |
|--------|-------------|----------|
| Acceptable — ship as-is | Algorithmic stats are the headline; yolo_conf is per-row. | ✓ |
| Re-run slim ONNX over filtered out-of-sample (~5 min) | Phase 11 enrichment, can do as Phase 10 prereq. | |
| Skip backtest stats entirely | Punts UI-03 to Phase 11. | |

**User's choice:** Acceptable — ship as-is

---

## Charts + failure handling

### Q1 — Bbox source for the annotated PNGs?

| Option | Description | Selected |
|--------|-------------|----------|
| Algorithmic 5-bar cluster bbox | Phase 8 D-02 geometry; known precisely from Detection. | ✓ |
| YOLO bbox from inference output | Decode 640×640 model output back to bar-coords. | |
| Both overlaid | Algo + model boxes per chart. | |
| No bbox | Just the 60-bar chart. | |

**User's choice:** Algorithmic 5-bar cluster bbox

### Q2 — Render style for the public PNGs?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated publication style | New non-randomized style key in renderer.py. | ✓ |
| Reuse STYLES[0] (Phase 9 D-13) | Same as inference rendering. | |
| Randomize per chart | Visually varied but inconsistent. | |

**User's choice:** Dedicated publication style

### Q3 — Failure model on partial yfinance failures?

| Option | Description | Selected |
|--------|-------------|----------|
| Partial success + errors[] | pipeline_status.errors[] populated; completed=true if ≥95% succeed. | ✓ |
| Fail-fast | Any per-ticker error aborts. | |
| Best-effort, no error reporting | Skip silently. | |

**User's choice:** Partial success + errors[]

### Q4 — Stale PNG cleanup strategy?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete only stale | Set difference; recurring PNGs byte-identical, no commit churn. | ✓ |
| rm -rf charts/ before each run | Simplest; nightly commit churn = N PNGs × ~50 KB. | |
| Keep PNGs forever | Conflicts with PIPE-03. | |

**User's choice:** Delete only stale

---

## Claude's Discretion

Captured in CONTEXT.md `<decisions>` "Claude's Discretion" subsection. Highlights:
- Exact yfinance call shape inside `_fetch_ohlc` (period="6mo" suggested).
- Per-ticker parallelization (sequential first, optimize only if measured wall-time excessive).
- Bbox stroke color/width in the publication style.
- `stats.json` schema_version field (suggest yes).
- `pipeline_status.errors[]` truncation cap (suggest cap at ~50 entries).
- Exact one-shot extraction helper for `_backtest_aggregates.json` (D-10).

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` section. Headlines:
- YOLO output bbox overlay (Phase 11 / 10.1 enrichment).
- ONNX-aware re-scoring of Phase 9 backtest cache (Phase 11 follow-up, ~5 min).
- Tier thresholds for yolo_conf badges (Phase 11 UI decision).
- Per-ticker parallelization in `run_pipeline.py`.
- Active-trade-window / pre-entry filter views (Phase 11 UI).
- Filtered + unfiltered side-by-side ablation toggle (Phase 11 narrative enrichment).
- Workflow-level fail on threshold breach (annotation, not data semantic).
- Cross-link to DCF screener drilldown (Phase 11 UI-04).
