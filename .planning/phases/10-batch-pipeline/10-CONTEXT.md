# Phase 10: Batch Pipeline - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A nightly GitHub Actions workflow that runs detection + ONNX inference across the S&P 500 universe and writes the live-screener data the frontend reads. Concretely the phase delivers:

1. **`scripts/pattern_scanner/run_pipeline.py`** — orchestrator (pure-function core + thin CLI wrapper, mirroring `detector.py` / `backtest.py` / `generate_training_data.py`). Iterates the S&P 500, fetches ~90 bars of OHLC per ticker, runs the algorithmic detector with trend filters on, restricts results to detections whose `confirmation_date` is within the last 20 trading days from "today" (the run date), runs Phase 9's `simulate_trade` per detection on live OHLC to populate per-row resolution state, scores each detection with the committed ONNX model (`models/inside_bar_v1.onnx`) for a `yolo_conf` quality overlay, renders an annotated chart PNG per detection using a dedicated publication style, and writes `docs/projects/patterns/data.json` atomically (temp file + `os.replace`) plus annotated PNGs to `docs/projects/patterns/charts/`.
2. **`docs/projects/patterns/stats.json`** — committed nightly alongside `data.json`. Built by the same pipeline by reading a small repo-committed `_backtest_aggregates.json` (extracted once from Phase 9's gitignored `_dev/backtest_cache.json`) and projecting the out-of-sample `by_type_x_spring` slice into a frontend-ready shape, with a fallback to `by_confirmation_type` for sparse cells (n < 10).
3. **A new committed source-of-truth file** `docs/projects/patterns/_backtest_aggregates.json` — a few KB extracted from the Phase 9 cache. Lives in the repo so the GHA runner has it without rebuilding the 27.8 MB cache nightly. Updated only when the backtest is rerun (manual / future phase).
4. **A renderer addition** in `scripts/pattern_scanner/renderer.py`: a new named style key (e.g., `STYLES["publication"]`) used exclusively for the live-screener PNGs. Non-randomized. Same 60-bar right-aligned 640×640 geometry as Phase 8 D-01..D-04 so visitors see the chart in the same framing the model was trained on.
5. **`.github/workflows/nightly-pattern-scanner.yml`** — runs at 07:00 UTC weekdays (1h after the existing DCF screener at 06:00 UTC); `actions/checkout@v4` + `actions/setup-python@v5` (3.11); installs only `requirements.txt` (production deps — `onnxruntime`, `mplfinance`, `matplotlib`, `Pillow`, `pandas`, `yfinance`); runs the pipeline; commits and pushes via `github-actions[bot]` mirroring `nightly-screener.yml`.
6. **Pytest suite** following the Phase 8/9 pattern: synthetic OHLC fixture + monkeypatched `_fetch_ohlc` so tests run in milliseconds without network and without invoking ONNX (graceful fallback per Phase 9 D-14 reused).

**Explicitly out of scope:**
- Frontend rendering of the screener table, drilldown layout, badge color thresholds — Phase 11 (UI-01..UI-05).
- Tier thresholds for `yolo_conf` (green/yellow/red badges) — Phase 11 UI decision once the live distribution is visible.
- Re-running ONNX over the Phase 9 backtest cache to populate `yolo_conf` retroactively — flagged in Phase 9 SUMMARY as a Phase 11 follow-up; not blocking Phase 10.
- Equity curve, P&L, position sizing — locked out by REQUIREMENTS Out of Scope.
- Real-time / intraday bars — daily bars only.
- Live re-training, dataset regeneration in CI — training pipeline (Phase 8) is offline-only by design.

</domain>

<decisions>
## Implementation Decisions

### Scan Window — What Counts as a "Current Detection" (D-01 — D-04)

- **D-01 — Window definition:** A "current detection" is one whose `confirmation_date` is within the last **20 trading days** from the run date (today on the GHA runner). Trading-day arithmetic uses pandas business-day offsets (`pd.tseries.offsets.BDay`), not calendar days — this is consistent with how Phase 7's detector indexes bars. Detections older than 20 trading days are dropped from `data.json`. Window size is locked at 20 but exposed as a CLI flag `--window-days 20` for easy retuning post-launch without a code change.

- **D-02 — Per-row resolution payload:** Each detection in `data.json` carries the **full output of `simulate_trade()`** (Phase 9 contract): `status ∈ {pending, open, target, stop}`, `entry_date`, `entry_price`, `stop_price`, `target_price`, `risk`, `exit_date`, `exit_price`, `exit_reason`, `hold_days`, `R`. `pending` is a new state introduced by Phase 10 — used when the entry bar (`confirmation_bar_index + 1`) hasn't opened yet on the live OHLC slice (i.e., today is the confirmation day or there's no next bar yet). The other four states are exactly what Phase 9 returns. **Implementation note:** `simulate_trade` already returns `{stop, target, open}`; Phase 10 wraps the call with a pre-check — if `entry_idx >= len(df)`, status = `pending`; else delegate. The wrapper lives in `run_pipeline.py`, not in `backtest.py`, so Phase 9's contract stays untouched.

- **D-03 — OHLC fetch depth:** Each ticker fetched at **~90 bars** (60 for the detection window + 20 for resolution coverage of the oldest in-window detection + 10-bar safety buffer). Mirrors `yahoo_finance_fetcher.py` idiom (`auto_adjust=True`, `period="6mo"` is a reasonable conservative call to guarantee ≥90 bars; the actual slicing happens in pure Python after fetch). Lighter than Phase 8's 10y fetch — keeps wall-clock low for the nightly hot path.

- **D-04 — Strategy:** **Filtered only.** Pipeline calls `detect(df, ticker)` with default `apply_trend_filters=True`. Aligned with the Phase 7 methodological claim and the portfolio narrative ("the trend filters are the methodology"). Phase 9's filter ablation showed unfiltered marginally outperforming on the small post-cutoff slice; that's a backtest-narrative point in the SUMMARY, not a public-screener change. The unfiltered superset is **not** rendered to the live frontend.

### ONNX Role in the Pipeline (D-05 — D-08)

- **D-05 — Quality overlay (Phase 9 D-13 pattern):** Algorithmic `detect()` is the source of truth for *what is a detection*. ONNX inference (`models/inside_bar_v1.onnx`, the Phase 8 export) runs **per detection** to produce `yolo_conf ∈ [0.0, 1.0]` as a quality score on each row. The model judges "how textbook does this look" on top of an algorithmic positive. ONNX is **never a gate** — even a low `yolo_conf` row appears on the screener; tier thresholds (green / yellow / red) are a Phase 11 UI decision once the live histogram is visible (D-13 inheritance from Phase 9).

- **D-06 — Inline session, no caching layer:** The pipeline loads the ONNX session **once at process start** (mirrors Phase 9 `_load_onnx_session`), then runs inference per detection inside the orchestration loop. With ~tens to low-hundreds of detections per nightly run (S&P 500 × ~20-day window × filtered), total inference time is small — no per-(ticker, confirmation_date) cache file is needed. The complexity of cache invalidation isn't worth it at this volume.

- **D-07 — Conf format = raw float per row:** Each `data.json` row carries `yolo_conf: float` (raw). **No backend tier bucketing.** Tier badge thresholds are a Phase 11 UI decision — locking them on the backend before seeing the live distribution would be premature. Rationale: the model was trained to mimic the algorithmic detector (Phase 8 D-10 hard-negative strategy), so `yolo_conf` is a chart-textbook-ness score, not a P&L-success score. Storing the float defers the tier call to Phase 11, where the histogram is visible.

- **D-08 — Trust the committed ONNX (no per-run round-trip):** Phase 8 D-19's clean-venv ONNX round-trip (`scripts/pattern_scanner/verify_onnx.py`) is the **commit-time gate** — if the ONNX is in the repo, it has already passed. The nightly hot path does NOT re-run that gate. Pipeline calls inference directly using the same `[1, 3, 640, 640]` preprocessing and output-parsing shape as Phase 9's `_score_detection`. ONNX-absence fallback (D-14 from Phase 9): if `models/inside_bar_v1.onnx` does not exist at runtime, log one warning and set `yolo_conf=null` on every row — pipeline must remain runnable independently of model artifacts.

### Backtest Stats Integration (D-09 — D-12)

- **D-09 — Phase 10 owns the join:** Pipeline produces a separate `docs/projects/patterns/stats.json` alongside `data.json`. Frontend reads two files; Phase 11 stays pure UI. The stats file is small (one nested aggregate object — kilobytes, not megabytes) and is regenerated atomically each night using the same temp + `os.replace` protocol as `data.json`.

- **D-10 — Stats source = committed `_backtest_aggregates.json`:** The full Phase 9 cache `_dev/backtest_cache.json` (~27.8 MB) is gitignored (Phase 9 D-06) and the GHA runner won't have it. **A new committed file** `docs/projects/patterns/_backtest_aggregates.json` carries only the `aggregates` blocks (no per-detection rows) — a few KB — extracted once from the local cache via a one-shot helper. Pipeline reads this file each night and projects from it. The aggregates file is committed alongside the Phase 10 plan; refreshing it is a manual rerun-of-backtest concern (not nightly). **Researcher: design the extraction helper minimally — `python -m scripts.pattern_scanner.export_aggregates --in _dev/backtest_cache.json --out docs/projects/patterns/_backtest_aggregates.json` is one shape; an inline mode of `backtest.py` is another.**

- **D-11 — Cuts shipped = out-of-sample `by_type_x_spring` (with fallback):** `stats.json` exposes the **out-of-sample** block only (the integrity number per Phase 9 D-11). Per-detection lookup goes by `f"{confirmation_type}_{is_spring ? 'spring' : 'extended'}"` (e.g., `pin_spring`, `mark_up_extended`). When a `by_type_x_spring` cell has `n < 10`, fall back to the parent `by_confirmation_type` cell so the drilldown is never empty. If even that has `n < 10`, fall back to `all`. **No `in_sample` block in `stats.json`** — the live screener is forward-looking and the out-of-sample is the integrity story. (The drilldown can mention "based on N out-of-sample detections" so visitors know the denominator.)

- **D-12 — Algorithmic-only stats are acceptable for v1:** Phase 9's run was `--no-onnx` (yolo_conf=null on every backtest record). The `by_type_x_spring` aggregates therefore reflect algorithmic detections only — not stratified by ML confidence. **Acceptable for Phase 10.** Per-row `yolo_conf` is still in `data.json` (D-07) for visual filtering; aggregate stratification by tier is a Phase 11 enrichment (the Phase 9 SUMMARY flagged this as a ~5-min follow-up: re-score the ~1325 filtered out-of-sample detections). Phase 10 does not block on it.

### Charts (D-13 — D-15)

- **D-13 — Bbox source = algorithmic 5-bar cluster (Phase 8 D-02 geometry):** The annotated PNGs use the algorithmic bbox: `x0 = mother bar left edge`, `x1 = confirmation bar right edge`, `y0 = min(low) over the 5 bars`, `y1 = max(high) over the 5 bars`. All four values are derivable from the `Detection.bars` field already exposed by `detector.py`. **Not the YOLO output bbox** — the model bbox is in 640×640 image space and would need decoding back to bar coordinates; the algorithmic bbox is exact and free. (If a Phase 11 follow-up wants to overlay the model bbox dashed alongside, that's an enrichment, not a Phase 10 deliverable.)

- **D-14 — Render style = dedicated publication style:** Add a new style key to `scripts/pattern_scanner/renderer.py` (e.g., `STYLES["publication"]` or a separate constant `PUBLICATION_STYLE`) with consistent dark theme, larger DPI (e.g., 150), clear bbox stroke. **Non-randomized.** Used exclusively for the live-screener PNGs. Does NOT replace `STYLES[0]` (Phase 9 inference) or the randomized training-time styles (Phase 8 D-04). Phase 7 / Phase 8 / Phase 9 callers are unaffected. **Filename convention:** `{TICKER}_{CONFIRMATION_DATE}.png` (e.g., `AAPL_2026-04-22.png`) — same composite key shape as `data.json` row identity (Phase 9 D-08 noted the same key derivation). Same ticker on multiple confirmation dates → multiple PNG files, no collision.

- **D-15 — Stale PNG cleanup = delete-only-stale (not rm -rf):** Before writing new PNGs, the pipeline computes `expected_paths = {f"{t}_{d}.png" for t, d in current_run_detections}`. It then iterates `docs/projects/patterns/charts/` and deletes any file not in `expected_paths`. PNGs that recur night-to-night (same detection still inside the 20-day window) are written byte-identical (deterministic publication style + same OHLC slice) — git sees no change for those, no commit churn. Only churned files are: new detections (added) and aged-out detections (removed). Net commit size per night should stay small.

### Failure Model (D-16 — D-18)

- **D-16 — Partial success + per-ticker errors[]:** Each per-ticker yfinance failure is caught, logged, and appended to an in-memory `errors[]` list (shape: `{ticker, stage, message, timestamp}`). The pipeline does **not** abort. `data.json` carries a `pipeline_status` object: `{completed: bool, errors: [...], succeeded_count: int, failed_count: int, generated_at: ISO8601, run_id: str}`. **`completed = true` if the success rate ≥ 95%** (i.e., `succeeded_count / 503 >= 0.95`); otherwise `false` and the frontend can choose to show a "stale data" banner. Mirrors the existing `nightly-screener.yml` pattern's tolerance for transient yfinance flakiness.

- **D-17 — Atomic write protocol (PIPE-02):** `data.json` and `stats.json` are both written via the temp-file-then-rename pattern: write to `data.json.tmp` (or `stats.json.tmp`) → `fsync` → `os.replace(tmp, final)`. `os.replace` is atomic on the same filesystem (cross-platform, including Windows). **A simulated mid-run kill never leaves a partial JSON visible to the frontend** (success criterion 2). PNG writes don't need atomicity individually (they're written before the data.json that references them; partial state means an orphan PNG referenced nowhere — cleaned up on next run by D-15).

- **D-18 — Workflow-level failure visibility:** The GHA workflow itself only fails (red X) on uncaught exceptions outside the orchestrator (e.g., the ONNX file is corrupt and inference raises). Per-ticker yfinance errors are NOT workflow failures — they're data-level signals carried in `pipeline_status.errors`. Rationale: a single flaky ticker shouldn't take the whole nightly down (yfinance is famously flaky); but a model-level failure should make the page red.

### Module Surface & Conventions (D-19 — D-21)

- **D-19 — New file:** `scripts/pattern_scanner/run_pipeline.py` — pure-function core + thin CLI wrapper. Public API:
  - `_fetch_ohlc(ticker, period="6mo") -> pd.DataFrame` (test seam, monkeypatchable; mirrors `backtest._fetch_ohlc`).
  - `_resolve_status(df, detection) -> dict` (wraps `simulate_trade` with the `pending` pre-check).
  - `_score_detection(session, df, detection) -> float | None` (reuses the inference shape from Phase 9 `backtest._score_detection`; returns `null` if `session is None`).
  - `_render_publication_chart(df, detection, out_path: Path) -> None` (uses the new publication style + algorithmic bbox).
  - `build_data_json(detections: list[dict], errors: list[dict], run_id: str) -> dict` (assembles the final shape).
  - `build_stats_json(aggregates: dict) -> dict` (projects the committed `_backtest_aggregates.json` into frontend-ready cuts per D-11).
  - `main(argv) -> int` (CLI orchestrator).

- **D-20 — CLI shape (suggested; researcher may refine):** `python -m scripts.pattern_scanner.run_pipeline --tickers all --window-days 20 --out-dir docs/projects/patterns`. Same `--limit N` smoke-test arg as `backtest.py` / `generate_training_data.py`. Same `RATE_LIMIT_SLEEP = 0.5` cadence for yfinance. Per-ticker progress logging like `[i/total] TICKER: ...`.

- **D-21 — Test scaffold:** `tests/test_run_pipeline_*.py` (or `tests/test_run_pipeline.py` consolidated — researcher's choice). Required tests:
  - `test_resolve_status_pending` — entry bar not yet present in df.
  - `test_resolve_status_delegates_to_simulate_trade` — sanity check that `_resolve_status` produces the same fields Phase 9 returns.
  - `test_window_filter_drops_old_detections` — 20-day cutoff enforced.
  - `test_atomic_write_protocol` — `os.replace` semantics; simulated mid-write doesn't corrupt the visible file.
  - `test_stale_png_cleanup_keeps_current_drops_old` — D-15 enforcement.
  - `test_yolo_conf_null_when_onnx_missing` — D-08 / Phase 9 D-14 graceful fallback (reuse Phase 9 fixture).
  - `test_partial_failure_completed_true_when_success_rate_above_95pct` — D-16 threshold.
  - `test_partial_failure_completed_false_below_95pct` — D-16 negative case.
  - `test_stats_json_falls_back_to_by_confirmation_type_when_sparse` — D-11 fallback chain.
  - `test_stats_json_falls_back_to_all_when_both_sparse` — D-11 ultimate fallback.
  - `test_publication_render_is_deterministic` — same input → byte-identical PNG (so D-15 cleanup works).
  - All run in milliseconds, no network, no ONNX session.

### Workflow & Schedule (D-22 — D-24)

- **D-22 — Workflow file:** `.github/workflows/nightly-pattern-scanner.yml`. Mirrors `.github/workflows/nightly-screener.yml` line-for-line where possible: `actions/checkout@v4` with `secrets.GITHUB_TOKEN`, `actions/setup-python@v5` (Python 3.11), `pip install -r requirements.txt` (NOT `requirements-training.txt`), invoke the pipeline, `git config` as `github-actions[bot]`, `git add docs/projects/patterns/data.json docs/projects/patterns/stats.json docs/projects/patterns/charts/`, `git diff --staged --quiet || git commit -m "chore: nightly pattern scanner data update" && git push`. Permissions: `contents: write`. Triggers: `schedule` + `workflow_dispatch`.

- **D-23 — Schedule:** `cron: '0 7 * * 1-5'` — 07:00 UTC weekdays. **Exactly 1h after** `nightly-screener.yml` (06:00 UTC weekdays). Both run after US market close (16:00 ET / 21:00 UTC) so daily bars are settled. The 1h offset avoids both jobs hitting yfinance simultaneously and gives the screener a clean commit window before the pattern-scanner adds its commit.

- **D-24 — Bot identity:** Same as `nightly-screener.yml` — `github-actions[bot]` with `users.noreply.github.com` email. Memory note: the user's git-attribution-guard rule (no AI co-author) applies to the developer's commits, not to GitHub-bot commits in CI; bot commits use the standard GitHub Actions bot identity, no Co-Authored-By trailer.

### Claude's Discretion

- Exact yfinance call shape inside `_fetch_ohlc` (`period="6mo"` vs explicit `start/end` from `today - 130d`). Suggest `period="6mo"` for simplicity, matching the existing fetcher idiom; researcher / planner may refine.
- Whether `_resolve_status` returns `simulate_trade(...)` directly or wraps with additional fields (suggest direct passthrough plus the `status` field overriding `exit_reason` when relevant — but the schema is researcher's call; what matters is the eight-field contract from D-02 is in every row).
- Per-ticker parallelization (process pool / async / sequential). Sequential is acceptable if total wall-time stays under 30 min — the pipeline scope is much smaller than Phase 9's full backtest. Suggest sequential first, optimize later only if measured wall-time is excessive.
- ONNX session caching across repeated process invocations (only relevant if the workflow runs the orchestrator multiple times; default is single run, no caching needed).
- Exact bbox stroke color and width in the publication style (suggest a saturated accent color — e.g., yellow-on-dark — and 2-3 px stroke; researcher / planner may consult site-wide design tokens).
- Whether `stats.json` includes a `schema_version` field (suggest yes, so future schema changes are explicit).
- Whether `pipeline_status.errors[]` truncates at some max length (suggest yes — cap at e.g. 50 entries with a `more_truncated: int` field — to avoid a gnarly 500-error data.json bloat scenario).
- The exact one-shot extraction helper for `_backtest_aggregates.json` (D-10) — its shape is researcher's call; what matters is it produces a small file with just the aggregates blocks and runs deterministically against the local Phase 9 cache.

### Folded Todos

None — no pending todos matched Phase 10.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level
- `.planning/PROJECT.md` — Milestone v2.0 vision; v2.0 Out of Scope list (no P&L sim, no equity curve, no signals/targets, no real-time).
- `.planning/REQUIREMENTS.md` §"Batch Pipeline" — PIPE-01..PIPE-04 acceptance criteria.
- `.planning/ROADMAP.md` §"Phase 10: Batch Pipeline" — Goal, dependencies (Phase 8, Phase 9), success criteria 1–4.

### Upstream phase contracts
- `.planning/phases/07-detection-engine/07-CONTEXT.md` — Detection record schema (D-10), `detect(df, ticker, apply_trend_filters=True)` public API, no-look-ahead invariants. Phase 10 calls `detect(df, ticker)` (filters on, default).
- `.planning/phases/08-training-pipeline/08-CONTEXT.md` — D-01..D-04 (60-bar right-aligned 640×640 framing), D-19 (clean-venv ONNX round-trip — Phase 10 trusts this gate; does not re-run), D-20 (`renderer.py` module surface — Phase 10 adds a publication style key).
- `.planning/phases/08-training-pipeline/08-05-SUMMARY.md` — Phase 10 hand-off notes: detector contract, ML confidence threshold = 0.3 (calibration only — Phase 10 doesn't gate on it), inference dep lock (`onnxruntime>=1.19`, `Pillow`, `numpy<2.0`, `mplfinance`, `matplotlib` — NEVER torch/ultralytics in `requirements.txt`).
- `.planning/phases/09-backtesting-engine/09-CONTEXT.md` — D-13 (`yolo_conf` quality-overlay pattern Phase 10 inherits), D-14 (graceful ONNX-absence fallback contract — pipeline reuses verbatim), D-15 (`scripts/pattern_scanner/backtest.py` module structure Phase 10 mirrors).
- `.planning/phases/09-backtesting-engine/09-SUMMARY.md` — Empirical Phase 9 results, methodology notes (R-multiples, dividend-adjusted prices, pessimistic intrabar D-03), and the explicit "score post-cutoff filtered slice with ONNX (~5 min)" follow-up flagged for Phase 11 — Phase 10 does NOT block on it.
- `scripts/pattern_scanner/detector.py` — `Detection` dataclass (`bars`, `mother_bar_index`, `confirmation_bar_index`, `confirmation_date`, `confirmation_type`, `is_spring`) — the source of every field Phase 10 reads.
- `scripts/pattern_scanner/backtest.py` — `simulate_trade()` (Phase 10 wraps with a pending pre-check), `_load_onnx_session` and `_score_detection` (Phase 10 reuses the inference shape).
- `scripts/pattern_scanner/renderer.py` — Add a publication style key here (D-14). Existing `STYLES[0]` (Phase 9) and randomized training styles (Phase 8) stay untouched.
- `scripts/pattern_scanner/verify_onnx.py` — Reference for the ONNX inference shape `[1, 3, 640, 640]`. Phase 10 calls inference inline (not as a subprocess test).
- `scripts/pattern_scanner/split_config.py` — Source of `TRAIN_TEST_CUTOFF`. Phase 10 does NOT use the cutoff (live pipeline is forward-looking, post-cutoff by definition).
- `scripts/fetch_sp500.py` — Source of `fetch_sp500_tickers()`. Phase 10 imports it the same way Phase 8 / Phase 9 do.
- `yahoo_finance_fetcher.py` — yfinance idiom (`auto_adjust=True`, version 0.2.65). `_fetch_ohlc` in `run_pipeline.py` follows the same style.

### Codebase pattern references (for downstream reuse)
- `.github/workflows/nightly-screener.yml` — **Closest workflow analog.** `nightly-pattern-scanner.yml` mirrors it line-for-line. `cron: '0 6 * * 1-5'` → `cron: '0 7 * * 1-5'` (1h offset). Same checkout / setup-python / pip install / commit-and-push pattern. Same `permissions: contents: write`.
- `.github/workflows/monthly-moat-analysis.yml` — Secondary reference for any workflow-level conventions (env vars, secrets handling).
- `tests/conftest.py`, `tests/test_backtest_*.py` — Synthetic OHLC fixtures + monkeypatched `_fetch_ohlc`. Phase 10 test files mirror this; in particular reuse Phase 9's `tests/test_backtest_yolo_conf_fallback.py` shape for the ONNX-absence test (D-08).
- `.planning/codebase/CONVENTIONS.md` — snake_case files/functions, PascalCase classes, leading underscore for private helpers, UPPER_SNAKE_CASE module constants.
- `.planning/codebase/STRUCTURE.md` — `scripts/pattern_scanner/` package; `tests/` at repo root; `.github/workflows/` for CI YAML.
- `requirements.txt` — Already includes `onnxruntime`, `Pillow`, `numpy`, `mplfinance`, `matplotlib`, `pandas`, `yfinance` (per Phase 8 D-20). Phase 10 should add **nothing new** to `requirements.txt`. **Must NOT** add torch or ultralytics. Phase 10 explicitly does NOT install `requirements-training.txt` in the GHA workflow.

### ML / data artifacts (read at runtime; not regenerated by Phase 10)
- `models/inside_bar_v1.onnx` — Inference target. If absent → `yolo_conf: null` + warning (D-08 / Phase 9 D-14).
- `models/dataset_manifest.json` — Reference; not consumed by Phase 10 directly.
- `docs/projects/patterns/_backtest_aggregates.json` — **NEW committed file** (D-10). Carries only the `aggregates` blocks (no per-detection rows) extracted from the local `_dev/backtest_cache.json`. Phase 10 plan must include the one-shot extraction helper.

### Out-of-scope-but-related (do not implement here)
- Frontend screener / drilldown rendering (UI-01..UI-05) — Phase 11.
- Tier thresholds (green / yellow / red) on `yolo_conf` — Phase 11 UI decision.
- ONNX-aware re-score of Phase 9 backtest cache — Phase 9 SUMMARY follow-up; Phase 11 enrichment.
- Cross-link to DCF screener drilldown (UI-04) — Phase 11.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`scripts/pattern_scanner/detector.detect(df, ticker, apply_trend_filters=True)`** — The detection source. Phase 10 calls with default (filters on). Returns a list of `Detection` records with `bars`, `mother_bar_index`, `confirmation_bar_index`, `confirmation_date`, `confirmation_type`, `is_spring` — every field Phase 10 needs.
- **`scripts/pattern_scanner/backtest.simulate_trade(df, detection, stop_price, target_price)`** — Phase 9's resolution function. Phase 10 wraps with a `pending` pre-check (D-02) but does NOT modify `simulate_trade` itself. The four `{stop, target, open}` outcomes flow through unchanged.
- **`scripts/pattern_scanner/backtest._stop_for(detection)` / `_target_for(detection, stop)`** — The 1:2 R:R rule (cluster low stop, 2R target). Phase 10 reuses verbatim — no new strategy.
- **`scripts/pattern_scanner/backtest._load_onnx_session()` and `_score_detection()`** — The Phase 9 inference shape. Phase 10 reuses verbatim or reimports.
- **`scripts/pattern_scanner/renderer.py`** — Renderer module. Phase 10 adds a new named style for publication-quality charts; existing styles untouched.
- **`scripts/fetch_sp500.fetch_sp500_tickers()`** — Universe loader.
- **`tests/conftest.py` `synthetic_ohlc` fixture + `_fetch_ohlc` monkeypatch pattern** — Phase 8/9's deterministic test scaffold. Phase 10 tests mirror this shape.
- **`tests/test_backtest_yolo_conf_fallback.py`** — Direct template for D-08 (ONNX-missing) tests.

### Established Patterns
- **Pure-function core, thin CLI wrapper** — every `scripts/pattern_scanner/*.py` follows this split. `run_pipeline.py` does too.
- **`_fetch_ohlc` mirrors byte-for-byte across modules** — `detector._fetch_ohlc`, `generate_training_data._fetch_ohlc`, `backtest._fetch_ohlc`, and now `run_pipeline._fetch_ohlc` are conceptually identical (different `period`).
- **Per-ticker progress logging** — `[i/total] TICKER: ...` from `generate_training_data.py` and `backtest.py`. Mirror in `run_pipeline.py`.
- **GHA bot commit-and-push pattern** — `nightly-screener.yml` and `monthly-moat-analysis.yml` use the identical block. Phase 10 follows.
- **Atomic-write semantics via `os.replace`** — new pattern for this phase. Tested at the unit level (D-21).
- **Inference deps in `requirements.txt`; training deps in `requirements-training.txt`** — Phase 8 D-20 split. Phase 10 GHA installs only `requirements.txt`.

### Integration Points
- **New file:** `scripts/pattern_scanner/run_pipeline.py`.
- **New file:** `.github/workflows/nightly-pattern-scanner.yml`.
- **New committed data files (initial seeds + nightly updates):**
  - `docs/projects/patterns/data.json` — written nightly.
  - `docs/projects/patterns/stats.json` — written nightly.
  - `docs/projects/patterns/_backtest_aggregates.json` — committed once at Phase 10 plan time (extracted from local Phase 9 cache); rarely refreshed.
  - `docs/projects/patterns/charts/{TICKER}_{DATE}.png` — written nightly.
- **New tests:** `tests/test_run_pipeline*.py` per D-21.
- **Modified file:** `scripts/pattern_scanner/renderer.py` — new publication style key (no breaking change).
- **No requirements changes** — `requirements.txt` already has every dep needed (Phase 8 D-20).
- **Read-only consumers:** Phase 11 frontend reads `data.json` + `stats.json` + the `charts/` dir.

</code_context>

<specifics>
## Specific Ideas

- **The screener's product purpose was reframed during discussion:** not just "what to trade tomorrow" but "show the strategy in motion so visitors can audit accuracy themselves." This is what drove the 20-day window (D-01) and the full `simulate_trade` payload per row (D-02). The portfolio narrative is "here is the rule, here are the recent confirmations, here is how each one played out — judge for yourself." Frontend (Phase 11) should surface that — it's the difference between a generic screener and a transparent demonstration of methodology.
- **Filtered-only on the public screener (D-04) is a deliberate methodology defense.** Phase 9 showed unfiltered marginally outperforming on the small post-cutoff slice; that's a data-honest backtest finding documented in the SUMMARY. The public screener defends the methodology Phase 7 was designed around. The unfiltered numbers stay in the backtest narrative; the live screener doesn't expose them.
- **The publication renderer style (D-14) is a separate concern from training/inference styles.** Visitors see the same 60-bar right-aligned framing the model trains on (D-03 from Phase 8 — distribution-shift mitigation), but with publication-quality polish. Three style purposes coexist in `renderer.py`: training (randomized, Phase 8), inference (deterministic STYLES[0], Phase 9), publication (deterministic, polished, Phase 10). They share the geometric framing, differ in DPI/colors/strokes.
- **Stale-PNG cleanup as set difference (D-15) is the right complexity.** rm -rf would commit ~50 KB × N PNGs every night even when most haven't changed. Set-difference cleanup means git only sees the actual delta — which over a 20-day window in a stable market is small (one or two new detections per day on average). The repo stays small; the commit history stays readable.
- **The 95% completed threshold (D-16) is a researcher knob.** It's a concrete starting point, not a religious number. yfinance flakiness historically affects single-digit ticker counts per run. If empirical data shows a different cliff, revise. The point is to avoid the "all or nothing" trap and the "silently broken" trap simultaneously.
- **The `pending` status (D-02) is genuinely new state.** Phase 9's `simulate_trade` returns `{stop, target, open}` — three buckets that all assume entry happened. Phase 10 introduces a fourth: entry hasn't opened yet because today IS the confirmation day. This is rare on a multi-day window but possible on the boundary; surfacing it correctly distinguishes "this just confirmed and tomorrow's open is the entry" from "this entered and is still in flight."
- **`_backtest_aggregates.json` is committed deliberately, not as a leak (D-10).** Phase 9 D-06 gitignores the full cache because it's 27.8 MB and per-detection rows are reproducible from `(seed, tickers, cutoff, onnx_hash)`. The aggregates file is a few KB — small enough to commit, useful enough that the GHA runner (and Phase 11 frontend, indirectly) needs it. The aggregates are stable: they only change when the backtest is rerun, not nightly.

</specifics>

<deferred>
## Deferred Ideas

- **YOLO output bbox overlay** — D-13 chose algorithmic bbox only. A Phase 11 (or Phase 10.1) enrichment could overlay the model's bbox dashed alongside the algorithmic one to demonstrate visual agreement. Adds bbox-decoding complexity; not worth the lift now.
- **ONNX-aware re-scoring of Phase 9 backtest cache (~5 min)** — explicitly flagged in Phase 9 SUMMARY as a Phase 11 follow-up. Would let `stats.json` carry by-tier stratified aggregates ("win-rate when yolo_conf ≥ 0.7"). Phase 10 ships without it (D-12).
- **Tier thresholds for `yolo_conf` badges** — Phase 11 UI decision once the live histogram is visible (D-07 inheritance from Phase 9 D-13).
- **Per-ticker parallelization in `run_pipeline.py`** — sequential first; only optimize if wall-clock is excessive. Mirrors Phase 9 deferral.
- **Active-trade-window filter view** ("show me only `open` rows") — possible Phase 11 frontend filter. Phase 10's data carries `status` per row; the filter is purely UI.
- **Pre-entry pending view** ("show me only `pending` rows so I know what to set alerts for") — same as above; UI filter on top of D-02's payload.
- **Both filtered + unfiltered shown side-by-side in the public screener** — rejected (D-04). Could be revisited if the frontend wants an "ablation toggle" for narrative purposes.
- **Workflow-level fail on threshold breach** (e.g., red X on success_rate < 95%) — D-18 keeps it data-level. Could be promoted to a workflow-level alert (e.g., job summary annotation) without changing `pipeline_status` semantics.
- **`pipeline_status.errors[]` truncation cap** — researcher's knob (Claude's Discretion). Default unbounded; cap at e.g. 50 if real-world runs produce excessive bloat.
- **Cross-link from pattern drilldown to DCF screener drilldown (UI-04)** — Phase 11's job. Phase 10's `data.json` carries `ticker` per row, which is the only key needed.
- **Re-running ONNX over historical detections in CI** — explicitly not a CI concern. Training and historical re-scoring are offline / occasional. Nightly stays lean.

### Reviewed Todos (not folded)

None — no pending todos were reviewed in this discussion.

</deferred>

---

*Phase: 10-batch-pipeline*
*Context gathered: 2026-05-11*
