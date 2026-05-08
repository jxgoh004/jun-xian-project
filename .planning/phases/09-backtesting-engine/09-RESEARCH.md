# Phase 9: Backtesting Engine - Research

**Researched:** 2026-05-09
**Domain:** Forward-walk backtest simulation, R-multiple statistics, ONNX overlay scoring
**Confidence:** HIGH on stack/patterns/pitfalls (all upstream evidence is verified in-repo); MEDIUM on cutoff arithmetic (depends on yfinance availability); LOW on ONNX wall-clock per-detection latency (not benchmarked in Phase 8).

## Summary

Phase 9 extends a fully-locked architecture: Phase 7 ships a stable `detect()` with the `apply_trend_filters` kwarg, Phase 8 ships a renderer + ONNX session contract + `split_config.TRAIN_TEST_CUTOFF`, and the test scaffold (`synthetic_ohlc` fixture + monkeypatched `_fetch_ohlc`) is already battle-tested across 30 passing pytest cases. The phase is essentially "wire three known components (`detect` → `simulate_trade` → `aggregate`) into a deterministic JSON writer, with an ONNX overlay loop." The real planning risks are not in the algorithmic core but in three places: (1) cutoff feasibility math (verified favorable: ~1,040 expected post-cutoff filtered detections, well above N≥10 per type), (2) JSON byte-stable determinism contract (numpy floats and pandas Timestamps will silently break it without explicit coercion), and (3) ONNX inference cost over ~25k–50k detections (must reuse the renderer + session-once pattern from `verify_onnx.py`).

**Primary recommendation:** Keep `TRAIN_TEST_CUTOFF=2024-01-01` unchanged. Implement `simulate_trade` as a pure forward-walk loop returning a plain dict (matches existing `Detection.to_dict` pattern). Implement `aggregate` as a single-pass grouped accumulator with sorted-key JSON output. Run the unfiltered backtest once and partition into filtered/unfiltered by re-applying the filter booleans already attached to each `Detection.filters` field — this saves ~10× redundant work. Cache the ONNX session at module-load and feed per-detection 60-bar windows through `renderer.render(window, STYLES[0])` exactly as Phase 8's holdout fixture pipeline did. Sequential per-ticker is acceptable; if wall-clock pushes past 30 min, fall back to `concurrent.futures.ThreadPoolExecutor` (yfinance is I/O-bound and the ONNX session is thread-safe for `Run`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OHLC ingestion | Data layer (`_fetch_ohlc`) | — | Mirror `generate_training_data._fetch_ohlc` byte-for-byte; same yfinance idiom across the package |
| Detection | Detection module (Phase 7 `detect`) | — | Pure function; Phase 9 imports it, never reimplements |
| Trade resolution | Backtest core (`simulate_trade`) | — | Pure-function tier mirroring `detector._build_detection`; no I/O |
| Aggregation / stats | Backtest core (`aggregate`) | — | Pure-function rollup over resolved trade dicts |
| ONNX scoring | Inference overlay | Renderer | Reuses `renderer.render(window, STYLES[0])` + `verify_onnx.py` inference shape; runs INSIDE this process (not in clean venv subprocess — that gate already passed at Phase 8 close-out) |
| Cutoff partitioning | Backtest core (orchestrator) | split_config | Single import of `TRAIN_TEST_CUTOFF`; partition happens after detection list is collected |
| Filter ablation | Backtest orchestrator | detector kwarg | Run unfiltered once; re-derive filtered by reading `Detection.filters` booleans (saves a second `detect()` pass) |
| JSON output | I/O tier (orchestrator) | — | Pure `json.dump` with explicit `sort_keys=True`, `indent=2`, after explicit numpy-float / Timestamp coercion |
| Test seam | Test fixtures (`synthetic_ohlc`) | conftest | Reuse Phase 7/8 fixture verbatim — already supports the bar-tuple → DataFrame path |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Strategy `1to2_rr_cluster_low_stop`. Entry = open of `confirmation_bar_index + 1`. Stop = `min(bar.low for bar in detection.bars)`. Target = `entry + 2 × (entry − stop)`.
- **D-02:** Three-bucket outcome `{stop, target, open}`. No timeout. Open trades excluded from win-rate denominator, included in N. Open trades carry unrealized R.
- **D-03:** Pessimistic intrabar — single bar containing both stop and target ⇒ stop wins.
- **D-04:** Entry-bar gap-down at/below stop ⇒ recorded as `stop` with `R = (entry_open − stop) / risk` (negative, possibly worse than −1.0R). Entry bar with stop in `[low, high]` but open above ⇒ pessimistic same-day stop.
- **D-05:** Returns reported in R-multiples; field name `avg_return_r`. BT-03's "return %" is reinterpreted as "return in R" (note in SUMMARY).
- **D-06:** Output at `_dev/backtest_cache.json`. Add to `.gitignore`. Reproducibility tuple = `(seed, ticker list, TRAIN_TEST_CUTOFF, ONNX hash)`.
- **D-07:** Top-level `strategies` map. Schema includes `schema_version=1`, `generated_at`, `train_test_cutoff`, `seed`. Each strategy has `rule` metadata + `in_sample` + `out_of_sample` blocks.
- **D-08:** Per-detection record fields locked (identity, trade, resolution, ML overlay).
- **D-09:** Four aggregate slices per sample-block per strategy: `all`, `by_confirmation_type`, `by_is_spring`, `by_type_x_spring`. Per-cell: `n`, `n_resolved`, `win_rate`, `avg_return_r`, `median_hold_days`, `target_count`, `stop_count`, `open_count`. Cells with `n < 1` omitted.
- **D-10:** `TRAIN_TEST_CUTOFF` imported from `scripts.pattern_scanner.split_config`. Phase 9 may revise. Caveat: revising changes Phase 8's training-set boundary retroactively.
- **D-11:** Two parallel `in_sample` / `out_of_sample` blocks per strategy. `out_of_sample` is the integrity number for Phase 11.
- **D-12:** Two strategy entries: `1to2_rr_cluster_low_stop` (filtered) and `1to2_rr_cluster_low_stop__unfiltered` (full superset via `apply_trend_filters=False`). Not just rejects — full superset.
- **D-13:** `yolo_conf` is a raw float per-detection. NO `by_yolo_tier` aggregate.
- **D-14:** ONNX-missing fallback ⇒ `yolo_conf: null` + single warning. Backtest stays runnable.
- **D-15:** New file `scripts/pattern_scanner/backtest.py`. Public API: `_fetch_ohlc`, `simulate_trade`, `aggregate`, `main`.
- **D-16:** CLI suggested: `python -m scripts.pattern_scanner.backtest --seed 42 --tickers all --out _dev/backtest_cache.json`. `--limit N` for smoke tests. `RATE_LIMIT_SLEEP=0.5`.
- **D-17:** 8 required tests. Synthetic OHLC + monkeypatched `_fetch_ohlc`. All run in milliseconds.

### Claude's Discretion

- Runtime parallelization (sequential acceptable if total wall-time < 30 min).
- Per-detection record field ordering, JSON pretty-print, sort order.
- ONNX session caching shape (load once, reuse).
- `simulate_trade` returns frozen dataclass or plain dict (recommend dict).
- Calendar vs trading days for `median_hold_days` (recommend calendar; record choice).
- Per-ticker progress logging (recommend mirroring `generate_training_data.py`).
- Refinements to gap-down-on-entry handling beyond D-04.
- Exact CLI flag shape (`--seed`, `--tickers`, `--limit`, `--out` suggested).
- `simulate_trade` accepts df slices ending at entry bar OR full df + forward-walk loop (recommend full df).

### Deferred Ideas (OUT OF SCOPE)

- By-tier `yolo_conf` aggregation — Phase 11 with histogram.
- Per-ticker rollup ("best tickers for this setup").
- Per-filter-combo cross-tab (8 cells of 2³ filter on/off).
- Additional strategies (`fixed_20bar_hold`, `1to3_rr_mother_low_stop`, etc.).
- Variable hold with ATR-based exits.
- Slippage and commission modeling.
- Equity-curve simulation, position sizing, compounding (REQUIREMENTS Out of Scope — locked).
- Phase 9 → Phase 11 build step transforming `_dev/backtest_cache.json` into frontend-ready `docs/projects/patterns/backtest_stats.json`.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BT-01 | Compute 10-year forward-return stats per detection using fixed entry rule (open of conf+1) and fixed exit rule | `simulate_trade` pseudocode below; pessimistic D-03 + D-04 gap-down rules; R-multiple return semantic |
| BT-02 | Hard time-based train/test split — no detections from training period appear in backtest results | `TRAIN_TEST_CUTOFF` import from `split_config`; partition into `in_sample`/`out_of_sample` blocks; cross-check against `models/dataset_manifest.json` for proof of disjoint sets |
| BT-03 | Output win-rate (with N), avg return %, median hold to `_dev/backtest_cache.json`. At least one confirmation_type with N ≥ 10 | Cutoff feasibility math (below) shows ~1,040 expected post-cutoff filtered detections; even the thinnest confirmation type clears N ≥ 10 with margin |

## Project Constraints (from CLAUDE.md)

- **No AI co-author in commits** (memory directive — `git-attribution-guard`). Commits to be authored as the user only.
- **Use virtualenv `.venv/`** for any Python invocation; deps not in system Python.
- **Domain honesty:** finance-portfolio piece. Methodology must be defensible — R-multiples not %, pessimistic intrabar, no P&L sim.
- **MCP `code-review-graph` server connected:** Use `query_graph`, `get_impact_radius`, `semantic_search_nodes` over Grep/Read where applicable for plan-time impact analysis.
- **Never add `torch` or `ultralytics`** to `requirements.txt`. Phase 9 needs nothing beyond what Phase 8 already locked. [VERIFIED: requirements.txt grep — only `mplfinance`, `matplotlib`, `onnxruntime>=1.19`, `Pillow>=10.0` were added in Phase 8].
- **Pure-function core, thin CLI wrapper:** Per `CONVENTIONS.md` and verified across `detector.py`, `renderer.py`, `generate_training_data.py`, `verify_onnx.py` — every script in `scripts/pattern_scanner/` follows this split.

## Standard Stack

### Core (no additions to requirements.txt)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | >=2.2.0 | OHLC frames, Timestamp arithmetic | [VERIFIED: requirements.txt L5] Already used end-to-end |
| numpy | >=1.26.0 | Float arithmetic; numpy<2.0 transitively pinned by ultralytics in training env, but Phase 9 runs against `requirements.txt` only | [VERIFIED: requirements.txt L6 + 08-05-SUMMARY hand-off] |
| yfinance | ==0.2.65 | 10y daily OHLC fetch | [VERIFIED: requirements.txt L3] Used by `_fetch_ohlc` in detector and gen_training_data — Phase 9 mirrors byte-for-byte |
| onnxruntime | >=1.19 | Inference for `yolo_conf` overlay | [VERIFIED: requirements.txt L16] Reused via `verify_onnx.py` `INFERENCE_SCRIPT` shape |
| Pillow | >=10.0 | PNG decode → numpy array for ONNX | [VERIFIED: requirements.txt L17] Used in inference path |
| mplfinance | >=0.12.10b0 | Candlestick PNG render via `renderer.render()` | [VERIFIED: requirements.txt L14] |

**No new dependencies required.** [VERIFIED: 08-CONTEXT D-20 + 08-05-SUMMARY hand-off note]

### Standard Library Used

| Module | Purpose |
|--------|---------|
| `argparse` | CLI shape mirroring `generate_training_data.py` |
| `concurrent.futures` (optional) | Thread pool fallback if sequential wall-time exceeds 30 min |
| `dataclasses` | None — `simulate_trade` returns plain dict (D-15 discretion) |
| `hashlib` | Optional ONNX artifact hash for the reproducibility tuple (D-06) |
| `json` | Output writer; `sort_keys=True, indent=2, default=str` for date coercion |
| `pathlib.Path` | File I/O paths matching `generate_training_data.py` style |
| `time` | `RATE_LIMIT_SLEEP = 0.5` between yfinance calls |
| `warnings` | D-14 "ONNX missing" single warning |
| `statistics.median` | `median_hold_days` (no numpy needed for one-D median) |

**Installation:** No-op. All deps already in `requirements.txt`.

**Version verification:** `requirements.txt` was last updated by Phase 8 (commit history confirms). Phase 9 should NOT touch it. [VERIFIED: in-repo file]

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                       backtest.main(argv)                        │
│                  (CLI: --seed --tickers --limit --out)           │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
       ┌────────────────────────────────────────────────┐
       │   _load_tickers(limit) → fetch_sp500_tickers   │
       │   (mirrors generate_training_data.py L85-94)   │
       └────────────────────────────────────────────────┘
                                │
                                ▼
       ┌────────────────────────────────────────────────┐
       │   ONNX session = ort.InferenceSession(...)     │
       │   loaded ONCE; None if model file missing      │
       │   → emit single D-14 warning on miss           │
       └────────────────────────────────────────────────┘
                                │
                                ▼
   ╭─── for ticker in tickers (sequential, RATE_LIMIT_SLEEP=0.5) ───╮
   │                                                                │
   │   df = _fetch_ohlc(ticker)        # monkeypatchable test seam  │
   │   if len(df) < 60: skip                                        │
   │                                                                │
   │   # ── Filter ablation: ONE detect() call ───────────────────  │
   │   all_dets = detect(df, ticker, apply_trend_filters=False)     │
   │   # filtered = subset where all 3 booleans pass                │
   │   filtered = [d for d in all_dets if all(d.filters.values())]  │
   │                                                                │
   │   for det in all_dets:                                         │
   │       result = simulate_trade(df, det, stop, target)           │
   │       window = df.iloc[conf-59 : conf+1]                       │
   │       yolo_conf = score(window, sess) if sess else None        │
   │       record = build_record(det, result, yolo_conf)            │
   │       partition by (filtered? in/out_of_sample) → 4 buckets    │
   ╰────────────────────────────────────────────────────────────────╯
                                │
                                ▼
       ┌────────────────────────────────────────────────┐
       │   aggregate(records, group_keys) per slice     │
       │   × 4 slices × 2 sample blocks × 2 strategies  │
       │   = 16 aggregate dicts                         │
       └────────────────────────────────────────────────┘
                                │
                                ▼
       ┌────────────────────────────────────────────────┐
       │   json.dump({ schema_version: 1, ... },        │
       │             open("_dev/backtest_cache.json"),  │
       │             sort_keys=True, indent=2,          │
       │             default=str)                       │
       └────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
scripts/pattern_scanner/
├── __init__.py              (exists)
├── detector.py              (Phase 7 — read-only consumer)
├── renderer.py              (Phase 8 — call render(window, STYLES[0]))
├── verify_onnx.py           (Phase 8 — copy INFERENCE_SCRIPT preprocessing inline)
├── split_config.py          (Phase 8 — import TRAIN_TEST_CUTOFF)
├── generate_training_data.py (Phase 8 — orchestrator template)
└── backtest.py              ← NEW. _fetch_ohlc, simulate_trade, aggregate, main

tests/
├── conftest.py              (existing — synthetic_ohlc fixture reused)
├── test_backtest_simulate_trade.py    ← NEW. 4 tests
├── test_backtest_aggregate.py         ← NEW. 1 test
├── test_backtest_cutoff.py            ← NEW. 1 test
├── test_backtest_unfiltered_superset.py  ← NEW. 1 test
└── test_backtest_yolo_conf_fallback.py   ← NEW. 1 test

(or one consolidated tests/test_backtest.py — researcher leaves to planner)
```

### Pattern 1: Forward-walk trade resolution (`simulate_trade`)

**What:** Pure function. Given full df, a `Detection`, and resolved entry/stop/target prices, walks bars `conf+1, conf+2, ..., end-of-df` until stop, target, or end-of-data. Returns a dict.

**When to use:** Once per detection.

**Pseudocode (planner can lift directly):**

```python
def simulate_trade(
    df: pd.DataFrame,
    detection: Detection,
    stop_price: float,
    target_price: float,
) -> dict:
    """
    Returns: {
        entry_date, entry_price, stop_price, target_price, risk,
        exit_date, exit_price, exit_reason ∈ {stop, target, open},
        hold_days, R,
    }
    """
    entry_idx = detection.confirmation_bar_index + 1
    if entry_idx >= len(df):
        # Detection at the last bar — no entry possible. Treat as 'open' with R=0.
        return _open_record(detection, stop_price, target_price, last_close=df.iloc[-1]["Close"])

    entry_open = float(df.iloc[entry_idx]["Open"])
    entry_date = df.index[entry_idx]
    risk = entry_open - stop_price  # positive by construction (stop = cluster low; entry = open of conf+1 generally above)
    if risk <= 0:
        # Pathological: stop is at or above entry. Treat conservatively as immediate stop.
        # (Rare — would imply entry bar gapped down at or below the cluster low itself.)
        return _stop_record(detection, entry_open, stop_price, target_price, entry_idx, df,
                            R=(entry_open - stop_price) / max(abs(entry_open - stop_price), 1e-9))

    # ── D-04: entry-bar gap-down handling ─────────────────────────────────
    if entry_open <= stop_price:
        # Gap down at or below stop — recorded as 'stop' with R possibly < -1.0
        R = (entry_open - stop_price) / risk  # negative, magnitude depends on gap size
        return {
            **_identity(detection),
            "entry_date": _iso(entry_date),
            "entry_price": float(entry_open),
            "stop_price": float(stop_price),
            "target_price": float(target_price),
            "risk": float(risk),
            "exit_date": _iso(entry_date),
            "exit_price": float(entry_open),
            "exit_reason": "stop",
            "hold_days": 0,
            "R": float(R),
        }

    # ── D-04 + D-03: entry bar's [low, high] contains stop ⇒ pessimistic stop ──
    entry_low = float(df.iloc[entry_idx]["Low"])
    entry_high = float(df.iloc[entry_idx]["High"])
    if entry_low <= stop_price:
        # Stop touched intrabar on entry bar. Pessimistic: stop wins (same day).
        return _resolved(detection, entry_open, stop_price, target_price, entry_idx, entry_idx,
                         exit_price=stop_price, exit_reason="stop", R=-1.0, df=df)

    # ── Forward walk bars conf+2, conf+3, ..., end ─────────────────────────
    for j in range(entry_idx + 1, len(df)):
        bar_low = float(df.iloc[j]["Low"])
        bar_high = float(df.iloc[j]["High"])
        hit_stop = bar_low <= stop_price
        hit_target = bar_high >= target_price
        if hit_stop and hit_target:
            # D-03 pessimistic: stop wins same-day.
            return _resolved(detection, entry_open, stop_price, target_price, entry_idx, j,
                             exit_price=stop_price, exit_reason="stop", R=-1.0, df=df)
        if hit_stop:
            return _resolved(detection, entry_open, stop_price, target_price, entry_idx, j,
                             exit_price=stop_price, exit_reason="stop", R=-1.0, df=df)
        if hit_target:
            return _resolved(detection, entry_open, stop_price, target_price, entry_idx, j,
                             exit_price=target_price, exit_reason="target", R=2.0, df=df)

    # ── End of data — neither hit (D-02 'open') ─────────────────────────────
    last_close = float(df.iloc[-1]["Close"])
    R_open = (last_close - entry_open) / risk
    return {
        **_identity(detection),
        "entry_date": _iso(entry_date),
        "entry_price": float(entry_open),
        "stop_price": float(stop_price),
        "target_price": float(target_price),
        "risk": float(risk),
        "exit_date": _iso(df.index[-1]),
        "exit_price": float(last_close),
        "exit_reason": "open",
        "hold_days": (df.index[-1] - entry_date).days,
        "R": float(R_open),
    }
```

**Key invariants:**
- Order of checks per bar: gap-down > entry-bar-intrabar > forward-walk. This locks D-04 default behaviour (entry-bar pessimism).
- Within forward walk: `hit_stop and hit_target` checked BEFORE individual checks ⇒ D-03 pessimism is enforced explicitly, not accidentally.
- `hold_days = (exit_date - entry_date).days` (calendar days; record this choice in SUMMARY per Claude's discretion).
- Float coercion `float(...)` everywhere — eliminates numpy.float64 leaks into the JSON serializer (see Pitfall 1 below).

### Pattern 2: Aggregate single-pass grouped accumulator

**What:** Pure function over a list of resolved trade dicts. Groups by zero or more keys, emits per-cell stat dict. Must be deterministic in JSON serialization order.

**When to use:** Four times per (sample_block × strategy) — once per slice (`all`, `by_confirmation_type`, `by_is_spring`, `by_type_x_spring`).

**Recommendation:** Single-pass `defaultdict` accumulator with explicit sorted-key emission. Pandas `groupby` is overkill and introduces numpy-int / numpy-float key types into the dict (Pitfall 2). Code:

```python
from collections import defaultdict
from statistics import median

def aggregate(records: list[dict], group_keys: list[str]) -> dict:
    """Single-pass groupby. Empty group_keys → returns {'all': {...}}-style cell directly.

    For multi-key grouping, key is "_".join(str(r[k]) for k in group_keys).
    Cells with n < 1 are omitted on output (D-09).
    """
    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if not group_keys:
            key = "all"
        elif len(group_keys) == 1:
            key = str(r[group_keys[0]])
        else:
            key = "_".join(str(r[k]) for k in group_keys)
        buckets[key].append(r)

    out = {}
    for key in sorted(buckets):  # deterministic key order
        rs = buckets[key]
        n = len(rs)
        if n < 1:
            continue  # D-09 omit empty cells
        resolved = [r for r in rs if r["exit_reason"] != "open"]
        n_resolved = len(resolved)
        target_count = sum(1 for r in rs if r["exit_reason"] == "target")
        stop_count = sum(1 for r in rs if r["exit_reason"] == "stop")
        open_count = sum(1 for r in rs if r["exit_reason"] == "open")
        win_rate = (target_count / n_resolved) if n_resolved > 0 else None
        avg_return_r = sum(r["R"] for r in rs) / n  # includes 'open' per D-05 (open carries unrealized R)
        median_hold_days = median(r["hold_days"] for r in resolved) if n_resolved > 0 else None
        out[key] = {
            "n": n,
            "n_resolved": n_resolved,
            "win_rate": win_rate,
            "avg_return_r": float(avg_return_r),
            "median_hold_days": median_hold_days,
            "target_count": target_count,
            "stop_count": stop_count,
            "open_count": open_count,
        }
    return out
```

For the global `all` slice, call `aggregate(records, group_keys=[])` and return `out["all"]` directly (single object, not a map).

### Pattern 3: ONNX session caching

**What:** Load `models/inside_bar_v1.onnx` ONCE at the start of `main()`; pass the session as an argument to the per-detection scoring function. Reuse the preprocessing inline from `verify_onnx.INFERENCE_SCRIPT` lines 60–82.

**When to use:** Once per `main()` invocation. If the file does not exist, leave the session as `None` and emit a single warning per D-14.

**Code skeleton:**

```python
def _load_onnx_session(model_path: Path):
    if not model_path.exists():
        warnings.warn(
            f"ONNX model not found at {model_path}; yolo_conf will be null for all records.",
            stacklevel=2,
        )
        return None
    import onnxruntime as ort
    return ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])


def _score_detection(window: pd.DataFrame, sess) -> float | None:
    """Render 60-bar window via STYLES[0], run inference, return max-conf bbox score.
    Returns None if sess is None (D-14 fallback)."""
    if sess is None:
        return None
    from PIL import Image
    import numpy as np, io
    from scripts.pattern_scanner.renderer import render, STYLES
    png_bytes = render(window, STYLES[0])  # deterministic style at inference (D-13)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB").resize((640, 640), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float32) / 255.0
    arr = arr.transpose(2, 0, 1)[None, ...]
    inp_name = sess.get_inputs()[0].name
    out_names = [o.name for o in sess.get_outputs()]
    raw = sess.run(out_names, {inp_name: arr})[0]
    pred = raw[0].T  # (N, 5) = [cx, cy, w, h, score]
    scores = pred[:, 4]
    if scores.size == 0:
        return 0.0
    return float(scores.max())
```

### Anti-Patterns to Avoid

- **Anti-pattern: `pandas.groupby` for aggregate.** Introduces numpy.int64/float64 keys into the JSON path. Use `defaultdict(list)` and explicit `str(...)` key coercion.
- **Anti-pattern: Re-running `detect()` twice for filter ablation.** `Detection.filters` already records all three booleans on every detection. Run `detect(df, ticker, apply_trend_filters=False)` ONCE and partition by `all(d.filters.values())`. Saves ~50% wall time. [VERIFIED in detector.py L373-380: filtered branch only adds when all three filter booleans pass; the unfiltered path returns the same Detection objects.]
- **Anti-pattern: Re-rendering windows inside the inner loop multiple times.** Render once per detection, regardless of strategy bucket. ONNX inference cost is per-render-and-infer; cache nothing more aggressive than the session itself (window arrays are bytes-large but transient).
- **Anti-pattern: Calling `verify_onnx.py` as a subprocess.** That gate runs at Phase 8 close-out. Phase 9 runs ONNX in-process, in the same venv that has full deps. Subprocess venv is the wrong tool here.
- **Anti-pattern: `ProcessPoolExecutor` with onnxruntime.** Each worker would load its own ONNX session — wastes memory and breaks determinism (worker assignment order is not stable). If parallelizing, use `ThreadPoolExecutor`: yfinance is I/O-bound; onnxruntime `Run` is thread-safe. [CITED: onnxruntime docs say "Concurrent calls to InferenceSession.run() are thread-safe."]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Calendar-day math | `(date2 - date1).total_seconds() / 86400` | `(idx2 - idx1).days` on pandas Timestamps | Built-in; handles tz-naive index correctly |
| Median of integers | manual sort + middle index | `statistics.median(...)` | Stdlib; handles even-length lists correctly |
| ONNX YOLOv8 output decode | re-implement bbox decode + NMS | Copy preprocessing block from `verify_onnx.INFERENCE_SCRIPT` L60-82 | Already verified correct against ground truth (Phase 8 close-out: bbox IoU ≈ 1.0) |
| Per-detection 60-bar window | bespoke slicing logic | `df.iloc[conf-59 : conf+1]` mirroring `generate_training_data._slice_window` | Right-aligned framing parity with training-time renderer (D-03 in Phase 8) |
| Cutoff partition | string compare on date strings | `pd.Timestamp(d.confirmation_date) < pd.Timestamp(TRAIN_TEST_CUTOFF)` | `_detect_positives` in `generate_training_data.py` L100-104 already uses this idiom — copy verbatim |
| ONNX session lifecycle | per-detection session creation | Module-load once; pass as arg | Session creation is ~hundreds-of-ms; per-detection cost would dominate wall-time |
| Float-vs-numpy coercion | hope `json.dumps` figures it out | Explicit `float(x)` at write-time on every numeric field | numpy.float64 silently serializes BUT pandas Timestamp does not — must coerce both |

**Key insight:** Phase 9 is "compose Phase 7+8 components without re-implementing them." Every algorithmic primitive (5-bar cluster, filter booleans, 60-bar render, ONNX preprocessing, cutoff arithmetic, deterministic seed plumbing) already exists and is tested. Hand-rolled re-implementations are the single biggest planning risk.

## Common Pitfalls

### Pitfall 1: numpy/pandas types break JSON byte-stability

**What goes wrong:** `pd.DataFrame.iloc[i]["Open"]` returns numpy.float64. `json.dumps` serializes it (numpy.float64 supports `__float__`), but the serialization path is platform-specific in edge cases. Worse: a `pd.Timestamp` in the dict raises `TypeError: Object of type Timestamp is not JSON serializable`.

**Why it happens:** pandas vectorized accessors return numpy scalar types, not Python natives. The `Detection.bars` field uses `float(...)` already (see detector.py L278-282) — Phase 9 must do the same for every numeric field added to the per-detection record.

**How to avoid:**
- Wrap every scalar in `float(...)`, `int(...)`, or `str(...)` at write-time.
- For dates: `df.index[i].strftime("%Y-%m-%d")` matching detector.py L289 verbatim. Never write `df.index[i]` directly.
- Belt-and-braces: pass `default=str` to `json.dump`. Catches stragglers but masks bugs — prefer explicit coercion.

**Warning signs:** `concat_sha256` differs across machines (Phase 8 hit this — see 08-04-SUMMARY note about laptop vs desktop hash differing). For Phase 9, byte-stability across `(seed, ticker_list, cutoff, ONNX_hash)` is the contract — any platform-dependent serialization breaks it.

### Pitfall 2: Confusing pandas iloc result types

**What goes wrong:** `df.iloc[entry_idx]` returns a pandas Series whose `.dtype` is `object`. Calling `bar["Low"]` returns numpy.float64. Comparison `bar["Low"] <= stop_price` works (numpy broadcasts), but accumulating these into the JSON dict leaves typed scalars.

**Why it happens:** pandas tries to be helpful with type promotion.

**How to avoid:** Same as Pitfall 1 — coerce at the boundary. `entry_low = float(df.iloc[entry_idx]["Low"])` not `entry_low = df.iloc[entry_idx]["Low"]`.

### Pitfall 3: ONNX missing AT IMPORT vs AT RUNTIME

**What goes wrong:** Plan accidentally imports `onnxruntime` at module top. Then a CI job that doesn't install onnxruntime crashes at import. D-14 says backtest should be runnable without the model, but module-level import couples Phase 9 to Phase 8 artifacts.

**Why it happens:** It's the natural Python idiom.

**How to avoid:** Defer onnxruntime import inside `_load_onnx_session()`. Pattern matches detector.py L390 (deferred yfinance import) and verify_onnx.py L66 (subprocess-only inference). The model file check happens at runtime; the import happens at runtime; the session creation happens at runtime. Three failure points, each individually graceful.

### Pitfall 4: `apply_trend_filters=False` returning a non-superset

**What goes wrong:** Detector's filter loop short-circuits when `apply_trend_filters=True` — emits a detection iff all three booleans pass. When `False`, every cluster-shape match is emitted regardless of filters. Plans that assume "filtered = all_unfiltered ∩ filtered" need this to be a strict superset.

**Why it works:** [VERIFIED in detector.py L373-380]. The detection-record assembly in `_build_detection` (L237-301) is identical regardless of `apply_trend_filters`. The kwarg only affects the `if` block at L373-380. Therefore `detect(df, t, apply_trend_filters=False)` returns ALL records that the filtered call would have returned, plus all the records where one or more filter booleans is False. Same `(ticker, mother_bar_index, confirmation_bar_index)` keys.

**How to avoid (for the test):** `test_unfiltered_strategy_is_superset` should compare keys: `set(filtered_keys) ⊆ set(unfiltered_keys)`, then `unfiltered ⊋ filtered` for at least one ticker (existing test fixture in `_flat_prefix_rows` from `tests/test_generate_training_data.py` L102-137 already produces this exact case — reuse it).

### Pitfall 5: yfinance auto_adjust mixing dividends into close

**What goes wrong:** With `auto_adjust=True`, yfinance returns adjusted OHLC where dividends are baked into the close price retroactively. A 10% dividend distributed mid-trade silently shifts the historical "close" downward, making the historical "open" of conf+1 a wrong entry price relative to today's view of the past.

**Why it happens:** yfinance's auto_adjust is a backward-looking reconciliation. Unrelated to look-ahead bias — purely an artifact of how dividends propagate through historical series.

**How to avoid:** This is INHERITED from Phase 7. [VERIFIED detector.py L388-396 uses `auto_adjust=True`]. Phase 9 mirrors. The portfolio narrative is honest because (a) all of Phase 8's training data uses the same convention, so the model and the backtester live in the same numerical universe, and (b) the alternative (`auto_adjust=False`) would put us in a worse place — split-adjusted but not div-adjusted is its own inconsistency. **Document this in the SUMMARY:** "Returns are computed against dividend-adjusted close prices; absolute % return ≠ price-chart % return on tickers with material dividend yield. R-multiples are unaffected because the ratio normalizes within the same series."

### Pitfall 6: Cutoff partition off-by-one

**What goes wrong:** D-11 says `in_sample = confirmation_date < cutoff` and `out_of_sample = confirmation_date >= cutoff`. Phase 8's `_detect_positives` uses `< cutoff` (in_sample) — verified at `generate_training_data.py` L100-104. Get the operator wrong and a 2024-01-01 detection ends up in BOTH samples or NEITHER.

**How to avoid:** Use `pd.Timestamp(d.confirmation_date) < pd.Timestamp(TRAIN_TEST_CUTOFF)` for in_sample (matches Phase 8); negate for out_of_sample. The `test_train_test_cutoff_isolation` test must explicitly construct a detection with `confirmation_date == cutoff` and assert it lands in `out_of_sample`, not `in_sample`.

### Pitfall 7: Detection records have pandas.Timestamp confirmation_dates in some code paths

**What goes wrong:** Phase 7 `Detection.confirmation_date` is `str` (ISO format) — verified at detector.py L289 (`df.index[conf_idx].strftime("%Y-%m-%d")`). But if a downstream developer ever swaps it for `pd.Timestamp` for "convenience", JSON serialization breaks immediately.

**How to avoid:** Phase 9 trusts the contract: `confirmation_date` is a string. If `simulate_trade` adds `entry_date` and `exit_date`, those must also be strings, generated identically: `df.index[idx].strftime("%Y-%m-%d")`. Test `test_simulate_trade_*_first` should assert `isinstance(record["entry_date"], str)`.

### Pitfall 8: stop_price > entry_price (pathological)

**What goes wrong:** Cluster-low stop is supposed to be below entry (entry = open of conf+1, generally above the cluster). But on a gap-up entry bar where the open closes above the cluster high, AND the lowest of the 5 cluster bars is BELOW the next-day's open... wait, the math is fine. The pathological case is: cluster low > next-day open. That happens when the next day gaps DOWN through the entire cluster.

**How to handle:** The pseudocode above already handles this: `risk = entry_open - stop_price`; if `risk <= 0`, treat as immediate stop with R = -1.0 (or compute R from gap size). Practically rare; should NOT crash. Add to test inventory if budget permits (not in D-17's required 8).

## Runtime State Inventory

> Phase 9 is a greenfield phase (new file, no rename/refactor). Section retained per template; categories explicitly answered.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `_dev/backtest_cache.json` is brand-new and gitignored. No existing cache to migrate. | None |
| Live service config | None — no n8n / Datadog / external service touches Phase 9. | None |
| OS-registered state | None — no scheduled task / pm2 / systemd registration in this phase (that's Phase 10). | None |
| Secrets / env vars | None — yfinance and onnxruntime require no API keys. | None |
| Build artifacts | None — `scripts/pattern_scanner/` is a regular module; no setup.py egg-info. The `models/inside_bar_v1.onnx` artifact is read-only consumed, not rebuilt by Phase 9. | None |

**Nothing found in any category** — Phase 9 is purely additive. (Verified by grepping for "devos", "rename", "migration" patterns — none apply.)

## Code Examples

### Example 1: Forward-walk skeleton (consumed by `simulate_trade` planner task)

```python
# Source: derived from detector.py L237-301 (record-assembly idiom)
#         + generate_training_data.py L100-104 (cutoff arithmetic)
def simulate_trade(df, detection, stop_price, target_price):
    entry_idx = detection.confirmation_bar_index + 1
    if entry_idx >= len(df):
        return _open_record(detection, stop_price, target_price,
                            last_close=float(df.iloc[-1]["Close"]))
    entry_open = float(df.iloc[entry_idx]["Open"])
    entry_date = df.index[entry_idx]
    risk = entry_open - stop_price
    # ... (full pseudocode in Pattern 1 above)
```

### Example 2: ONNX session caching (consumed by orchestrator task)

```python
# Source: verify_onnx.py L62-72 (preprocessing) + onnxruntime docs (session creation)
def _score_detection(window, sess):
    if sess is None:
        return None
    png_bytes = render(window, STYLES[0])
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB").resize((640, 640), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float32) / 255.0
    arr = arr.transpose(2, 0, 1)[None, ...]
    raw = sess.run(None, {sess.get_inputs()[0].name: arr})[0]
    scores = raw[0].T[:, 4]
    return float(scores.max()) if scores.size else 0.0
```

### Example 3: JSON write with byte-stable determinism

```python
# Source: generate_training_data.py L327-333 — same pattern, same flags
import json
from pathlib import Path
out_path = Path("_dev/backtest_cache.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with out_path.open("w", encoding="utf-8") as f:
    json.dump(
        cache,
        f,
        indent=2,
        sort_keys=True,
        default=str,        # Timestamp safety net; should never trigger
    )
    f.write("\n")           # POSIX trailing newline
```

### Example 4: Cutoff arithmetic (verbatim from gen_training_data.py)

```python
# Source: generate_training_data.py L100-104
cutoff = pd.Timestamp(TRAIN_TEST_CUTOFF)
in_sample = [r for r in records if pd.Timestamp(r["confirmation_date"]) < cutoff]
out_of_sample = [r for r in records if pd.Timestamp(r["confirmation_date"]) >= cutoff]
```

## Cutoff Feasibility Analysis (Question 1)

**Empirical anchor:** `models/dataset_manifest.json` reports **4,010 filtered positives** across the full S&P 500 (503 tickers) for the 10-year window MINUS the post-cutoff portion. Cutoff = 2024-01-01. Manifest dates are pre-2024-01-01.

**Time-window math:**
- Full 10y range fetched: roughly 2014-01 → 2024-01 (pre-cutoff) ≈ 9 years post-cutoff-aware
- Post-cutoff range: 2024-01-01 → 2026-05-09 (today) ≈ 2.357 years

**Density:**
- Filtered detections per ticker per year (pre-cutoff): 4010 / (503 × ~9) ≈ **0.886 detections/ticker/year**
- Expected post-cutoff filtered total: 503 × 0.886 × 2.357 ≈ **1,050 detections** (rough estimate; assumes density is stable)

**Per-confirmation_type expected count (assuming uniform distribution across pin/mark_up/ice_cream — a conservative simplification; in practice pin tends to dominate):**
- Worst-case uniform: ~350 per type → far above N≥10
- Realistic skewed (pin = 60%, mark_up = 25%, ice_cream = 15%): pin ~630, mark_up ~262, ice_cream ~158 → all far above N≥10

**Unfiltered superset:**
- Manifest also reports 21,849 hard-negatives (= unfiltered − filtered, pre-cutoff). So unfiltered total pre-cutoff = 4,010 + 21,849 = 25,859.
- Density: 25859 / (503 × 9) ≈ **5.71 unfiltered detections/ticker/year**.
- Expected post-cutoff unfiltered: 503 × 5.71 × 2.357 ≈ **6,770 detections**. Per-type ≥ 100 even on conservative skew.

**Recommendation: KEEP cutoff at 2024-01-01.** [VERIFIED via models/dataset_manifest.json + arithmetic above]

**Caveat:** The 0.886/ticker/year density is an averaged figure. Some confirmation types are rarer than others; the conservative skew above puts ice_cream at ~158, which is comfortable. If post-cutoff yfinance availability drops (delisted tickers, recent IPOs with <10y history, etc.), expect ~5–10% attrition. Even at 30% attrition, ice_cream still clears N≥10 by an order of magnitude.

**No revision required to `split_config.py`.** Phase 9 SUMMARY should record the actual post-cutoff N values once `_dev/backtest_cache.json` is written, so the audit trail captures empirical confirmation of this estimate.

[ASSUMED] Confirmation-type distribution skew (60/25/15 split) — Phase 8 manifest does not break down positives by `confirmation_type`. The estimate is based on general pattern-distribution knowledge and the user's research memory file `project_milestone2_pattern_scanner.md`. The actual distribution will be visible from the Phase 9 output JSON itself; no upstream evidence currently fixes the ratios.

## Filter Ablation Execution Shape (Question 5)

**Verified:** `apply_trend_filters=False` returns a strict superset. [VERIFIED detector.py L373-380.] The detection-record assembly is identical; only the `if` filter is bypassed.

**Therefore: run detect ONCE per ticker.** Specifically:

```python
all_dets = detect(df, ticker, apply_trend_filters=False)
filtered = [d for d in all_dets if all(d.filters.values())]
```

Where `all(d.filters.values())` evaluates to True iff `hh_hl AND above_50sma AND sma_cluster` — the exact predicate at detector.py L375-378.

**Cost saving:** Per-ticker work goes from `2 × O(n²)` (two detect passes) to `1 × O(n²)` (one pass) plus a Python list comprehension. Approximately 50% reduction in Phase 7 detect-loop time.

**Test (`test_unfiltered_strategy_is_superset`):** Use the existing `_flat_prefix_rows` fixture from `tests/test_generate_training_data.py` L102-137 — already produces `filtered = []` and `unfiltered ≥ 1`. Reuse verbatim.

## ONNX Overlay Performance Estimation (Question 4)

**Components per detection:**
1. `renderer.render(window, STYLES[0])` — produces 640×640 PNG bytes via mplfinance.
2. `Image.open(...).convert("RGB").resize((640, 640))` — ~10ms based on Pillow benchmarks.
3. `numpy.asarray + transpose + batch dim` — sub-millisecond.
4. `sess.run(...)` — onnxruntime CPU inference for YOLOv8n at imgsz=640: ~20–60ms on a modern laptop CPU [CITED: ultralytics docs report YOLOv8n CPU inference at ~80–100ms for unoptimized; ONNX export with opset 12 typically halves that].
5. Output decode (no NMS needed — we just take max score): sub-millisecond.

**Renderer cost is the dominant term.** mplfinance plot creation invokes matplotlib Figure construction, candlestick plotting, savefig to BytesIO, then Pillow resize. Empirical estimate from Phase 8 dataset generation: ~150–250ms per 60-bar render on the user's machine (Phase 8 generated ~26k images in ~3 hours of dataset-gen wall time on the laptop, before training).

**Per-detection total estimate:** ~200–300ms.

**Total inference budget:**
- Filtered run: ~1,050 post-cutoff detections + 4,010 pre-cutoff = 5,060 total ⇒ ~17 minutes.
- Unfiltered run: ~6,770 post-cutoff + 21,849 pre-cutoff = 28,619 total ⇒ ~1.5 hours.

**WAIT** — the unfiltered count would push past the 30-min wall-clock target.

**Mitigation options:**
1. **Render batching:** Pillow + onnxruntime can process N=8 or N=16 image batches in one `sess.run` call, exploiting BLAS parallelism. ONNX export was `dynamic=False` per Phase 8 D-17 — verify whether the model supports batch dim > 1; if not, single-image inference is the only path.
2. **Parallel I/O:** yfinance fetches dominate the front of the loop. Use `concurrent.futures.ThreadPoolExecutor(max_workers=4)` for the fetch + detect stage; merge results before the inference pass.
3. **Accept the wall-clock:** D-15 discretion explicitly allows up to 30 min. If the unfiltered run blows past it, the planner's recommendation should be: run sequentially the first time, capture the wall-clock empirically, and only optimize if the empirical number exceeds tolerance.

**Recommendation:** Plan for sequential per-ticker. Defer parallelization to a refinement task IF the first end-to-end run exceeds 30 minutes for the unfiltered strategy. Do not preemptively parallelize — adds determinism risk for a problem that may not bind.

[ASSUMED] mplfinance per-render latency 150–250ms. Phase 8's 3-hour dataset-gen wall time is a rough divisor; actual per-render cost was not benchmarked in isolation. Should be measured during the Phase 9 first-end-to-end run.

[ASSUMED] ONNX YOLOv8n CPU inference at 20–60ms. Not benchmarked in Phase 8 (the verify_onnx subprocess overhead was ~30s but inference itself was sub-second per the holdout fixture; tighter timing was not recorded). Worst-case bound is the 5,060-detection filtered run at <17 min.

## Test Fixture Design (Question 7)

The 8 tests in D-17 map cleanly onto the existing `synthetic_ohlc` fixture. **No new conftest fixtures required.** Specifics:

| Test | Min synthetic input | New fixture needed? |
|------|---------------------|---------------------|
| `test_simulate_trade_stop_first` | A `Detection` (constructed manually with `mother_bar_index`, `confirmation_bar_index`, `bars` dict for cluster low) + 5-bar follow-up frame where bar `j.low <= stop` and `bar.high < target`. | No — synthetic_ohlc + a small `_make_detection()` helper inline in the test |
| `test_simulate_trade_target_first` | Same Detection scaffold + follow-up where `bar.high >= target` and `bar.low > stop`. | No |
| `test_simulate_trade_intrabar_pessimistic` | Detection scaffold + ONE follow-up bar with `bar.low <= stop AND bar.high >= target` (single-bar conflict). Assert `exit_reason == "stop"`. | No |
| `test_simulate_trade_open_outcome` | Detection scaffold + 3-bar follow-up where neither stop nor target ever hit. Assert `exit_reason == "open"`, `R = (last_close - entry) / risk`. | No |
| `test_aggregate_groupings` | List of dict-records (no df needed). Construct directly in the test: `[{"confirmation_type": "pin", "is_spring": True, "exit_reason": "target", "R": 2.0, "hold_days": 5, ...}, ...]`. Assert all four slices return correctly. | No — pure-dict input |
| `test_train_test_cutoff_isolation` | Full backtest run with monkeypatched `_fetch_ohlc` returning a frame whose detections straddle the cutoff. Assert no in_sample record has `confirmation_date >= cutoff`; no out_of_sample has `< cutoff`. Use the `_spring_setup_rows` fixture (or extend it) starting at `2023-09-01` so detections naturally fall on either side of `2024-01-01`. | No — monkey-patch fixtures already in `tests/test_generate_training_data.py` |
| `test_unfiltered_strategy_is_superset` | Use the existing `_flat_prefix_rows` from `tests/test_generate_training_data.py` L102-137. Already returns `filtered=[]`, `unfiltered≥1`. | No — copy verbatim; or import it (recommended) |
| `test_yolo_conf_null_when_onnx_missing` | Run main with monkeypatched ONNX path pointing to a non-existent file. Assert all records have `yolo_conf is None` and a warning was emitted. Use `pytest.warns(UserWarning)` to capture the D-14 warning. | No — `monkeypatch.setattr(backtest_mod, "_load_onnx_session", lambda p: None)` is sufficient |

**Fixture reuse summary:**
- `synthetic_ohlc` (conftest.py L46-66) — for OHLC frame construction.
- `patched_fetch` pattern (gen_training_data tests L141-165) — copy this fixture to `test_backtest_cutoff.py` and adapt for backtest_mod.
- `_spring_setup_rows` and `_flat_prefix_rows` helpers (test_generate_training_data L65-137) — recommend extracting these into conftest.py if Phase 9 reuses them, otherwise copy with comment "duplicated from test_generate_training_data.py L65-137".

**Helper required (not a fixture):** `_make_detection(mother_idx, conf_idx, conf_type, is_spring, bars=None)` — constructs a `Detection(...)` for tests that don't need to run `detect()` end-to-end. Place inline in test files; no conftest entry.

## CLI Shape & Ergonomics (Question 8)

Mirror `generate_training_data.py` argparse exactly (lines 188-199):

```python
p = argparse.ArgumentParser(
    description="Backtest the inside bar spring strategy across the S&P 500."
)
p.add_argument("--seed", type=int, required=True,
               help="Deterministic seed for any RNG; included in cache header.")
p.add_argument("--limit", type=int, default=None,
               help="Process only the first N tickers (testing).")
p.add_argument("--out", type=Path, default=Path("_dev/backtest_cache.json"),
               help="Output JSON path.")
p.add_argument("--no-onnx", action="store_true",
               help="Force yolo_conf=null even if ONNX model exists (fast iteration).")
p.add_argument("--tickers", type=str, default="all",
               help="'all' for full S&P 500 universe; comma-separated list for subset.")
```

**Divergences from generate_training_data.py:**
- New `--no-onnx`: useful for fast filter-ablation iteration without paying the ONNX cost. Skips the `_load_onnx_session` call entirely (bypasses warning too — `--no-onnx` is intentional, not failure).
- `--tickers all` vs `--tickers AAPL,MSFT`: gen_training_data only has `--limit`; Phase 9 backtest is more useful with explicit ticker selection for debugging a single name. Implement: `if args.tickers != "all": tickers = [t.strip().upper() for t in args.tickers.split(",")]`.
- No `--dataset-root` / `--models-root`: Phase 9 doesn't write a dataset; just the one `--out` JSON.

**Test seam:** `_load_tickers` and `_fetch_ohlc` are monkeypatchable (mirror gen_training_data L70-94). The tests should NOT exercise `--tickers` parsing — they should monkeypatch `_load_tickers` directly.

## Failure Modes & Rate Limiting (Question 9)

**Inheritance:** `RATE_LIMIT_SLEEP=0.5` between yfinance fetches. [VERIFIED in generate_training_data.py L65 + L226-227.]

**Per-ticker error swallowing:** Match the broad `except Exception` pattern at gen_training_data L224-225:

```python
for i, t in enumerate(tickers, start=1):
    try:
        df = _fetch_ohlc(t)
        if len(df) < 60:
            print(f"[{i}/{total}] {t}: insufficient history ({len(df)} bars) — skip")
            continue
        # ... detect, simulate_trade, score, accumulate
        print(f"[{i}/{total}] {t}: pos={...} unfiltered={...} ...")
    except Exception as exc:
        print(f"[{i}/{total}] {t}: unexpected error — {exc}")
    if i < total:
        time.sleep(RATE_LIMIT_SLEEP)
```

**Expected wall-time for 503 × 10y fetches:** 0.5s × 502 sleeps + ~1–3s per fetch × 503 ≈ **8–25 minutes for the fetch loop alone**. Phase 8 dataset gen had identical fetches and completed in <30 min for the fetch-and-detect portion. Phase 9 inherits.

**Failure modes & expected handling:**
| Failure | How | Behaviour |
|---------|-----|-----------|
| yfinance 429 rate-limit | Excess concurrent fetches | The 0.5s sleep mitigates; if it still hits, broad `except` swallows and skips that ticker |
| Ticker delisted / no history | Empty DataFrame | `len(df) < 60` skip; print "insufficient history" |
| Network timeout | yfinance raises | Broad `except`; print "unexpected error"; continue to next ticker |
| Ticker IPO'd post-2014 | Less than 10y of bars | Some bars present but pre-cutoff slice may be thin; the cutoff partition handles this naturally — no special case |
| ONNX session crash mid-run | onnxruntime exception in `sess.run` | Plan: catch in `_score_detection`, return None, continue. Don't abort the whole run for one bad render. |
| `models/inside_bar_v1.onnx` checksum mismatch | File exists but wrong opset | onnxruntime raises at session creation. Plan: catch in `_load_onnx_session`, log warning, return None (graceful D-14 fallback). |

**Determinism implication:** Per-ticker error skips are NOT deterministic across machines if yfinance returns different errors at different times. The `concat_sha256`-equivalent reproducibility tuple for Phase 9 (D-06: `seed, ticker_list, cutoff, ONNX_hash`) IS deterministic only when the same yfinance fetch results are received. This is the same caveat Phase 8 hit (08-04-SUMMARY note about laptop vs desktop hash difference). Document in the Phase 9 SUMMARY and don't try to engineer around it — it is upstream behaviour.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed N-bar hold | Variable hold with R:R stop/target/open | This phase (D-01) | Aligns with discretionary trader rule; encodes finance domain |
| Percent return | R-multiples | This phase (D-05) | Methodologically clean unit for fixed-R:R rule; comparable across tickers |
| One strategy column | `strategies` namespace map | This phase (D-07) | Forward-compatible for additional strategies without schema break |
| Optimistic / 50-50 intrabar | Pessimistic | This phase (D-03) | Standard backtester convention without intraday data; avoids overstating win rate |
| ONNX in main pipeline | ONNX as overlay (raw float, no tier) | This phase (D-13) | Defers tier threshold to Phase 11 once histogram is visible; keeps the methodology honest |

**Deprecated/outdated:** None within this project. Phase 9 is the first instance of a backtester in the v2.0 milestone; no prior implementation to deprecate.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Confirmation-type skew approx 60/25/15 (pin/mark_up/ice_cream) | Cutoff Feasibility | If skew is more extreme, ice_cream might fall below N≥10 — but estimate has 16× headroom, so risk is negligible |
| A2 | mplfinance per-render latency ~150–250ms | ONNX Performance | If much slower, unfiltered run could exceed 30 min wall-clock; mitigation = `--no-onnx` flag for iteration + measure first |
| A3 | ONNX YOLOv8n CPU inference ~20–60ms | ONNX Performance | If much slower (e.g., 200ms), filtered run still fits in budget; only unfiltered is at risk |
| A4 | Yfinance availability for post-cutoff data is comparable to pre-cutoff (no major API regression) | Cutoff Feasibility | If yfinance throttles or returns gaps, post-cutoff N could drop ~10–30% — still passes BT-03 N≥10 with margin |
| A5 | Detection density (0.886/ticker/year filtered) is stable across the post-cutoff period | Cutoff Feasibility | Market regime changes (e.g., 2024 was a strong-trend year) could shift density up or down by ~30%; estimates have ~10× margin |

**Assumptions A2 and A3 should be promoted to measured values during Plan 09-04 (full S&P 500 run) and recorded in the Phase 9 SUMMARY.** Phase 8 hit a similar gap (didn't benchmark per-image ONNX latency); Phase 9 should close it.

## Open Questions

1. **Per-tracking-test-cell `n` skew across confirmation_types in cross-tab `by_type_x_spring`.**
   - What we know: 6 cells max, some will be very small (e.g., `ice_cream_extended` could be < 5).
   - What's unclear: D-09 says cells with `n < 1` are omitted. Do we want a stricter floor (e.g., `n < 5` or `n < 10`) for cells in `out_of_sample`?
   - Recommendation: Honor D-09 strictly (`n < 1` only). Phase 11 UI can filter low-N cells at render time. The JSON should not pre-censor.

2. **Ticker-list provenance for the reproducibility tuple.**
   - What we know: D-06 names `(seed, ticker list, TRAIN_TEST_CUTOFF, ONNX hash)` as the reproducibility tuple. Phase 8's manifest committed the full ticker list verbatim.
   - What's unclear: Should Phase 9 re-fetch from Wikipedia each run (potential drift), or read the ticker list from `models/dataset_manifest.json["tickers"]`?
   - Recommendation: Re-fetch via `fetch_sp500_tickers()` (matches gen_training_data.py L90-91 and Phase 10 will do the same). Document in the cache header that the ticker list is the live S&P 500 at run time. Phase 11 readers compare against the cache header, not against any earlier manifest. Reproducibility within a single fetch session is preserved; cross-day variance is acceptable.

3. **`yolo_conf` rendered using right-aligned 60-bar window only — is that the intended scope?**
   - What we know: D-13 says "render each detection's 60-bar right-aligned window via `renderer.py`" — same framing as Phase 8 training.
   - What's unclear: For detections where confirmation is at index <60 (no full 60-bar history), the window is short. `renderer.render` validates `len(df) == 60` strictly (renderer.py L75-76).
   - Recommendation: Skip ONNX scoring for detections with `confirmation_bar_index < 59`; emit `yolo_conf = None` for those records (treat as if model were absent — single record-level fallback, not the global D-14 warning). Detector itself filters this naturally (`_LOOKBACK = 60` requires 60 bars before the confirmation, so this case should be impossible for any real detection — but defensive code is cheap).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x with `requirements.txt` deps | All of Phase 9 | Assumed (Phase 8 closed out 2026-05-08) | per requirements.txt | — |
| yfinance | `_fetch_ohlc` | Assumed (Phase 7+8 used it) | 0.2.65 | Per-ticker error swallow + skip |
| onnxruntime | yolo_conf overlay | Assumed (Phase 8 added) | >=1.19 | D-14 graceful: skip → null |
| `models/inside_bar_v1.onnx` | yolo_conf overlay | Available — committed at Phase 8 close | n/a | D-14 graceful: skip → null + single warning |
| `scripts.fetch_sp500.fetch_sp500_tickers` | Universe loader | Available [VERIFIED scripts/fetch_sp500.py L134-174] | — | Monkeypatched in tests |
| `scripts.pattern_scanner.detector.detect` | Detection source | Available [VERIFIED detector.py L305-384] | — | — |
| `scripts.pattern_scanner.renderer.render` + `STYLES` | yolo_conf overlay | Available [VERIFIED renderer.py L65-137] | — | — |
| `scripts.pattern_scanner.split_config.TRAIN_TEST_CUTOFF` | Cutoff arithmetic | Available [VERIFIED split_config.py L9, value="2024-01-01"] | — | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `models/inside_bar_v1.onnx` is committed but D-14 mandates a graceful fallback if absent. Plan must include the test (D-17 #8) that exercises the fallback path.

## Validation Architecture

> Phase 9 inherits `nyquist_validation: true` from `.planning/config.json`. This section feeds the planner's eventual VALIDATION.md compilation.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (standard discovery) [VERIFIED tests/conftest.py exists with addopts/markers] |
| Config file | `tests/conftest.py` (no separate pytest.ini) |
| Quick run command | `pytest tests/test_backtest_simulate_trade.py tests/test_backtest_aggregate.py -x --no-network` |
| Full suite command | `pytest tests/ -q --no-network` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BT-01 | simulate_trade stop_first resolution | unit | `pytest tests/test_backtest_simulate_trade.py::test_simulate_trade_stop_first -x` | ❌ Wave 0 |
| BT-01 | simulate_trade target_first resolution | unit | `pytest tests/test_backtest_simulate_trade.py::test_simulate_trade_target_first -x` | ❌ Wave 0 |
| BT-01 | D-03 pessimistic intrabar | unit | `pytest tests/test_backtest_simulate_trade.py::test_simulate_trade_intrabar_pessimistic -x` | ❌ Wave 0 |
| BT-01 | D-02 'open' outcome at end-of-data | unit | `pytest tests/test_backtest_simulate_trade.py::test_simulate_trade_open_outcome -x` | ❌ Wave 0 |
| BT-01 | D-09 four-slice rollup correctness | unit | `pytest tests/test_backtest_aggregate.py::test_aggregate_groupings -x` | ❌ Wave 0 |
| BT-02 | D-11 cutoff isolation (no in_sample > cutoff; no out_of_sample < cutoff) | integration (synthetic) | `pytest tests/test_backtest_cutoff.py::test_train_test_cutoff_isolation -x` | ❌ Wave 0 |
| BT-02 | D-12 unfiltered = strict superset of filtered | unit | `pytest tests/test_backtest_unfiltered_superset.py::test_unfiltered_strategy_is_superset -x` | ❌ Wave 0 |
| BT-03 | D-14 yolo_conf=null fallback when ONNX missing | unit (synthetic) | `pytest tests/test_backtest_yolo_conf_fallback.py::test_yolo_conf_null_when_onnx_missing -x` | ❌ Wave 0 |
| BT-03 | (deferred to Plan 09-04 — the full run): at least one confirmation_type clears N ≥ 10 in `out_of_sample` | manual / one-time | `python -m scripts.pattern_scanner.backtest --seed 42 --tickers all` then inspect JSON | n/a — produced by full run |

### Sampling Rate

- **Per task commit:** Run the unit tests touched by that task, e.g., `pytest tests/test_backtest_simulate_trade.py -x --no-network` after editing `simulate_trade`.
- **Per wave merge:** Full backtest test set: `pytest tests/test_backtest_*.py -q --no-network`.
- **Phase gate:** Full suite green (`pytest tests/ -q --no-network`) plus the one-time full-run that produces a `_dev/backtest_cache.json` with N ≥ 10 evidence (Plan 09-04 deliverable).

### Wave 0 Gaps

- [ ] `tests/test_backtest_simulate_trade.py` — covers BT-01 (4 sub-tests).
- [ ] `tests/test_backtest_aggregate.py` — covers BT-01 aggregation (1 sub-test).
- [ ] `tests/test_backtest_cutoff.py` — covers BT-02 isolation (1 sub-test).
- [ ] `tests/test_backtest_unfiltered_superset.py` — covers BT-02 ablation (1 sub-test).
- [ ] `tests/test_backtest_yolo_conf_fallback.py` — covers BT-03 fallback (1 sub-test).
- [ ] (No Wave 0 framework install needed — pytest already in dev environment per Phase 7+8 evidence.)

### Validation Dimensions for Backtest Correctness

1. **Deterministic reproducibility:** Same `(seed, ticker list, cutoff, ONNX hash)` must produce identical `_dev/backtest_cache.json`. Test = run twice with `--limit 3 --seed 42` against monkeypatched `_fetch_ohlc`; assert byte-identical files. (Note Phase 8's caveat: yfinance is the determinism-breaking variable across runs; the test must monkeypatch _fetch_ohlc to remove this variable.)

2. **Cutoff isolation:** No `in_sample` record has `confirmation_date >= cutoff`. No `out_of_sample` record has `confirmation_date < cutoff`. This is a per-record assertion across the entire JSON, not just at slice granularity.

3. **Aggregate math correctness:** For any cell, `n == target_count + stop_count + open_count`. `n_resolved == target_count + stop_count`. `win_rate == target_count / n_resolved` (if n_resolved > 0). Test validates these identities on hand-rolled record fixtures.

4. **Outcome resolution monotonicity:** A trade resolved at bar `j` cannot be re-resolved at bar `j+1`. Once `exit_reason ∈ {stop, target}`, the loop exits. Test = construct a 5-bar synthetic post-confirmation series where stop hits bar 2 AND target would hit bar 3; assert exit_reason is "stop", exit_date is bar 2's date.

5. **Filter ablation strict-superset:** For every `(ticker, mother_idx, conf_idx)` triple in the filtered strategy's records, the same triple appears in the unfiltered strategy's records. Test verified via `_flat_prefix_rows` reuse.

## Security Domain

> `security_enforcement` is not explicitly set in `.planning/config.json` — defaulting to enabled per template rules.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 9 is offline batch; no auth surface |
| V3 Session Management | no | Same — no sessions |
| V4 Access Control | no | Same — no access surface |
| V5 Input Validation | yes (mild) | CLI `--tickers` parser must validate against `_TICKER_RE` from detector.py L48 (`^[A-Z0-9.-]{1,10}$`) before passing to yfinance — same protection as detector.py main() L411-414 |
| V6 Cryptography | no | No secrets or crypto in this phase |

### Known Threat Patterns for Phase 9

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious ticker injection via `--tickers` | Tampering | Validate each token against `_TICKER_RE` before fetching; reject otherwise (mirror detector.py L412-414) |
| Path traversal via `--out` | Tampering | Use `Path.resolve()` and require the resolved path to be under `_dev/`; reject otherwise. Soft mitigation: this is a developer-only CLI, not an internet-facing one |
| ONNX file substitution | Tampering | The ONNX file is gitignored at the model level — anyone with write access to the repo could replace it. Mitigation: include the ONNX file SHA-256 in the cache header (D-06) so anomalous swaps are visible in diff |
| yfinance returning malicious payload | Tampering | yfinance is a pinned 0.2.65 dependency; no JSON injection surface in the OHLC numeric path. Out-of-band concern. |

**Conclusion:** Phase 9 has minimal security surface. The single concrete mitigation is the `_TICKER_RE` re-use for the `--tickers` parser. All other patterns are inherited from Phase 7+8 controls or out of scope for an offline batch script.

## Plan Decomposition Recommendation (Question 11)

**Recommended split: 3 plans + 1 optional closeout.**

### 09-01-PLAN — Core pure-functions + Wave 0 unit tests (offline, no network)
**Scope:**
- Create `scripts/pattern_scanner/backtest.py` skeleton with module docstring + constants + dataclass-free record helpers.
- Implement `simulate_trade(df, detection, stop, target) → dict` with full forward-walk loop, gap-down handling, pessimistic intrabar.
- Implement `aggregate(records, group_keys) → dict` with single-pass defaultdict accumulator.
- Wave 0 tests: `test_simulate_trade_stop_first`, `test_simulate_trade_target_first`, `test_simulate_trade_intrabar_pessimistic`, `test_simulate_trade_open_outcome`, `test_aggregate_groupings`.

**Deliverable: 5 of 8 D-17 tests green; pure functions complete; no orchestration yet.**

**Rationale:** This is the algorithmic core of Phase 9. Land it in isolation so any errors are localized. Mirrors how Phase 8 Plan 02 (renderer) was kept pure before Plan 03 (orchestrator) wired it up.

### 09-02-PLAN — Orchestrator main() + cutoff partition + filter ablation + remaining tests
**Scope:**
- Implement `_fetch_ohlc` (mirror gen_training_data L70-82 byte-for-byte).
- Implement `_load_tickers(limit)` (mirror gen_training_data L85-94).
- Implement `main(argv)`: argparse, ticker loop, single `detect(apply_trend_filters=False)` call per ticker, partition into filtered/unfiltered + in_sample/out_of_sample, call simulate_trade per detection, build records (yolo_conf=None for now), call aggregate per slice, build cache dict, write JSON.
- Tests: `test_train_test_cutoff_isolation`, `test_unfiltered_strategy_is_superset`.
- `.gitignore` update: add `_dev/backtest_cache.json`.

**Deliverable: 7 of 8 D-17 tests green; backtest runnable end-to-end with `yolo_conf=None`.**

**Rationale:** Wires the pure functions into a complete batch pipeline. ONNX is deferred to keep this plan focused. After this plan, the JSON output is fully usable for the filter-ablation portfolio narrative, just without the ML overlay column.

### 09-03-PLAN — ONNX overlay integration + fallback test
**Scope:**
- Implement `_load_onnx_session(model_path) → session | None` with D-14 warning on miss.
- Implement `_score_detection(window, sess) → float | None` reusing verify_onnx.py preprocessing.
- Wire into main() so each per-detection record gets `yolo_conf` (real float when sess available, None otherwise).
- Honor `--no-onnx` CLI flag.
- Test: `test_yolo_conf_null_when_onnx_missing` (D-14 fallback).

**Deliverable: All 8 D-17 tests green; `yolo_conf` populated end-to-end; missing-model fallback covered.**

**Rationale:** ONNX integration touches a different concern (rendering + inference) than the trade-resolution logic. Separating it lets reviewers focus on the inference path independently. If wall-clock pushes past 30 min, parallelization (ThreadPoolExecutor) is added INSIDE this plan as a refinement task, not as a new plan.

### 09-04-PLAN (optional, depends on 09-03) — Full S&P 500 run + cutoff revision decision + commit cache
**Scope:**
- Run `python -m scripts.pattern_scanner.backtest --seed 42 --tickers all --out _dev/backtest_cache.json`.
- Inspect output: confirm at least one confirmation_type has N ≥ 10 in `out_of_sample`.
- Record empirical post-cutoff distribution + per-detection wall-clock numbers in 09-04-SUMMARY.
- IF the empirical N falls below threshold (unexpected per cutoff feasibility math): propose a revised `TRAIN_TEST_CUTOFF`, update `split_config.py`, document trade-off, possibly trigger a Phase 8 retrain note (NOT a retrain).
- IF N is comfortable (expected): close out without revision.
- Add the cache file to `.gitignore` (already done in 09-02 — this plan verifies).
- DO NOT commit `_dev/backtest_cache.json` (gitignored per D-06).
- Phase 9 SUMMARY closing notes for Phase 10/11 hand-off.

**Deliverable: empirical confirmation that BT-03 N ≥ 10 is met; closeout for Phase 9.**

**Rationale:** This is the "pull the trigger" plan. Separates the empirical-validation step from the implementation work so any issues found during the real run don't block the implementation review.

**Why 3+1 not 2 plans:** Phase 8's experience showed that mixing implementation with the "real run" creates execute-mode workflow friction. Phase 8 used 5 plans (one for each major concern); Phase 9 is simpler so 3+1 is right-sized. The optional 09-04 is gated behind 09-03 — if 09-03 lands cleanly and the user wants to fast-finish, the empirical run can be folded into 09-03's verification step instead.

## Risks & Gotchas (Question 12)

### Risk 1: numpy.float64 in pandas DataFrames silently breaks reproducibility

**Specific example:** `df.iloc[i]["Open"]` returns numpy.float64. `json.dumps({"entry_price": that_value})` succeeds but the underlying repr can vary by NumPy version (`1.234500000000001` vs `1.2345`). Across two runs with identical input, the cache file has different bytes.

**Mitigation:** Wrap every numeric scalar in `float(...)` at write-time. Coverage is enforced by `test_simulate_trade_*_first` asserting `isinstance(record["entry_price"], float) and not isinstance(record["entry_price"], np.floating)` — note both checks because `np.float64` IS-A `float` in some Python distributions.

### Risk 2: Detection.confirmation_date is a string but entry_date might leak as Timestamp

**Specific example:** `entry_date = df.index[entry_idx]` returns a `pd.Timestamp`. Passing it to a dict that gets JSON-dumped raises `TypeError`. The `default=str` keyword catches it but produces `"2024-03-01 00:00:00"` not `"2024-03-01"`, breaking schema parity with `confirmation_date`.

**Mitigation:** Always `df.index[i].strftime("%Y-%m-%d")`. Mirrors detector.py L289 verbatim. Test asserts `record["entry_date"]` matches `r"\d{4}-\d{2}-\d{2}"`.

### Risk 3: yfinance auto_adjust=True hides dividend impact

**Specific example:** A 4% dividend mid-trade adjusts historical close prices retroactively. Stop/target levels (computed from cluster low/entry open) are in the adjusted price space; that's fine for R-multiples. But absolute `entry_price` and `exit_price` recorded in the JSON are also adjusted, which may surprise a reader comparing them against TradingView (which typically shows split-adjusted but not div-adjusted by default).

**Mitigation:** Honest documentation in 09-SUMMARY:
> "Prices in `_dev/backtest_cache.json` are dividend-adjusted (yfinance auto_adjust=True), matching the price space the detector and trainer operate in. R-multiples are unaffected — they are ratios within the same series. Absolute prices may differ from non-adjusted external charts on dividend-paying tickers."

[VERIFIED detector.py L392 uses `auto_adjust=True`. Phase 8 inherited this; Phase 9 inherits it. Out-of-scope to revisit.]

### Risk 4: simulate_trade walks an "open" detection forever (no cap)

**Specific example:** A detection in 2014 that never hits stop or target and was never resolved by 2026 — its record claims `hold_days = ~4400 days`, R = something. The backtester correctly marks it `open`, but a downstream reader might assume "open" means "recently active". The 4400-day field disambiguates, but the schema doesn't surface a "max hold" semantic.

**Mitigation:** No code change — D-02 explicitly chose "no timeout". Document in 09-SUMMARY that `open` outcomes can be very old; Phase 11 UI should treat `out_of_sample.open` as "still pending" only when `hold_days < some_recent_threshold` — that's a Phase 11 UI decision per D-02 alignment.

### Risk 5: ONNX session is held in memory across thousands of detections

**Specific example:** The session itself is small (~12 MB), but each `sess.run` allocates input/output tensor buffers. Across 26k detections (worst-case unfiltered + in_sample), buffer churn could fragment memory or surface a slow leak.

**Mitigation:** onnxruntime is well-tested for this scale (it's used in production servers). Empirical: the single-shot inference in verify_onnx subprocess used <100MB resident. No mitigation needed; if a leak shows up, switch to creating a new session every N detections (rare).

### Risk 6: detect() detection ordering not stable across pandas/numpy versions

**Specific example:** detect() emits detections in `mother_idx` ascending order (verified via the for-loop at detector.py L342). The detection LIST is therefore deterministic. The records list in the cache JSON is sorted by `(ticker, confirmation_date)` per Claude's discretion. As long as Phase 9 sorts after collection, ordering is stable.

**Mitigation:** Sort `records` by `(ticker, confirmation_date, mother_bar_index)` before serialization. Tested implicitly by the byte-identity test in Validation Dimension 1.

### Risk 7: Ticker list drift between Phase 8 manifest and Phase 9 fetch

**Specific example:** `models/dataset_manifest.json` was generated 2026-05-05 with 503 tickers. Wikipedia adds/removes constituents periodically. A Phase 9 run on 2026-05-09 might have 502 or 504 tickers.

**Mitigation:** The reproducibility tuple D-06 explicitly includes `ticker_list`, so the cache header captures the live list at run time. Cross-machine determinism is guaranteed only when the same fetch result was received. Document in SUMMARY. Same caveat as Phase 8's concat_sha256 cross-machine drift.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/09-backtesting-engine/09-CONTEXT.md` (this phase, in-repo) — D-01 through D-17 + canonical refs
- `.planning/phases/07-detection-engine/07-CONTEXT.md` — Detection schema, detect() public API
- `.planning/phases/08-training-pipeline/08-CONTEXT.md` — split_config, manifest reproducibility, ONNX inference shape
- `.planning/phases/08-training-pipeline/08-04-SUMMARY.md` — Empirical training-set numbers (4010 positives, 21849 negatives)
- `.planning/phases/08-training-pipeline/08-05-SUMMARY.md` — Phase 9 hand-off notes (CONFIDENCE_FLOOR=0.3, dep lock, renderer reuse)
- `models/dataset_manifest.json` — Empirical anchor for cutoff feasibility math
- `scripts/pattern_scanner/detector.py` — Detection dataclass, detect() signature, L373-380 filter logic, L388-396 _fetch_ohlc idiom
- `scripts/pattern_scanner/generate_training_data.py` — Orchestrator template, L70-94 fetch/load idioms, L100-104 cutoff arithmetic, L327-333 manifest write
- `scripts/pattern_scanner/renderer.py` — render(), STYLES, L75 60-bar validation
- `scripts/pattern_scanner/verify_onnx.py` — ONNX preprocessing (L60-82) + session creation pattern
- `scripts/pattern_scanner/split_config.py` — TRAIN_TEST_CUTOFF source
- `tests/conftest.py` — synthetic_ohlc fixture
- `tests/test_generate_training_data.py` — _spring_setup_rows + _flat_prefix_rows + patched_fetch fixture pattern
- `requirements.txt` — Locked dep set (no torch/ultralytics)

### Secondary (MEDIUM confidence)
- onnxruntime threading docs (cited inline; concurrent `sess.run` is thread-safe per general onnxruntime documentation)
- ultralytics YOLOv8 inference latency benchmarks (cited inline for ONNX cost estimation)

### Tertiary (LOW confidence)
- mplfinance per-render latency (estimated from Phase 8 dataset-gen wall time; not benchmarked in isolation)
- Confirmation-type distribution skew (estimated; manifest does not break down by type)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps already locked by Phase 8; no new additions
- Architecture: HIGH — patterns directly mirror generate_training_data.py + verify_onnx.py + detector.py
- Pitfalls: HIGH — derived from in-repo evidence (Phase 8 hit several of these explicitly)
- Cutoff feasibility: MEDIUM — empirical anchor strong (4010 / 503 / 9 = 0.886/ticker/year), but post-cutoff density assumed stable
- ONNX wall-clock: LOW — not benchmarked in Phase 8; estimates from external docs and proxy data

**Research date:** 2026-05-09
**Valid until:** ~2026-06-09 (30 days; v2.0 milestone is mid-execution and the upstream landscape is stable)

## RESEARCH COMPLETE
