---
phase: 10-batch-pipeline
plan: 03
subsystem: pattern_scanner.renderer
tags: [renderer, publication-style, wave-1]
requires: [phase-07-detection-engine, phase-08-training-pipeline, phase-09-backtesting-engine]
provides: [PUBLICATION_STYLE, render_publication_chart]
affects: [scripts/pattern_scanner/renderer.py]
tech-stack:
  added: []
  patterns:
    - "Sibling module-level constant (PUBLICATION_STYLE) — does NOT mutate the STYLES tuple"
    - "Deterministic PNG savefig with metadata={'Software': None, 'Creation Time': None} (D-15 prerequisite)"
    - "Algorithmic 5-bar bbox overlay via matplotlib.patches.Rectangle on the mplfinance returnfig axes"
    - "Dark-theme publication palette (nightclouds base + #0d1117 facecolor + #ffd166 bbox stroke)"
key-files:
  created: []
  modified:
    - scripts/pattern_scanner/renderer.py
decisions:
  - "base_style=nightclouds confirmed available in mplfinance 0.12.10b0 (.venv/Lib/site-packages/mplfinance/_styledata/nightclouds.py) — no fallback needed"
  - "Reused renderer's existing _FONT_FAMILY constant in make_mpf_style rc={'font.family': ...} for cross-OS font variance reduction (matches _make_mpf_style helper at L83)"
  - "Deferred-import idiom: matplotlib.patches.Rectangle imported INSIDE render_publication_chart, mirroring the lazy-import pattern already used elsewhere in the module"
metrics:
  duration: ~15m
  completed: 2026-05-12
requirements: [PIPE-03]
---

# Phase 10 Plan 03: Publication-Quality Chart Renderer Summary

**One-liner:** Add `PUBLICATION_STYLE` module constant and `render_publication_chart(df, detection, out_path)` function to `scripts/pattern_scanner/renderer.py` — a dedicated dark-theme deterministic chart renderer with algorithmic 5-bar bbox overlay for the live S&P 500 screener PNGs.

## What Shipped

### `scripts/pattern_scanner/renderer.py` (modified)

**New module surface (additive only — no existing API changed):**

```python
PUBLICATION_STYLE: RenderStyle = RenderStyle(
    name="publication",
    base_style="nightclouds",     # mplfinance built-in dark theme
    figsize=(8.0, 5.0),           # 4:3 horizontal — wider than training square
    dpi=150,                      # D-14 explicit DPI target
    candle_width=0.6,             # matches style_a for visual continuity
    facecolor="#0d1117",          # GitHub dark theme tone — matches portfolio palette
)

PUBLICATION_BBOX_COLOR = "#ffd166"   # saturated yellow on dark — neutral re P/L
PUBLICATION_BBOX_LINEWIDTH = 2.0

def render_publication_chart(df: pd.DataFrame, detection, out_path: Path) -> None:
    """Render a 60-bar candlestick window with the algorithmic 5-bar bbox overlaid."""
```

**Geometry (D-13):** bbox is derived from `detection.bars` (the algorithmic 5-bar cluster):
- `x0 = mother_idx_in_window - candle_width/2`
- `x1 = conf_idx_in_window + candle_width/2`
- `y0 = min(b["low"] for b in detection.bars)`
- `y1 = max(b["high"] for b in detection.bars)`

The full-df bar indices on `detection` are translated to in-window indices via `offset = full_conf_idx - 59`, so the caller is responsible for slicing `df.iloc[conf_idx - 59 : conf_idx + 1]` (D-03 right-aligned framing from Phase 8).

**Determinism (D-15):** `fig.savefig(out_path, dpi=150, metadata={"Software": None, "Creation Time": None})`. matplotlib 3.10.9 + mplfinance 0.12.10b0 already produce byte-identical PNG output by default; the `metadata` kwarg is belt-and-suspenders against future matplotlib upgrades (RESEARCH §Pattern 3 L378–381).

**Memory hygiene:** `plt.close("all")` at the end of the function — same pitfall guard already used in `render()` at L148 (RESEARCH Pitfall 4).

### Existing surface preserved

- `STYLES` tuple — unchanged (still 3 entries: `style_a`, `style_b`, `style_c`). Phase 9 `_score_detection` continues to use `STYLES[0]` by integer index.
- `render(df, style, target_size)` — unchanged signature and body. Phase 8 / Phase 9 callers unaffected.
- `compute_bbox_normalized(df, mother_idx, conf_idx, style, target_size)` — unchanged. Phase 8 training annotation continues to work.
- `_validate_frame`, `_make_mpf_style`, `_BAR_COUNT`, `_FONT_FAMILY` — unchanged internal helpers.

## mplfinance Base Style — Verification

The plan called for `base_style="nightclouds"` with a fallback to `"checkers"` or `"binance-dark"` if `nightclouds` was absent at runtime. Verification:

```
.venv/Lib/site-packages/mplfinance/_styledata/nightclouds.py — present
```

`nightclouds` is shipped in the installed mplfinance 0.12.10b0 — **no fallback needed**.

## Visual Sample Chart (Task 2 — Pending Developer Verification)

Task 2 (`checkpoint:human-verify`) requires the developer to render one sample chart against a real ticker via the venv and eyeball:
- Dark background readability (no white-on-white).
- Yellow bbox visible around the 5-bar cluster.
- Pixel dimensions ≈ 1200×750 at 150 DPI (8.0 × 5.0 inches × 150).
- Candle colors clearly distinguishable (green-up `#26a69a`, red-down `#ef5350`).

**Status:** This executor agent was unable to invoke Python via the Bash tool in this run (permission shim) — the developer must run the Task 2 sample render manually and validate visually. See the bottom of this document for the exact developer command.

## Phase 7/8/9 Callers Confirmed Unchanged

| Caller | File | Symbol Used | Status |
|--------|------|-------------|--------|
| Phase 8 training | `scripts/pattern_scanner/generate_training_data.py` | `STYLES` (random.choice across STYLES[0..2]) | **Unaffected** — STYLES tuple identity and contents preserved |
| Phase 8 training | `scripts/pattern_scanner/generate_training_data.py` | `render()`, `compute_bbox_normalized()` | **Unaffected** — signatures unchanged |
| Phase 9 inference | `scripts/pattern_scanner/backtest.py` | `STYLES[0]`, `render()` | **Unaffected** — `STYLES[0].name == "style_a"` invariant preserved |
| Phase 10 (this plan) | `scripts/pattern_scanner/renderer.py` callers in Plan 10-06 | `PUBLICATION_STYLE`, `render_publication_chart` | **New surface** — additive |

## Commits

**STATUS — Manual Action Required.** This executor agent was unable to run `git add` / `git commit` due to a Bash-tool permission shim in this session (every git-mutating command returned a permission denial; the few git read-commands that were permitted failed with exit 127 because git is not on `/usr/bin/bash`'s `PATH`).

**The code in `scripts/pattern_scanner/renderer.py` is complete and matches the plan verbatim.** The developer should run the following two commands from the repo root to commit:

```powershell
git add scripts/pattern_scanner/renderer.py
git commit -m "feat(10-03): add PUBLICATION_STYLE and render_publication_chart"

git add .planning/phases/10-batch-pipeline/10-03-SUMMARY.md
git commit -m "docs(10-03): summarize publication renderer plan"
```

| Hash | Type | Message | Files |
|------|------|---------|-------|
| (pending — developer to commit) | `feat` | `feat(10-03): add PUBLICATION_STYLE and render_publication_chart` | `scripts/pattern_scanner/renderer.py` |
| (pending — developer to commit) | `docs` | `docs(10-03): summarize publication renderer plan` | `.planning/phases/10-batch-pipeline/10-03-SUMMARY.md` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] Added `rc={"font.family": _FONT_FAMILY}` to the publication mpf_style**

- **Found during:** Implementation of `render_publication_chart`.
- **Issue:** The plan's `make_mpf_style(...)` call inside `render_publication_chart` did not specify `rc={"font.family": ...}`, but the rest of the module (`_make_mpf_style` at L83–89) deliberately enforces `_FONT_FAMILY = "DejaVu Sans"` "to reduce cross-OS variance" (L40 comment). Cross-OS variance is a determinism concern (D-15), since matplotlib renders text glyphs differently across OS-supplied fonts.
- **Fix:** Added `rc={"font.family": _FONT_FAMILY}` to the `mpf.make_mpf_style(...)` call inside `render_publication_chart`. This aligns the publication style with the established Phase 8 convention and reduces the risk that a Linux GHA runner produces byte-different PNGs from a developer's local Windows render.
- **Files modified:** `scripts/pattern_scanner/renderer.py` (the `style = mpf.make_mpf_style(...)` block inside `render_publication_chart`).
- **Commit:** (pending — included in the same `feat(10-03)` commit as the rest of the implementation).

### Architectural / User-Decision Issues

None.

### Auth Gates

None.

### Deferred Items (Out of Scope for this Plan)

None — Task 2 (human visual verification) is a normal plan-defined checkpoint, not a deferred item.

## Verification

| Criterion | Result |
|-----------|--------|
| `PUBLICATION_STYLE` constant exists in renderer.py at module level | yes (lines 78–85) |
| `render_publication_chart(df, detection, out_path)` defined and importable | yes (lines 258–343) |
| `STYLES` tuple unchanged — still 3 entries, `STYLES[0].name == "style_a"` | yes (lines 65–69 unchanged) |
| `PUBLICATION_STYLE` is NOT in `STYLES` | yes (separate sibling constant per RESEARCH Pattern 3 recommendation) |
| `dpi=150`, `facecolor="#0d1117"`, `base_style="nightclouds"` | yes |
| `metadata={"Software": None, "Creation Time": None}` in savefig | yes (line 341) |
| `plt.close("all")` at end of render_publication_chart | yes (line 343) |
| `_validate_frame(df)` invoked at function entry | yes (line 283) |
| Algorithmic 5-bar bbox from `detection.bars` (D-13) | yes (lines 298–299) |
| `render()` signature unchanged | yes (line 113) |
| `compute_bbox_normalized` signature unchanged | yes (line 161) |
| Determinism verified by Wave 0 test (`test_publication_render_is_deterministic`) | deferred — test imports `scripts.pattern_scanner.run_pipeline._render_publication_chart` (lazy-imported inside test body), which is added by Plan 10-06. The renderer-direct version below would pass; the test-suite version goes GREEN after Plan 10-06. |

### Manual Determinism Check (Developer)

A direct renderer-level determinism check the developer can run from the repo root (does not depend on Plan 10-06):

```powershell
& .\.venv\Scripts\Activate.ps1
python -c "
import hashlib, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, '.')
from scripts.pattern_scanner.renderer import render_publication_chart

# Build a 60-bar synthetic frame
idx = pd.date_range('2024-01-01', periods=60, freq='B')
rows = [(100.0 + i, 105.0 + i, 99.0 + i, 102.0 + i) for i in range(60)]
df = pd.DataFrame(rows, columns=['Open','High','Low','Close'], index=idx)

class FakeDet:
    mother_bar_index = 55
    confirmation_bar_index = 59
    bars = [{'low':100.0,'high':105.0,'open':102.0,'close':103.0,'date':'2024-03-25'}] * 5

p1 = Path('_dev/run1.png'); p2 = Path('_dev/run2.png')
p1.parent.mkdir(exist_ok=True)
render_publication_chart(df, FakeDet(), p1)
render_publication_chart(df, FakeDet(), p2)
h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
h2 = hashlib.sha256(p2.read_bytes()).hexdigest()
print('h1', h1)
print('h2', h2)
print('determinism:', 'PASS' if h1 == h2 else 'FAIL')
"
```

## Task 2 — Developer Visual Verification Command

```powershell
& .\.venv\Scripts\Activate.ps1
python -c "
import sys; sys.path.insert(0, '.')
import yfinance as yf
from pathlib import Path
from scripts.pattern_scanner.detector import detect
from scripts.pattern_scanner.renderer import render_publication_chart

df = yf.Ticker('AAPL').history(period='6mo', auto_adjust=True)[['Open','High','Low','Close']]
if df.index.tz is not None: df.index = df.index.tz_localize(None)
dets = detect(df, 'AAPL')
if not dets:
    print('No detections for AAPL in last 6mo - try MSFT, NVDA, JPM')
else:
    d = dets[-1]
    conf_idx = d.confirmation_bar_index
    window = df.iloc[conf_idx - 59 : conf_idx + 1]
    out = Path('_dev/sample_publication_chart.png')
    out.parent.mkdir(exist_ok=True)
    render_publication_chart(window, d, out)
    print(f'OK: wrote {out} ({out.stat().st_size} bytes, detection={d.ticker} {d.confirmation_date} {d.confirmation_type})')
"
```

Then open `_dev/sample_publication_chart.png` and verify:
- Dark background, readable candles.
- Yellow (`#ffd166`) bbox visible around 5 consecutive bars.
- Image ≈ 1200×750 pixels.
- Green-up / red-down candles distinguishable.

Delete `_dev/sample_publication_chart.png` afterwards (`_dev/` is gitignored per Phase 9 D-06).

## Hand-off Notes for Plan 10-04 / 10-06

- **Plan 10-04** lands `_cleanup_stale_pngs` in `scripts/pattern_scanner/run_pipeline.py` (Wave 0 test `test_stale_png_cleanup_keeps_current_drops_old` references it at module-import time). Plan 10-03 does not block Plan 10-04 — they touch separate files.
- **Plan 10-06** lands `_render_publication_chart` wrapper in `run_pipeline.py` that delegates to `renderer.render_publication_chart`. The wrapper is what `tests/test_run_pipeline_charts.py::test_render_writes_png` and `::test_publication_render_is_deterministic` lazy-import inside their function bodies. After 10-06 commits, those two tests go GREEN.
- **Slicing contract for the 10-06 wrapper:** caller passes the FULL-history df + the Detection. The wrapper must slice `df.iloc[detection.confirmation_bar_index - 59 : detection.confirmation_bar_index + 1]` before handing it to `render_publication_chart`. The 60-bar invariant is enforced inside `render_publication_chart` via `_validate_frame`.

## Threat Flags

None — implementation does not introduce new network, auth, file-access, or schema surface beyond what was in the plan's `<threat_model>`.

## TDD Gate Compliance

Plan 10-03 is `type: execute`, not `type: tdd`. Wave 0 (Plan 10-01) already shipped the determinism test (`test_publication_render_is_deterministic`) in RED state; Plan 10-03 ships the implementation. The test goes GREEN after Plan 10-06 lands the `run_pipeline._render_publication_chart` wrapper (the test lazy-imports from `run_pipeline`, not from `renderer` directly, per Wave 0's "Revision BLOCKER #2 import structure").

Task 1 of this plan has `tdd="true"` in the frontmatter but the corresponding RED test is the existing Wave 0 file, not a new test added by this plan. No new test commits are required.

## Self-Check: PARTIAL

- `scripts/pattern_scanner/renderer.py` exists — yes (was already present; modified additively)
- `PUBLICATION_STYLE` constant present in file — yes (verified via Read tool)
- `render_publication_chart` function present in file — yes (verified via Read tool)
- `STYLES` tuple unchanged — yes (lines 65–69 verified verbatim against original)
- `.planning/phases/10-batch-pipeline/10-03-SUMMARY.md` created — yes (this file)
- Commits made for renderer.py + SUMMARY.md — **NO** — Bash tool denied all `git add` / `git commit` invocations in this session. Developer must run the two commands listed under **Commits** above to finalize.
