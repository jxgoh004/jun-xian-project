# Phase 8: Training Pipeline — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 18 (12 new, 3 modified, 3 new committed artifacts/fixtures)
**Analogs found:** 13 / 18 with strong-or-good codebase analog; 5 have **no codebase analog** (matplotlib/Agg, mplfinance, ultralytics, onnxruntime, subprocess venv) — those follow §RESEARCH.md §Code Examples directly.

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `scripts/pattern_scanner/renderer.py` (new) | pure-function module | DataFrame → bytes (transform) | `scripts/pattern_scanner/detector.py` (pure `detect()` + CLI shim) | **role match** — pure-function-with-CLI |
| `scripts/pattern_scanner/generate_training_data.py` (new) | orchestrator / batch CLI | S&P 500 ticker iteration → file-I/O (PNG + label + manifest) | `scripts/fetch_sp500.py` (S&P 500 batch with argparse, per-ticker error handling, JSON manifest) | **exact** |
| `scripts/pattern_scanner/train.py` (new) | training entry / CLI wrapper | dataset dir → `.onnx` artifact + `training_summary.json` | `scripts/pattern_scanner/detector.py` (CLI wrapper around library, deferred import idiom) | **role match** — thin CLI on top of one library call |
| `scripts/pattern_scanner/verify_onnx.py` (new) | verifier / round-trip gate | onnx + fixture PNG → exit code | (none in codebase — subprocess+venv is novel) | **no analog** — follow RESEARCH §Code Examples — Verifier |
| `scripts/pattern_scanner/split_config.py` (new) | config (constants only) | (none) | `scripts/fetch_sp500.py` lines 34-43 (`_DISCOUNT_TABLE_US` UPPER_SNAKE_CASE module constant) | **partial** — same UPPER_SNAKE_CASE idiom |
| `requirements-training.txt` (new) | dep file | n/a | `requirements-dev.txt` (single-purpose extra requirements file) | **exact** |
| `tests/test_renderer.py` (new) | unit test (offline) | DataFrame → asserted PNG bytes | `tests/test_detector_schema.py` (pure-unit, uses `synthetic_ohlc`, no `@network`) | **exact** |
| `tests/test_generate_training_data.py` (new) | unit test (offline + tmp_path) | small synthetic ticker subset → asserted dataset structure | `tests/test_detector_schema.py` (synthetic builder + assertions) | **role match** |
| `tests/test_onnx_round_trip.py` (new) | unit / smoke test | committed `.onnx` + fixture PNG → assertions | `tests/test_detector_known_setups.py` (artifact-driven assertions, may use `@pytest.mark.network` for the subprocess gate) | **role match** |
| `tests/test_detector_apply_trend_filters_kwarg.py` (new) | regression test for Phase 7 contract preservation | synthetic OHLC → detector list | `tests/test_detector_schema.py` (`_spring_setup_rows` builder, `synthetic_ohlc` fixture) | **exact** |
| `tests/fixtures/known_positive_*.png` (new) | committed binary fixture | n/a | (none — first fixture binary in repo) | **no analog** — see §Shared Patterns "Committed Binary Fixtures" |
| `models/inside_bar_v1.onnx` (new) | committed binary artifact | n/a | (none — first committed model artifact) | **no analog** — committed under regular git per CONTEXT D-13 |
| `models/dataset_manifest.json` (new) | committed JSON manifest | n/a | `docs/projects/screener/data.json` (committed JSON snapshot from a batch script — same "regenerable artifact, committed for transparency" pattern) | **role match** |
| `models/training_summary.json` (new) | committed JSON manifest | n/a | `docs/projects/screener/data.json` (committed `updated_at` + payload pattern) | **role match** |
| `scripts/pattern_scanner/detector.py` (modified) | pure-function module | (no change to flow) | itself — adds **one default-true kwarg** that preserves all 23 existing call sites | **self** |
| `requirements.txt` (modified) | dep file | n/a | itself — append four lines below existing | **self** |
| `.gitignore` (modified) | config | n/a | itself — append two lines | **self** |

---

## Pattern Assignments

### `scripts/pattern_scanner/renderer.py` (pure-function module, transform)

**Analog:** `scripts/pattern_scanner/detector.py` (Phase 7) — same package, same "pure function + CLI shim" idiom mandated by RESEARCH §Architecture Pattern 2.

**Module-header pattern** (detector.py lines 1-30, 31-48):

```python
"""Inside bar spring detector — pure-Python rule-based candlestick pattern detection.

Public API:
    detect(df: pd.DataFrame, ticker: str) -> list[Detection]
...
CLI:
    python scripts/pattern_scanner/detector.py AAPL
"""
from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── Module constants ────────────────────────────────────────────────────────
_LOOKBACK = 60
_ATR_PERIOD = 14
```

Renderer should mirror: `from __future__ import annotations`, stdlib group, third-party group, local group, then UPPER_SNAKE_CASE module constants for `_TARGET_SIZE = 640`, `_BAR_COUNT = 60`. Section dividers `# ── … ──` are required by CONVENTIONS.md.

**Pure-function signature pattern** (detector.py line 305):

```python
def detect(df: pd.DataFrame, ticker: str) -> List[Detection]:
    """Detect bullish inside bar spring setups in daily OHLC data.

    Args:
        df: DataFrame with flat columns Open/High/Low/Close and a tz-naive
            DatetimeIndex (yfinance auto_adjust + tz_localize(None) format).
        ticker: uppercase symbol; included in each Detection record.

    Returns:
        List of Detection records, one per emitted setup. ...
    """
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"detect() requires columns {required}; missing: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("detect() requires a DatetimeIndex on df.")
```

Renderer's `render(df, style, target_size=640) -> bytes` should validate identically: explicit `if len(df) != 60: raise ValueError(...)` with matching message style. `frozen=True` `@dataclass` for `RenderStyle` mirrors detector.py's `Detection`.

**Deferred-import pattern for heavy deps** (detector.py lines 380-388):

```python
def _fetch_ohlc(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Fetch daily OHLC via yfinance. Deferred import keeps unit tests fast."""
    import yfinance as yf  # noqa: WPS433 — deferred by design

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    df = df[["Open", "High", "Low", "Close"]]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df
```

**Adaptation needed:** matplotlib must be configured BEFORE `pyplot`/`mplfinance` imports — the deferred-import idiom does NOT apply to `matplotlib.use("Agg")`. The fix is **module-top** (not deferred):

```python
import matplotlib
matplotlib.use("Agg")  # MUST come before pyplot/mplfinance import
import matplotlib.pyplot as plt
import mplfinance as mpf
```

This is **novel for the codebase** — no existing module forces a matplotlib backend. Document in the module docstring.

**CLI wrapper pattern** (detector.py lines 391-410):

```python
def main(argv: List[str]) -> int:
    """CLI entry point. Returns process exit code.

    argv mimics sys.argv (argv[0] is the program name). ...
    """
    if len(argv) < 2:
        print(
            "Usage: python scripts/pattern_scanner/detector.py <TICKER>",
            file=sys.stderr,
        )
        return 1
    # ... validation + work ...
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Renderer's CLI is optional but if added must follow this exact shape (return-code-based, not raise).

---

### `scripts/pattern_scanner/generate_training_data.py` (orchestrator, batch file-I/O)

**Analog:** `scripts/fetch_sp500.py` — exact match: same role (S&P 500 batch orchestration), same data flow (per-ticker iteration → JSON output), and explicitly named in CONTEXT.md §Canonical References as the template.

**Module docstring + imports + sys.path hack** (fetch_sp500.py lines 1-29):

```python
"""
fetch_sp500.py — S&P 500 batch DCF script

Fetches all S&P 500 tickers from Wikipedia, computes DCF intrinsic values
using the same logic as api_server.py and the calculator's computeIV function,
and writes a static data.json snapshot to docs/projects/screener/data.json.

Usage:
    python scripts/fetch_sp500.py             # process all ~500 tickers
    python scripts/fetch_sp500.py --limit 10  # process first 10 tickers (testing)
    python scripts/fetch_sp500.py --seed       # write empty seed file only
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime

import pandas as pd

# Add project root to sys.path so fetcher modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yahoo_finance_fetcher import YahooFinanceFetcher
from finviz_fetcher import FinVizFetcher
```

Generator must replicate the `sys.path.insert(...)` block — `scripts/pattern_scanner/` cannot import `scripts.pattern_scanner.detector` cleanly without it when invoked as a script.

**Argparse pattern with `--limit` and `--seed`** (fetch_sp500.py lines 444-459):

```python
parser = argparse.ArgumentParser(
    description="Fetch S&P 500 data and compute DCF intrinsic values."
)
parser.add_argument(
    "--limit",
    type=int,
    default=None,
    metavar="N",
    help="Process only the first N tickers (for local testing).",
)
parser.add_argument(
    "--seed",
    action="store_true",
    help="Write an empty seed data.json and exit immediately.",
)
args = parser.parse_args()
```

**Adaptation:** in Phase 8, `--seed` must be `type=int, required=True` (RESEARCH §Pattern 3 — deterministic seeded outputs), NOT `action="store_true"`. Different semantics but argparse shape is the analog.

**S&P 500 ticker fetcher with defensive column lookup** (fetch_sp500.py lines 134-174) — generator should reuse the same Wikipedia-scrape helper or import-and-call `fetch_sp500_tickers()`:

```python
def fetch_sp500_tickers():
    """
    Fetch the current S&P 500 constituent list from Wikipedia.
    Searches for a column whose name contains 'symbol' or 'ticker'
    (case-insensitive) to survive Wikipedia table format changes.

    Returns a list of normalised ticker strings (e.g. 'BRK-B').
    """
    import io
    import requests as req_lib

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": ("Mozilla/5.0 ... Chrome/124.0.0.0 ...")}
    resp = req_lib.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]

    ticker_col = None
    for col in df.columns:
        if "symbol" in col.lower() or "ticker" in col.lower():
            ticker_col = col
            break
    ...
    return [t.replace(".", "-") for t in tickers]
```

**Recommendation for generator:** import `fetch_sp500_tickers` from `scripts.fetch_sp500` rather than copy-paste. Single source of truth.

**Per-ticker error handling + progress logging** (fetch_sp500.py lines 501-537):

```python
total = len(tickers)
stocks = []

for i, ticker in enumerate(tickers, start=1):
    try:
        record = process_ticker(ticker, i, total)
    except Exception as exc:
        print(f"[{i}/{total}] {ticker}: unexpected error — {exc}")
        record = { ... null record ... }
    stocks.append(record)

    # Rate limiting — avoid Yahoo Finance 429 errors
    if i < total:
        time.sleep(0.5)
```

This is the **exact pattern** generator must adopt for the per-ticker loop: `[i/total]` progress prefix, broad `except Exception` with logged ticker, no early exit on a single failure, the **0.5 s sleep between fetches** is the established rate-limit cadence — keep it.

**yfinance idiom for daily history** (detector.py lines 380-388 above + `test_detector_known_setups.py` lines 60-67):

```python
def _fetch(ticker: str) -> pd.DataFrame:
    """Fetch 10y daily OHLC via yfinance with the same normalisation as the detector CLI."""
    df = yf.Ticker(ticker).history(period="10y", auto_adjust=True)[
        ["Open", "High", "Low", "Close"]
    ]
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df
```

Generator's per-ticker fetch must use this exact 4-line normalisation block (`auto_adjust=True`, `tz_localize(None)`, four-column projection) so the resulting DataFrame is the same shape `detect()` consumes — RESEARCH §Pitfall #6 hinges on yfinance idiom uniformity.

**JSON manifest write** (fetch_sp500.py lines 539-543):

```python
updated_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
output = {"updated_at": updated_at, "stocks": stocks}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
```

Generator's `dataset_manifest.json` write follows this exact shape (`indent=2`, `encoding="utf-8"`, ISO-8601 UTC timestamp). RESEARCH §Code Examples uses `Path.write_text(json.dumps(manifest, indent=2))` — both are acceptable; prefer the `with open(...)` form for parity with the codebase analog.

**Adaptation needed:**
- Generator must NOT mutate `docs/projects/screener/data.json` (out-of-scope). Outputs go to `_dev/training_dataset/dataset_manifest.json` (gitignored) and `models/dataset_manifest.json` (committed).
- Random number generation must use seeded local instances (`random.Random(seed)`, `numpy.random.default_rng(seed)`) — fetch_sp500 doesn't seed anything; this is **new convention** introduced by Phase 8 per RESEARCH §Pattern 3.

---

### `scripts/pattern_scanner/train.py` (training entry, CLI wrapper)

**Analog:** `scripts/pattern_scanner/detector.py` lines 391-414 — the CLI shim around a single pure operation. Same role: thin argparse wrapper that imports a heavy library lazily and prints structured output.

**Deferred heavy import** (detector.py line 382): keep `from ultralytics import YOLO` inside `main()` so `python -c "import scripts.pattern_scanner.train"` does not pull torch + CUDA. RESEARCH §Code Examples — Trainer line:

```python
def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--batch", type=int, default=-1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--patience", type=int, default=20)
    args = p.parse_args(argv)

    from ultralytics import YOLO   # deferred — don't trigger torch import at CLI parse
```

**Print-and-summarise pattern** (fetch_sp500.py lines 561-565):

```python
print(f"\nDone. {len(stocks)} stocks written to {output_path}")
print(f"Calculator cache written to {calc_cache_path}")
print(f"updated_at: {updated_at}")
```

`train.py` must echo `[train] best mAP50: ...`, `[export] OPSET: 12 (logged to stdout per D-17)` (RESEARCH §Code Examples — Trainer) using the same `[component] message` prefix style.

**Adaptation needed:** ultralytics + ONNX export are **novel libraries** for this codebase. Follow RESEARCH §Code Examples — Trainer verbatim for parameter surface (`opset=12`, `dynamic=False`, `imgsz=640`, `simplify=True`, `fliplr=0.0`). Apply RESEARCH §Pitfall #4 correction: do **not** add a `--cls-pw` flag; leave `cls_pw=1.0` and document the rationale.

---

### `scripts/pattern_scanner/verify_onnx.py` (verifier / round-trip gate)

**Analog:** **no codebase analog.** Subprocess-driven temp-venv creation is novel for this repo.

Follow RESEARCH §Code Examples — Verifier (08-RESEARCH.md lines 749-870) verbatim. Key load-bearing pieces:

- `tempfile.TemporaryDirectory(prefix="onnx_verify_")` for guaranteed cleanup.
- Cross-platform venv binary path: `bin_dir = "Scripts" if sys.platform == "win32" else "bin"` — required because CLAUDE.md specifies the project shell is PowerShell on Windows AND the repo is also operated from Git Bash.
- Pin pip-installed versions: `onnxruntime>=1.19`, `numpy>=1.26`, `Pillow>=10.0` (matching `requirements.txt` floors).
- The numpy NMS implementation (~30 lines) ships **inside** the inference subprocess script as a `dedent('''...''').strip()` string — RESEARCH §Pitfall #3 explains why (no torchvision in clean venv).

**CLI return-code idiom** (detector.py line 414): `if __name__ == "__main__": sys.exit(main(sys.argv))` — follow exactly.

**Naming/styling adaptation:** module-level UPPER_SNAKE_CASE constants `ONNX_PATH`, `FIXTURES_DIR`, `CONFIDENCE_FLOOR` (matches CONVENTIONS.md and detector.py constants block).

---

### `scripts/pattern_scanner/split_config.py` (config / constants)

**Analog:** `scripts/fetch_sp500.py` lines 30-43 — module-level constants block with section divider and a single source of truth for a tunable value.

**Module-constant pattern** (fetch_sp500.py lines 30-43):

```python
# ---------------------------------------------------------------------------
# Discount-rate lookup table (copied from api_server.py)
# ---------------------------------------------------------------------------

_DISCOUNT_TABLE_US = [
    (0.80, 5.15),
    (1.00, 5.89),
    ...
]
```

`split_config.py` should look like:

```python
"""Train/test split source-of-truth shared by Phase 8 (training pipeline) and
Phase 9 (backtester).

Detections with confirmation_date >= TRAIN_TEST_CUTOFF are EXCLUDED from
training and form the out-of-sample backtest slice.
"""
# ── Train/test split (D-07) ─────────────────────────────────────────────────
TRAIN_TEST_CUTOFF = "2024-01-01"  # placeholder; Phase 9 may revise
```

**Decision:** prefer `.py` over `.yaml` (CONTEXT D-07 leaves it open; RESEARCH §Architecture Patterns recommends `.py`). Rationale: zero-dep import, type-checkable, no YAML parser in the prod requirements stack.

---

### `requirements-training.txt` (new dep file)

**Analog:** `requirements-dev.txt` (single line: `pytest>=8.4,<9`) — exact same pattern: a single-purpose extra-requirements file alongside the production `requirements.txt`.

```
# Training-only dependencies. Never install in production / nightly CI.
# Install via: source .venv/Scripts/activate && pip install -r requirements-training.txt
ultralytics>=8.4.0,<9.0
```

(Comment header is per RESEARCH §Standard Stack.)

---

### `tests/test_renderer.py` (unit test, offline)

**Analog:** `tests/test_detector_schema.py` — exact match: pure-unit, no `@pytest.mark.network`, uses `synthetic_ohlc` fixture for deterministic OHLC.

**Synthetic-fixture usage** (test_detector_schema.py lines 140-171):

```python
def test_atr14_wilder(synthetic_ohlc):
    rng = np.random.default_rng(0)
    rows = []
    base = 100.0
    for _ in range(30):
        o = base + rng.uniform(-1, 1)
        h = max(o, base) + rng.uniform(0.5, 2.0)
        l = min(o, base) - rng.uniform(0.5, 2.0)
        c = base + rng.uniform(-1, 1)
        rows.append((o, h, l, c))
        base = c
    df = synthetic_ohlc(rows)
    atr = _compute_atr(df, 14)
    ...
```

`test_renderer.py` should:
1. Build a 60-row synthetic OHLC frame via `synthetic_ohlc(rows)` (conftest.py provides this).
2. Call `render(df, STYLES[0])` and assert the returned PNG bytes decode to a 640×640 RGB image (use `PIL.Image.open(io.BytesIO(png))`).
3. Assert determinism: two calls with same `(df, style)` produce **byte-identical** PNG (same machine — RESEARCH §Pitfall #6 caveat applies cross-machine).
4. Assert variance: `render(df, STYLES[0])` ≠ `render(df, STYLES[1])` byte-wise (RESEARCH Wave 0 §test_render_styles_differ).

**Header pattern** (test_detector_schema.py lines 1-29):

```python
"""Unit tests for scripts.pattern_scanner.detector — DET-01..DET-04 schema lock.

All tests are pure-unit and run offline using the `synthetic_ohlc` fixture.
NO `@pytest.mark.network` markers in this file — live yfinance regression
tests live in `test_detector_known_setups.py` (Plan 02).
"""
from __future__ import annotations

import json
import math
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest

from scripts.pattern_scanner.detector import (
    Detection,
    detect,
    ...
)
```

Adapt imports to `from scripts.pattern_scanner.renderer import RenderStyle, STYLES, render`.

---

### `tests/test_generate_training_data.py` (unit test, offline + tmp_path)

**Analog:** `tests/test_detector_schema.py` — for the synthetic-builder pattern. **Plus** standard pytest `tmp_path` fixture for filesystem isolation (no codebase analog needed; `tmp_path` is a pytest stdlib fixture).

**Adaptation needed:**
- Use `tmp_path` to redirect `DATASET_ROOT` (likely via monkeypatch on the module constant).
- Use a 2-3 ticker `--limit 3` synthetic dataset; build OHLC with `synthetic_ohlc` helper from `conftest.py` (already exposed there).
- The generator currently calls `yfinance` directly — for unit tests, monkeypatch the per-ticker fetch to return a `synthetic_ohlc(...)` DataFrame. **Pattern reused from** `tests/test_detector_schema.py::test_cli_ticker_validation` (line 455-478):

```python
def test_cli_ticker_validation(monkeypatch, synthetic_ohlc):
    """The module's main() must reject non-conforming tickers BEFORE any fetch."""
    import scripts.pattern_scanner.detector as det

    fetch_calls = {"count": 0}

    def fake_fetch(ticker, period="10y"):
        fetch_calls["count"] += 1
        return synthetic_ohlc([(1.0, 2.0, 0.5, 1.5)])

    monkeypatch.setattr(det, "_fetch_ohlc", fake_fetch)
    ...
```

This is **the exact monkeypatch pattern** for keeping generator unit tests offline. Generator should expose its yfinance fetch as a module-level helper (e.g., `_fetch_ohlc(ticker)`) so `monkeypatch.setattr(generate_training_data, "_fetch_ohlc", fake_fetch)` works.

Required tests (per RESEARCH §Wave 0 + §Phase Requirements → Test Map):
- `test_yolo_directory_layout`
- `test_positive_label_format` (normalized 0..1, class_id 0)
- `test_negative_labels_empty`
- `test_neg_pos_ratio_capped` (10:1)
- `test_cutoff_enforced`
- `test_hard_negative_set_difference`
- `test_style_randomization_used`
- `test_manifest_sha256_consistent`

---

### `tests/test_onnx_round_trip.py` (smoke / unit)

**Analog:** `tests/test_detector_known_setups.py` — for the artifact-driven assertion pattern (real fixture file → run pipeline → assert known result).

**Header pattern** (test_detector_known_setups.py lines 1-37): docstring documents the **provenance** of the fixture — required for any committed binary artifact.

**Test scope:**
- `test_opset_recorded`: read `models/training_summary.json`, assert `payload["opset"] == 12`.
- `test_onnx_file_exists`: `assert Path("models/inside_bar_v1.onnx").exists()`.
- The actual subprocess round-trip (`verify_onnx.py`) is invoked as a CLI gate (`bash`), not a pytest test — it requires creating a clean venv, which is too slow / brittle for the unit suite. RESEARCH §Sampling Rate confirms: "Phase gate: `verify_onnx.py` exits 0 in a NEW clean venv (not the project venv)" — manual gate.

If the round-trip IS wired into pytest, mark it `@pytest.mark.slow` (new marker — register in `conftest.py` alongside `network`) so the default `pytest -q` does not run it.

---

### `tests/test_detector_apply_trend_filters_kwarg.py` (regression, offline)

**Analog:** `tests/test_detector_schema.py::test_detect_returns_detection_list` and `test_spring_same_bar` — uses the `_spring_setup_rows()` and `_build_uptrend()` builders from that file.

**Reusable test builder** (test_detector_schema.py lines 227-300) — copy or import:

```python
def _build_uptrend(n: int, start: float = 100.0) -> list:
    """Build a HH/HL uptrend of `n` bars with multiple visible swing pivots."""
    ...

def _spring_setup_rows():
    """Build a non-spring (5-bar) setup where break-below at offset 2 and
    confirmation at offset 3.

    Returns (rows, mother_idx, conf_idx, mother_low, mother_high).
    """
    trend = _build_uptrend(70)
    ...
```

These builders produce a DataFrame where the trend filters PASS — useful for asserting the kwarg's default behaviour matches Phase 7. To exercise the `apply_trend_filters=False` branch, build a setup where the cluster shape is valid but at least one of the three filters fails (e.g., flat-trend prefix so HH/HL fails).

**Required tests** (per RESEARCH §Phase Requirements → Test Map):
- `test_default_kwarg_matches_phase7`: `detect(df, t)` and `detect(df, t, apply_trend_filters=True)` return identical lists on the spring fixture.
- `test_unfiltered_is_superset`: on a fixture that has cluster-valid but filter-failing setups, `detect(df, t, apply_trend_filters=False)` returns a strict superset of `detect(df, t)`, and at least one detection in the difference has `filters["hh_hl"] is False` OR `filters["above_50sma"] is False` OR `filters["sma_cluster"] is False`.

---

### `scripts/pattern_scanner/detector.py` (modified — add ONE kwarg)

**Analog:** itself. The change MUST preserve all 23 existing tests (12 schema + 11 known-setups) — RESEARCH §Critical Test confirms zero regressions allowed.

**Current signature** (detector.py line 305):

```python
def detect(df: pd.DataFrame, ticker: str) -> List[Detection]:
```

**Phase 8 change** (RESEARCH §Code Examples — Phase 7 detect() Modification):

```python
def detect(df: pd.DataFrame, ticker: str,
           apply_trend_filters: bool = True) -> List[Detection]:
```

**Insertion site:** the 3-AND filter check at lines 367-372:

```python
# CURRENT (Phase 7):
if (
    detection.filters["hh_hl"]
    and detection.filters["above_50sma"]
    and detection.filters["sma_cluster"]
):
    detections.append(detection)
```

becomes:

```python
# PHASE 8:
if not apply_trend_filters:
    detections.append(detection)
elif (
    detection.filters["hh_hl"]
    and detection.filters["above_50sma"]
    and detection.filters["sma_cluster"]
):
    detections.append(detection)
```

Per-filter booleans are still always evaluated in `_build_detection` (line 245-258) — D-08 invariant preserved automatically.

**Verification before commit:**
```bash
source .venv/Scripts/activate && python -m pytest tests/test_detector_schema.py tests/test_detector_known_setups.py -q
```
Expected: 23 passed (or 12 passed + 11 skipped under `--no-network`).

**Docstring addition** (detector.py lines 305-316) — append to `Args:` block:

```
        apply_trend_filters: when True (default — Phase 7 contract), only
            emit detections whose three trend filters all pass. When False
            (Phase 8 hard-negative pool), emit every detection that passes
            the cluster shape rules regardless of filter state. Per-filter
            booleans are recorded in either mode (D-08).
```

---

### `requirements.txt` (modified — append four lines)

**Analog:** itself. Existing file is 12 lines, no comments. Phase 8 adds a comment divider and four new lines — see RESEARCH §Standard Stack:

```
# ── Existing ──
flask==3.1.3
flask-cors==6.0.2
yfinance==0.2.65
curl_cffi>=0.7.0
pandas>=2.2.0
numpy>=1.26.0
requests==2.32.5
beautifulsoup4==4.13.5
lxml==6.0.1
gunicorn==23.0.0
openai>=1.0.0
python-dotenv>=1.0.0
# ── Added in Phase 8 (inference dependencies — required by Phase 10 nightly pipeline) ──
mplfinance>=0.12.10b0
matplotlib>=3.8
onnxruntime>=1.19
Pillow>=10.0
```

NOTE: research recommends `onnxruntime>=1.19` (not `>=1.18`) for hard numpy 2.x compatibility. CONTEXT D-13 says `>=1.18` — defer to research's stricter floor.

---

### `.gitignore` (modified — append two lines)

**Analog:** itself. Append at end (after line 42):

```
# Phase 8 — training pipeline artifacts (regenerable)
_dev/training_dataset/
yolov8n.pt
```

`_dev/` is **not** currently gitignored at the directory level (only specific scripts inside it are — see lines 14-23). Adding `_dev/training_dataset/` is a precise, additive ignore that does not affect existing behaviour.

---

## Shared Patterns

### Module Header + Section Dividers
**Source:** `scripts/pattern_scanner/detector.py` lines 1-49.
**Apply to:** All five new `scripts/pattern_scanner/` modules.

Required elements:
1. Triple-quoted module docstring with **Public API** section, **CLI** section, and any cross-cutting invariants.
2. `from __future__ import annotations` as the first import.
3. Imports grouped: stdlib → third-party → local, alphabetised within group.
4. UPPER_SNAKE_CASE module constants block under a `# ── Module constants ──` divider.

### Pure Function + CLI Wrapper
**Source:** `scripts/pattern_scanner/detector.py` lines 305-414.
**Apply to:** `renderer.py`, `generate_training_data.py`, `train.py`, `verify_onnx.py`.

```python
def main(argv: List[str]) -> int:
    """CLI entry point. Returns process exit code."""
    # parse, validate, work
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

Return-code-based, no raise from `main()`.

### Deferred Heavy Imports
**Source:** `scripts/pattern_scanner/detector.py` lines 380-388.
**Apply to:** `generate_training_data.py` (yfinance), `train.py` (ultralytics/torch), `verify_onnx.py` (none — uses subprocess).

```python
def _do_work():
    import yfinance as yf  # noqa: WPS433 — deferred by design
```

Keeps `python -c "import scripts.pattern_scanner.X"` fast and avoids torch import at argparse time.

### Per-Iteration Error Handling + Progress Logging
**Source:** `scripts/fetch_sp500.py` lines 501-537.
**Apply to:** `generate_training_data.py`'s S&P 500 loop.

```python
for i, ticker in enumerate(tickers, start=1):
    try:
        record = process_ticker(ticker, i, total)
    except Exception as exc:
        print(f"[{i}/{total}] {ticker}: unexpected error — {exc}")
        record = NULL_RECORD
    if i < total:
        time.sleep(0.5)  # rate-limit yfinance
```

`[{i}/{total}] {ticker}: ...` is the canonical progress prefix — match exactly so logs interleave cleanly.

### yfinance Fetch Idiom
**Source:** `scripts/pattern_scanner/detector.py` lines 380-388 + `tests/test_detector_known_setups.py` lines 60-67 + `yahoo_finance_fetcher.py` line 12.

```python
df = yf.Ticker(ticker).history(period="10y", auto_adjust=True)[
    ["Open", "High", "Low", "Close"]
]
if df.index.tz is not None:
    df.index = df.index.tz_localize(None)
```

`auto_adjust=True` is the project-wide standard. Period `"10y"` is locked by CONTEXT D-06.

### Deterministic Seeded Outputs
**Source:** **NEW** project-wide convention introduced by Phase 8 per RESEARCH §Pattern 3 + CONTEXT §Established Patterns.
**Apply to:** `generate_training_data.py`, `train.py`.

```python
import random
import numpy as np

rng = random.Random(args.seed)               # NOT random.seed()
np_rng = np.random.default_rng(args.seed)    # NOT np.random.seed()
```

Never touch the global `random` / `numpy.random` state. Test fixture `tests/test_detector_schema.py::test_atr14_wilder` already shows `np.random.default_rng(0)` — same idiom.

### Pytest Marker Registration (offline gate)
**Source:** `tests/conftest.py` lines 17-43.
**Apply to:** any new test file using `@pytest.mark.network` or proposed `@pytest.mark.slow`.

`conftest.py` already registers the `network` marker and wires `--no-network` / `PYTEST_OFFLINE=1`. If `test_onnx_round_trip.py` introduces a slow gate, register a `slow` marker the same way:

```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: marks tests that create a clean venv and run subprocess inference.",
    )
```

### `synthetic_ohlc` Fixture Reuse
**Source:** `tests/conftest.py` lines 46-66.
**Apply to:** `test_renderer.py`, `test_generate_training_data.py`, `test_detector_apply_trend_filters_kwarg.py`.

Provides a callable `synthetic_ohlc(rows, start_date="2024-01-01") -> pd.DataFrame` that builds a tz-naive business-day-indexed OHLC frame. **Already wired into pytest discovery** — no import needed; just declare `synthetic_ohlc` as a test parameter.

### Monkeypatch the Module-Level Fetch Function
**Source:** `tests/test_detector_schema.py::test_cli_ticker_validation` lines 455-478.
**Apply to:** `test_generate_training_data.py` (replacing yfinance with synthetic frames).

```python
def fake_fetch(ticker, period="10y"):
    return synthetic_ohlc([(1.0, 2.0, 0.5, 1.5)])

monkeypatch.setattr(module_under_test, "_fetch_ohlc", fake_fetch)
```

Generator must expose `_fetch_ohlc(ticker)` as a module-level helper for this to work.

### Committed Binary Fixtures
**Source:** **NEW.** Repo currently has zero committed binary test fixtures (all existing tests are pure-unit or live-network).
**Apply to:** `tests/fixtures/known_positive_*.png`, `models/inside_bar_v1.onnx`.

Closest analogous pattern is `tests/test_detector_known_setups.py` lines 1-56 — the **provenance docstring**:

```python
"""Live yfinance integration regression suite for the inside bar spring detector.

Provenance (D-15 / D-16, Phase 7 success criterion #4):
    The KNOWN_SETUPS fixture below is a curated, user-reviewed list of
    historical S&P 500 inside-bar-spring setups. Each entry was proposed by
    Claude from a detector dump under `_dev/phase07_proposal/`, then approved
    verbatim by the user on 2026-05-02 per the D-16 checkpoint in
    `.planning/phases/07-detection-engine/07-02-PLAN.md`. ...
"""
```

Phase 8 must apply the same provenance discipline to the binary fixtures: where the PNG came from (which ticker, which confirmation_date, which renderer style + seed), how to regenerate it. Document inside `08-SUMMARY.md` and reference from a comment header in any test that loads the fixture.

`.gitignore` already excludes `*.png` for `_dev/` regeneration but `tests/fixtures/` is **not** matched — committed PNGs there work without `.gitignore` change.

### JSON Manifest Write
**Source:** `scripts/fetch_sp500.py` lines 539-543.
**Apply to:** `generate_training_data.py` (manifest), `train.py` (training_summary).

```python
output = {"updated_at": updated_at, ...}
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
```

`indent=2`, `encoding="utf-8"`, ISO-8601 UTC `updated_at` field present at top of payload. Match exactly.

### CLI Validation BEFORE Side Effects
**Source:** `scripts/pattern_scanner/detector.py` lines 391-407 + `tests/test_detector_schema.py::test_cli_ticker_validation`.
**Apply to:** any new CLI accepting user input that maps to file paths or external calls.

```python
ticker = argv[1].upper()
if not _TICKER_RE.match(ticker):
    print(f"Invalid ticker: {ticker!r}", file=sys.stderr)
    return 2
df = _fetch_ohlc(ticker)
```

T-07-01 mitigation idiom — ticker regex `^[A-Z0-9.-]{1,10}$`. If the generator accepts a `--ticker` arg, reuse `_TICKER_RE` from detector.py.

### `frozen=True` Dataclass for Records
**Source:** `scripts/pattern_scanner/detector.py` lines 51-68.

```python
@dataclass(frozen=True)
class Detection:
    """Frozen detection record. Fields per CONTEXT D-10."""
    ticker: str
    ...

    def to_dict(self) -> Dict:
        return asdict(self)
```

**Apply to:** `RenderStyle` in `renderer.py` (RESEARCH §Code Examples uses `@dataclass(frozen=True)` already — confirms this pattern is the expected idiom).

---

## No Analog Found

| File | Role | Data Flow | Reason | Fallback Reference |
|------|------|-----------|--------|-------------------|
| `scripts/pattern_scanner/verify_onnx.py` | verifier (subprocess + temp venv) | onnx + fixture → exit code | No existing module creates a subprocess venv or runs cross-process inference | RESEARCH §Code Examples — Verifier (08-RESEARCH.md lines 749-870) |
| `scripts/pattern_scanner/renderer.py` (mplfinance + matplotlib Agg) | pure-function render | DataFrame → PNG bytes | matplotlib backend forcing is novel; no codebase analog uses image generation | RESEARCH §Code Examples — Renderer (08-RESEARCH.md lines 408-503) + Pillow resize |
| `scripts/pattern_scanner/train.py` (ultralytics) | training entry | dataset → onnx | First ML training script in repo | RESEARCH §Code Examples — Trainer + RESEARCH §Pitfall #4 (cls_pw correction) |
| `tests/fixtures/known_positive_*.png` | committed binary fixture | n/a | First committed binary test fixture | Provenance idiom from `test_detector_known_setups.py` lines 1-56; `.gitignore` does NOT exclude `tests/fixtures/` |
| `models/inside_bar_v1.onnx` | committed binary artifact | n/a | First committed model artifact; new top-level `models/` dir | CONTEXT D-13 (regular git, no LFS); RESEARCH Open Question #5 confirms 6-12 MB is well below GitHub limits |

**For all five:** the planner should reference RESEARCH.md §Code Examples directly rather than search for a non-existent codebase analog. The illustrative scaffolding there is the contract; CONTEXT.md decisions override where they conflict.

---

## Cross-File Invariants the Planner Must Carry into All Plans

1. **`apply_trend_filters: bool = True`** — same default value, same kwarg name, same docstring wording across `detector.py` (signature), `generate_training_data.py` (call site for hard negatives), and `test_detector_apply_trend_filters_kwarg.py` (regression). Single source of truth: detector.py line 305 after modification.

2. **`TRAIN_TEST_CUTOFF`** — imported from `scripts.pattern_scanner.split_config` by `generate_training_data.py` and (Phase 9) `backtester.py`. Never inlined.

3. **`_LOOKBACK = 60` / `target_size = 640`** — already a constant in `detector.py` (`_LOOKBACK = 60`). Renderer and generator must import or re-declare with **the same numeric value**; ideally renderer imports `_LOOKBACK` from detector OR exposes its own `_BAR_COUNT = 60` and a comment noting the parity requirement.

4. **yfinance fetch normalisation block** — duplicated identically in detector.py (`_fetch_ohlc`), `test_detector_known_setups.py` (`_fetch`), and the new generator. CONVENTIONS does not require DRYing this; matching idiom is sufficient. Period `"10y"`, `auto_adjust=True`, four-column projection, `tz_localize(None)` — exact match.

5. **Seeded RNG** — `random.Random(seed)` and `numpy.random.default_rng(seed)` only. Never `random.seed()`, never `np.random.seed()`. Single seed value flows from `--seed` arg through every random call.

6. **`opset=12`** — declared in `train.py` `model.export()` call AND echoed in `models/training_summary.json` AND read back by `tests/test_onnx_round_trip.py::test_opset_recorded`. Three sites; one value.

7. **Phase 7 contract preservation** — `tests/test_detector_schema.py` (12) + `tests/test_detector_known_setups.py` (11) = 23 tests must remain green after the kwarg addition. Hard rollback gate.

---

## Metadata

**Analog search scope:**
- `scripts/pattern_scanner/` (Phase 7 package — primary reference)
- `scripts/` (`fetch_sp500.py` — batch S&P 500 template)
- repo root (`yahoo_finance_fetcher.py`, `finviz_fetcher.py`, `requirements*.txt`, `.gitignore`)
- `tests/` (4 files — fixtures + Phase 7 test patterns)
- `.planning/codebase/` (CONVENTIONS.md, STRUCTURE.md)

**Files scanned:** 11 source/test/config files + CONTEXT.md + RESEARCH.md (1247 lines).

**Strong analogs found in codebase:** detector.py (renderer template, train CLI template, kwarg modification target), fetch_sp500.py (generator template), test_detector_schema.py (synthetic-fixture test template), test_detector_known_setups.py (provenance pattern for committed fixtures), conftest.py (pytest fixture + marker registration).

**Patterns sourced from RESEARCH.md (no codebase analog):** matplotlib Agg backend, mplfinance API, ultralytics train + ONNX export, numpy NMS, subprocess + venv module orchestration, YOLOv8 directory contract.

**Pattern extraction date:** 2026-05-02
