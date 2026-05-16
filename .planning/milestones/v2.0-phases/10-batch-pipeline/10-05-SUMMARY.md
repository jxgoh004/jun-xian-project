---
plan: 10-05
phase: 10-batch-pipeline
status: complete
completed_at: 2026-05-12
---

# Plan 10-05 — Pure Builders (build_data_json + build_stats_json)

Two pure projector functions added to `scripts/pattern_scanner/run_pipeline.py`. Both have no I/O — Plan 10-06's `main()` calls them and `_atomic_write_json` performs the disk write.

## What was built

### `build_data_json(detections, errors, run_id, succeeded, failed, window_days) -> dict`
- Assembles the `data.json` payload per D-02 / D-16 / D-17 schema.
- Top-level keys: `schema_version`, `generated_at`, `window_days`, `as_of_date`, `pipeline_status`, `detections`.
- `pipeline_status.completed = succeeded / (succeeded + failed) >= 0.95` (D-16 95% threshold).
- Direct boundary unit-check confirmed: 95/100 → `completed=True`; 94/100 → `completed=False`.

### `build_stats_json(aggregates) -> dict`
- Projects the committed `_backtest_aggregates.json` (Plan 10-02 output) into frontend-ready shape per D-11.
- Accepts both the full envelope (top-level `aggregates`) and the inner block — total / never raises on partial input.
- Renames Phase 9's raw `_True`/`_False` keys → `_spring`/`_extended` via `_normalize_by_type_x_spring` (idempotent).
- Emits `fallback_order = ["by_type_x_spring", "by_confirmation_type", "all"]` and `n_floor = 10`; client walks the chain.

## Verification

```
pytest tests/test_run_pipeline_main.py tests/test_run_pipeline_stats.py --no-network -v
```

| Test | Result | Notes |
|------|--------|-------|
| `test_stats_json_falls_back_to_by_confirmation_type_when_sparse` | ✓ PASSED | D-11 fallback chain |
| `test_stats_json_falls_back_to_all_when_both_sparse` | ✓ PASSED | D-11 ultimate fallback |
| `test_stats_json_normalizes_is_spring_keys` | ✓ PASSED | D-11 key normalization |
| `test_pipeline_status_completed_true_when_above_95pct` | RED (expected) | Test calls `main()`, not `build_data_json` directly — turns GREEN when 10-06 lands |
| `test_pipeline_status_completed_false_when_below_95pct` | RED (expected) | Same — main() integration test |
| `test_main_smoke_with_synthetic_ohlc` | RED (expected) | Same — main() integration test |

**Live-fixture sanity check** against committed `docs/projects/patterns/_backtest_aggregates.json`:
- `build_stats_json` returns 6 normalized type×spring cells: `pin_spring (n=237)`, `pin_extended (n=58)`, `mark_up_spring (n=78)`, `mark_up_extended (n=239)`, `ice_cream_spring (n=293)`, `ice_cream_extended (n=420)`.
- Matches Phase 9 SUMMARY out-of-sample totals exactly.
- Top-level keys: `schema_version`, `generated_at`, `source`, `rule`, `stats`, `fallback_order`, `n_floor`.

## Deviation from plan

- Plan stated "5 Wave 0 tests turn GREEN" but two of those (`test_pipeline_status_completed_*`) actually invoke `main()` (which is still a NotImplementedError stub from 10-04). They are misleadingly named — they're integration tests, not unit tests of `build_data_json`. The build_data_json contract was verified directly via inline boundary checks (95/100 → True, 94/100 → False); the named tests will turn GREEN as a side effect of 10-06's `main()` wiring.
- No code-level deviation. Both pure functions match the plan's RESEARCH §Schema Designs spec verbatim.

## Files modified
- `scripts/pattern_scanner/run_pipeline.py` — added `_normalize_by_type_x_spring`, `build_data_json`, `build_stats_json`.

## Self-Check: PASSED
- `build_data_json` and `build_stats_json` implemented per D-02/D-11/D-16/D-17.
- 3/3 pure-builder Wave 0 tests GREEN.
- Live fixture round-trip verified — 6 normalized cells, n totals match Phase 9.
- Remaining 3 RED tests are 10-06 dependencies, not 10-05 gaps.
- No regressions in non-`main()` tests.
- No `Co-Authored-By: Claude` trailers.
