---
phase: 10-batch-pipeline
reviewed: 2026-05-12T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - scripts/pattern_scanner/run_pipeline.py
  - scripts/pattern_scanner/renderer.py
  - scripts/pattern_scanner/export_aggregates.py
  - docs/projects/patterns/_backtest_aggregates.json
  - .github/workflows/nightly-pattern-scanner.yml
  - tests/test_run_pipeline_pending.py
  - tests/test_run_pipeline_window.py
  - tests/test_run_pipeline_atomic.py
  - tests/test_run_pipeline_charts.py
  - tests/test_run_pipeline_onnx_fallback.py
  - tests/test_run_pipeline_main.py
  - tests/test_run_pipeline_stats.py
  - tests/test_workflow_yaml.py
findings:
  blocker: 4
  critical: 0
  high: 5
  medium: 7
  low: 4
  total: 20
status: has_findings
---

# Phase 10: Code Review Report

**Reviewed:** 2026-05-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11 source files + 7 test files (+ 1 data file + 1 GHA workflow)
**Status:** has_findings

## Summary

Phase 10 delivers a clean, well-structured batch-pipeline orchestrator with strong test seams (monkeypatch surfaces on the module), good separation of pure builders from the I/O-driven `main()`, and disciplined re-export of Phase 9 symbols. Atomic-write semantics are correctly implemented (sibling tmp + `os.replace`), and the ONNX-missing fallback is correctly wired.

However, several genuine production defects are present:

1. **A `confirmation_date` typing slip** silently emits filesystem-hostile filenames containing spaces and colons when the detector returns a Timestamp instead of a date-string. The `default=str` fallback in `_atomic_write_json` masks this rather than catching it.
2. **`chart_path` is written to `data.json` even when the render skips** (insufficient history), causing 404s on the frontend.
3. **`_cleanup_stale_pngs` deletes non-PNG files** in `charts/` unconditionally — a `.gitkeep`, README, or thumbnail in that directory would be lost on every run.
4. **The GHA workflow has no rebase/pull before push**, so a race with the nightly DCF screener (06:00 UTC → 07:00 UTC, 1h gap) at one minute past the hour can cause non-fast-forward push failures.
5. **Per-ticker render failures fail the entire ticker** — partial rows already accumulated for that ticker are then "ghosted" via the broad-except that flips it to `failed`, simultaneously skewing the 95% completion threshold and leaving inconsistent state.

The pure builders (`build_data_json`, `build_stats_json`, `_normalize_by_type_x_spring`) are clean. The style-fallback probe is over-engineered for a deterministic deployment target but is defensive in the right way.

## Blocker Issues

### BL-01: `confirmation_date` becomes a path-hostile string in pending records

**File:** `scripts/pattern_scanner/run_pipeline.py:98-99, 580, 587`

**Issue:** `_resolve_status` writes `"confirmation_date": str(detection.confirmation_date)`. If `Detection.confirmation_date` is a `pd.Timestamp` (which `pd.Timestamp(d.confirmation_date) >= cutoff` at line 575 strongly implies — Timestamp comparison would be free), then `str(Timestamp("2024-01-10"))` returns `'2024-01-10 00:00:00'` — a string containing a space and colons.

This value is then interpolated into a filename twice:
- Line 580: `rec["chart_path"] = f"charts/{rec['ticker']}_{rec['confirmation_date']}.png"`
- Line 587: `out_png = charts_dir / f"{rec['ticker']}_{rec['confirmation_date']}.png"`

Result on Windows: `os.replace`/`f.unlink()` may fail outright because `:` is illegal in filenames. On Unix, you get `AAPL_2024-01-10 00:00:00.png` — works but breaks shell globbing, breaks the `_cleanup_stale_pngs` set-difference matcher if encoding ever drifts, and is hostile to downstream URL-encoding in the frontend.

The Phase 9 `simulate_trade` path (line 117-119) uses the original `rec["confirmation_date"]` from `simulate_trade`, which may or may not have the same shape — this is an unaudited divergence between the two code paths in `_resolve_status`.

**Fix:**
```python
# In _resolve_status — normalize once at boundary.
conf_date_str = pd.Timestamp(detection.confirmation_date).strftime("%Y-%m-%d")
return {
    ...
    "confirmation_date": conf_date_str,
    ...
}

# And after the simulate_trade delegation, force the same shape:
rec["confirmation_date"] = pd.Timestamp(rec["confirmation_date"]).strftime("%Y-%m-%d")
rec["status"] = rec.pop("exit_reason")
return rec
```
Add an assertion to lock this: `assert " " not in rec["confirmation_date"] and ":" not in rec["confirmation_date"]`.

---

### BL-02: `chart_path` set unconditionally — but render can silently skip, producing a 404

**File:** `scripts/pattern_scanner/run_pipeline.py:259-298, 580-588`

**Issue:** `_render_publication_chart` warns and `return`s without raising when:
- `start < 0` (line 283): insufficient history, conf_idx < 59
- `len(window) != 60` (line 292): slice anomaly

But in `main()` at lines 580/588, `rec["chart_path"]` is assigned BEFORE the render call. When render skips, the PNG is never written but `data.json` still claims it exists. The frontend fetches `charts/{TICKER}_{date}.png` and gets a 404 — not visible in CI logs, only on the live site.

Compounding: `_cleanup_stale_pngs` at line 608 builds `expected_filenames` from `rec['ticker']` + `rec['confirmation_date']`, so the missing PNG is "expected" — no error.

**Fix:** Inside the loop, only assign `chart_path` after a successful render. Refactor `_render_publication_chart` to return a boolean (or have render produce `out_path` and the caller verify `out_path.exists()`):
```python
out_png = charts_dir / f"{rec['ticker']}_{rec['confirmation_date']}.png"
rendered = _render_publication_chart(df, d, out_png)  # return True/False
rec["chart_path"] = f"charts/{out_png.name}" if rendered else None
```
The frontend then renders a "no chart available" placeholder when `chart_path is None`.

---

### BL-03: `_cleanup_stale_pngs` deletes non-PNG files indiscriminately

**File:** `scripts/pattern_scanner/run_pipeline.py:143-159`

**Issue:** The function name and docstring promise "PNG cleanup", but the implementation deletes any file whose name is not in `expected_filenames`:

```python
for f in charts_dir.iterdir():
    if f.is_file() and f.name not in expected_filenames:
        f.unlink()
```

A `.gitkeep` (common pattern to keep an empty directory tracked in git), a `README.md`, a thumbnail file, or any debugging artefact placed in `charts/` is deleted on every nightly run. This is a destructive side-effect not gated on the file extension.

Additionally, on a first-run-with-zero-detections day, `expected_filenames` is empty and EVERY existing PNG is deleted — also catastrophic if `failed_count` was high that night and `completed=False`.

**Fix:**
```python
def _cleanup_stale_pngs(charts_dir: Path, expected_filenames: set[str]) -> int:
    charts_dir.mkdir(parents=True, exist_ok=True)
    deleted = 0
    for f in charts_dir.iterdir():
        # Only consider .png files — never touch .gitkeep, README, etc.
        if not (f.is_file() and f.suffix.lower() == ".png"):
            continue
        if f.name not in expected_filenames:
            f.unlink()
            deleted += 1
    return deleted
```
Additionally, consider guarding against the empty-`expected_filenames` case when `failed_count > 0`: if the pipeline obviously regressed (e.g., succeeded < 50% AND expected is empty), refuse to delete.

---

### BL-04: GHA workflow has no fetch-depth or pull-rebase — race-prone push

**File:** `.github/workflows/nightly-pattern-scanner.yml:15-35`

**Issue:** The workflow uses `actions/checkout@v4` with the default `fetch-depth: 1`. The commit step then runs `git push` directly with no `git pull --rebase` first.

The nightly DCF screener (`nightly-screener.yml`, per CLAUDE.md and code comments) runs at 06:00 UTC; this workflow runs at 07:00 UTC. If the screener ever overruns its hour (it processes ~500 tickers — plausible), or if anyone pushes to `main` between 06:00 and 07:00 UTC, the pattern-scanner push will fail with non-fast-forward and the entire night's data will be lost. The workflow exits non-zero only on the push step; the data is gone.

Compounding: there is no retry, no `[skip ci]` tag on the bot commit (so any concurrent CI gets re-triggered), and no GitHub Actions concurrency group, so a `workflow_dispatch` manual run during cron will race.

**Fix:**
```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    fetch-depth: 0

- name: Commit updated pattern scanner data
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add docs/projects/patterns/data.json docs/projects/patterns/stats.json docs/projects/patterns/charts/
    if git diff --staged --quiet; then
      echo "No changes to commit."
      exit 0
    fi
    git commit -m "chore: nightly pattern scanner data update [skip ci]"
    # Rebase against the latest remote main before push (handles the 06/07 UTC race).
    for i in 1 2 3; do
      git pull --rebase origin main && git push && exit 0
      sleep 5
    done
    exit 1

concurrency:
  group: nightly-pattern-scanner
  cancel-in-progress: false
```

## High Issues

### HI-01: Per-ticker partial state on render failure

**File:** `scripts/pattern_scanner/run_pipeline.py:562-600`

**Issue:** The per-ticker loop iterates over `dets_in_window` and calls `rows.append(rec)` (line 589) for each detection BEFORE moving to the next detection. If a later detection's `_render_publication_chart` raises an exception, the broad-except at line 592 increments `failed` and the ticker is recorded as a failure — but `rows` has already accumulated the EARLIER detections from the same ticker.

The result: `data.json` carries detections from a "failed" ticker, the 95% completion-rate denominator includes that ticker as `failed`, and observability is inconsistent. The errors list has one entry for the ticker, but `data.json["detections"]` shows N rows for it.

**Fix:** Build the per-ticker rows into a local list, only extend the master `rows` after the ticker fully succeeds:

```python
for i, ticker in enumerate(tickers, start=1):
    try:
        df = _fetch_ohlc(ticker, period="6mo")
        ...
        ticker_rows: list[dict] = []
        for d in dets_in_window:
            rec = _resolve_status(df, d)
            ...
            ticker_rows.append(rec)
        rows.extend(ticker_rows)  # atomic per ticker
        succeeded += 1
    except Exception as exc:
        # Don't pollute rows with partial-ticker data.
        failed += 1
        errors.append({...})
```

---

### HI-02: `_atomic_write_json` leaks `.tmp` on serialisation failure

**File:** `scripts/pattern_scanner/run_pipeline.py:124-139`

**Issue:** If `json.dump` raises (e.g., a deeply nested non-serialisable object that even `default=str` can't repr without recursion, or an `IOError` mid-write because the disk fills up), the `with` block exits cleanly closing the file, but the `.tmp` file is never deleted. A subsequent run sees a stale `.tmp` next to a valid `data.json` — atomic-write contract preserved, but disk litter accumulates and the next run's `path.with_suffix(...)` overwrites it without issue. Still, a future cross-run reader looking for diagnostics may be confused.

**Fix:** Wrap in `try/except` with cleanup:
```python
def _atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True, default=str)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```

---

### HI-03: `default=str` in `_atomic_write_json` is a silent type-coercion footgun

**File:** `scripts/pattern_scanner/run_pipeline.py:135`

**Issue:** `json.dump(obj, f, indent=2, sort_keys=True, default=str)`. The `default=str` argument is a defense against un-serialisable types, but in this codebase it actively masks the BL-01 bug (Timestamp → `'2024-01-10 00:00:00'`). For a pipeline where the JSON shape is a public contract (frontend, downstream), the right posture is to fail loudly on unexpected types rather than coerce them into ambiguous strings.

**Fix:** Replace `default=str` with a strict serializer that explicitly handles known types and raises on the rest:
```python
def _json_default(obj):
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    raise TypeError(f"Unexpected type {type(obj).__name__} in data.json payload: {obj!r}")

json.dump(obj, f, indent=2, sort_keys=True, default=_json_default)
```
This would have caught BL-01 at write time during testing.

---

### HI-04: `_load_company_lookup` swallows `AttributeError` and `TypeError`

**File:** `scripts/pattern_scanner/run_pipeline.py:180-193`

**Issue:** The except clause catches only `(json.JSONDecodeError, OSError)`. If `data.json` parses successfully but is e.g. a list at the top level (a future schema change to the DCF screener), `data.get("stocks", [])` raises `AttributeError` — uncaught — aborting the entire pipeline. The whole pattern-scanner run dies because the screener changed its schema.

Similarly, if `row.get("ticker")` returns a non-string (a number), `str(ticker).upper()` works but downstream `company_lookup.get(ticker.upper(), ...)` calls `ticker.upper()` on the raw ticker string (line 584), which is fine — but if the lookup table contains a tuple-string mismatch, the row enrichment silently fails to `(ticker, "")` default.

**Fix:**
```python
def _load_company_lookup(path: Path | None = None) -> dict[str, tuple[str, str]]:
    target = path or SCREENER_DATA_PATH
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            warnings.warn(
                f"{target}: expected dict, got {type(data).__name__}; "
                "company/sector enrichment skipped.",
                UserWarning,
            )
            return {}
        stocks = data.get("stocks", [])
        if not isinstance(stocks, list):
            return {}
        lookup: dict[str, tuple[str, str]] = {}
        for row in stocks:
            if not isinstance(row, dict):
                continue
            ticker = row.get("ticker")
            if not ticker or not isinstance(ticker, str):
                continue
            lookup[ticker.upper()] = (
                str(row.get("company_name") or ""),
                str(row.get("sector") or ""),
            )
        return lookup
    except (json.JSONDecodeError, OSError, AttributeError, TypeError) as exc:
        warnings.warn(f"Failed to load company lookup from {target}: {exc}", UserWarning)
        return {}
```

---

### HI-05: `_resolved_publication_base_style` global is never reset between runs

**File:** `scripts/pattern_scanner/run_pipeline.py:197-256, 548`

**Issue:** `main()` clears `_render_substitutions.clear()` at line 548, but the companion global `_resolved_publication_base_style` is set once per process and never reset. In a test environment where `PUBLICATION_STYLE` is monkey-patched (or `mpf.available_styles` returns a different set per test), the second test in the same process gets the cached value from the first test — a hidden test-order dependency.

Within production this doesn't bite because there's one `main()` per `python -m` invocation, but tests run multiple `main()` calls in one process.

**Fix:** Either clear both globals at the top of `main()`, OR refactor the resolver to take its dependencies as arguments (preferred — no module-level mutable state):

```python
def main(argv=None) -> int:
    global _resolved_publication_base_style
    _resolved_publication_base_style = None
    _render_substitutions.clear()
    ...
```

## Medium Issues

### ME-01: `today` and `generated_at` use two independent `now()` calls

**File:** `scripts/pattern_scanner/run_pipeline.py:362-364, 544`

**Issue:** `main()` computes `today = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)` at line 544 (start of run). `build_data_json` computes its own `datetime.now(timezone.utc)` for `generated_at` (line 362) and a third `pd.Timestamp.now()` for `as_of_date` (line 364). These can land on different sides of midnight UTC during a slow run.

**Fix:** Pass the run's "anchor" timestamp through as a parameter:
```python
def build_data_json(detections, errors, run_id, succeeded, failed, window_days, now_utc: datetime):
    generated_at = now_utc.isoformat()
    as_of_date = now_utc.strftime("%Y-%m-%d")
    ...
```
In `main()`, capture one `now_utc = datetime.now(timezone.utc)` at the top and thread it through.

---

### ME-02: `_window_cutoff` ignores US market holidays

**File:** `scripts/pattern_scanner/run_pipeline.py:68-75`

**Issue:** Documented in the docstring — uses `BDay`, which only skips Saturday/Sunday. A US-market month with multiple holidays (e.g., Thanksgiving week + Christmas) can shift the effective trading-day cutoff by 2-3 trading days relative to the intent. Detections at the boundary may be incorrectly included or excluded.

**Fix:** Use `pandas.tseries.offsets.CustomBusinessDay` with a US holiday calendar:
```python
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

_US_BDAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())

def _window_cutoff(today: pd.Timestamp, window_days: int) -> pd.Timestamp:
    return today - window_days * _US_BDAY
```
Or accept the documented imprecision and document the user-visible consequence.

---

### ME-03: GHA workflow has no failure observability

**File:** `.github/workflows/nightly-pattern-scanner.yml`

**Issue:** When `pipeline_status.completed = False` (below 95% threshold), the pipeline still exits 0 (per `return 0` at line 649 of `run_pipeline.py`). The workflow succeeds, the bad data is committed, and the only signal is a banner on the live frontend. There's no Slack/email/issue-creation hook for failure modes.

**Fix:** Add a post-step that reads the freshly written `data.json` and fails the workflow when `completed=False`:
```yaml
- name: Verify pipeline completed
  run: |
    python -c "
    import json, sys
    data = json.load(open('docs/projects/patterns/data.json'))
    ps = data['pipeline_status']
    if not ps['completed']:
        print(f'::warning::pipeline_status.completed=False: '
              f'succeeded={ps[\"succeeded_count\"]} failed={ps[\"failed_count\"]}')
        sys.exit(1)
    "
```
Combined with a `if: failure()` block that opens a GitHub issue.

---

### ME-04: `_render_substitutions` is never persisted to `data.json` or `stats.json`

**File:** `scripts/pattern_scanner/run_pipeline.py:200, 230-254, 642-648`

**Issue:** Style-substitution events are accumulated in a module-level list and surfaced only in the final `print()` line. If the production runner installs a slimmer `mplfinance` that lacks `nightclouds`, the substitution will appear in CI logs (which are then discarded after 90 days) but will not be visible in the committed `data.json` for forensic later analysis.

**Fix:** Add `style_substitutions: list[dict]` to `pipeline_status` in `build_data_json`, populated from `_render_substitutions`.

---

### ME-05: `export_aggregates.py` does not use atomic write

**File:** `scripts/pattern_scanner/export_aggregates.py:82-86`

**Issue:** `args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")` — a naked write. If the process is killed mid-write, the committed `_backtest_aggregates.json` is partially corrupted. Since this file is git-tracked, that corruption is persistent.

**Fix:** Use `run_pipeline._atomic_write_json` here too (after extracting it to a shared utility module to avoid the circular import). Alternatively, write to `.tmp` + `os.replace`:
```python
import os
tmp = args.out.with_suffix(args.out.suffix + ".tmp")
tmp.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(tmp, args.out)
```

---

### ME-06: `errors[].message` truncation does not preserve UTF-8 boundaries

**File:** `scripts/pattern_scanner/run_pipeline.py:597`

**Issue:** `"message": str(exc)[:500]` — slicing a string by character count. For a Python `str`, this is safe. But the downstream JSON encoding then serialises this; if `exc` contains non-ASCII content (yfinance occasionally surfaces ticker symbols with `.` or accented characters from upstream APIs), a 500-char slice could land mid-grapheme. Low likelihood, but cleaner to use a sentinel: append `"... [truncated]"` if truncated, so readers know.

**Fix:**
```python
msg = str(exc)
if len(msg) > 500:
    msg = msg[:497] + "..."
errors.append({"ticker": ticker, "stage": "fetch_or_detect", "message": msg, ...})
```

---

### ME-07: `_render_publication_chart` mutates a renderer module-level constant

**File:** `scripts/pattern_scanner/run_pipeline.py:314-319`

**Issue:** When the resolved style differs from `PUBLICATION_STYLE.base_style`, the wrapper temporarily rebinds `renderer.PUBLICATION_STYLE` to a `replace()`-d copy. This is concurrency-hostile: any other thread (or, more realistically, any test running `renderer.render_publication_chart` directly while this wrapper is mid-flight) sees the mutated constant. The `try/finally` guard is correct for single-threaded sequential calls but not for `pytest-xdist` or future parallelisation.

**Fix:** Add a `style` parameter to `renderer.render_publication_chart(df, detection, out_path, *, style: RenderStyle = PUBLICATION_STYLE)`, and pass the resolved style explicitly instead of rebinding the module attribute.

## Low Issues

### LO-01: `_load_company_lookup` is called even when `--tickers` is a tiny list

**File:** `scripts/pattern_scanner/run_pipeline.py:546`

**Issue:** Even for a 1-ticker smoke test, the full screener `data.json` is parsed and an entire `{ticker: (name, sector)}` dict is built (~500 entries). Minor wasted I/O and memory. Not a correctness issue.

**Fix:** Lazy-load on first lookup, or accept the cost (it's ~1 file read of <500KB).

---

### LO-02: `--no-onnx` does not log/warn that scoring is disabled

**File:** `scripts/pattern_scanner/run_pipeline.py:496-499, 543`

**Issue:** When `--no-onnx` is passed, the pipeline silently sets `sess = None`. The only signal that ONNX scoring is off is `yolo_conf: null` in every output row. A future operator using `--no-onnx` for debugging may forget it's set.

**Fix:** Print a one-line notice at startup:
```python
if args.no_onnx:
    print("[run_pipeline] --no-onnx: ONNX scoring disabled; yolo_conf will be null on all rows.")
    sess = None
else:
    sess = _load_onnx_session(ONNX_PATH)
```

---

### LO-03: Test `test_main_smoke_with_synthetic_ohlc` uses `--limit 5` without asserting `len(detections)`

**File:** `tests/test_run_pipeline_main.py:123-170`

**Issue:** The smoke test asserts the data.json shape but never validates that any detections were produced from the 5 synthetic-OHLC tickers. The synthetic OHLC is monotonic-rising (line 45-47), which is unlikely to produce any pin/mark_up/ice_cream pattern detection. The test therefore validates the empty-detections path rather than the populated path. Combined with the broader assertion `isinstance(data["detections"], list)`, the test passes for `detections == []`.

**Fix:** Either explicitly assert `len(data["detections"]) == 0` to lock the contract, OR feed a fixture known to produce detections (the `_spring_setup_rows` used in `test_run_pipeline_onnx_fallback.py`).

---

### LO-04: `print()` statements throughout `main()` are not log-leveled

**File:** `scripts/pattern_scanner/run_pipeline.py:566, 591, 600, 642-648`

**Issue:** Per-ticker progress and final summary go through `print()`, which dumps to stdout unconditionally. In CI this is fine; for any future scenario where this module is imported and called from another orchestrator (the structural pattern this codebase encourages), the consumer can't filter or suppress these messages.

**Fix:** Use `logging.getLogger(__name__)` with `info` / `warning` levels. Configure a basic handler in `__main__` only. Out-of-scope-but-noted: structured logging would let the GHA workflow grep for `[run_pipeline] complete:` lines.

---

_Reviewed: 2026-05-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
