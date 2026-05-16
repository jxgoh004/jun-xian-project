---
phase: 10-batch-pipeline
plan: 02
subsystem: pattern_scanner
tags: [export, aggregates, wave0, one-shot, data-pipeline]
requires:
  - "Phase 9: _dev/backtest_cache.json on local disk (gitignored, 27.8 MB)"
  - "D-10: stats source is a committed aggregates-only file"
  - "D-11: out_of_sample is the integrity story"
  - "D-04: filtered strategy 1to2_rr_cluster_low_stop is the public methodology"
provides:
  - "scripts/pattern_scanner/export_aggregates.py: one-shot CLI extractor (project_aggregates + main)"
  - "docs/projects/patterns/_backtest_aggregates.json: committed source-of-truth file (3,750 bytes)"
affects:
  - "Plan 10-05 (build_stats_json): reads docs/projects/patterns/_backtest_aggregates.json at runtime in nightly CI"
  - "GHA runner: no longer needs to rebuild Phase 9 cache nightly (D-10)"
tech-stack:
  added: []
  patterns:
    - "Pure-function core + thin CLI wrapper (mirrors verify_onnx.py / detector.py / backtest.py)"
    - "stdlib-only (argparse, json, sys, pathlib) — no new requirements"
    - "Deterministic output (json.dumps sort_keys=True) for byte-identical regeneration"
key-files:
  created:
    - "scripts/pattern_scanner/export_aggregates.py"
    - "docs/projects/patterns/_backtest_aggregates.json"
  modified: []
decisions:
  - "Reused verbatim skeleton from RESEARCH §D-10 L913-947 (no design drift)"
  - "Output is aggregates-only: omits per-detection records by construction (the projector touches only strat['aggregates'])"
  - "stdlib-only — no new requirements.txt entries"
metrics:
  duration: "~6 min"
  completed: 2026-05-12
  tasks: 2
  files: 2
  commits: 2
---

# Phase 10 Plan 02: Aggregates Extraction Helper Summary

One-shot CLI helper that projects a full Phase 9 backtest cache into a tiny aggregates-only JSON, plus the committed source-of-truth file `docs/projects/patterns/_backtest_aggregates.json` (3,750 bytes) that Phase 10's nightly stats projector will read.

## Deliverables

### `scripts/pattern_scanner/export_aggregates.py`

Two-symbol public API:

```python
def project_aggregates(cache: dict, strategy: str, sample: str) -> dict
def main(argv=None) -> int
```

CLI:

```
python -m scripts.pattern_scanner.export_aggregates \
    --in _dev/backtest_cache.json \
    --out docs/projects/patterns/_backtest_aggregates.json \
    --strategy 1to2_rr_cluster_low_stop  \   # default (D-04)
    --sample out_of_sample                    # default (D-11)
```

Defaults match D-04 (filtered strategy is the public methodology) and D-11 (`out_of_sample` is the integrity slice). `--sample` is constrained to `{in_sample, out_of_sample}` via `choices=`.

stdlib-only: `argparse`, `json`, `sys`, `pathlib`. No new `requirements.txt` entries.

### `docs/projects/patterns/_backtest_aggregates.json`

**Final size:** 3,750 bytes (well under the 50 KB D-10 cap; closer to the "few KB" wording).

**Top-level keys** (alphabetised): `aggregates`, `extracted_at`, `extracted_from`, `onnx_sha256`, `sample`, `schema_version`, `strategy`, `train_test_cutoff`.

**`aggregates` sub-keys:** `all`, `by_confirmation_type`, `by_is_spring`, `by_type_x_spring`.

**Headline numbers (matches Phase 9 SUMMARY § Empirical Results exactly):**

| slice                                    | n    | win_rate | avg_return_r |
|------------------------------------------|------|----------|--------------|
| all (filtered, out_of_sample)            | 1325 | 0.330    | -0.007       |
| by_confirmation_type → pin               | 295  | 0.296    | -0.112       |
| by_confirmation_type → mark_up           | 317  | 0.328    | -0.007       |
| by_confirmation_type → ice_cream         | 713  | 0.345    | +0.036       |

`onnx_sha256` is `null` (Phase 9 ran `--no-onnx`, documented in Phase 9 SUMMARY § Run anomalies). `train_test_cutoff` is `2024-01-01`. `extracted_at` is sourced from the cache's `generated_at` header so re-runs against the same cache produce byte-identical output.

## Verification

- `python -c "from scripts.pattern_scanner.export_aggregates import project_aggregates, main; print('OK')"` → **OK**
- `python -m scripts.pattern_scanner.export_aggregates --help` → prints `--in / --out / --strategy / --sample` with documented defaults.
- File schema sanity check (all 8 top-level keys present, all 4 aggregate sub-keys present, `n >= 10`, `strategy == 1to2_rr_cluster_low_stop`, `sample == out_of_sample`) → **PASS**.
- `git check-ignore _dev/backtest_cache.json` echoes the path → cache **still gitignored** (Phase 9 D-06 intact).

## Refresh procedure (future Phase 9 reruns)

When the Phase 9 backtest is rerun (manual / methodology change):

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.pattern_scanner.export_aggregates `
    --in _dev/backtest_cache.json `
    --out docs/projects/patterns/_backtest_aggregates.json
```

Output is deterministic (`json.dumps(..., sort_keys=True)`) — re-running against an unchanged cache produces a byte-identical file (git sees no diff). Re-running against a fresh Phase 9 cache produces a single small commit. **Never hand-edit** the JSON — it must remain regeneratable from the extractor (threat T-10-02-02).

## Deviations from Plan

None. Plan executed exactly as written. Skeleton from RESEARCH §D-10 L913-947 was used verbatim; defaults match D-04 + D-11; numbers in the output file match Phase 9 SUMMARY § Empirical Results exactly.

## Commits

| Hash      | Type    | Subject                                          |
|-----------|---------|--------------------------------------------------|
| `798ab7f` | `feat`  | `feat(10-02): add export_aggregates helper`      |
| `cbb4229` | `data`  | `data(10-02): commit _backtest_aggregates.json`  |

## Threat Surface

Threat register (in PLAN.md) covers the three relevant boundaries; no new threat surface introduced beyond what the plan anticipated. The committed JSON contains only statistical aggregates (no ticker symbols, no PII); aggregates-only-by-construction means hand-edit drift (T-10-02-02) is the only Phase-10-time concern and is mitigated by the regeneration procedure documented above.

## Self-Check: PASSED

- `scripts/pattern_scanner/export_aggregates.py` exists.
- `docs/projects/patterns/_backtest_aggregates.json` exists, 3,750 bytes.
- Commit `798ab7f` present in `git log --oneline`.
- Commit `cbb4229` present in `git log --oneline`.
- `_dev/backtest_cache.json` still gitignored.
