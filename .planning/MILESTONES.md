# Milestones

## v2.0 Inside Bar Pattern Scanner (Shipped: 2026-05-16)

**Phases completed:** 5 phases, 21 plans, ~63 tasks
**Timeline:** 2026-05-01 → 2026-05-16 (16 days, 140 commits)
**Requirements satisfied:** 16/16 (DET×4, TRAIN×4, BT×3, PIPE×4, UI×5)
**Live deployment:** https://jxgoh004.github.io/jun-xian-project/projects/patterns/

### Key accomplishments

- **Phase 7 — Detection Engine.** Algorithmic 5-bar inside-bar-spring detector with full ruleset, trend filters, and no-look-ahead guarantee. 12 unit tests + 11 live yfinance regression tests over 5 user-approved historical setups all green (DET-01..04).
- **Phase 8 — Training Pipeline.** YOLOv8n trained on algorithmically annotated chart images with style randomisation (DPI/figsize/candle width) and 10:1 negative-sample cap; exported to `models/inside_bar_v1.onnx` (opset 12) and verified via clean-venv round-trip with no torch/ultralytics leak (TRAIN-01..04).
- **Phase 9 — Backtesting Engine.** Pure-function `simulate_trade` + `aggregate` core with three-bucket outcome (stop_first / target_first / open), filter-ablation rollup, shared `TRAIN_TEST_CUTOFF=2024-01-01`. BT-03 PASS: out-of-sample filtered pin=295, mark_up=317, ice_cream=713 — all far above the n≥10 gate (BT-01..03).
- **Phase 10 — Batch Pipeline.** Nightly GitHub Actions cron at 07:00 UTC weekdays running detection → ONNX inference → atomic `data.json` + `stats.json` + annotated PNG charts under `docs/projects/patterns/charts/`; three consecutive green nightly runs through 2026-05-15 with 503/503 tickers succeeding (PIPE-01..04).
- **Phase 11 — Frontend.** GitHub-blue screener at `docs/projects/patterns/index.html` (sortable/filterable table, 5-bar SVG legend, status chips, stale-data banner) + analytical-dark drilldown at `docs/projects/patterns/stock.html` (annotated PNG hero as LCP, TradingView daily chart, 5-bar anatomy, resolution card, 3-up backtest stats, on-demand DCF cross-link) + portfolio home-card wiring with og-image and sitemap (UI-01..05).
- **End-to-end pipeline live for ~30 trading days** at the time of milestone close, demonstrating a second working portfolio tool alongside the DCF screener.

### Archived artefacts

- `.planning/milestones/v2.0-ROADMAP.md` — phase plans, success criteria, traceability
- `.planning/milestones/v2.0-REQUIREMENTS.md` — requirements with phase mappings
- `.planning/milestones/v2.0-MILESTONE-AUDIT.md` — pre-close audit report (status: passed post-remediation)
- `.planning/milestones/v2.0-phases/` — five phase directories (07-detection-engine, 08-training-pipeline, 09-backtesting-engine, 10-batch-pipeline, 11-frontend) with all PLAN.md / SUMMARY.md / RESEARCH.md / VERIFICATION.md / PATTERNS.md / VALIDATION.md / CONTEXT.md per phase

---
