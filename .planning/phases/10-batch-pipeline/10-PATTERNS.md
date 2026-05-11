# Phase 10: Batch Pipeline - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 13 (1 modified, 12 new — 1 orchestrator, 1 helper CLI, 1 workflow, 3 data files, 7 test files)
**Analogs found:** 12 / 13 (one new data shape — `stats.json` — has no direct analog; uses `data.json`'s atomic-write pattern)

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `scripts/pattern_scanner/run_pipeline.py` | orchestrator (pure core + CLI) | batch / request-response | `scripts/pattern_scanner/backtest.py` | exact (same role, same data flow, same module shape) |
| `scripts/pattern_scanner/export_aggregates.py` | one-shot CLI utility (pure projector + thin wrapper) | transform (read JSON → write JSON) | `scripts/pattern_scanner/verify_onnx.py` | role-match (standalone CLI; different I/O target) |
| `scripts/pattern_scanner/renderer.py` (MODIFIED) | renderer module | transform (df → PNG bytes) | self (additive change; coexists with `STYLES` tuple) | self-extension |
| `.github/workflows/nightly-pattern-scanner.yml` | CI workflow | event-driven (cron) | `.github/workflows/nightly-screener.yml` | exact (mirror line-for-line, 3 deltas) |
| `docs/projects/patterns/data.json` | nightly data artifact | output / static | `docs/projects/screener/data.json` | role-match (nightly-written committed data file with `updated_at` + `stocks[]` shape) |
| `docs/projects/patterns/stats.json` | nightly data artifact | output / static | `docs/projects/screener/data.json` (write pattern) + Phase 9 `aggregates` block shape | partial (new shape, but write idiom + aggregate keys both already exist) |
| `docs/projects/patterns/_backtest_aggregates.json` | one-shot committed data | input (read at runtime) | `models/dataset_manifest.json` (committed JSON sidecar) | role-match |
| `tests/test_run_pipeline_pending.py` | unit test (D-02 `_resolve_status`) | request-response | `tests/test_backtest_simulate_trade.py` | exact (test of simulate_trade wrapper) |
| `tests/test_run_pipeline_window.py` | unit test (D-01 BDay cutoff) | request-response | `tests/test_backtest_cutoff.py` | exact (cutoff-filter test) |
| `tests/test_run_pipeline_atomic.py` | unit test (D-17 `_atomic_write_json`) | file I/O | (no direct analog — new pattern; `tmp_path` fixture is stdlib pytest) | new |
| `tests/test_run_pipeline_charts.py` | unit test (D-15 stale cleanup + determinism) | file I/O | `tests/test_renderer.py` | role-match (render output assertions) |
| `tests/test_run_pipeline_onnx_fallback.py` | unit test (D-08 ONNX-absence) | request-response | `tests/test_backtest_yolo_conf_fallback.py` | exact (template — line-for-line shape) |
| `tests/test_run_pipeline_main.py` | unit test (D-16 95% threshold + smoke) | orchestrator-level | `tests/test_backtest_cli.py` | role-match (calls `main(argv)` with monkeypatched I/O) |
| `tests/test_run_pipeline_stats.py` | unit test (D-11 fallback chain) | transform | `tests/test_backtest_aggregate.py` | role-match (groupby/aggregate semantics on records) |

---

## Pattern Assignments

### `scripts/pattern_scanner/run_pipeline.py` (orchestrator, batch)

**Analog:** `scripts/pattern_scanner/backtest.py`

The Phase 9 backtester is the closest structural twin. Phase 10's `run_pipeline.py` re-uses **half its public symbols verbatim** (`simulate_trade`, `_load_onnx_session`, `_score_detection`, `_window_for`, `_stop_for`, `_target_for`, `RATE_LIMIT_SLEEP`, `ONNX_PATH`) and mirrors its `main(argv)` orchestration loop with three substantive deltas: (a) ~6-month fetch instead of 10y, (b) 20-business-day window filter on `confirmation_date` before resolution, (c) atomic writes + chart rendering + stale-PNG cleanup at the end.

**Module header / imports** (`backtest.py` lines 1-39 — copy verbatim, adjust module docstring + `DEFAULT_OUT`):

```python
"""Inside-bar-spring backtester (Phase 9).

Pure-function core + thin CLI wrapper.
See .planning/phases/09-backtesting-engine/09-CONTEXT.md for D-01..D-17.
"""
from __future__ import annotations

import argparse
import io
import json
import time
import warnings
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Callable

import pandas as pd

# Note: yfinance is imported lazily inside _fetch_ohlc to mirror
# detector._fetch_ohlc / generate_training_data._fetch_ohlc.
from scripts.fetch_sp500 import fetch_sp500_tickers
from scripts.pattern_scanner.detector import Detection, _TICKER_RE, detect
from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF

RATE_LIMIT_SLEEP = 0.5  # seconds between yfinance fetches; matches gen_training_data L65
```

Phase 10 deltas: drop `split_config` (not used live); add `from scripts.pattern_scanner.backtest import simulate_trade, _stop_for, _target_for, _load_onnx_session, _score_detection, _window_for, ONNX_PATH`; add `from pandas.tseries.offsets import BDay`; add `import os, uuid` for atomic-write + run_id; add `from scripts.pattern_scanner.renderer import render, PUBLICATION_STYLE` (the new style key from the renderer modification).

**`_fetch_ohlc` test seam** (`backtest.py` lines 280-291 — copy verbatim, change `period` default to `"6mo"`):

```python
def _fetch_ohlc(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Fetch daily OHLC via yfinance with auto_adjust=True. Lazy import for testability.

    Mirrors generate_training_data._fetch_ohlc / detector._fetch_ohlc byte-for-byte.
    """
    import yfinance as yf  # noqa: WPS433 — deferred by design

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df
```

Phase 10 deltas: change default `period="6mo"` (D-03); same function name + signature so existing monkeypatch idiom (`monkeypatch.setattr(run_pipeline_mod, "_fetch_ohlc", lambda t, period="6mo": df)`) works unchanged.

**Per-ticker progress loop** (`backtest.py` lines 559-580 — copy verbatim, replace inner body):

```python
total = len(tickers)
filtered_records: list[dict] = []
unfiltered_records: list[dict] = []

for i, ticker in enumerate(tickers, start=1):
    try:
        df = _fetch_ohlc(ticker)
        if len(df) < 60:
            print(f"[{i}/{total}] {ticker}: insufficient history ({len(df)} bars) — skip")
        else:
            # Single detect() call — RESEARCH §Filter ablation.
            all_dets = detect(df, ticker, apply_trend_filters=False)
            f_dets = [d for d in all_dets if _is_filtered(d)]
            f_recs = [_build_record(d, df, sess=sess) for d in f_dets]
            u_recs = [_build_record(d, df, sess=sess) for d in all_dets]
            filtered_records.extend(f_recs)
            unfiltered_records.extend(u_recs)
            print(f"[{i}/{total}] {ticker}: filtered={len(f_recs)} unfiltered={len(u_recs)}")
    except Exception as exc:  # broad except — match gen_training_data.py L224-227
        print(f"[{i}/{total}] {ticker}: unexpected error — {exc}")
    if i < total:
        time.sleep(RATE_LIMIT_SLEEP)
```

Phase 10 deltas:
- `detect(df, ticker)` with default `apply_trend_filters=True` (D-04 — filtered only; do NOT call with `apply_trend_filters=False`).
- After detect: filter by window — `dets = [d for d in dets if pd.Timestamp(d.confirmation_date) >= cutoff]`.
- Inside per-detection loop: build record via `_resolve_status(df, d)` (the new D-02 wrapper); attach `rec["yolo_conf"] = _score_detection(_window_for(d, df), sess)`; render via `_render_publication_chart(df, d, out_dir)` and set `rec["chart_path"] = f"charts/{rec['ticker']}_{rec['confirmation_date']}.png"`.
- On per-ticker exception: append `{ticker, stage, message, timestamp}` to `errors[]` and increment `failed`; on success increment `succeeded`. (Phase 9 only prints — Phase 10 must accumulate structured errors per D-16.)

**ONNX session — load once at process start** (`backtest.py` lines 555-557 — copy verbatim, drop `--no-onnx` flag):

```python
# Plan 09-03: load ONNX session ONCE per run (RESEARCH §Pattern 3).
# --no-onnx bypasses session loading entirely (no warning, no session object).
sess = None if args.no_onnx else _load_onnx_session(ONNX_PATH)
```

Phase 10 deltas: drop `--no-onnx` (the live pipeline always tries; D-08 graceful-absence covers the missing-model case).

**`_score_detection` per-detection** (`backtest.py` lines 406-449 — DO NOT REIMPLEMENT; **import and reuse verbatim**):

The Phase 9 implementation already covers: (a) `sess is None` → returns `None` (D-08); (b) `window is None` for short history → returns `None`; (c) inference-level exception on a single window → `warnings.warn` + return `None` without aborting the run (Pitfall 5). Reuse via `from scripts.pattern_scanner.backtest import _score_detection`.

**CLI argparse shape** (`backtest.py` lines 533-548 — adapt: drop `--seed` + `--no-onnx`, add `--window-days` + `--out-dir`):

```python
parser = argparse.ArgumentParser(
    description="Backtest the inside bar spring strategy across the S&P 500."
)
parser.add_argument("--seed", type=int, required=True, ...)
parser.add_argument("--limit", type=int, default=None,
                    help="Process only the first N tickers (smoke-test).")
parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="Output JSON path.")
parser.add_argument("--no-onnx", action="store_true", ...)
parser.add_argument("--tickers", type=_parse_tickers_arg, default="all",
                    help="'all' for full S&P 500, or comma-separated tokens "
                         "(validated against _TICKER_RE before any yfinance call).")
```

Phase 10 final shape (per D-20):
```python
parser.add_argument("--tickers", type=_parse_tickers_arg, default="all")
parser.add_argument("--limit", type=int, default=None)
parser.add_argument("--window-days", type=int, default=20)
parser.add_argument("--out-dir", type=Path, default=Path("docs/projects/patterns"))
```

Reuse `_parse_tickers_arg` + `_validate_ticker_token` from `backtest.py` lines 302-319 verbatim.

**Atomic JSON write** (new pattern — no direct analog in `backtest.py`, which uses plain `with out_path.open("w")` at L601-603):

```python
def _atomic_write_json(path: Path, obj: dict) -> None:
    """Write JSON atomically. Reader sees the old file or the new file, never partial."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())  # hygiene; not load-bearing for atomicity
    os.replace(tmp, path)
```

(RESEARCH Example 2 lines 603-617. Per RESEARCH §"Anti-Patterns to Avoid" line 440: never put `tmp` in a different filesystem.)

**`_resolve_status` wrapper for `pending` state** (D-02 — the wrapper that distinguishes Phase 10 from Phase 9):

Patterned on Phase 9's `simulate_trade` lines 78-95 (the `entry_idx >= len(df)` branch is the exact code-location Phase 9 calls "open with risk=0"; Phase 10 rebrands this slice as `pending` and returns null-valued trade fields). The wrapper appears verbatim in RESEARCH lines 391-427.

---

### `scripts/pattern_scanner/export_aggregates.py` (one-shot CLI, transform)

**Analog:** `scripts/pattern_scanner/verify_onnx.py`

This file is a one-shot developer tool — runs locally once, output committed, never re-run in CI. The closest analog is `verify_onnx.py` (standalone CLI module, pure-function core, `main(argv)` entry, no test scaffold needed).

**Module shell pattern** (`verify_onnx.py` lines 110-167 — adapt):

```python
def main(argv=None) -> int:
    if not ONNX_PATH.exists():
        print(f"[verify] FAIL: {ONNX_PATH} does not exist", file=sys.stderr)
        return 2
    fixtures = sorted(FIXTURES_DIR.glob("known_positive_*.png"))
    if not fixtures:
        print(f"[verify] FAIL: no fixtures in {FIXTURES_DIR}", file=sys.stderr)
        return 3
    ...
    return 0 if any_pass else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Phase 10 final shape (RESEARCH lines 913-947 — copy verbatim, the recommended skeleton is small and self-contained):

```python
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

**Aggregates input shape** comes from `backtest.aggregate()` (`backtest.py` lines 233-276) which is already in the committed cache `_dev/backtest_cache.json` under `strategies[<strategy_name>][<sample>]["aggregates"]`. No transformation needed beyond plucking that subtree — projection is structural, not computational.

---

### `scripts/pattern_scanner/renderer.py` (MODIFIED — add publication style)

**Analog:** self (additive change preserving Phase 7 / 8 / 9 callers).

**Existing `STYLES` tuple** (lines 65-69 — leave untouched; backtest._score_detection uses STYLES[0]):

```python
STYLES: Tuple[RenderStyle, ...] = (
    RenderStyle("style_a", "yahoo",   (8.0, 6.0), 100, 0.6, "#ffffff"),
    RenderStyle("style_b", "charles", (10.0, 7.0), 120, 0.5, "#fafafa"),
    RenderStyle("style_c", "classic", (6.0, 5.0),  90, 0.7, "#f5f5f5"),
)
```

**Phase 10 addition** (sibling constant per RESEARCH Pattern 3 / A7 / line 342 recommendation):

```python
# ── Phase 10 publication style (D-14) ───────────────────────────────────────
# Used exclusively by run_pipeline._render_publication_chart for the live screener.
# NOT in STYLES tuple — backtest._score_detection (Phase 9) and the
# generate_training_data randomized style pick (Phase 8) reference STYLES[0..2]
# directly; mutating STYLES would break those call-sites.
PUBLICATION_STYLE = RenderStyle(
    name="publication",
    base_style="nightclouds",   # mplfinance built-in dark theme (RESEARCH A5 — planner verify)
    figsize=(8.0, 5.0),         # 4:3 horizontal — wider than training square
    dpi=150,                    # higher DPI per D-14 ("~150")
    candle_width=0.6,
    facecolor="#0d1117",        # GitHub dark theme tone — matches portfolio palette
)
```

**Existing `_validate_frame`** (lines 73-80) **REQUIRES `len(df) == 60`**. The publication renderer in `run_pipeline.py` must therefore slice a 60-bar right-aligned window before calling `render()` — same idiom as `generate_training_data._slice_window` (lines 127-135):

```python
def _slice_window(df: pd.DataFrame, conf_idx: int) -> pd.DataFrame | None:
    """60-bar window ending AT confirmation bar (D-03 right-aligned).

    Returns None if the confirmation index has insufficient leading history.
    """
    start = conf_idx - (WINDOW_SIZE - 1)
    if start < 0:
        return None
    return df.iloc[start:conf_idx + 1]
```

**Bbox overlay** (D-13 algorithmic 5-bar cluster): `renderer.compute_bbox_normalized` (lines 140-235) already implements `returnfig=True` axis-extraction in YOLO-normalized coords. Phase 10's `_render_publication_chart` will NOT call `compute_bbox_normalized` (which returns YOLO float coords for label files). Instead it will replicate the `returnfig=True` pattern from lines 181-194 to grab the axis, then draw a `matplotlib.patches.Rectangle` in data coords using the geometry from RESEARCH lines 366-368:

```python
# Geometry (D-13): from Detection.bars (5-bar cluster).
x0_data = mother_idx_in_window - PUBLICATION_STYLE.candle_width / 2
x1_data = confirmation_idx_in_window + PUBLICATION_STYLE.candle_width / 2
y0_data = min(b["low"] for b in detection.bars)
y1_data = max(b["high"] for b in detection.bars)
```

**Memory pitfall (Pitfall 4 / Pitfall in RESEARCH line 522):** Always call `plt.close("all")` after each render — already done at line 128 of existing `renderer.render`. The new publication path must mirror this.

---

### `.github/workflows/nightly-pattern-scanner.yml` (CI workflow, cron)

**Analog:** `.github/workflows/nightly-screener.yml`

**Existing file** (line-for-line template — 35 lines total):

```yaml
name: Nightly S&P 500 Screener Data

on:
  schedule:
    - cron: '0 6 * * 1-5'  # 06:00 UTC weekdays only (after US market close)
  workflow_dispatch:         # manual trigger for testing

permissions:
  contents: write            # required for git push with GITHUB_TOKEN

jobs:
  fetch-data:
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

      - name: Fetch S&P 500 data
        run: python scripts/fetch_sp500.py

      - name: Commit updated data.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/projects/screener/data.json
          git diff --staged --quiet || git commit -m "chore: nightly S&P 500 screener data update"
          git push
```

**Phase 10 deltas (3 lines):**

| Line | screener.yml | pattern-scanner.yml |
|------|--------------|---------------------|
| `name:` | `Nightly S&P 500 Screener Data` | `Nightly Pattern Scanner Data` |
| `cron:` | `'0 6 * * 1-5'` | `'0 7 * * 1-5'` (D-23: 1h offset) |
| script invocation | `python scripts/fetch_sp500.py` | `python -m scripts.pattern_scanner.run_pipeline --tickers all --window-days 20 --out-dir docs/projects/patterns` |
| `git add` paths | `docs/projects/screener/data.json` | `docs/projects/patterns/data.json docs/projects/patterns/stats.json docs/projects/patterns/charts/` |
| commit msg | `chore: nightly S&P 500 screener data update` | `chore: nightly pattern scanner data update` |
| `jobs:` key | `fetch-data` | `pattern-scanner` |

Final file in RESEARCH Example 5 (lines 671-710).

**Secondary reference** `.github/workflows/monthly-moat-analysis.yml` confirms the same `actions/checkout@v4` + `setup-python@v5` + `permissions: contents: write` block is the universal pattern across the three workflows in this repo. No env vars needed (moat uses `OPENAI_API_KEY`; pattern scanner needs none).

---

### `docs/projects/patterns/data.json` (output, static nightly artifact)

**Analog:** `docs/projects/screener/data.json`

**Existing screener shape** (header):

```json
{
  "updated_at": "2026-05-08T07:41:50Z",
  "stocks": [
    { "ticker": "MMM", "company_name": "3M Company", "sector": "Industrials", ... }
  ]
}
```

**Phase 10 shape** mirrors the convention (top-level `generated_at` + array of records) and extends with `schema_version`, `pipeline_status`, and per-row `simulate_trade` fields. Full shape in RESEARCH lines 781-826. Field-by-field provenance:

| Field | Source |
|-------|--------|
| `schema_version: 1` | new (Phase 10 — per Claude's Discretion recommendation) |
| `generated_at` | `datetime.now(timezone.utc).isoformat()` — mirrors `backtest.py` L587 |
| `window_days`, `as_of_date` | new (D-01 self-documentation) |
| `pipeline_status` | new (D-16) |
| `detections[].ticker / confirmation_date / confirmation_type / is_spring / bars` | `Detection` dataclass from `detector.py` L288-302; numeric fields already `float()`-coerced and dates `.strftime("%Y-%m-%d")` |
| `detections[].status / entry_* / stop_price / target_price / risk / exit_* / hold_days / R` | `simulate_trade()` from `backtest.py` L83-95 (and the seven other return sites in the same function). Phase 10 renames `exit_reason` → `status` at the run_pipeline boundary (RESEARCH line 426: `rec["status"] = rec.pop("exit_reason")`) |
| `detections[].yolo_conf` | `_score_detection()` from `backtest.py` L406-449 (returns `float \| None`) |
| `detections[].chart_path` | new — relative path `"charts/{TICKER}_{DATE}.png"` (Pitfall 6 — never absolute) |
| `detections[].company_name / sector` | enrich from `docs/projects/screener/data.json` (RESEARCH Open Question 3 recommendation); fall back to `ticker` if screener file absent |
| `detections[].current_price` | `float(df.iloc[-1]["Close"])` — last close from the same fetched OHLC frame |
| `detections[].filters` | `Detection.filters` dict from `detector.py` L296-300 (already `bool()`-coerced) |

---

### `docs/projects/patterns/stats.json` (output, static nightly artifact)

**Analog:** Phase 9 cache aggregates shape (`backtest._sample_block` lines 472-483) + atomic-write pattern from `data.json`.

**Phase 9 source shape** (input — read from `_backtest_aggregates.json`):

```python
"aggregates": {
    "all": all_cell,
    "by_confirmation_type": aggregate(records, ["confirmation_type"]),
    "by_is_spring": aggregate(records, ["is_spring"]),
    "by_type_x_spring": aggregate(records, ["confirmation_type", "is_spring"]),
}
```

Each cell has the keys from `aggregate()` lines 266-275: `{n, n_resolved, win_rate, avg_return_r, median_hold_days, target_count, stop_count, open_count}`.

**Phase 10 output shape** (RESEARCH lines 838-865 — full target). Two transformations vs the raw input:

1. **Key rename** (RESEARCH line 868): Phase 9 `aggregate` uses `_record["is_spring"]` directly which Python str-coerces to `"True"` / `"False"` — so cross-keys are `"pin_True"` / `"mark_up_False"`. Phase 10 normalizes to `"pin_spring"` / `"mark_up_extended"` in `build_stats_json` before writing.
2. **Fallback metadata** (D-11): emit `fallback_order: ["by_type_x_spring", "by_confirmation_type", "all"]` and `n_floor: 10` so the frontend can resolve sparse cells (the chain itself is walked client-side per RESEARCH Open Question 1).

**Atomic write protocol** — same `_atomic_write_json` helper used for `data.json` (no separate code path).

---

### `docs/projects/patterns/_backtest_aggregates.json` (input, committed once)

**Analog:** `models/dataset_manifest.json` (Phase 8 — small committed JSON sidecar generated by an offline helper).

**Existing dataset_manifest pattern** (`generate_training_data.py` lines 313-329):

```python
manifest = {
    "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "seed": args.seed,
    "tickers": tickers,
    ...
}
(args.dataset_root / "dataset_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True)
)
(args.models_root / "dataset_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True)
)
```

**Phase 10 file** is produced by `export_aggregates.py` once at plan time. Shape in RESEARCH lines 875-890. Production rule:
- `json.dumps(out, indent=2, sort_keys=True)` (matches `dataset_manifest.json` formatting)
- Committed to repo
- Refreshed only when the Phase 9 backtest is rerun (manual)

---

### `tests/test_run_pipeline_pending.py` (D-02 wrapper)

**Analog:** `tests/test_backtest_simulate_trade.py` (the canonical test of `simulate_trade`).

**Pattern excerpt** from `tests/test_backtest_aggregate.py` lines 7-26 (the synthetic-record fixture style — small inline records, no fixture file):

```python
def _record(ct: str, is_spring: bool, exit_reason: str, R: float, hold_days: int) -> dict:
    return {
        "confirmation_type": ct,
        "is_spring": is_spring,
        "exit_reason": exit_reason,
        ...
    }

@pytest.fixture
def records():
    return [
        _record("pin", True, "target", 2.0, 5),
        ...
    ]
```

Phase 10 test reuses the `synthetic_ohlc` fixture from `tests/conftest.py` (lines 46-66) for the DataFrame, and a small `@dataclass(frozen=True)` `FakeDet` stand-in for `Detection` (RESEARCH Example 6 lines 715-742 — copy verbatim).

Required tests (per CONTEXT D-21):
- `test_resolve_status_pending` — entry_idx >= len(df) → `status="pending"` + null trade fields.
- `test_resolve_status_delegates_to_simulate_trade` — sanity check that the wrapper returns Phase 9's 8 fields when entry is possible.

---

### `tests/test_run_pipeline_window.py` (D-01 BDay cutoff)

**Analog:** `tests/test_backtest_cutoff.py` (cutoff-filter unit test).

The test asserts that detections with `confirmation_date < today - BDay(window_days)` are dropped. Pattern: build a list of synthetic `Detection`-shaped records with varying `confirmation_date` strings, pass through the `_window_filter`, assert membership. No fixture needed beyond a fixed `today` constant.

Required test: `test_window_filter_drops_old_detections`.

---

### `tests/test_run_pipeline_atomic.py` (D-17 atomic write)

**Analog:** no direct analog — new pattern (`os.replace` semantics). Uses stdlib `tmp_path` pytest fixture.

**Pattern excerpt** (RESEARCH lines 1086-1100):

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

    # 3. Post-condition: final exists, is valid JSON, and the .tmp is gone
    assert final.exists()
    assert json.loads(final.read_text())["pipeline_status"]["completed"] is True
    assert not tmp.exists()
```

Required test: `test_atomic_write_protocol`.

---

### `tests/test_run_pipeline_charts.py` (D-15 stale cleanup + determinism)

**Analog:** `tests/test_renderer.py` (already exercises `render()` output byte-shape).

**Pattern excerpt** (RESEARCH Example 7 lines 752-773 — deterministic render test):

```python
def test_publication_render_is_deterministic(tmp_path, synthetic_ohlc):
    """D-15 prerequisite: same input → byte-identical PNG."""
    rows = [(100 + i, 105 + i, 99 + i, 102 + i) for i in range(60)]
    df = synthetic_ohlc(rows)
    ...
    _render_publication_chart(df, fake, p1)
    _render_publication_chart(df, fake, p2)
    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
    assert h1 == h2
```

**Set-difference cleanup test** — populate `tmp_path / "charts"` with three files (`AAPL_2024-01-01.png`, `MSFT_2024-01-01.png`, `STALE_2023-01-01.png`); call `_cleanup_stale_pngs(charts_dir, expected={"AAPL_2024-01-01.png", "MSFT_2024-01-01.png"})`; assert `STALE_2023-01-01.png` is gone and the other two remain. Helper signature from RESEARCH Example 4 lines 653-666.

Required tests: `test_stale_png_cleanup_keeps_current_drops_old`, `test_publication_render_is_deterministic`, optional `test_render_writes_png`.

---

### `tests/test_run_pipeline_onnx_fallback.py` (D-08)

**Analog:** `tests/test_backtest_yolo_conf_fallback.py` — **direct line-for-line template** (D-08 in CONTEXT explicitly names this file).

**Reusable fixture pattern** (lines 19-32):

```python
@pytest.fixture
def patched_environment(monkeypatch, tmp_path, synthetic_ohlc):
    """Single ticker producing >= 1 detection so we have records to inspect."""
    rows, *_ = _spring_setup_rows()
    df = synthetic_ohlc(rows, start_date="2024-02-01")
    monkeypatch.setattr(backtest_mod, "_load_tickers", lambda limit: ["TEST"])
    monkeypatch.setattr(backtest_mod, "_fetch_ohlc", lambda t, period="10y": df)
    monkeypatch.setattr(backtest_mod.time, "sleep", lambda *a, **kw: None)
    return tmp_path / "backtest_cache.json"
```

**Negative-path test pattern** (lines 43-62):

```python
def test_yolo_conf_null_when_onnx_missing(patched_environment, monkeypatch):
    """D-14: missing ONNX file -> single UserWarning + every record yolo_conf=None."""
    out_path = patched_environment
    monkeypatch.setattr(backtest_mod, "ONNX_PATH", Path("/nonexistent/inside_bar_v1.onnx"))

    with pytest.warns(UserWarning, match="ONNX model not found"):
        rc = backtest_mod.main(["--seed", "42", "--tickers", "all", "--out", str(out_path)])
    assert rc == 0

    cache = json.loads(out_path.read_text())
    records = _all_records(cache)
    assert len(records) >= 1, "Test fixture must produce at least one detection"
    for rec in records:
        assert rec["yolo_conf"] is None
```

Phase 10 deltas: import `run_pipeline as run_pipeline_mod` instead of `backtest_mod`; monkeypatch `run_pipeline_mod.ONNX_PATH` (or `backtest_mod.ONNX_PATH` if Phase 10 re-exports); fetch monkeypatch uses `period="6mo"`; assert iterates `data.json["detections"][*]["yolo_conf"] is None`. Use `start_date="2026-04-01"` (within the 20-BDay window from a 2026-05 run-date) so the fixture's detection survives the window filter.

Required test: `test_yolo_conf_null_when_onnx_missing`. May also include the positive-path test (mocked session → float in [0, 1]) — same pattern as lines 90-118 of the analog.

---

### `tests/test_run_pipeline_main.py` (D-16 95% threshold + smoke)

**Analog:** `tests/test_backtest_cli.py` (orchestrator-level `main(argv)` test) + same monkeypatch idiom as `test_backtest_yolo_conf_fallback.py`.

**Strategy**: monkeypatch `_load_tickers` to return e.g. `["A", "B", ..., "T"]` (20 tickers); make `_fetch_ohlc` raise for 2 specific tickers (10% failure → completed=false) or 1 ticker (5% failure → completed=true); assert `data.json["pipeline_status"]["completed"]` matches expectation. The 95% threshold is computed against `len(tickers)` not the literal 503 — so smaller test fixtures work.

Required tests: `test_pipeline_status_completed_true_when_above_95pct`, `test_pipeline_status_completed_false_when_below_95pct`, optional `test_main_smoke_with_synthetic_ohlc`.

---

### `tests/test_run_pipeline_stats.py` (D-11 fallback chain)

**Analog:** `tests/test_backtest_aggregate.py` (groupby/aggregate semantics on records).

**Pattern excerpt** (`tests/test_backtest_aggregate.py` lines 7-50):

```python
def _record(ct: str, is_spring: bool, exit_reason: str, R: float, hold_days: int) -> dict:
    return {"confirmation_type": ct, "is_spring": is_spring, ...}

def test_aggregate_groupings(records):
    all_slice = aggregate(records, [])
    assert set(all_slice.keys()) == {"all"}
    ...
```

Phase 10 tests target `build_stats_json(aggregates: dict) -> dict` (D-19 public API) plus the fallback resolver. The unit test passes a synthetic `aggregates` dict with:
- `by_type_x_spring["pin_spring"] = {n: 5, ...}` (sparse — below `n_floor=10`)
- `by_confirmation_type["pin"] = {n: 17, ...}` (sufficient)

Assertion: when frontend (or `build_stats_json`'s helper) resolves `("pin", True)`, it walks `by_type_x_spring → by_confirmation_type` and returns the `"pin"` cell. The second test sets both sparse and asserts fallback to `"all"`.

Required tests: `test_stats_json_falls_back_to_by_confirmation_type_when_sparse`, `test_stats_json_falls_back_to_all_when_both_sparse`.

---

## Shared Patterns

### 1. Lazy `import yfinance` inside `_fetch_ohlc`

**Source:** `backtest.py` lines 280-291 (and identical in `detector._fetch_ohlc`, `generate_training_data._fetch_ohlc`).

**Apply to:** `scripts/pattern_scanner/run_pipeline.py` only.

Justification: keeps the module importable without yfinance installed (test seam — tests monkeypatch the function and never trigger the import). Phase 10 uses the identical idiom.

```python
def _fetch_ohlc(ticker: str, period: str = "6mo") -> pd.DataFrame:
    import yfinance as yf  # noqa: WPS433 — deferred by design
    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df
```

### 2. Float coercion + ISO date strings at every record-construction site

**Source:** `backtest.py` lines 41-55 (`_identity`, `_iso`) plus every `return {…}` site in `simulate_trade()`.

**Apply to:** every dict construction in `run_pipeline.py` that ends up in `data.json` or `stats.json`. Phase 9 Risk 1 / Risk 2 mitigation pattern.

```python
def _identity(detection: Detection) -> dict:
    return {
        "ticker": str(detection.ticker),
        "confirmation_date": str(detection.confirmation_date),
        "confirmation_type": str(detection.confirmation_type),
        "is_spring": bool(detection.is_spring),
        ...
    }

def _iso(ts) -> str:
    """Coerce a pandas.Timestamp (or datetime-like) to YYYY-MM-DD string."""
    return ts.strftime("%Y-%m-%d")
```

Plus `json.dump(obj, f, indent=2, sort_keys=True, default=str)` at every JSON write site.

### 3. Per-ticker progress logging `[i/total] TICKER: ...`

**Source:** `generate_training_data.py` line 223, `backtest.py` lines 567 / 576 / 578.

**Apply to:** `run_pipeline.py` orchestration loop.

```python
print(f"[{i}/{total}] {ticker}: filtered={len(f_recs)} unfiltered={len(u_recs)}")
print(f"[{i}/{total}] {ticker}: insufficient history ({len(df)} bars) — skip")
print(f"[{i}/{total}] {ticker}: unexpected error — {exc}")
```

Phase 10 variant: `print(f"[{i}/{total}] {ticker}: {len(dets_in_window)} in-window")`.

### 4. `RATE_LIMIT_SLEEP = 0.5` between yfinance fetches

**Source:** `backtest.py` line 33, `generate_training_data.py` line 65 (and original `fetch_sp500.py`).

**Apply to:** `run_pipeline.py` per-ticker loop tail.

```python
RATE_LIMIT_SLEEP = 0.5  # seconds between yfinance fetches
...
if i < total:
    time.sleep(RATE_LIMIT_SLEEP)
```

Test seam: `monkeypatch.setattr(run_pipeline_mod.time, "sleep", lambda *a, **kw: None)` (mirrors `test_backtest_yolo_conf_fallback.py` line 31).

### 5. Broad-except per-ticker error containment

**Source:** `generate_training_data.py` lines 224-227, `backtest.py` lines 577-578.

**Apply to:** every per-ticker iteration in `run_pipeline.py`. Phase 10 extends with `errors[]` accumulation (D-16):

```python
except Exception as exc:  # broad except — match gen_training_data.py L224-227
    failed += 1
    errors.append({
        "ticker": ticker,
        "stage": "fetch_or_detect",
        "message": str(exc)[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    print(f"[{i}/{total}] {ticker}: ERROR — {exc}")
```

### 6. Single-call `_load_onnx_session` at process start; reuse `_score_detection` per detection

**Source:** `backtest.py` lines 360-449 + lines 555-557 (load) + line 468 (use).

**Apply to:** `run_pipeline.py` main loop. **Reuse via import — do not reimplement.**

```python
from scripts.pattern_scanner.backtest import _load_onnx_session, _score_detection, _window_for, ONNX_PATH
sess = _load_onnx_session(ONNX_PATH)  # may be None → yolo_conf=null on every record (D-08)
...
rec["yolo_conf"] = _score_detection(_window_for(d, df), sess)
```

The Phase 9 implementation already covers all three failure modes (model absent / onnxruntime absent / single-window inference exception) with the right warning-once-then-null semantics. **Do not duplicate.**

### 7. `_TICKER_RE` validation for `--tickers` CLI flag

**Source:** `backtest.py` lines 302-319 + `detector.py` `_TICKER_RE`.

**Apply to:** `run_pipeline.py` CLI argparse.

```python
def _validate_ticker_token(token: str) -> str:
    upper = token.strip().upper()
    if not _TICKER_RE.fullmatch(upper):
        raise argparse.ArgumentTypeError(f"Invalid ticker token {token!r}: must match {_TICKER_RE.pattern}")
    return upper

def _parse_tickers_arg(value: str) -> str | list[str]:
    if value == "all":
        return "all"
    return [_validate_ticker_token(tok) for tok in value.split(",")]
```

### 8. matplotlib `plt.close("all")` after every render

**Source:** `renderer.py` line 128 (and noted at RESEARCH Pitfall 4 / line 522).

**Apply to:** every new render path added in `_render_publication_chart`. Memory leaks unbounded otherwise.

### 9. Synthetic OHLC test fixture + `_fetch_ohlc` monkeypatch

**Source:** `tests/conftest.py` lines 46-66 (`synthetic_ohlc` fixture) + `tests/test_backtest_yolo_conf_fallback.py` lines 19-32 (monkeypatch idiom).

**Apply to:** all 7 new test files in `tests/test_run_pipeline_*.py`. No new conftest.py needed.

```python
@pytest.fixture
def synthetic_ohlc():
    def _build(rows, start_date="2024-01-01"):
        idx = pd.bdate_range(start=start_date, periods=len(rows))
        return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)
    return _build
```

### 10. GHA bot identity + commit-and-push idiom

**Source:** `.github/workflows/nightly-screener.yml` lines 29-35 (and identical in `monthly-moat-analysis.yml`).

**Apply to:** `.github/workflows/nightly-pattern-scanner.yml`.

```yaml
- name: Commit updated <ARTIFACT>
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add <PATHS>
    git diff --staged --quiet || git commit -m "chore: <MESSAGE>"
    git push
```

**No Co-Authored-By trailer** — D-24 explicit: the user's git-attribution-guard rule applies to developer commits, not GitHub-bot CI commits.

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| (none — every file has at least one in-repo analog or established pattern reference) | — | — |

**Note:** `tests/test_run_pipeline_atomic.py` has no per-test analog, but the testing idiom (`tmp_path` pytest fixture + assert post-conditions on file state) is universal stdlib pytest and needs no codebase reference beyond the RESEARCH Example 7 snippet (lines 1086-1100).

---

## Metadata

**Analog search scope:**
- `scripts/pattern_scanner/*.py` (8 files; 1924 LOC)
- `scripts/fetch_sp500.py` (referenced via import only)
- `.github/workflows/*.yml` (2 files; 73 LOC)
- `tests/test_*.py` (12 files — focus on `test_backtest_*.py` and `test_renderer.py`)
- `tests/conftest.py` (shared fixtures)
- `docs/projects/screener/data.json` (output shape reference; header only)
- `models/dataset_manifest.json` (committed-JSON-sidecar pattern reference, by description)

**Files scanned (full Read):** 7 — `backtest.py` (610 LOC), `renderer.py` (260 LOC), `nightly-screener.yml` (35 LOC), `monthly-moat-analysis.yml` (37 LOC), `verify_onnx.py` (171 LOC), `test_backtest_yolo_conf_fallback.py` (118 LOC), `conftest.py` (66 LOC).
**Files partial Read:** 3 — `detector.py` lines 240-350 (Detection construction); `generate_training_data.py` lines 1-344 (chunked); `test_backtest_aggregate.py` lines 1-60.

**Pattern extraction date:** 2026-05-11

---

*Phase: 10-batch-pipeline*
*Pattern map ready for planning.*
