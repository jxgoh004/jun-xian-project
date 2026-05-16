# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v2.0 — Inside Bar Pattern Scanner

**Shipped:** 2026-05-16
**Phases:** 5 (07 Detection · 08 Training · 09 Backtesting · 10 Batch Pipeline · 11 Frontend)
**Plans:** 21 (~63 tasks) | **Timeline:** 2026-05-01 → 2026-05-16 (16 days, 140 commits)
**Requirements:** 16/16 satisfied · **Integration links:** 11/11 wired

### What Was Built

- A 5-phase pipeline that takes the portfolio from one live finance tool (DCF screener) to two: algorithmic 5-bar inside-bar-spring detection → algorithmically annotated 2D OHLC chart images → YOLOv8n model exported to `models/inside_bar_v1.onnx` (opset 12) → backtest engine with three-bucket outcome resolution and a single-source-of-truth `TRAIN_TEST_CUTOFF` → nightly GitHub Actions cron at 07:00 UTC weekdays writing `data.json` + `stats.json` + annotated PNG charts atomically.
- Two new portfolio pages: a sortable / filterable screener (`docs/projects/patterns/index.html`, GitHub-blue) and a per-stock drilldown (`docs/projects/patterns/stock.html`, analytical-dark) with annotated PNG hero as LCP candidate, TradingView daily chart, 5-bar anatomy table, status-driven resolution card, 3-up backtest stat cards with a D-13 fallback chain, and an on-demand DCF cross-link.
- Portfolio shell wiring: third project card inserted first on the home grid (D-17), patterns registry entry, og-image (1200×630 letterboxed on `#080c12`), sitemap.xml +2 URLs.
- Live deployment at https://jxgoh004.github.io/jun-xian-project/projects/patterns/ — three consecutive green nightly cron runs through 2026-05-15 with 503/503 tickers succeeding; 44 live detections rendered.

### What Worked

- **Wave-based parallel execution in Phase 11.** Plans 11-01 and 11-02 ran concurrently in separate worktrees with zero conflicts because they touched disjoint files. The wave model paid for itself on the first try.
- **Pure-function core in Phase 9.** `simulate_trade` and `aggregate` are deterministic, dependency-free, and unit-testable without yfinance or onnxruntime. That cleanly separated D-01..D-05 outcome resolution from the orchestrator concerns (rate limiting, ONNX session lifecycle, JSON I/O).
- **Lazy ONNX session creation.** `_load_onnx_session` imports `onnxruntime` *inside* the function body so the backtest module is importable in environments that don't have it (test runs, contributor laptops, CI lint jobs).
- **Cloning verbatim from analog files.** Phase 11 mirrored the DCF screener's HTML/CSS/JS structure, and Phase 10's nightly workflow mirrored `nightly-screener.yml` line-for-line with three documented deltas. This halved design overhead and made review trivially "did the deltas land?".
- **Single-source train/test cutoff.** One literal in `scripts/pattern_scanner/split_config.py`, imported by both `generate_training_data.py` and `backtest.py`. Zero partition violations across 40,022 records.
- **Pitfall doc per phase (`RESEARCH.md`).** In Phase 11 specifically, Pitfall 1 (no `exit_reason` field) and Pitfall 8 (inclusive `>=` tier boundaries) would have been silent bugs without the docs. The lint gate that scans for the forbidden string `exit_reason` caught at least one regression attempt.

### What Was Inefficient

- **Phase 9-04 ONNX backtest projected ~9hr wall-clock vs the 50–180min budget.** Had to fall back to `--no-onnx` for the empirical dev cache (`yolo_conf=null` on every record by design). The plan's `must_haves` explicitly permitted this, but the divergence between planned and actual runtime should have been caught earlier with a per-ticker timing probe.
- **Bash background task got reaped at ~70 min.** The detached PowerShell child (`Start-Process -PassThru`) combined with `python -u` for real-time flushing was the workaround that survived. Worth pinning as a standard for any future >60min child process.
- **Phase 08 lost its `VERIFICATION.md`.** The audit caught it post-hoc; TRAIN-01..04 had to rest on plan-level SUMMARY frontmatter + downstream wiring evidence from Phases 9 and 10. The phase shipped fine, but the governance gap was real.
- **REQUIREMENTS.md traceability table fell behind ROADMAP.** All DET/TRAIN/PIPE rows still showed "Pending" at audit time even though the corresponding phases had been marked complete in ROADMAP for days. Required a reconciliation pass during milestone close.
- **Phase 11 lost its `11-VERIFICATION.md` once during the wave-parallel work** and had to be rebuilt — a worktree merge churned the file. Worth standardising the verifier as the very last step of each plan, not an end-of-phase batch.

### Patterns Established

- **Cross-phase audit before milestone close** — `gsd-audit-milestone` caught both the missing `08-VERIFICATION.md` and the stale REQUIREMENTS table that ROADMAP+SUMMARY signals had silently outgrown. Should become a hard gate at every milestone close.
- **Worktree isolation for non-overlapping plans within a wave** — proven on Phase 11; safe to generalise for any future wave where plans touch disjoint paths.
- **Atomic commit per task; one rollup commit per plan if multiple tiny tasks combine cleanly** — the audit log was readable end-to-end thanks to this discipline; bisects would land cleanly.
- **`exit_reason` lint gate** — a plan-level forbidden-string scan (PowerShell `-match`) wired into VERIFICATION.md proved its worth. Generalise the pattern: every phantom-field prohibition gets a one-line lint test.
- **Lazy import of heavy deps inside the function that uses them** — applied to `onnxruntime` in `_load_onnx_session`; should become the default for any optional CI dependency.
- **Twin-theme portfolio split is now canonical:** tables/index pages = GitHub-blue (`#0d1117`); drilldowns / moat = analytical-dark (`#080c12`). Future pages should pick a side rather than invent a third.

### Key Lessons

1. **Run the verifier RIGHT AFTER `execute-phase`, not as a milestone-close discovery.** Both Phase 8's missing VERIFICATION.md and the stale REQUIREMENTS table would have surfaced same-day if the verifier ran before "phase complete" was logged in STATE.md.
2. **Pitfall docs are not optional polish.** Phase 11's `11-RESEARCH.md` Pitfall 1 (no `exit_reason`) and Pitfall 8 (inclusive `>=` boundaries) directly prevented bugs the implementer would otherwise have written. Every phase deserves one.
3. **Filter ablation result was a surprise that the UI should be honest about.** Unfiltered out-of-sample (n=8841, win_rate=0.353, avg_return_r=+0.061) marginally outperforms filtered (n=1325, win_rate=0.330, avg_return_r=-0.007). The frontend frames filters as "tightens selectivity at small cost" rather than claiming an edge — that honesty is the demonstration of judgement, not a weakness.
4. **Probe wall-clock cost before committing to a full empirical run.** A 5-ticker timing probe in Phase 9-04 would have surfaced the ~9hr ONNX projection in minutes rather than after starting the run.
5. **Single source of truth for shared constants pays off twice.** `TRAIN_TEST_CUTOFF` in `split_config.py` was imported by both training and backtest; the audit verified zero literal duplication via grep. Worth applying the same discipline to threshold constants in Phase 10's pipeline (`CONFIDENCE_FLOOR`, `n_floor`).
6. **The phase RESEARCH.md is where the milestone's value compounds.** Reading Phase 11's Pitfall section before writing a single line of HTML produced a tighter implementation than the analog DCF page.

### Cost Observations

- Model mix: predominantly Opus 4.7 (1M context) on planning, audit, and milestone close; mixed Sonnet for plan execution.
- Sessions: ~30+ over 16 days (multi-session per phase typical).
- Notable: Wave parallel execution on Phase 11 traded extra wall-clock setup for ~40% reduction in end-to-end plan latency.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0      | many     | 6      | Established the planning → research → plan → execute → verify → transition pipeline; first GHA nightly cron (DCF screener) |
| v2.0      | ~30+     | 5      | Cross-phase milestone audit became a milestone-close gate; wave-parallel plan execution proved out; pitfall-doc-per-phase formalised |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|--------------------|
| v1.0      | —     | —        | Vanilla JS, no framework — every page is hand-rolled HTML/CSS/JS |
| v2.0      | ~50+ unit + 11 live integration | Detector + backtest fully covered; renderer + generator 5+8 tests respectively | Frontend pages added **zero** new runtime deps — pure verbatim recombination of existing portfolio CSS/HTML/JS patterns |

### Top Lessons (Verified Across Milestones)

1. **Static-site architecture scales to live data via committed JSON.** Both DCF screener and Pattern Scanner write `data.json` from a nightly GHA cron; the frontend stays free of any backend. This is now the default for any future data-driven project on the portfolio.
2. **Pitfall docs per phase pay for themselves.** Phase 6 (v1.0 marketing revamp) and Phase 11 (v2.0 frontend) both prevented concrete bugs because the implementer read a pitfall list before writing code.
3. **Verbatim cloning from a working analog beats greenfield design.** v1.0 Phase 5 cloned the calculator's frontend layout; v2.0 Phase 11 cloned Phase 5's; v2.0 Phase 10's nightly workflow cloned `nightly-screener.yml`. Every clone shipped faster than the original.
