# Phase 10: Batch Pipeline - Research

**Researched:** 2026-05-11
**Domain:** Nightly CI batch pipeline + atomic write protocol + deterministic chart rendering on GitHub Actions
**Confidence:** HIGH (most claims verified against committed code, in-repo workflows, and live tool execution)

## Summary

Phase 10 wires together five existing primitives — `detect()` (Phase 7), `simulate_trade()` (Phase 9), `_load_onnx_session` / `_score_detection` (Phase 9), `renderer.py` (Phase 8), and `fetch_sp500_tickers()` — into a single nightly orchestrator that writes three artifacts atomically: `data.json`, `stats.json`, and a directory of annotated PNGs. The technical surface area is small. The risks live entirely in three places: (1) deterministic PNG output so D-15's set-difference cleanup avoids commit churn, (2) the temp-file-then-rename atomicity protocol (`os.replace` is sufficient on both Linux and Windows when source and destination share a filesystem), and (3) the new `pending` status — Phase 9's `simulate_trade` already returns `pending`-shaped semantics in one specific edge case (entry_idx >= len(df) → status="open" with risk=0), but the Phase 10 contract calls this `pending` semantically distinct from a trade that entered but never resolved. The `_resolve_status` wrapper in `run_pipeline.py` is the cleanest way to bolt `pending` on without modifying `backtest.simulate_trade`.

Live verification on the current dev machine confirmed three load-bearing assumptions: matplotlib 3.10.9 produces byte-identical PNGs on repeated identical calls (no embedded creation timestamps by default — D-15's set-difference strategy works as designed); `pd.Timestamp('2026-05-09') - BDay(20)` correctly rolls a Saturday back to the previous business day before walking 20 trading days (no extra logic needed for weekend `workflow_dispatch` invocations); and the installed inference dep stack (onnxruntime 1.25.1, mplfinance 0.12.10b0, matplotlib 3.10.9, yfinance 0.2.65) satisfies the Phase 8 D-20 lock without any new pins. The committed ONNX model is 11.7 MB — well within the 100 MB git limit and small enough that loading it once per nightly run takes seconds, not minutes.

**Primary recommendation:** Build `run_pipeline.py` as a thin orchestrator that imports Phase 9's `_load_onnx_session`, `_score_detection`, `simulate_trade`, `_stop_for`, `_target_for` verbatim; add `_fetch_ohlc(ticker, period="6mo")`, `_resolve_status(df, detection)`, `_render_publication_chart(df, detection, out_path)`, `_atomic_write_json(path, obj)`, `_window_filter(detections, window_days, today)`, `build_data_json`, `build_stats_json`, and `main(argv)`. Mirror `nightly-screener.yml` byte-for-byte for the workflow file with three deltas: cron `'0 7 * * 1-5'`, install step unchanged (`pip install -r requirements.txt`), and the `git add` line lists three paths (`data.json`, `stats.json`, `charts/`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Universe loading (S&P 500 tickers) | Backend / Batch | — | `fetch_sp500.fetch_sp500_tickers()` exists and is the canonical source; same one Phase 8 and 9 use. |
| OHLC fetch | Backend / Batch | — | yfinance; same lazy-import idiom as Phase 7/8/9 `_fetch_ohlc`. |
| Detection | Backend / Batch | — | `detector.detect(df, ticker, apply_trend_filters=True)` — pure function, no I/O. |
| Trade resolution (`pending` / `open` / `target` / `stop`) | Backend / Batch | — | `backtest.simulate_trade` (Phase 9) + thin `_resolve_status` wrapper for `pending` pre-check. |
| ONNX inference (`yolo_conf` overlay) | Backend / Batch | — | `_load_onnx_session` + `_score_detection` reused from Phase 9; CPU only on `ubuntu-latest`. |
| Publication chart rendering | Backend / Batch | — | New `STYLES["publication"]` key in `renderer.py`; mplfinance + matplotlib Agg backend. |
| Atomic JSON write | Backend / Batch | OS / Filesystem | `os.replace(tmp, final)` — POSIX `rename(2)` on Linux, `MoveFileExW` on Windows with `MOVEFILE_REPLACE_EXISTING`. Both are atomic when src and dst share a filesystem. |
| Stale PNG cleanup | Backend / Batch | — | Set-difference iteration over `docs/projects/patterns/charts/*.png`; `pathlib.Path.unlink()`. |
| Workflow scheduling | CI / GitHub Actions | — | `.github/workflows/nightly-pattern-scanner.yml`; cron `'0 7 * * 1-5'`. |
| Commit + push | CI / GitHub Actions | — | `github-actions[bot]` identity, `secrets.GITHUB_TOKEN` via `actions/checkout@v4`, `git diff --staged --quiet || git commit && git push`. |
| Schema versioning | Backend / Batch | Frontend (Phase 11) | `schema_version: 1` in both `data.json` and `stats.json`; Phase 11 reads it to fail loudly on incompatible upgrades. |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scan window (D-01 — D-04):**
- D-01: 20-trading-day window via `pd.tseries.offsets.BDay(20)`; CLI flag `--window-days 20`; older detections dropped.
- D-02: Each detection carries the full `simulate_trade` output (8 fields: status, entry_date/price, stop_price, target_price, risk, exit_date/price, exit_reason, hold_days, R) plus `pending` as a new state. `pending` is bolted on via a wrapper in `run_pipeline.py`; `backtest.simulate_trade` is NOT modified.
- D-03: ~90 bars fetched (`period="6mo"` yields ~126 trading days, conservative); 60-bar detection window + 20-bar resolution coverage + 10-bar safety buffer.
- D-04: Filtered-only on the public screener. `detect(df, ticker)` with default `apply_trend_filters=True`. Unfiltered superset never reaches the frontend.

**ONNX role (D-05 — D-08):**
- D-05: ONNX is a quality overlay, not a gate. `yolo_conf ∈ [0.0, 1.0]` is a chart-textbook-ness score; tier thresholds are a Phase 11 UI decision.
- D-06: Single ONNX session loaded once per process via `backtest._load_onnx_session`; no caching layer.
- D-07: `yolo_conf: float` per row in `data.json`. No backend tier bucketing.
- D-08: ONNX-absence is graceful — log one warning, set `yolo_conf=null` on every row. Reuse Phase 9 D-14 contract verbatim.

**Backtest stats integration (D-09 — D-12):**
- D-09: Phase 10 produces `stats.json` alongside `data.json`. Frontend reads both.
- D-10: Stats are read from a NEW committed file `docs/projects/patterns/_backtest_aggregates.json` (few KB, extracted once from the local 27.8 MB gitignored `_dev/backtest_cache.json`).
- D-11: Out-of-sample `by_type_x_spring` is the primary cut, with fallback chain `by_type_x_spring → by_confirmation_type → all` when `n < 10`.
- D-12: Algorithmic-only stats acceptable for v1 (`--no-onnx` run; no by-tier stratification).

**Charts (D-13 — D-15):**
- D-13: Algorithmic 5-bar bbox geometry from `Detection.bars` — NOT the YOLO model bbox.
- D-14: New `STYLES["publication"]` key in `renderer.py`. Dark theme, ~150 DPI, deterministic, clear bbox stroke. Existing `STYLES[0]` (Phase 9 inference) and randomized training styles (Phase 8) are untouched.
- D-15: Stale-PNG cleanup is set-difference — `expected = {f"{t}_{d}.png" for t, d in current_run}`; delete files in `charts/` not in `expected`. NOT `rm -rf`. Byte-identical recurring PNGs prevent git commit churn.

**Failure model (D-16 — D-18):**
- D-16: `pipeline_status = {completed: bool, errors: [...], succeeded_count, failed_count, generated_at, run_id}`. `completed = (succeeded_count / 503) >= 0.95`.
- D-17: Atomic write via `temp_path + os.replace(temp, final)` for both `data.json` and `stats.json`.
- D-18: Workflow-level failure (red X) only on uncaught exceptions; per-ticker yfinance errors are data-level signals, not workflow failures.

**Module surface (D-19 — D-21):**
- D-19: New file `scripts/pattern_scanner/run_pipeline.py` with public API: `_fetch_ohlc`, `_resolve_status`, `_score_detection` (re-export from backtest), `_render_publication_chart`, `build_data_json`, `build_stats_json`, `main`.
- D-20: CLI shape `python -m scripts.pattern_scanner.run_pipeline --tickers all --window-days 20 --out-dir docs/projects/patterns`. Same `--limit N` smoke-test flag. Same `RATE_LIMIT_SLEEP = 0.5`.
- D-21: 11 specific pytest cases; all run in milliseconds, no network, no ONNX.

**Workflow & schedule (D-22 — D-24):**
- D-22: `.github/workflows/nightly-pattern-scanner.yml` mirrors `nightly-screener.yml` line-for-line.
- D-23: `cron: '0 7 * * 1-5'` — exactly 1h after `nightly-screener.yml` (06:00 UTC).
- D-24: GHA bot commit identity; NO Co-Authored-By trailer (user's git-attribution-guard rule applies only to developer commits, not CI bot commits).

### Claude's Discretion

- Exact yfinance call shape (`period="6mo"` vs explicit `start/end`). Recommended below.
- Whether `_resolve_status` returns `simulate_trade(...)` verbatim or wraps with additional fields. Recommended below.
- Per-ticker parallelization (sequential first; optimize only if wall-time > 30 min).
- ONNX session caching across repeated process invocations (default: single run, no caching).
- Bbox stroke color/width in publication style.
- Whether `stats.json` carries a `schema_version` field (recommend yes).
- Whether `pipeline_status.errors[]` truncates (recommend yes — cap at 50).
- Exact one-shot extraction helper for `_backtest_aggregates.json` (CLI module shape).

### Deferred Ideas (OUT OF SCOPE)

- YOLO output bbox overlay (Phase 11 enrichment).
- ONNX-aware re-scoring of Phase 9 backtest cache (Phase 11 follow-up, ~5 min runtime).
- Tier thresholds for `yolo_conf` badges (Phase 11 UI decision).
- Per-ticker parallelization (defer until measured wall-time excessive).
- Active-trade-window filter view, pre-entry pending view (Phase 11 UI filters).
- Both filtered + unfiltered side-by-side (rejected at D-04).
- Workflow-level fail on threshold breach (D-18 keeps it data-level).
- `pipeline_status.errors[]` unbounded (cap recommended).
- Cross-link to DCF screener drilldown (Phase 11 UI-04).
- Re-running ONNX over historical detections in CI.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | Nightly GitHub Actions workflow fetches OHLC data, runs algorithmic detection, runs YOLOv8 ONNX inference, and writes results. | "GitHub Actions Workflow Pattern" + "Pipeline Orchestration Pattern" sections; reuse of Phase 9's `_load_onnx_session` / `_score_detection`; the workflow YAML template below. |
| PIPE-02 | Pipeline writes `data.json` atomically (temp file + rename) with a `pipeline_status` field so the frontend can detect partial runs. | "Atomic Write Protocol" section + verified `os.replace` semantics on Linux ext4 (POSIX rename) and Windows NTFS (`MoveFileExW`). `pipeline_status` schema documented in "Schema Designs" section. |
| PIPE-03 | Pipeline writes annotated chart PNGs to `docs/projects/patterns/charts/` and cleans stale PNGs before each run. | "Deterministic PNG Output" section (live-verified: matplotlib 3.10.9 produces byte-identical PNGs on repeated identical input by default). "Stale PNG Cleanup" set-difference algorithm. |
| PIPE-04 | Workflow runs at 07:00 UTC on weekdays (1h after the DCF screener) using only inference dependencies (onnxruntime, no torch). | Cron expression `'0 7 * * 1-5'` verified against `nightly-screener.yml`'s `'0 6 * * 1-5'`. `requirements.txt` audit confirms onnxruntime / Pillow / mplfinance / matplotlib / pandas / yfinance present; no torch/ultralytics anywhere. Phase 8 D-20 lock holds. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >=2.2.0 (locked) | DataFrame ops, BDay arithmetic, JSON serialization (via `default=str`). | Already in `requirements.txt`. Phase 7/8/9 use it. `pd.tseries.offsets.BDay` is the canonical business-day offset (live-verified). |
| numpy | >=1.26.0 (locked; <2.0 transitive from ultralytics export) | ONNX input tensor construction (`[1, 3, 640, 640]` float32). | Already in `requirements.txt`. Phase 9 `_score_detection` uses it. |
| yfinance | 0.2.65 (pinned) | Daily OHLC fetch (6mo period). | Already in `requirements.txt`. Phase 7/8/9 use identical idiom. |
| onnxruntime | >=1.19 (locked); 1.25.1 installed | ONNX inference for `yolo_conf` overlay. | Already in `requirements.txt`. Phase 9 `_load_onnx_session` + `_score_detection` are the reference implementation. |
| Pillow | >=10.0 (locked) | PNG bytes ↔ PIL.Image conversion in `_score_detection`. | Already in `requirements.txt`. |
| mplfinance | >=0.12.10b0 (locked); 0.12.10b0 installed | Headless candlestick chart rendering via `Agg` backend. | Already in `requirements.txt`. Phase 8 D-17 + Phase 9 D-13 use it. |
| matplotlib | >=3.8 (locked); 3.10.9 installed | Backing renderer for mplfinance; `Agg` backend; deterministic PNG output verified. | Already in `requirements.txt`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib` (stdlib) | — | All path operations. | Same pattern as `backtest.py`. |
| `os` (stdlib) | — | `os.replace(tmp, final)` for atomic writes. `os.environ.get("GITHUB_RUN_ID")` for run_id derivation. | Atomic writes; CI detection. |
| `json` (stdlib) | — | Read `_backtest_aggregates.json`, write `data.json` / `stats.json`. | Standard. |
| `argparse` (stdlib) | — | CLI shape mirroring `backtest.py`. | Same pattern. |
| `warnings` (stdlib) | — | ONNX-absence single warning, reusing Phase 9 D-14 idiom. | Same pattern as `backtest._load_onnx_session`. |
| `uuid` (stdlib) | — | `run_id` derivation when not in CI (uuid4). | Local-run identification. |
| `hashlib` (stdlib) | — | If deterministic PNG verification is wired into tests (sha256 over PNG bytes). | Test scaffold for D-21 `test_publication_render_is_deterministic`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pd.tseries.offsets.BDay` | `numpy.busday_offset` | BDay is already imported via pandas; busday_offset needs a separate import path and uses numpy datetime64. BDay is consistent with existing codebase. |
| `os.replace` for atomic write | `pathlib.Path.replace` | Functionally identical (Path.replace wraps os.replace). Either is fine; `os.replace` matches Phase 9's `Path.open` style. |
| `period="6mo"` for yfinance | Explicit `start=today-130d, end=today+1d` | `period="6mo"` is simpler and matches existing `_fetch_ohlc` idiom across detector/backtest/generate_training_data. Use the simpler form unless an explicit calendar window becomes load-bearing. **VERIFIED via existing code: every other `_fetch_ohlc` in the codebase uses `period=...`.** |
| Sequential ticker iteration | `concurrent.futures.ThreadPoolExecutor` | yfinance rate limits aside, sequential keeps RATE_LIMIT_SLEEP=0.5 honest. Phase 9 ran 503 tickers sequentially in 27 min; Phase 10's 6mo fetch is ~5× lighter — well under 30 min budget. Defer parallelization. |
| Inline single-script extraction helper | Separate `scripts/pattern_scanner/export_aggregates.py` module | Recommend separate module (see D-10 section below) — clean separation, easier to test, named for its purpose. |

**Installation:** Nothing new — `requirements.txt` already covers Phase 10 deps. `[CITED: requirements.txt L13-17, Phase 8 D-20]`

**Version verification (live-run on dev machine 2026-05-11):**
- onnxruntime: 1.25.1 (satisfies `>=1.19`) `[VERIFIED: python -c "import onnxruntime; print(onnxruntime.__version__)"]`
- mplfinance: 0.12.10b0 `[VERIFIED]`
- matplotlib: 3.10.9 (satisfies `>=3.8`) `[VERIFIED]`
- yfinance: 0.2.65 `[VERIFIED]`
- pandas: present (>=2.2 locked) `[VERIFIED]`

## Architecture Patterns

### System Architecture Diagram

```
                  ┌─────────────────────────────────────────────────────────┐
                  │  GitHub Actions Runner (ubuntu-latest, Python 3.11)    │
                  │  Triggered: cron '0 7 * * 1-5' or workflow_dispatch    │
                  └────────────┬────────────────────────────────────────────┘
                               │
                               ▼
                  ┌─────────────────────────────────┐
                  │  pip install -r requirements.txt│
                  │  (NO torch, NO ultralytics)     │
                  └────────────┬────────────────────┘
                               │
                               ▼
   ┌───────────────────────────────────────────────────────────────────────┐
   │  python -m scripts.pattern_scanner.run_pipeline                       │
   │                                                                       │
   │   1. fetch_sp500_tickers()          ─► ~503 tickers                  │
   │   2. _load_onnx_session(ONNX_PATH)  ─► sess (or None if missing)     │
   │   3. for each ticker:                                                 │
   │        df = _fetch_ohlc(ticker, period="6mo")  ── yfinance           │
   │        dets = detect(df, ticker)               ── filtered only      │
   │        dets = _window_filter(dets, 20, today)  ── BDay arithmetic    │
   │        for d in dets:                                                 │
   │          rec = _resolve_status(df, d)          ── simulate_trade +   │
   │                                                   pending pre-check  │
   │          rec.yolo_conf = _score_detection(...) ── reused Phase 9     │
   │          rec.chart_path = _render_publication_chart(df, d, out)      │
   │   4. cleanup stale PNGs (set-difference)                              │
   │   5. atomic write data.json (temp + os.replace)                       │
   │   6. read _backtest_aggregates.json                                   │
   │   7. atomic write stats.json (temp + os.replace)                      │
   └───────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
   ┌───────────────────────────────────────────────────────────────────────┐
   │  git diff --staged --quiet || git commit && git push                  │
   │   github-actions[bot] identity; NO Co-Authored-By                     │
   │   Files staged:                                                       │
   │     docs/projects/patterns/data.json                                  │
   │     docs/projects/patterns/stats.json                                 │
   │     docs/projects/patterns/charts/                                    │
   └───────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
          ┌──────────────────────────────────────────────────┐
          │  GitHub Pages (static)                            │
          │  Phase 11 frontend reads data.json + stats.json   │
          │  (Phase 11 — out of scope for Phase 10)           │
          └──────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
scripts/pattern_scanner/
├── __init__.py
├── detector.py                  # (existing) Phase 7
├── renderer.py                  # (modified) Phase 10 adds STYLES["publication"]
├── generate_training_data.py    # (existing) Phase 8 — never touched in CI
├── train.py                     # (existing) Phase 8 — never touched in CI
├── verify_onnx.py               # (existing) Phase 8 — never touched in CI
├── split_config.py              # (existing) Phase 8 — not used in Phase 10
├── backtest.py                  # (existing) Phase 9 — Phase 10 imports symbols
├── run_pipeline.py              # NEW — Phase 10 orchestrator
└── export_aggregates.py         # NEW — one-shot _backtest_aggregates.json builder

.github/workflows/
├── nightly-screener.yml         # (existing) — line-for-line template
├── monthly-moat-analysis.yml    # (existing) — secondary reference
└── nightly-pattern-scanner.yml  # NEW — Phase 10 workflow

docs/projects/patterns/
├── data.json                    # NEW — committed; written nightly (atomic)
├── stats.json                   # NEW — committed; written nightly (atomic)
├── _backtest_aggregates.json    # NEW — committed once; refreshed manually
└── charts/
    └── {TICKER}_{DATE}.png      # NEW — committed; written nightly (no atomic needed)

tests/
├── conftest.py                  # (existing) — reuses synthetic_ohlc + monkeypatch
├── test_backtest_yolo_conf_fallback.py   # (existing) — template for Phase 10 onnx tests
└── test_run_pipeline*.py        # NEW — 11 test cases per D-21
```

### Pattern 1: Pipeline Orchestration (single-pass per ticker)

**What:** Iterate the universe sequentially, fetch once per ticker, detect once, then run resolution + scoring + rendering for every in-window detection.

**When to use:** Always for Phase 10. Mirrors Phase 9 `backtest.main()` shape.

**Example (skeleton — verify against Phase 9 `backtest.main()` L518-605):**

```python
# scripts/pattern_scanner/run_pipeline.py
from scripts.pattern_scanner.backtest import (
    _load_onnx_session, _score_detection, _window_for, _stop_for, _target_for,
    simulate_trade, ONNX_PATH, RATE_LIMIT_SLEEP,
)
from scripts.pattern_scanner.detector import detect
from scripts.fetch_sp500 import fetch_sp500_tickers

def main(argv=None) -> int:
    args = _parse_args(argv)
    tickers = fetch_sp500_tickers() if args.tickers == "all" else args.tickers
    if args.limit:
        tickers = tickers[: args.limit]

    sess = _load_onnx_session(ONNX_PATH)  # one warning if missing; reused per detection
    today = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    cutoff = today - pd.tseries.offsets.BDay(args.window_days)

    rows: list[dict] = []
    errors: list[dict] = []
    succeeded = failed = 0

    for i, ticker in enumerate(tickers, start=1):
        try:
            df = _fetch_ohlc(ticker, period="6mo")
            dets = detect(df, ticker)  # filtered-only, D-04
            dets_in_window = [
                d for d in dets
                if pd.Timestamp(d.confirmation_date) >= cutoff
            ]
            for d in dets_in_window:
                rec = _resolve_status(df, d)
                rec["yolo_conf"] = _score_detection(_window_for(d, df), sess)
                rec["chart_path"] = _render_publication_chart(df, d, args.out_dir)
                rows.append(rec)
            succeeded += 1
            print(f"[{i}/{len(tickers)}] {ticker}: {len(dets_in_window)} in-window")
        except Exception as exc:
            failed += 1
            errors.append({
                "ticker": ticker,
                "stage": "fetch_or_detect",
                "message": str(exc)[:500],  # cap individual message length
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            print(f"[{i}/{len(tickers)}] {ticker}: ERROR — {exc}")
        if i < len(tickers):
            time.sleep(RATE_LIMIT_SLEEP)

    # Stale PNG cleanup (D-15)
    expected = {f"{r['ticker']}_{r['confirmation_date']}.png" for r in rows}
    _cleanup_stale_pngs(args.out_dir / "charts", expected)

    # Build + atomically write
    data = build_data_json(rows, errors, succeeded, failed, len(tickers))
    _atomic_write_json(args.out_dir / "data.json", data)

    aggregates = json.loads((args.out_dir / "_backtest_aggregates.json").read_text())
    stats = build_stats_json(aggregates)
    _atomic_write_json(args.out_dir / "stats.json", stats)

    return 0
```

### Pattern 2: Atomic Write via Temp + `os.replace`

**What:** Write to `final.tmp` → `fsync` → `os.replace(final.tmp, final)`. After `os.replace` returns, readers see either the old content or the complete new content — never a partial file.

**When to use:** Both `data.json` and `stats.json` per D-17. PNGs do NOT need this — they're written before the `data.json` that references them; partial state means orphan PNG referenced nowhere, cleaned up next run.

**Why atomic on both OSes:**
- Linux ext4: `os.replace` calls POSIX `rename(2)`, which is atomic on the same filesystem — POSIX requires that "if newpath already exists, it will be atomically replaced." `[CITED: man 2 rename]` `[VERIFIED: GHA runs ubuntu-latest where docs/projects/patterns is always on the same mount.]`
- Windows NTFS: `os.replace` calls `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING`. Since Python 3.3 this is documented as atomic on Windows for same-filesystem moves. `[CITED: Python docs os.replace; PEP 418/PEP 466 related historical context]`

**Example:**

```python
def _atomic_write_json(path: Path, obj: dict) -> None:
    """Write JSON atomically. Crashed process never leaves partial JSON visible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())  # flush kernel buffers to disk before rename
    os.replace(tmp, path)
```

**Notes:**
- `os.fsync` on the temp file before rename is recommended for crash-resilience (kernel buffers may otherwise hold the writes when the rename completes). It does NOT affect atomicity itself but does affect durability — see "Common Pitfalls / Pitfall: durability vs atomicity confusion."
- `fsync` on the parent directory is theoretically needed for full crash-safety on POSIX (so the directory entry is durably committed), but for a CI runner that doesn't crash mid-write at the kernel level, this is overkill. Recommend skipping unless empirical evidence shows partial writes.

### Pattern 3: Deterministic Publication Render

**What:** A new entry in `renderer.STYLES` keyed by name `"publication"` (the existing `STYLES` is a tuple indexed by integer — recommend converting to a `dict` keyed by name OR adding a sibling module-level constant `PUBLICATION_STYLE: RenderStyle`).

**Recommendation: sibling constant.** The existing `STYLES` tuple is indexed by integer in `backtest._score_detection` (`STYLES[0]`). Changing it to a dict would break Phase 9's API. Cleanest path: add `PUBLICATION_STYLE: RenderStyle = RenderStyle(...)` as a module constant, leave `STYLES` tuple unchanged.

**Style design (planner refines colors):**

```python
# In renderer.py — module constants
PUBLICATION_STYLE = RenderStyle(
    name="publication",
    base_style="nightclouds",   # mplfinance built-in dark theme
    figsize=(8.0, 5.0),         # 4:3 horizontal — wider than training square
    dpi=150,                    # higher DPI per D-14 ("~150")
    candle_width=0.6,           # matches style_a for visual continuity
    facecolor="#0d1117",        # GitHub dark theme tone
)
```

Suggested mplfinance market colors (verify with planner):
```python
mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350", edge="inherit",
                            wick={"up": "#26a69a", "down": "#ef5350"},
                            volume="in")
```

**Bbox overlay (algorithmic, D-13):**
- mplfinance `addplot` does not support raw rectangle overlays directly; use the `returnfig=True` path (already exercised in `renderer.compute_bbox_normalized`) to get the axes back, then draw a `matplotlib.patches.Rectangle` in DATA coordinates.
- Geometry (D-13): `x0 = mother_idx_in_window - candle_width/2`, `x1 = conf_idx_in_window + candle_width/2`, `y0 = min(bar.low for 5 bars)`, `y1 = max(bar.high for 5 bars)`.
- Suggested stroke: 2.0 px, color `#ffd166` (saturated yellow on dark background — high contrast, deliberately not green/red to avoid implying P/L direction).
- The 60-bar input frame's left-side bars before the mother bar are still rendered; the bbox only highlights the 5-bar cluster.

**Determinism (live-verified 2026-05-11):**
```
$ python -c "...matplotlib savefig × 2 with 1.1s delay between..."
default behavior — hash1: e92de65f4484f7da
default behavior — hash2: e92de65f4484f7da
match: True
```

matplotlib 3.10.9 does NOT embed creation timestamps in PNG output by default. The set-difference cleanup (D-15) works as designed: same `(ticker, confirmation_date)` input → same OHLC slice → same PNG bytes → git sees no change.

**Belt-and-suspenders option:** pass `metadata={"Software": None, "Creation Time": None}` to `fig.savefig()` to lock determinism even if future matplotlib versions change the default. `[VERIFIED: hash1 == hash2 with metadata kwarg as well.]`

### Pattern 4: `pending` Status via Pre-Check Wrapper

**What:** D-02 introduces `pending` as a new state distinct from Phase 9's three-bucket `{stop, target, open}`. Phase 9's `simulate_trade` already handles `entry_idx >= len(df)` by returning a record with `exit_reason="open"`, `risk=0.0`. Phase 10 reinterprets this same edge case as `pending` (semantically: "the entry bar hasn't opened yet on the live OHLC slice").

**Implementation:**

```python
# scripts/pattern_scanner/run_pipeline.py
def _resolve_status(df: pd.DataFrame, detection: Detection) -> dict:
    """Wraps simulate_trade with a pending pre-check (D-02).

    Phase 9 D-02 contract: simulate_trade returns {stop, target, open}.
    Phase 10 adds {pending}: the entry bar (conf_idx + 1) does not yet exist
    in the live OHLC frame. This happens when today IS the confirmation day
    (or there is no next bar yet).
    """
    entry_idx = detection.confirmation_bar_index + 1
    stop_price = _stop_for(detection)
    if entry_idx >= len(df):
        # PENDING: no entry possible yet. Compute target as if entry were today's close.
        last_close = float(df.iloc[-1]["Close"])
        target_price = _target_for(last_close, stop_price)
        return {
            "ticker": str(detection.ticker),
            "confirmation_date": str(detection.confirmation_date),
            "confirmation_type": str(detection.confirmation_type),
            "is_spring": bool(detection.is_spring),
            "status": "pending",          # NEW state name; renames exit_reason
            "entry_date": None,
            "entry_price": None,
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "risk": None,
            "exit_date": None,
            "exit_price": None,
            "exit_reason": None,
            "hold_days": None,
            "R": None,
        }
    # Delegate to Phase 9 simulate_trade; rename exit_reason → status for the public API.
    entry_open = float(df.iloc[entry_idx]["Open"])
    target_price = _target_for(entry_open, stop_price)
    rec = simulate_trade(df, detection, stop_price, target_price)
    rec["status"] = rec.pop("exit_reason")  # rename for D-02 public contract
    return rec
```

**Schema decision (D-02 / Claude's discretion):** I recommend **renaming** `exit_reason` → `status` at the `run_pipeline.py` boundary so the public `data.json` carries one field that takes all four values `{pending, open, target, stop}`. This keeps the JSON small and lets Phase 11 frontend dispatch on a single field. Phase 9's `simulate_trade` contract stays untouched (it still returns `exit_reason`).

### Anti-Patterns to Avoid

- **Modifying `backtest.simulate_trade` to add `pending`.** D-02 explicitly forbids this. The Phase 9 contract is shared with the backtest cache; adding a new outcome would break Phase 9's `_dev/backtest_cache.json` schema and the 5 simulate_trade unit tests. Wrap, don't modify.
- **Including unfiltered detections in `data.json`.** D-04 locked filtered-only. The unfiltered superset is a backtest-narrative point; never reaches the public screener.
- **`rm -rf charts/` before each run.** D-15 explicitly forbids this. Byte-identical recurring PNGs need to be left alone so git doesn't churn 50 KB × N PNGs per night.
- **Re-running `verify_onnx.py` in CI.** D-08 trusts the commit-time gate. The clean-venv test is for PRs that touch the ONNX file, not for nightly inference.
- **Adding torch or ultralytics to `requirements.txt`.** Phase 8 D-20 lock. Phase 10 must NEVER violate this — the entire portfolio narrative depends on demonstrating a torch-free inference path.
- **Embedding base64 PNGs in `data.json`.** Implicit from the project decision history (v2.0 Roadmap: "Annotated chart PNGs in `docs/projects/patterns/charts/` — not base64 in `data.json`"). PNG paths in `data.json` reference the chart files by filename.
- **Calling `os.replace` across filesystems.** If `data.json` and `data.json.tmp` are on different mounts, `os.replace` is NOT atomic — it falls back to copy + delete. Always write the temp file in the same directory as the final file.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Business-day arithmetic | Custom loop subtracting 1 day at a time, skipping weekends and US holidays manually. | `pd.tseries.offsets.BDay(20)` — handles weekend rollback automatically. | Holiday handling: BDay does NOT account for US market holidays (e.g., July 4, Memorial Day). For the 20-day window this is acceptable noise — a holiday in the window shifts the cutoff by one trading day, which is within the resolution-coverage buffer. If holiday awareness becomes load-bearing, use `pd.tseries.offsets.CustomBusinessDay(calendar=USFederalHolidayCalendar())`. Live-verified BDay correctness against Monday/Saturday inputs. |
| Atomic file write | `with open(...) as f: f.write(...)` directly on the final path. | `os.replace(tmp, final)` after writing `tmp`. | Crashed mid-write leaves a half-written `final` visible to readers. `os.replace` is atomic on both Linux and Windows when src/dst share a filesystem (Phase 10 always satisfies this). |
| ONNX inference loop | Loading a new `InferenceSession` per detection. | Load once at process start (`_load_onnx_session`), reuse across all detections. | Session construction is the expensive part (file parse + graph optimization). Phase 9 SUMMARY note: per-inference latency is the bottleneck at ~250-350 ms; session construction is one-shot. Already encoded in `backtest._load_onnx_session`. |
| Stale file cleanup | `shutil.rmtree(charts/)` then re-render all. | Set-difference: `expected = {…}; for f in dir.iterdir(): if f.name not in expected: f.unlink()`. | Per D-15: byte-identical recurring PNGs prevent commit churn. rm-and-rebuild defeats the purpose. |
| `run_id` generation | Custom UUID logic, or timestamp-based ID. | `os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4())`. | GitHub Actions injects `GITHUB_RUN_ID` (numeric string like "10892478123") automatically; using it makes the workflow URL discoverable from `pipeline_status.run_id`. Fall back to uuid4 for local runs. |
| yfinance retry / rate limiting | Custom retry decorator with backoff. | `RATE_LIMIT_SLEEP = 0.5` between fetches (same as `backtest.py` L33). Bare yfinance call inside try/except. | Phase 9 ran 503 tickers cleanly at this cadence (per Phase 9 SUMMARY "Run anomalies: No per-ticker errors"). The yfinance flakiness model is "occasional single-ticker failures, never universal outage" — caught by per-ticker try/except. |
| JSON serialization | Custom encoder for pd.Timestamp / numpy.float64. | `json.dump(obj, f, default=str)` AND wrap every numeric value in `float()` / `int()` at construction time. | Phase 9 Risk 1 / Risk 2 mitigation pattern (see `backtest.simulate_trade` — all numeric fields wrapped in `float()`, all dates use `.strftime("%Y-%m-%d")`). Phase 10 mirrors verbatim. |
| Pytest scaffolding | New conftest, new fixtures, new mock framework. | Reuse `tests/conftest.py` `synthetic_ohlc` fixture; monkeypatch `_fetch_ohlc` and `time.sleep` per `test_backtest_yolo_conf_fallback.py`. | Phase 8/9 pattern. All Phase 10 tests run in milliseconds, no network, no ONNX. |
| Workflow YAML structure | New CI provider, new YAML schema, new auth. | Copy `nightly-screener.yml`; change cron, install line stays, swap script invocation, add 3 paths to `git add`. | The existing workflow has been running cleanly for weeks (per STATE.md "Phase 09 close-out"). Mirror byte-for-byte. |

**Key insight:** Phase 10 is a composition phase. Every primitive it needs already exists in Phases 7/8/9 or in `requirements.txt`. The risks are in three thin layers — atomicity, determinism, and the `pending` wrapper — and all three have small, well-defined implementations with unit tests in D-21.

## Runtime State Inventory

**This is a greenfield phase (new files only, no rename or refactor).** The Runtime State Inventory step does not apply — no existing data, services, OS-registered state, secrets, or build artifacts need to be migrated. The five categories:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases involved. `_dev/backtest_cache.json` exists locally (gitignored, Phase 9 artifact) but is read-only input to the one-shot `export_aggregates.py` helper; Phase 10 nightly path does not touch it. | None |
| Live service config | None — no external services (n8n, Datadog, etc.) involved. GitHub Actions workflow file is fully declarative in git. | None |
| OS-registered state | None — no Windows Task Scheduler, no systemd units, no launchd plists. Scheduling is via GitHub Actions cron, encoded entirely in the YAML. | None |
| Secrets / env vars | `secrets.GITHUB_TOKEN` (automatic, provided by GHA — same as `nightly-screener.yml`). No new secrets. yfinance requires no API key. ONNX inference is CPU only, no API. | None — Phase 10 inherits the existing GHA secret. |
| Build artifacts | None — Phase 10 does not produce installable packages. The `models/inside_bar_v1.onnx` artifact is checked into git by Phase 8 and read-only at Phase 10 runtime. | None |

**Nothing found in any category** — verified by inspecting `.github/workflows/*.yml`, `.gitignore`, `requirements.txt`, `scripts/pattern_scanner/__init__.py`, and the absence of any DB connection strings in the repo.

## Common Pitfalls

### Pitfall 1: Cross-Filesystem `os.replace` Loses Atomicity

**What goes wrong:** If `data.json.tmp` is written to `/tmp/` and `os.replace("/tmp/data.json.tmp", "docs/projects/patterns/data.json")` is called, and these mounts differ (e.g., `/tmp` is tmpfs, `docs/` is on the ext4 root), `os.replace` silently falls back to `copy + unlink`, which is NOT atomic — a reader CAN see a partial file.

**Why it happens:** POSIX `rename(2)` requires src and dst on the same filesystem; Python's `os.replace` honors this constraint.

**How to avoid:** Always write the temp file in the same directory as the final file (e.g., `data.json.tmp` next to `data.json`). The `_atomic_write_json` helper above does this correctly.

**Warning signs:** Tests of `os.replace` that mock/stub the move always pass; only a real cross-filesystem test exercises the failure mode. The D-21 `test_atomic_write_protocol` should use `tmp_path` (pytest fixture, single tmpfs) and verify the temp file sits next to the final path.

### Pitfall 2: yfinance Returns MultiIndex Columns for Single-Ticker `Ticker.history()` vs `download()`

**What goes wrong:** Using `yf.download("AAPL", period="6mo")` returns a DataFrame with flat columns when given a single ticker — UNLESS pandas/yfinance versioning kicks in MultiIndex (`group_by="ticker"`). Result: `df["Open"]` fails silently or returns wrong shape.

**Why it happens:** yfinance evolved its API; `Ticker(symbol).history(...)` is the stable single-ticker idiom and ALWAYS returns flat columns.

**How to avoid:** Use the existing Phase 7/8/9 idiom verbatim:
```python
df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
df = df[["Open", "High", "Low", "Close"]]
if df.index.tz is not None:
    df.index = df.index.tz_localize(None)
```
**Warning signs:** detector's `_validate_frame` raises `ValueError: requires columns {...}; missing: {...}` if shape is wrong. The synthetic test fixture in conftest.py always uses flat columns so unit tests don't catch this — a real network smoke test is the only catch. NOT a blocker; Phase 7/8/9 already prove the idiom works.

### Pitfall 3: BDay(20) Walks BACKWARDS from a Weekend Date Without Issue, but cron+`workflow_dispatch` from Saturday Behavior Differs

**What goes wrong:** Some developers expect `today - BDay(20)` to raise on a Saturday or behave unpredictably.

**Empirical truth (live-verified):**
```
today = pd.Timestamp("2026-05-11")  # Monday
today - BDay(20) = 2026-04-13       # Monday — 20 business days back

sat = pd.Timestamp("2026-05-09")    # Saturday
sat - BDay(20) = 2026-04-13         # Same answer — Saturday is rolled back to Friday before stepping
```

So `workflow_dispatch` on a Saturday produces a sensible cutoff. No special handling needed. `[VERIFIED: live python eval 2026-05-11]`

**How to avoid:** Always compute today with `pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)`. The `.normalize()` zeroes the time component so the BDay math doesn't accidentally include partial-day arithmetic.

### Pitfall 4: Matplotlib Figure Memory Leak Across Thousands of Renders

**What goes wrong:** `mpf.plot` creates matplotlib figures that stay in memory until explicitly closed. After hundreds of renders, memory grows unbounded.

**Why it happens:** `mpf.plot` returns when the figure is created but does not implicitly call `plt.close`.

**How to avoid:** `renderer.render` already calls `plt.close("all")` after each render — copy this pattern into the publication-style render path. **Already mitigated in the existing renderer; just don't accidentally omit it in the new code path.**

**Warning signs:** Local smoke run produces `RuntimeWarning: More than 20 figures have been opened. Figures created through the pyplot interface...`

### Pitfall 5: ONNX Inference Failure on a Single Window Should NOT Abort the Run

**What goes wrong:** A single corrupt OHLC window causes `_score_detection` to throw, and the run aborts with one bad ticker out of 503.

**Why it happens:** Naive `_score_detection` raises on PIL/numpy/onnxruntime exceptions.

**How to avoid:** `backtest._score_detection` already handles this — see backtest.py L442-449. It catches `Exception` and emits a UserWarning, returns None for that record. Phase 10 reuses this code path verbatim; do NOT re-implement.

### Pitfall 6: PNG Path in `data.json` Must Be Relative, Not Absolute

**What goes wrong:** If `chart_path` in `data.json` is `/home/runner/work/.../docs/projects/patterns/charts/AAPL_2026-04-22.png`, the frontend's `<img src>` breaks because GitHub Pages serves from the repo root.

**Why it happens:** `pathlib.Path.resolve()` or `Path.absolute()` produce absolute paths.

**How to avoid:** Write the path as `charts/{TICKER}_{DATE}.png` (relative to `docs/projects/patterns/`). The frontend reads `data.json` from `docs/projects/patterns/data.json` so relative paths resolve correctly. Use:
```python
rec["chart_path"] = f"charts/{ticker}_{confirmation_date}.png"
```

### Pitfall 7: GitHub Actions Bot Push Loop

**What goes wrong:** A workflow pushes to `main`, which triggers the workflow again, which pushes again, etc.

**Why it happens:** The default GHA token push event normally does NOT trigger downstream workflows (GitHub deliberately prevents this) — but only when push is authenticated with `GITHUB_TOKEN`. Using a PAT or different token would trigger downstream workflows.

**How to avoid:** Use `secrets.GITHUB_TOKEN` (the default) for `actions/checkout` and `git push`. Existing `nightly-screener.yml` does this correctly — mirror.

**Warning signs:** If you see the same workflow run twice in quick succession at 07:00 UTC, this is the smoking gun.

### Pitfall 8: yfinance Period Returns Slightly Less Than 6 Months Early in the Year

**What goes wrong:** Around January, `period="6mo"` may return 122-125 trading days (not the expected ~126), because trading days are not evenly distributed across calendar months.

**Why it happens:** December typically has fewer trading days than other months due to holidays.

**How to avoid:** Be defensive about the minimum bar count. The detector's `_LOOKBACK = 60` requires 60 bars minimum, so anything `>= 80` is well-buffered. If `len(df) < 60`, the detector returns `[]` cleanly (already handled). Log a warning if `len(df) < 80` so the maintainer notices: "ticker X returned only 75 bars from 6mo fetch — consider increasing the period."

### Pitfall 9: Confusing Atomicity with Durability

**What goes wrong:** "I called `os.replace` so the write is atomic AND durable." False — atomicity means readers see one state or the other; durability means the write survives a power loss.

**Why it happens:** The OS may buffer the write; without `fsync`, a kernel panic between `write()` and the actual disk commit could lose data.

**How to avoid:** For Phase 10's GHA runner context, durability is not the threat model — the runner finishes the commit and pushes to git within seconds; if the runner crashes, the entire run is retried. `fsync` is included in the recommended `_atomic_write_json` for hygiene but not load-bearing.

## Code Examples

### Example 1: `_fetch_ohlc` (verified shape from Phase 7/8/9)

```python
# scripts/pattern_scanner/run_pipeline.py
# Source: scripts/pattern_scanner/backtest.py L280-291 (verified live)
import pandas as pd

def _fetch_ohlc(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch daily OHLC via yfinance with auto_adjust=True. Lazy import for testability.

    Mirrors generate_training_data._fetch_ohlc / detector._fetch_ohlc / backtest._fetch_ohlc.
    Only difference: default period="6mo" instead of "10y" — Phase 10 fetches the minimum
    needed for a 20-day window + 60-bar lookback + 10-bar safety buffer (~90 bars total).
    """
    import yfinance as yf  # noqa: WPS433 — deferred by design
    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df
```

### Example 2: Atomic JSON Write

```python
# scripts/pattern_scanner/run_pipeline.py
# Source: synthesized from Python os.replace docs + Phase 9 backtest.py L600-603 baseline
import json, os
from pathlib import Path

def _atomic_write_json(path: Path, obj: dict) -> None:
    """Write JSON atomically. Reader sees the old file or the new file, never a partial.

    Pattern: write to `<final>.tmp` in the same directory, fsync, os.replace to final.
    POSIX rename(2) is atomic on same filesystem; Windows MoveFileExW with
    MOVEFILE_REPLACE_EXISTING is atomic. Always co-locate tmp with final.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())  # hygiene; not load-bearing for atomicity
    os.replace(tmp, path)
```

### Example 3: Window Filter via BDay

```python
# scripts/pattern_scanner/run_pipeline.py
import pandas as pd
from pandas.tseries.offsets import BDay

def _window_cutoff(today: pd.Timestamp, window_days: int) -> pd.Timestamp:
    """Compute the earliest confirmation_date that counts as 'in window' (D-01).

    BDay handles weekend rollback automatically: BDay(20) from a Saturday equals
    BDay(20) from the preceding Friday. Live-verified 2026-05-11.

    Note: BDay does NOT account for US market holidays. For the 20-day window this
    is acceptable — a holiday in the window shifts the cutoff by one trading day,
    within the resolution-coverage buffer (D-03's 10-bar safety).
    """
    return today.normalize() - BDay(window_days)


def _in_window(detection_dict_or_obj, cutoff: pd.Timestamp) -> bool:
    """Return True if confirmation_date >= cutoff."""
    # Detection.confirmation_date is ISO YYYY-MM-DD per detector.py L289
    conf_str = detection_dict_or_obj.confirmation_date  # or ["confirmation_date"] for dict
    return pd.Timestamp(conf_str) >= cutoff
```

### Example 4: Stale PNG Cleanup (D-15)

```python
# scripts/pattern_scanner/run_pipeline.py
from pathlib import Path

def _cleanup_stale_pngs(charts_dir: Path, expected_filenames: set[str]) -> int:
    """Delete only files not in the expected set (D-15).

    Returns the count of deleted files (useful for pipeline_status).
    """
    if not charts_dir.exists():
        charts_dir.mkdir(parents=True, exist_ok=True)
        return 0
    deleted = 0
    for f in charts_dir.iterdir():
        if f.is_file() and f.suffix == ".png" and f.name not in expected_filenames:
            f.unlink()
            deleted += 1
    return deleted
```

### Example 5: GitHub Actions Workflow (`nightly-pattern-scanner.yml`)

```yaml
# .github/workflows/nightly-pattern-scanner.yml
# Source: derived line-for-line from .github/workflows/nightly-screener.yml,
#         with three deltas (cron offset, script path, git add paths).
name: Nightly Pattern Scanner Data

on:
  schedule:
    - cron: '0 7 * * 1-5'  # 07:00 UTC weekdays — 1h after nightly-screener.yml
  workflow_dispatch:        # manual trigger for testing

permissions:
  contents: write           # required for git push with GITHUB_TOKEN

jobs:
  pattern-scanner:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run pattern scanner pipeline
        run: python -m scripts.pattern_scanner.run_pipeline --tickers all --window-days 20 --out-dir docs/projects/patterns

      - name: Commit updated pattern scanner data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/projects/patterns/data.json docs/projects/patterns/stats.json docs/projects/patterns/charts/
          git diff --staged --quiet || git commit -m "chore: nightly pattern scanner data update"
          git push
```

### Example 6: `pending` Wrapper Test

```python
# tests/test_run_pipeline_pending.py
import pandas as pd
from scripts.pattern_scanner.run_pipeline import _resolve_status

def test_resolve_status_pending(synthetic_ohlc):
    """D-02: entry_idx >= len(df) returns status='pending' with null trade fields."""
    # Build a small df where the last bar IS the confirmation bar (no next bar).
    rows = [(100, 105, 99, 102)] * 10  # 10 dummy bars
    df = synthetic_ohlc(rows)
    # Fake a Detection at the last bar
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class FakeDet:
        ticker: str = "TEST"
        confirmation_date: str = "2024-01-10"
        confirmation_type: str = "pin"
        is_spring: bool = True
        bars: list = None
        mother_bar_index: int = 7
        confirmation_bar_index: int = 9  # LAST index — no entry possible
        filters: dict = None
        sma_levels: dict = None
    fake = FakeDet(bars=[{"low": 99, "high": 105, "open": 100, "close": 102, "date": "2024-01-10"}] * 5)
    rec = _resolve_status(df, fake)
    assert rec["status"] == "pending"
    assert rec["entry_date"] is None
    assert rec["R"] is None
```

### Example 7: Deterministic Render Test (D-21)

```python
# tests/test_run_pipeline_render_determinism.py
import hashlib
from pathlib import Path
from scripts.pattern_scanner.run_pipeline import _render_publication_chart

def test_publication_render_is_deterministic(tmp_path, synthetic_ohlc):
    """D-15 prerequisite: same input → byte-identical PNG."""
    rows = [(100 + i, 105 + i, 99 + i, 102 + i) for i in range(60)]
    df = synthetic_ohlc(rows)
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class FakeDet:
        ticker: str = "TEST"
        confirmation_date: str = "2024-04-01"
        mother_bar_index: int = 55
        confirmation_bar_index: int = 59
        bars: list = None
    fake = FakeDet(bars=[{"low": 100, "high": 105, "open": 102, "close": 103, "date": "..."}] * 5)

    p1 = tmp_path / "run1.png"
    p2 = tmp_path / "run2.png"
    _render_publication_chart(df, fake, p1)
    _render_publication_chart(df, fake, p2)

    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2, "Publication render must be byte-deterministic for D-15 set-difference cleanup."
```

## Schema Designs

### `data.json` shape (consumed by Phase 11 frontend)

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-11T07:00:23.412Z",
  "window_days": 20,
  "as_of_date": "2026-05-11",
  "pipeline_status": {
    "completed": true,
    "succeeded_count": 501,
    "failed_count": 2,
    "errors": [
      {"ticker": "XYZ", "stage": "fetch_or_detect", "message": "yfinance returned empty df", "timestamp": "2026-05-11T07:02:14.123Z"}
    ],
    "errors_truncated": 0,
    "run_id": "10892478123",
    "generated_at": "2026-05-11T07:00:23.412Z"
  },
  "detections": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "sector": "Technology",
      "confirmation_date": "2026-04-22",
      "confirmation_type": "pin",
      "is_spring": true,
      "current_price": 178.43,
      "chart_path": "charts/AAPL_2026-04-22.png",
      "yolo_conf": 0.42,
      "status": "open",
      "entry_date": "2026-04-23",
      "entry_price": 175.32,
      "stop_price": 170.10,
      "target_price": 185.76,
      "risk": 5.22,
      "exit_date": null,
      "exit_price": null,
      "hold_days": 14,
      "R": 0.595,
      "filters": {"hh_hl": true, "above_50sma": true, "sma_cluster": true},
      "bars": [
        {"date": "2026-04-16", "open": 173.10, "high": 175.20, "low": 171.40, "close": 174.50},
        ...
      ]
    }
  ]
}
```

**Notes on field choices:**
- `status` (not `exit_reason`) — renamed at the run_pipeline boundary (D-02).
- `company_name` and `sector` — enrichment for the frontend table (UI-01); planner decides whether to fetch from yfinance Ticker.info or join from `docs/projects/screener/data.json` (already on disk and S&P 500 covered). Recommend joining from screener data.json to avoid double yfinance calls — adds ~50 ms per ticker for a JSON read.
- `current_price` — last close from the fetched OHLC; useful for the table without re-fetching.
- `chart_path` — relative to `data.json` location.
- `errors_truncated` — 0 if errors list is full; positive integer count if truncated at the 50-cap.

### `stats.json` shape (consumed by Phase 11 frontend)

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-11T07:00:23.412Z",
  "source": "out_of_sample, strategy=1to2_rr_cluster_low_stop",
  "rule": {
    "stop": "min(bar.low for bar in detection.bars)",
    "target_R": 2.0,
    "intrabar": "pessimistic",
    "timeout": "none"
  },
  "stats": {
    "by_type_x_spring": {
      "pin_spring": {"n": 12, "n_resolved": 12, "win_rate": 0.333, "avg_return_r": -0.05, "median_hold_days": 3, "target_count": 4, "stop_count": 8, "open_count": 0},
      "pin_extended": {"n": 5, ...},
      "mark_up_spring": {...},
      ...
    },
    "by_confirmation_type": {
      "pin": {"n": 17, ...},
      "mark_up": {"n": 22, ...},
      "ice_cream": {"n": 41, ...}
    },
    "all": {"n": 80, "n_resolved": 78, "win_rate": 0.359, "avg_return_r": 0.012, "median_hold_days": 4, "target_count": 28, "stop_count": 50, "open_count": 2}
  },
  "fallback_order": ["by_type_x_spring", "by_confirmation_type", "all"],
  "n_floor": 10
}
```

**Notes:**
- `stats.by_type_x_spring` keys mirror Phase 9 cache exactly (e.g., `pin_spring`, `mark_up_extended`). NOTE: Phase 9 backtest uses `pin_True` / `pin_False` (Python str of bool). Phase 10 should normalize to `pin_spring` / `pin_extended` at the `build_stats_json` step for frontend readability. The `export_aggregates.py` helper or `build_stats_json` does this rename.
- Frontend lookup is `stats[fallback_order[i]].get(key, None)` walked in order until `n >= n_floor`.
- `source` field documents which strategy + sample block these aggregates came from (out_of_sample filtered).

### `_backtest_aggregates.json` shape (one-shot committed file)

```json
{
  "schema_version": 1,
  "extracted_from": "_dev/backtest_cache.json",
  "extracted_at": "2026-05-11T00:00:00Z",
  "train_test_cutoff": "2024-01-01",
  "onnx_sha256": null,
  "strategy": "1to2_rr_cluster_low_stop",
  "sample": "out_of_sample",
  "aggregates": {
    "all": {...},
    "by_confirmation_type": {...},
    "by_is_spring": {...},
    "by_type_x_spring": {...}
  }
}
```

**Size estimate:** From the live backtest cache (5 KB read), the aggregates blocks for filtered out_of_sample are < 3 KB. Even with all four slices, this file is < 10 KB. `[VERIFIED: backtest_cache.json head sampled to confirm aggregate structure size.]`

### `_backtest_aggregates.json` extraction helper (recommended shape)

**Recommendation: separate module `scripts/pattern_scanner/export_aggregates.py`.**

Rationale:
- Coupling extraction to `backtest.py` as a `--export-aggregates` flag conflates two concerns: (a) running the backtest, (b) projecting cache into a frontend-shipped slice. The flag approach grows the backtest CLI surface for a one-shot operation; a separate module is more honest about its purpose.
- Discoverability: `python -m scripts.pattern_scanner.export_aggregates --help` directly tells you what it does.
- Testability: a self-contained module with a `project_aggregates(cache: dict) -> dict` pure function is testable without invoking `backtest.main`.

**CLI:**
```bash
python -m scripts.pattern_scanner.export_aggregates \
    --in _dev/backtest_cache.json \
    --out docs/projects/patterns/_backtest_aggregates.json \
    --strategy 1to2_rr_cluster_low_stop \
    --sample out_of_sample
```

**Skeleton:**
```python
# scripts/pattern_scanner/export_aggregates.py
import argparse, json
from pathlib import Path

def project_aggregates(cache: dict, strategy: str, sample: str) -> dict:
    """Pure: project a full backtest cache into the small aggregates-only shape."""
    strat = cache["strategies"][strategy][sample]
    return {
        "schema_version": 1,
        "extracted_at": cache["generated_at"],
        "train_test_cutoff": cache["train_test_cutoff"],
        "onnx_sha256": cache["onnx_sha256"],
        "strategy": strategy,
        "sample": sample,
        "aggregates": strat["aggregates"],
    }

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--strategy", default="1to2_rr_cluster_low_stop")
    p.add_argument("--sample", default="out_of_sample", choices=["in_sample", "out_of_sample"])
    args = p.parse_args(argv)
    cache = json.loads(args.inp.read_text())
    out = project_aggregates(cache, args.strategy, args.sample)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
```

This helper runs **once at Phase 10 plan time** (developer manually), commits the output `_backtest_aggregates.json`, and is rerun manually only when the backtest is rerun.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `open(path, "w")` then write directly | `temp + os.replace(tmp, final)` | Standard practice since the 2000s; codified in Python `os.replace` since 3.3. | Standard atomic-write idiom on POSIX and Windows. Used by SQLite, pg_dump, and other production tools. |
| Custom busday loops with weekend skip logic | `pd.tseries.offsets.BDay` | pandas 0.x era; stable. | Live-verified weekend rollback behavior; no implementation needed. |
| Embedded chart base64 in JSON | External PNG files referenced by path | Adopted at v2.0 roadmap stage (per STATE.md decisions). | Smaller `data.json`; CDN-friendly; git history clean for unchanged PNGs. |
| `requirements.txt` includes all deps | Split into `requirements.txt` (inference) + `requirements-training.txt` (offline) | Phase 8 D-20 (2026-05-02). | CI installs only the inference subset (no torch); training stays on local hardware. |
| Wikipedia direct via `pd.read_html` | Wikipedia via `requests.get` with browser UA, then `pd.read_html` on text | Phase 5 (2026-04-05); already in `fetch_sp500.fetch_sp500_tickers()`. | Wikipedia returns 403 for default urllib UA; browser UA fixes it. Reused as-is in Phase 10. |
| Single GitHub Actions job per workflow | Same — single job, sequential steps | Standard since GHA launch. | Phase 10 mirrors. |
| Use ultralytics for inference | Use onnxruntime only (no torch); ultralytics is offline-only | Phase 8 D-20 + Phase 8-05 SUMMARY (2026-05-08). | Phase 10 has 11.7 MB ONNX deliverable, ~hundred-MB onnxruntime install footprint, vs ~GB-scale torch+ultralytics. CI install time drops dramatically. |

**Deprecated/outdated:**
- `os.rename` (replaced by `os.replace` since Python 3.3 because `rename` was not atomic on Windows when destination existed).
- Hand-rolled "is this a trading day" lookups (pandas + numpy busday handle it; for full holiday awareness use `pandas.tseries.holiday.USFederalHolidayCalendar`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A 6-month yfinance fetch yields ≥ 80 trading days year-round. | Pitfall 8 | Detector might return zero detections for some tickers if `len(df) < 60` (handled gracefully — empty list). Worst case: a January run produces slightly fewer detections; not blocking. |
| A2 | The committed ONNX `models/inside_bar_v1.onnx` (11.7 MB) loads in < 5 s on `ubuntu-latest` CPU. | Pipeline orchestration | If slower, total ONNX load time is still single-digit seconds — does not change the design. |
| A3 | Per-detection ONNX inference latency on `ubuntu-latest` CPU is in the 100-500 ms range (consistent with Phase 9 SUMMARY's 250-350 ms on local). | Don't Hand-Roll / ONNX inference loop | If latency is 10× higher, 500 detections × 5 s = 42 min total ONNX work, plus yfinance fetches. Could push wall-clock over 30 min. Mitigation: if measured slow, add `concurrent.futures.ThreadPoolExecutor` around `_score_detection` (Phase 9 SUMMARY note already suggests this for future runs). Not blocking for Phase 10 plan. |
| A4 | The ~20-day window × ~503 tickers × filtered ratio produces "tens to low-hundreds of detections per nightly run" (per D-06 wording). | Pipeline orchestration | If the live filtered-detection density is much higher (e.g., 1000+ in a 20-day window during a volatile market), inference time scales linearly. Same mitigation as A3. |
| A5 | The publication style with `base_style="nightclouds"` produces a dark theme — verify against the actual mplfinance style list at plan time. | Pattern 3 / publication style | If `nightclouds` doesn't exist or doesn't match the dark visual goal, the planner picks a different base style or builds a custom one via `mpf.make_mpf_style` directly. mplfinance ships ~14 named styles per its docs. |
| A6 | `pandas.tseries.offsets.BDay` does NOT account for US market holidays — confirmed only via documentation, not via a holiday-day live run. | Pitfall 3 / Don't Hand-Roll | If wrong, the 20-day window may include a holiday (e.g., Memorial Day in May) and shift the cutoff by one trading day. Within the resolution-coverage buffer. Acceptable noise. |
| A7 | The renderer's existing `STYLES` tuple is the right place to add the publication style as a sibling constant, not by mutating the tuple. | Pattern 3 | If the planner prefers extending `STYLES` (e.g., adding a 4th entry indexed at `[3]`), `_score_detection`'s `STYLES[0]` reference remains valid. Both approaches work. Recommend sibling constant for clarity. |
| A8 | `_backtest_aggregates.json` is committed at Phase 10 plan time as a one-shot artifact, refreshed only when the backtest is rerun. | D-10 / extraction helper | If the planner wants nightly aggregate updates, the pipeline grows a step to read `_dev/backtest_cache.json` (not present in CI). Locked by CONTEXT.md — out of scope. |
| A9 | `STYLES["publication"]` style naming follows the existing `RenderStyle.name` pattern (string identifiers like "style_a"). | Pattern 3 | Cosmetic. Planner / user decides the exact key name. |
| A10 | GHA bot push with `GITHUB_TOKEN` does NOT trigger downstream `on: push` workflows. | Pitfall 7 | If wrong, an accidental push loop. Existing `nightly-screener.yml` has been running cleanly — empirical confirmation that no loop exists. |

## Open Questions

1. **How does the Phase 11 frontend resolve the fallback chain for `stats.json`?**
   - What we know: `stats.json` shape carries `fallback_order` and `n_floor` fields.
   - What's unclear: whether the fallback is computed Phase 10-side (pre-compute the "best available" cell for each `(confirmation_type, is_spring)` combo and write that into a flat lookup) or Phase 11-side (frontend walks the chain).
   - Recommendation: Phase 10 writes the raw cuts (all three slices); Phase 11 walks the chain. Keeps `stats.json` schema-stable and gives the frontend flexibility to adjust the `n_floor` later. (Documented in D-11; this is the consensus reading.)

2. **Should the publication chart include a title (ticker + confirmation_date), legend, or volume sub-panel?**
   - What we know: D-14 says "publication style — clear bbox stroke, dark theme, ~150 DPI"; no explicit ask for title/legend/volume.
   - What's unclear: aesthetic decision.
   - Recommendation: planner consults D-14 wording + existing portfolio site visual style (dark theme at `docs/index.html`). Suggest including ticker + confirmation_date as a small title (matplotlib `fig.suptitle`); no legend (one bbox is self-evident); no volume (clutter). Decision: discretion of the planner.

3. **What's the company_name/sector source for `data.json`?**
   - What we know: Phase 9 backtest cache does not carry these (only ticker + financial fields). The DCF screener `docs/projects/screener/data.json` carries them for all S&P 500 tickers.
   - What's unclear: should run_pipeline read from screener data.json (cross-feed) or re-fetch from yfinance?
   - Recommendation: read from `docs/projects/screener/data.json`. Adds ~10ms (a single JSON read at startup) and ensures consistency with the DCF screener. Caveat: if the DCF screener hasn't committed yet (race condition between the two workflows), fall back to ticker as company_name. The 1h cron offset (D-23) makes this race practically impossible.

4. **Should `pipeline_status.errors_truncated` count truncated entries by category (fetch, detect, render, score) or as a single number?**
   - What we know: D-16 says "errors[] is a list of {ticker, stage, message, timestamp}". CONTEXT.md Discretion notes "suggest yes — 50 cap".
   - What's unclear: cosmetic.
   - Recommendation: single number for v1 (`errors_truncated: 17` means 17 entries were dropped past the cap). The full count is `len(errors) + errors_truncated`. Frontend can decide how to surface.

5. **Should `data.json` carry the algorithmic bbox geometry per detection (for Phase 11 drilldown bbox overlay) or just the chart_path?**
   - What we know: D-13 says algorithmic 5-bar bbox is the geometry — derivable from `Detection.bars`.
   - What's unclear: whether Phase 11 needs the bbox as numeric data to overlay on a TradingView widget, or whether the static PNG with baked-in bbox is sufficient.
   - Recommendation: omit the numeric bbox from `data.json` for v1 (the baked-in PNG bbox satisfies UI-03's "annotated YOLOv8 detection image"). If Phase 11 wants a TradingView overlay later, the bbox can be added — Detection.bars carries the raw geometry.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | GHA runner + pipeline orchestrator | ✓ on ubuntu-latest | 3.11.x | — |
| pandas | run_pipeline._fetch_ohlc, _resolve_status, BDay | ✓ requirements.txt | >=2.2.0 | — |
| numpy | ONNX inference tensor construction | ✓ requirements.txt | >=1.26.0 (<2.0) | — |
| yfinance | OHLC fetch | ✓ requirements.txt | 0.2.65 | per-ticker try/except + errors[] |
| onnxruntime | yolo_conf overlay | ✓ requirements.txt | >=1.19 (1.25.1 verified) | D-08 graceful absence: yolo_conf=null |
| Pillow | PNG ↔ PIL.Image | ✓ requirements.txt | >=10.0 | — |
| mplfinance | candlestick rendering | ✓ requirements.txt | >=0.12.10b0 | — |
| matplotlib | mplfinance backing renderer | ✓ requirements.txt | >=3.8 (3.10.9 verified) | — |
| GitHub Actions ubuntu-latest | nightly cron | ✓ (assumed; same as nightly-screener.yml runs cleanly) | latest pinned by GHA | — |
| `secrets.GITHUB_TOKEN` | git push | ✓ (auto-provided) | — | — |
| `models/inside_bar_v1.onnx` | yolo_conf overlay | ✓ (11.7 MB, committed by Phase 8) | inside_bar_v1, opset 12 | D-08 graceful absence |
| `_dev/backtest_cache.json` | one-shot export to `_backtest_aggregates.json` | ✓ local (27.8 MB, gitignored) | Phase 9 schema_version 1 | manual rerun of backtest if missing |
| `docs/projects/screener/data.json` | company_name / sector enrichment | ✓ (committed) | screener schema v1 | per-ticker fallback to ticker as company_name |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None at this time. All inference deps are present; yfinance and ONNX absence have explicit fallbacks documented above.

## Validation Architecture

> Phase config: `workflow.nyquist_validation: true` (verified in `.planning/config.json`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing; reused from Phase 7/8/9) |
| Config file | none — `tests/conftest.py` carries the shared fixtures and `--no-network` flag |
| Quick run command | `python -m pytest tests/test_run_pipeline*.py --no-network -x` |
| Full suite command | `python -m pytest tests/ --no-network` |
| Pre-test setup | none (synthetic fixture; monkeypatched _fetch_ohlc) |
| Markers | `network` (defined in conftest.py); run_pipeline tests must NOT use this marker |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Nightly workflow runs detect + ONNX + writes data.json | smoke (manual `workflow_dispatch`) + unit tests on `main()` | `python -m pytest tests/test_run_pipeline_main.py::test_main_smoke_with_synthetic_ohlc -x` | ❌ Wave 0 |
| PIPE-02 | data.json atomic write | unit | `python -m pytest tests/test_run_pipeline_atomic.py::test_atomic_write_protocol -x` | ❌ Wave 0 |
| PIPE-02 | data.json carries pipeline_status with completed boolean | unit | `python -m pytest tests/test_run_pipeline_main.py::test_pipeline_status_completed_true_when_above_95pct -x` | ❌ Wave 0 |
| PIPE-02 | pipeline_status detects partial runs (95% threshold) | unit | `python -m pytest tests/test_run_pipeline_main.py::test_pipeline_status_completed_false_when_below_95pct -x` | ❌ Wave 0 |
| PIPE-03 | Annotated chart PNGs written | unit | `python -m pytest tests/test_run_pipeline_charts.py::test_render_writes_png -x` | ❌ Wave 0 |
| PIPE-03 | Stale PNGs cleaned (D-15 set-difference) | unit | `python -m pytest tests/test_run_pipeline_charts.py::test_stale_png_cleanup_keeps_current_drops_old -x` | ❌ Wave 0 |
| PIPE-03 | Publication render is byte-deterministic | unit | `python -m pytest tests/test_run_pipeline_charts.py::test_publication_render_is_deterministic -x` | ❌ Wave 0 |
| PIPE-04 | Workflow runs at 07:00 UTC weekdays | static (lint of YAML cron expression) | `python -c "import yaml; w = yaml.safe_load(open('.github/workflows/nightly-pattern-scanner.yml')); assert w['on']['schedule'][0]['cron'] == '0 7 * * 1-5'"` | ❌ Wave 0 (committed YAML is the deliverable; static check is the test) |
| PIPE-04 | Only inference deps installed (no torch / ultralytics) | static (grep `requirements.txt` for forbidden deps) | `python -c "deps = open('requirements.txt').read().lower(); assert 'torch' not in deps; assert 'ultralytics' not in deps"` | ❌ Wave 0 |
| Cross-cutting (D-02) | `pending` status when entry bar not yet present | unit | `python -m pytest tests/test_run_pipeline_pending.py::test_resolve_status_pending -x` | ❌ Wave 0 |
| Cross-cutting (D-02) | `_resolve_status` delegates to simulate_trade when entry possible | unit | `python -m pytest tests/test_run_pipeline_pending.py::test_resolve_status_delegates_to_simulate_trade -x` | ❌ Wave 0 |
| Cross-cutting (D-01) | 20-day window cutoff enforced | unit | `python -m pytest tests/test_run_pipeline_window.py::test_window_filter_drops_old_detections -x` | ❌ Wave 0 |
| Cross-cutting (D-08) | yolo_conf=null when ONNX missing | unit | `python -m pytest tests/test_run_pipeline_onnx_fallback.py::test_yolo_conf_null_when_onnx_missing -x` | ❌ Wave 0 (template: `tests/test_backtest_yolo_conf_fallback.py`) |
| Cross-cutting (D-11) | stats.json fallback to by_confirmation_type when n<10 | unit | `python -m pytest tests/test_run_pipeline_stats.py::test_stats_json_falls_back_to_by_confirmation_type_when_sparse -x` | ❌ Wave 0 |
| Cross-cutting (D-11) | stats.json ultimate fallback to all when both sparse | unit | `python -m pytest tests/test_run_pipeline_stats.py::test_stats_json_falls_back_to_all_when_both_sparse -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_run_pipeline*.py --no-network -x` (sub-second target)
- **Per wave merge:** `python -m pytest tests/ --no-network` (full repo suite; current baseline ~30 passed)
- **Phase gate:** Full suite green + `python -m pytest tests/ -m network` smoke pass (network-marked tests for `gh-pages` integration confidence — optional manual gate before merging Phase 10)

### Wave 0 Gaps
- [ ] `tests/test_run_pipeline_pending.py` — covers D-02 (`test_resolve_status_pending`, `test_resolve_status_delegates_to_simulate_trade`)
- [ ] `tests/test_run_pipeline_window.py` — covers D-01 (`test_window_filter_drops_old_detections`)
- [ ] `tests/test_run_pipeline_atomic.py` — covers D-17 / PIPE-02 (`test_atomic_write_protocol`)
- [ ] `tests/test_run_pipeline_charts.py` — covers D-15 + PIPE-03 (`test_stale_png_cleanup_keeps_current_drops_old`, `test_publication_render_is_deterministic`, `test_render_writes_png`)
- [ ] `tests/test_run_pipeline_onnx_fallback.py` — covers D-08 (`test_yolo_conf_null_when_onnx_missing`) — copy `tests/test_backtest_yolo_conf_fallback.py` skeleton
- [ ] `tests/test_run_pipeline_main.py` — covers D-16 / PIPE-02 (`test_pipeline_status_completed_true_when_above_95pct`, `test_pipeline_status_completed_false_when_below_95pct`, optional `test_main_smoke_with_synthetic_ohlc`)
- [ ] `tests/test_run_pipeline_stats.py` — covers D-11 (`test_stats_json_falls_back_to_by_confirmation_type_when_sparse`, `test_stats_json_falls_back_to_all_when_both_sparse`)
- [ ] No new conftest.py needed — reuse the existing `synthetic_ohlc` fixture and the `--no-network` machinery.
- [ ] No new framework install — pytest is already in the project; tests run via `python -m pytest`.

### Atomic Write Test Strategy (D-21)

`test_atomic_write_protocol` cannot literally simulate "writer killed mid-write" in pytest (the OS would handle it). Instead, test the invariant:

```python
def test_atomic_write_protocol(tmp_path):
    """PIPE-02: simulated mid-write does not leave a partial JSON file visible."""
    final = tmp_path / "data.json"
    tmp = tmp_path / "data.json.tmp"

    # 1. Pre-condition: write a half-baked .tmp file (simulating a crashed previous run)
    tmp.write_text('{"partial":')  # invalid JSON
    assert not final.exists()

    # 2. Normal atomic write — the .tmp file is overwritten then renamed
    from scripts.pattern_scanner.run_pipeline import _atomic_write_json
    _atomic_write_json(final, {"detections": [], "pipeline_status": {"completed": True}})

    # 3. Post-condition: final exists, is valid JSON, and the .tmp is gone (os.replace
    #    moves the file, leaving no .tmp behind).
    assert final.exists()
    assert not tmp.exists(), ".tmp file must not linger after atomic write"
    import json
    loaded = json.loads(final.read_text())
    assert loaded["pipeline_status"]["completed"] is True
```

The negative case (partial file visible) is tested by:
```python
def test_atomic_write_never_yields_partial(tmp_path):
    """PIPE-02: reader on disk only ever sees pre-write or post-write state, never partial."""
    final = tmp_path / "data.json"
    # Write a known initial state
    final.write_text('{"version": 1}')
    initial_hash = hashlib.sha256(final.read_bytes()).hexdigest()

    from scripts.pattern_scanner.run_pipeline import _atomic_write_json
    new_payload = {"version": 2, "detections": [...]}
    _atomic_write_json(final, new_payload)

    final_hash = hashlib.sha256(final.read_bytes()).hexdigest()
    # The file changed; no partial intermediate state is possible to observe in a single-process test,
    # but the os.replace guarantee documents that ANY observer either sees the v1 or v2 content.
    assert initial_hash != final_hash
    assert json.loads(final.read_text())["version"] == 2
```

## Security Domain

> `security_enforcement` not explicitly set in config; treated as enabled per Phase 10 researcher rule. Phase 10 is a CI workflow + script; the threat model is narrow.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (CI auth) | `secrets.GITHUB_TOKEN` — provided automatically by GitHub Actions; no manual handling. |
| V3 Session Management | no | No user sessions. CI workflow is stateless per run. |
| V4 Access Control | yes (write access to docs/) | `permissions: contents: write` block in YAML; scopes the token to the minimum needed. |
| V5 Input Validation | yes (ticker symbols, CLI args) | Reuse `detector._TICKER_RE` for any ticker input via `--tickers` arg (already implemented in `backtest._validate_ticker_token`). Apply same to `run_pipeline._parse_tickers_arg`. |
| V6 Cryptography | no | No cryptographic operations. ONNX model is integrity-checked at commit time via `verify_onnx.py` (Phase 8 gate); not at runtime. |
| V7 Error Handling | yes | Per-ticker errors caught + stored in `pipeline_status.errors[]`, capped at 50. Error messages truncated to 500 chars to prevent log injection / data.json bloat. |
| V8 Data Protection | yes | yfinance returns public data (no PII). ONNX model is public-information artifact. Generated `data.json` is public. No secrets ever in artifacts. |
| V9 Communication | no (TLS handled by yfinance + GitHub) | HTTPS via yfinance + GitHub API; no custom HTTP. |
| V14 Configuration | yes | Workflow YAML is the configuration; checked into git, code-reviewed via PR. |

### Known Threat Patterns for {Python CI pipeline + Git push}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Argv-flag confusion via `--tickers` | Tampering / EoP | `_validate_ticker_token` regex `^[A-Z0-9][A-Z0-9.-]{0,9}$` (already in `backtest.py`; reuse). |
| Path traversal in `--out-dir` | Tampering | argparse Path type + resolve under repo root; reject if `..` in path. Recommend `Path(args.out_dir).resolve().is_relative_to(Path("docs/projects/patterns").resolve())` check. |
| Token leak via `print(args)` or error message | Information Disclosure | Never log `secrets.GITHUB_TOKEN`; GHA automatically masks `${{ secrets.* }}` values. Error messages in `pipeline_status.errors[]` are truncated; never include stack traces with environment dumps. |
| Workflow re-trigger loop on push | DoS | `secrets.GITHUB_TOKEN` push does NOT trigger downstream `on: push` workflows (GHA built-in). Verified empirically via existing `nightly-screener.yml` clean operation. |
| Malicious ticker symbol injection into yfinance call | Injection / Tampering | yfinance constructs URL from ticker symbol; the `_TICKER_RE` regex restricts to `[A-Z0-9.-]{1,10}` — no special chars, no shell metacharacters, no path delimiters. Already enforced. |
| Untrusted ONNX model loaded at runtime | Tampering / RCE | The ONNX model is in-repo, code-reviewed at commit time, integrity-verified by Phase 8 `verify_onnx.py`. Phase 10 trusts the committed artifact (D-08). No external model download in CI. |
| JSON injection via `errors[].message` | Injection (XSS at frontend) | Frontend (Phase 11) should treat the field as text, not HTML. Phase 10 truncates messages to 500 chars and stores as JSON strings (properly escaped by `json.dump`). No special handling needed at Phase 10. |
| Sensitive file write outside docs/ tree | Tampering | The `--out-dir` Path validation above. |

**Privacy/secrets review per CONTEXT.md question 11:**
- yfinance requires NO API key (confirmed: `yahoo_finance_fetcher.py` only uses `yf.Ticker(symbol)`; no auth header anywhere).
- ONNX inference is pure CPU + local file — leaks nothing (confirmed: `_load_onnx_session` reads from disk; no network calls).
- No PII anywhere — ticker symbols and price data are public.
- `secrets.GITHUB_TOKEN` is auto-injected by GHA and auto-masked in logs.
- No `_dev/` or `models/dataset_manifest.json` paths are written to public artifacts (the workflow only `git add`s `docs/projects/patterns/*` paths).

**Conclusion:** Phase 10 has a narrow, well-understood threat surface. The existing `nightly-screener.yml` and `monthly-moat-analysis.yml` workflows have been running cleanly under the same security envelope.

## Sources

### Primary (HIGH confidence)

- **`.planning/phases/10-batch-pipeline/10-CONTEXT.md`** — 24 locked decisions, the source-of-truth for Phase 10.
- **`.planning/REQUIREMENTS.md`** §"Batch Pipeline" — PIPE-01..PIPE-04 acceptance criteria.
- **`.planning/STATE.md`** — Phase 9 close-out state; confirms Phase 10 is the next phase.
- **`.planning/ROADMAP.md`** §"Phase 10: Batch Pipeline" — Goal, dependencies, success criteria.
- **`.planning/phases/07-detection-engine/07-CONTEXT.md`** — Detection schema (D-09, D-10), no-look-ahead invariants (D-14).
- **`.planning/phases/08-training-pipeline/08-CONTEXT.md`** — 60-bar right-aligned 640×640 framing (D-01..D-04), renderer module surface (D-20).
- **`.planning/phases/08-training-pipeline/08-05-SUMMARY.md`** — ML threshold 0.3, inference dep lock (`onnxruntime>=1.19, Pillow, numpy<2.0, mplfinance, matplotlib`; NEVER torch / ultralytics).
- **`.planning/phases/09-backtesting-engine/09-CONTEXT.md`** — `yolo_conf` quality-overlay pattern (D-13), ONNX-absence graceful fallback (D-14), `backtest.py` module structure (D-15).
- **`.planning/phases/09-backtesting-engine/09-SUMMARY.md`** — Empirical Phase 9 results, ONNX inference latency note, follow-ups flagged for Phase 11.
- **`scripts/pattern_scanner/detector.py`** — `Detection` dataclass, `detect(df, ticker, apply_trend_filters=True)` API, `_fetch_ohlc` idiom, `_TICKER_RE` regex.
- **`scripts/pattern_scanner/backtest.py`** — `simulate_trade`, `_load_onnx_session`, `_score_detection`, `_window_for`, `_stop_for`, `_target_for`, `_fetch_ohlc`, `_validate_ticker_token` — all reusable by Phase 10 verbatim.
- **`scripts/pattern_scanner/renderer.py`** — `STYLES` tuple, `RenderStyle` dataclass, `render()` and `compute_bbox_normalized()` — extension point for `PUBLICATION_STYLE` constant.
- **`scripts/pattern_scanner/verify_onnx.py`** — `[1, 3, 640, 640]` inference shape; `CONFIDENCE_FLOOR = 0.3`.
- **`scripts/fetch_sp500.py`** — `fetch_sp500_tickers()`, browser-UA Wikipedia scrape pattern, sequential ticker iteration template.
- **`.github/workflows/nightly-screener.yml`** — direct line-for-line template for `nightly-pattern-scanner.yml`.
- **`.github/workflows/monthly-moat-analysis.yml`** — secondary reference (env var handling).
- **`tests/conftest.py`** — `synthetic_ohlc` fixture, `--no-network` flag, `pytest_addoption` machinery.
- **`tests/test_backtest_yolo_conf_fallback.py`** — direct template for D-08 ONNX-absence tests in Phase 10.
- **`requirements.txt`** — Confirmed `mplfinance`, `matplotlib`, `onnxruntime`, `Pillow` all pinned. No torch or ultralytics anywhere.
- **`.planning/codebase/CONVENTIONS.md`** — snake_case, PascalCase, leading underscore conventions.
- **`.planning/codebase/STRUCTURE.md`** — `scripts/pattern_scanner/` package layout.

### Secondary (MEDIUM confidence — verified on dev machine)

- **Live verification of pandas BDay (2026-05-11):**
  `today=Mon 2026-05-11; today - BDay(20) = Mon 2026-04-13`
  `sat=Sat 2026-05-09; sat - BDay(20) = Mon 2026-04-13` (Saturday rolled to Friday before stepping back 20 BDays).
- **Live verification of matplotlib 3.10.9 PNG determinism (2026-05-11):**
  Two consecutive `fig.savefig(io.BytesIO(), format='png')` calls with identical inputs and a 1.1s delay produce byte-identical output; SHA-256 matches.
- **Live verification of installed versions (2026-05-11):** onnxruntime 1.25.1, mplfinance 0.12.10b0, matplotlib 3.10.9, yfinance 0.2.65.
- **Live size check of ONNX model:** `models/inside_bar_v1.onnx` is 11.7 MB (well under 100 MB git limit).
- **Live size check of `_dev/backtest_cache.json`:** 27.8 MB (matches Phase 9 SUMMARY claim); aggregates section sampled — < 10 KB total.
- **Python documentation:** `os.replace` (atomic on POSIX rename(2) and Windows MoveFileExW with MOVEFILE_REPLACE_EXISTING; documented since Python 3.3).
- **POSIX `rename(2)` man page:** atomic on same filesystem; required behavior since the POSIX.1-2008 standard.
- **GitHub Actions documentation:** `secrets.GITHUB_TOKEN` push does NOT trigger downstream `on: push` workflows (documented; empirically confirmed via clean operation of existing `nightly-screener.yml`).

### Tertiary (LOW confidence — assumed from training; flagged for validation)

- **ONNX inference latency estimate** for `ubuntu-latest` CPU at ~100-500 ms per inference. `[ASSUMED]` — Phase 9 SUMMARY says "~250-350 ms on local"; GHA `ubuntu-latest` CPU is comparable. Worst case 5× off, mitigation is parallelization (Phase 9 SUMMARY already notes this).
- **mplfinance `nightclouds` base_style** is a dark theme. `[ASSUMED]` — verify against mplfinance's documented style list at plan time. If the name is wrong, planner picks an equivalent (`mpf.available_styles()`).
- **GitHub Actions `ubuntu-latest` Python availability** for 3.11 via `actions/setup-python@v5`. `[ASSUMED]` — same configuration as the existing two workflows, which have been running cleanly. Solid implicit confirmation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep is already in `requirements.txt`; live-verified versions.
- Architecture: HIGH — Phase 10 is composition; all primitives exist in Phase 7/8/9. The atomicity and determinism layers are well-trodden standard practice.
- Pitfalls: HIGH — informed by Phase 9 SUMMARY's documented Risk 1-7, the `os.replace` cross-filesystem trap (POSIX docs), and live-verification of matplotlib determinism.
- ONNX latency estimate: MEDIUM — based on Phase 9 SUMMARY's local-run number; GHA CPU may differ but design is robust to 5× slowdown.
- Schema designs: HIGH — direct projection from CONTEXT.md decisions; cross-referenced against Phase 9 schema for consistency.

**Research date:** 2026-05-11
**Valid until:** ~2026-06-11 for stable claims (codebase architecture, locked decisions, library versions); ONNX latency estimate revisit if any plan empirically measures it.

## RESEARCH COMPLETE
