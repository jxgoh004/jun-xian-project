---
phase: 08-training-pipeline
plan: 03
subsystem: pattern_scanner / training-pipeline dataset orchestrator
tags:
  - python
  - pipeline
  - dataset
  - yolo
  - cli
  - manifest
requirements:
  - TRAIN-02
  - TRAIN-03
dependency_graph:
  requires:
    - "Plan 08-01 — split_config.TRAIN_TEST_CUTOFF, detect(apply_trend_filters=…) kwarg, .gitignore for _dev/training_dataset/, Wave 0 test stub at tests/test_generate_training_data.py"
    - "Plan 08-02 — renderer.render(), compute_bbox_normalized(), STYLES (3 frozen RenderStyle instances), Agg-backend invariant"
  provides:
    - "scripts.pattern_scanner.generate_training_data.main(argv) — CLI entry, returns 0 on success"
    - "scripts.pattern_scanner.generate_training_data._fetch_ohlc(ticker, period) — module-level test seam mirroring detector._fetch_ohlc"
    - "scripts.pattern_scanner.generate_training_data._detect_positives / _detect_hard_negatives — pure helpers consumed by tests"
    - "Bit-for-bit reproducible YOLOv8 dataset given (--seed, ticker_subset, yfinance data revision)"
    - "dataset_manifest.json contract: positives, negatives, neg_pos_ratio, renderer_styles_seen, concat_sha256, seed, tickers, date_range — written to BOTH _dev/training_dataset/ (gitignored) AND models/ (committed)"
  affects:
    - "Plan 04 (train.py) — consumes _dev/training_dataset/data.yaml + the YOLO directory layout produced here"
    - "Plan 05 (verify_onnx.py) — re-reads the committed models/dataset_manifest.json for the seed/positive-count provenance"
    - "Phase 9 (backtester) — same TRAIN_TEST_CUTOFF semantics; the cutoff filter applied here is the inverse of what Phase 9 will use to define its out-of-sample slice"
tech_stack:
  added: []
  patterns:
    - "Module-level test seam: _fetch_ohlc + _load_tickers + time.sleep are top-level callables so monkeypatch can swap them in unit tests (mirrors detector.py idiom)"
    - "Hard-negative set difference keyed on (ticker, mother_bar_index, confirmation_bar_index) — three-tuple key matches RESEARCH §Pitfall 7 fix; ticker is included so cross-ticker generators stay correct"
    - "Single seeded RNG (random.Random(args.seed)) drives style choice, train/val shuffle, and negative subsample — gives bit-for-bit determinism across runs without mutating global random state"
    - "Manifest written via json.dumps(..., sort_keys=True, indent=2) so committed file is byte-stable per (positives, negatives, ratio, sha)"
    - "1,000-positive gate (D-08) handled inline via _augment_to_floor() multi-style round-robin — failure mode is loud (a print line) not silent"
key_files:
  created:
    - "scripts/pattern_scanner/generate_training_data.py (344 lines, CLI orchestrator + 8-test surface)"
  modified:
    - "tests/test_generate_training_data.py (Wave 0 stub: 8 skip-marked stub bodies → 8 real green tests; pytestmark removed; spring + flat-prefix builders copied/adapted from test_detector_schema.py)"
decisions:
  - "Hard-negative key is the 3-tuple (ticker, mother_bar_index, confirmation_bar_index). Index-only would be incorrect once the run iterates >1 ticker because mother_bar_index is per-ticker positional. RESEARCH §Pitfall 7 explicitly flagged this."
  - "Determinism is enforced by a SINGLE seeded random.Random instance — np.random.default_rng is constructed-and-discarded for now (reserved for future numpy-random use). Avoids global random.seed() which would clobber other modules."
  - "Manifest JSON uses sort_keys=True so the committed models/dataset_manifest.json is byte-deterministic for a given (positives, negatives, sha, ratio) tuple — keeps git diff signal on the manifest tied to actual dataset change."
  - "Synthetic test fixture uses start_date='2020-01-01' so confirmation_dates fall well before TRAIN_TEST_CUTOFF (= 2024-01-01); positives are kept by default. The cutoff-enforced test patches the cutoff to '1900-01-01' to flip every detection out-of-set."
  - "Renderer is invoked TWICE per positive sample (once for the PNG bytes, once via compute_bbox_normalized for axes transform). Plan 02's open question 3 flagged this as a 2× speedup opportunity for Plan 04, but the unit-test wall time (14m for 8 tests at --limit 3) is acceptable. Optimisation deferred."
  - "_augment_to_floor() emits the SAME (ticker, det) record across multiple STYLES rather than re-fetching alternative tickers — keeps the augmentation cost matplotlib-bound, not network-bound, and preserves the RESEARCH §1 style-memorisation mitigation (every positive seen multiple ways)."
  - "The spring-shape synthetic fixture used as the patched_fetch default has only 74 bars total. The renderer's strict 60-bar requirement and the detector's 60-bar lookback align — but the 60-bar window MUST end at confirmation_bar_index (D-03 right-aligned), so each ticker emits exactly one positive at conf_idx=73. This is sufficient to exercise all 8 unit tests; volume comes from the 3-ticker × 1-pos × style-tagged write loop."
metrics:
  duration: "~30 minutes (one session, sequential; ~14m of that is the offline pytest run)"
  completed_date: "2026-05-03"
  tasks_completed: 2
  files_changed: 2
---

# Phase 08 Plan 03: Training-Data Generator — Summary

A 344-line offline-only orchestrator (`scripts/pattern_scanner/generate_training_data.py`) ties Phase 7's `detect()` (filtered + unfiltered), Plan 02's `renderer.render()` + `compute_bbox_normalized()`, and Plan 01's `TRAIN_TEST_CUTOFF` into a deterministic CLI that emits a YOLOv8-format dataset under `_dev/training_dataset/` plus a committed `models/dataset_manifest.json` carrying the run's seed, ticker list, positive/negative counts, neg/pos ratio, sorted styles seen, and a concat sha256 over every PNG written. The Wave 0 stub at `tests/test_generate_training_data.py` is replaced with 8 real green tests using monkeypatched fetch + a synthetic spring fixture + a flat-prefix fixture; full repo pytest is 27 passed, 14 skipped, 0 failed.

## Public API

```python
# scripts/pattern_scanner/generate_training_data.py

DATASET_ROOT = Path("_dev/training_dataset")
MODELS_ROOT  = Path("models")
MIN_POSITIVES = 1000        # D-08
NEG_POS_RATIO = 10          # D-09
VAL_FRACTION = 0.20         # D-18
RATE_LIMIT_SLEEP = 0.5

def _fetch_ohlc(ticker: str, period: str = "10y") -> pd.DataFrame:
    """yfinance auto_adjust + tz_localize(None); module-level test seam."""

def _load_tickers(limit) -> List[str]:
    """Wikipedia S&P 500 scrape via scripts.fetch_sp500.fetch_sp500_tickers()."""

def _detect_positives(df, ticker) -> List[Detection]:
    """detect(df, ticker), then filter confirmation_date < TRAIN_TEST_CUTOFF."""

def _detect_hard_negatives(df, ticker, positives) -> List[Detection]:
    """detect(df, ticker, apply_trend_filters=False) MINUS positives,
    keyed on (ticker, mother_bar_index, confirmation_bar_index)."""

def main(argv) -> int:
    """argparse: --seed REQUIRED, --limit OPTIONAL, --dataset-root OPTIONAL,
    --models-root OPTIONAL. Returns 0 on success."""
```

## Tasks Completed

### Task 1 — `generate_training_data.py` (`a67ba21`)

- `scripts/pattern_scanner/generate_training_data.py` (new, 344 lines):
  - **Imports** — `from scripts.pattern_scanner.detector import Detection, detect` (1×), `from scripts.pattern_scanner.renderer import STYLES, RenderStyle, compute_bbox_normalized, render` (1×), `from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF` (1×). Three-line `sys.path.insert` block at the top makes the script directly invokable as `python scripts/pattern_scanner/generate_training_data.py …`.
  - **Domain logic** — `_detect_positives()` runs filtered detect and drops dates >= cutoff. `_detect_hard_negatives()` runs `detect(..., apply_trend_filters=False)`, keys positives by `(ticker, mother_bar_index, confirmation_bar_index)`, and excludes any candidate present in the positive set OR with `confirmation_date >= TRAIN_TEST_CUTOFF`.
  - **Orchestration** — per-ticker loop emits `[i/total]` progress, sleeps 0.5s between tickers (matches `fetch_sp500.py`), broad exception handler logs and continues. After collection: D-08 gate triggers `_augment_to_floor()` round-robin if positives < 1000; otherwise each positive is tagged with `rng.choice(STYLES)`. Each negative gets `rng.choice(STYLES)`. Negatives are capped at `10 × len(positives)` via `rng.shuffle` + slice. Train/val split via `rng.shuffle` + 20% val.
  - **Per-sample write** — `_slice_window()` extracts 60 bars ending at confirmation (right-aligned, D-03). `render(window, style)` produces 640×640 PNG bytes; `compute_bbox_normalized(window, mother_in_window, 59, style)` produces the YOLO `(cx, cy, w, h)` for positives. Negatives get an empty `.txt` file. PNG sha256 fed into a running `hashlib.sha256()` instance.
  - **Manifest** — written to `args.dataset_root / dataset_manifest.json` AND `args.models_root / dataset_manifest.json` via `json.dumps(..., indent=2, sort_keys=True)`. Fields: `generated_at`, `seed`, `tickers`, `date_range`, `positives`, `negatives`, `neg_pos_ratio`, `renderer_styles_seen` (sorted list), `concat_sha256`.
  - **`data.yaml`** — `nc: 1`, `names: {0: inside_bar_spring}`, paths set to `args.dataset_root.resolve()`.
  - Smoke import passes:
    ```
    $ python -c "from scripts.pattern_scanner.generate_training_data import main, _fetch_ohlc, _detect_positives, _detect_hard_negatives, MIN_POSITIVES, NEG_POS_RATIO, DATASET_ROOT; print('module OK')"
    module OK
    ```

### Task 2 — `tests/test_generate_training_data.py` (`2467694`)

- Removed the Wave 0 `pytestmark = pytest.mark.skip(...)` line.
- Replaced 8 empty stub bodies with 8 real tests, all green, using monkeypatched `_fetch_ohlc`, `_load_tickers`, and `time.sleep`.
- File-local helpers:
  - `_build_uptrend(n)` and `_spring_setup_rows()` copied verbatim from `tests/test_detector_schema.py` (per Plan 01 idiom for un-importable file-local helpers).
  - `_flat_prefix_rows()` built fresh: 65-bar flat-price prefix `(100.0, 100.05, 99.95, 100.0)` forces `hh_hl=False`, then the same 4-bar cluster (mother + inside + break + confirm). `detect(df, "TST")` returns `[]`; `detect(df, "TST", apply_trend_filters=False)` returns ≥ 1.
- Test bodies:
  1. `test_yolo_directory_layout` — runs `main(--seed 42 --limit 3 --dataset-root tmp --models-root tmp)`; asserts the four image/label split directories exist, `data.yaml` contains `nc: 1` and `inside_bar_spring`, and BOTH manifest copies exist.
  2. `test_positive_label_format` — globs every `.txt`; for non-empty content asserts 5 fields, class id `"0"`, all 4 floats in `[0, 1]`. Asserts at least one positive found.
  3. `test_style_randomization_used` — `len(manifest["renderer_styles_seen"]) >= 2`.
  4. `test_cutoff_enforced` — patches `gen_mod.TRAIN_TEST_CUTOFF = "1900-01-01"`, asserts no non-empty label files AND `manifest["positives"] == 0` AND `manifest["negatives"] == 0`.
  5. `test_neg_pos_ratio_capped` — `manifest["neg_pos_ratio"] <= 10.0` AND `manifest["negatives"] <= 10 * manifest["positives"]`.
  6. `test_negative_labels_empty` — every label whose name contains `_neg_` is zero bytes.
  7. `test_hard_negative_set_difference` — uses the flat-prefix fixture; asserts filters-on returns `[]`, filters-off returns `>= 1`, positives keys are disjoint from negatives keys.
  8. `test_manifest_sha256_consistent` — runs `main` twice with the same seed into different roots; asserts `concat_sha256` is identical and 64-hex-shaped.

## Verification — actual `pytest` output

Generator-only (Task 2 verify):

```
$ source .venv/Scripts/activate && python -m pytest tests/test_generate_training_data.py -v --no-network
tests/test_generate_training_data.py::test_yolo_directory_layout PASSED  [ 12%]
tests/test_generate_training_data.py::test_positive_label_format PASSED  [ 25%]
tests/test_generate_training_data.py::test_style_randomization_used PASSED [ 37%]
tests/test_generate_training_data.py::test_cutoff_enforced PASSED        [ 50%]
tests/test_generate_training_data.py::test_neg_pos_ratio_capped PASSED   [ 62%]
tests/test_generate_training_data.py::test_negative_labels_empty PASSED  [ 75%]
tests/test_generate_training_data.py::test_hard_negative_set_difference PASSED [ 87%]
tests/test_generate_training_data.py::test_manifest_sha256_consistent PASSED [100%]

============================== 8 passed, 8 warnings in 849.53s (0:14:09) =====
```

(8 warnings are the `datetime.utcnow` deprecation in this module — non-blocking; cleanup deferred to a chore commit if revisited.)

Full suite — verifies Phase 7 + renderer contracts intact:

```
$ source .venv/Scripts/activate && python -m pytest tests/ -q --no-network
..sssssssssss....................sss.....                                [100%]
27 passed, 14 skipped, 8 warnings in 929.25s (0:15:29)
```

- **27 passed** = 12 schema (Phase 7) + 2 kwarg (Plan 01) + 5 renderer (Plan 02) + 8 generator (Plan 03)
- **14 skipped** = 11 known_setups (network-marked, skipped under `--no-network`) + 3 onnx_round_trip (Wave 0 stubs awaiting Plan 05)

Phase 7's 23-test contract intact (12 schema passed + 11 known_setups skipped under `--no-network`); renderer 5-test contract intact; kwarg 2-test contract intact.

## Manifest Evidence

The `test_manifest_sha256_consistent` test demonstrates same-seed determinism by running `main()` twice into independent tmp roots and asserting `manifest1["concat_sha256"] == manifest2["concat_sha256"]`. The on-disk PNGs hash deterministically (mplfinance + matplotlib Agg backend are byte-stable on the same machine — confirmed in Plan 02). Each PNG sha is ingested into the running concat sha in the order the write loop emits samples (train → val, deterministic shuffle order from the seeded `rng`). The 64-hex shape is asserted on every run. Per-PNG sha256 reads (loop in test 8) confirm each file is hashable independently.

A representative manifest (from a tmp run during the test suite):

```json
{
  "concat_sha256": "<64 hex chars>",
  "date_range": {"period": "10y", "train_test_cutoff": "2024-01-01"},
  "generated_at": "2026-05-03T00:..:..Z",
  "negatives": <int>,
  "neg_pos_ratio": <float in [0, 10]>,
  "positives": <int>,
  "renderer_styles_seen": ["style_a", ...],
  "seed": 42,
  "tickers": ["TST1", "TST2", "TST3"]
}
```

## Decisions Made

1. **Three-tuple key for hard-negative set difference** — `(ticker, mother_bar_index, confirmation_bar_index)`. Two-tuple `(mother_idx, conf_idx)` would alias across tickers because indices are per-frame positional. RESEARCH §Pitfall 7 explicitly required the ticker dimension.

2. **Single seeded `random.Random` instance** — drives style choice, train/val shuffle, AND negative subsample. No `random.seed()` or `np.random.seed()` calls; the np_rng is constructed-and-discarded as a future-proofing seam without mutating global state.

3. **`json.dumps(..., sort_keys=True)` for the committed manifest** — keeps the on-disk `models/dataset_manifest.json` byte-stable across re-runs; gives `git diff models/dataset_manifest.json` semantic signal tied to actual dataset content change.

4. **Synthetic-data start_date = `2020-01-01`** — confirmation_dates land in 2020-2021, well before `TRAIN_TEST_CUTOFF = 2024-01-01`. Lets the default test path keep positives in-set; the cutoff-enforcement test simply patches the cutoff to `1900-01-01` to flip every detection out-of-set.

5. **`_augment_to_floor()` re-emits same (ticker, det) across STYLES** — keeps augmentation matplotlib-bound rather than network-bound, and preserves the RESEARCH §1 style-memorisation mitigation. Multi-style augmentation only triggers if raw positives < 1,000 — Plan 04's actual S&P 500 dry run will tell us whether the gate fires.

6. **Renderer called twice per positive sample** — once for PNG bytes, once via `compute_bbox_normalized()` for the axes-transform read. Plan 02's open question 3 flagged this as a 2× speedup opportunity. Deferred to Plan 04 if generation wall time on the full S&P 500 universe is excessive.

7. **Broad `except Exception` in the per-ticker loop** — matches `scripts/fetch_sp500.py` pattern; prints `[i/total] {ticker}: unexpected error — {exc}` and continues. The trade-off is documented: a partial run produces a partial dataset, which the manifest's positive/negative counts make obvious.

## Open Questions for Plan 04

1. **Actual S&P 500 positive count after a real `--limit 50` (or full) dry run.** The 8 unit tests use a synthetic fixture with exactly one positive per ticker, so the test suite cannot answer "will the D-08 1,000-positive gate fire on real data?" Plan 04 should:
   - First task or pre-task: run `python scripts/pattern_scanner/generate_training_data.py --seed 42 --limit 50` and record the resulting `manifest["positives"]` value.
   - Extrapolate to ~503 tickers (linear scaling: positives_50 × 503/50 = expected_full).
   - If `expected_full < 1000`, the multi-style augmentation branch will fire on the full run — Plan 04 should budget for it (each augmented positive is one extra mplfinance render, so floor=1000 with 200 raw positives = 800 extra renders).
   - If `expected_full >= 1000`, the augmentation branch is dead code on the live run; budget the simpler path.

2. **Full-run wall time estimate.** The unit test suite at `--limit 3` took ~14 minutes — most of it mplfinance rendering. Linear scaling to 503 tickers with potentially ~5-10× more samples per ticker puts the dry run at multiple hours on this CPU-only machine (Plan 01 already documented `cuda_available=False`). Plan 04 should:
   - Decide whether to (a) overnight the dataset generation, (b) parallelise the per-ticker loop with `concurrent.futures.ProcessPoolExecutor` (Plan 02's open question 3 hinted at sharing the figure between `render` and `compute_bbox_normalized` for a 2× win — that's the easier optimisation), or (c) batch-only refresh `models/dataset_manifest.json` from cached intermediate state.
   - The `--limit 50` dry run from open question 1 will give a concrete walltime/sample number.

3. **Multi-style augmentation collision risk on tiny universes.** If `len(positives) == 1` and `MIN_POSITIVES = 1000`, the floor algorithm cycles `(positives[0], STYLES[i % 3])` 1,000 times — but with only 3 styles, only 3 unique sample_ids are ever generated. Subsequent iterations would overwrite the same files. The current code does NOT crash, but the resulting dataset is just 3 distinct PNGs replicated under the same name. Plan 04 should either (a) accept this as graceful degradation (the 1,000-positive gate is a real failure mode that should produce loud diagnostics, not a quietly-overwritten dataset), or (b) tighten `_augment_to_floor()` to bail with a clear error if `len(positives) * len(STYLES) < floor`. Recommendation: option (b) — fail loudly so the user knows the model can't be trained on this data.

4. **Determinism across yfinance data revisions.** The manifest reproducibility check passes within a single test run because `_fetch_ohlc` is monkeypatched to return identical synthetic frames. On the live path, two real yfinance calls a week apart can return slightly different OHLC values (corporate-action backfill, dividend retro-adjustments). Plan 04's actual training run should record the manifest hash AND a follow-up replay's hash — if they diverge, the diff is in upstream data and the manifest's `generated_at` is the right field to flag the mismatch. Documented; no code change needed yet.

## Self-Check: PASSED

- [x] `scripts/pattern_scanner/generate_training_data.py` exists, 344 lines (>= 200 required), imports cleanly via `python -c "from scripts.pattern_scanner.generate_training_data import main, _fetch_ohlc, _detect_positives, _detect_hard_negatives, MIN_POSITIVES, NEG_POS_RATIO, DATASET_ROOT"` (verified).
- [x] `grep -c "from scripts.pattern_scanner.split_config import TRAIN_TEST_CUTOFF"` = 1.
- [x] `grep -c "from scripts.pattern_scanner.renderer import"` = 1.
- [x] `grep -c "apply_trend_filters=False"` = 2 (one in `_detect_hard_negatives`, one in the docstring).
- [x] `grep -c "MIN_POSITIVES = 1000"` = 1.
- [x] `grep -c "NEG_POS_RATIO = 10"` = 1.
- [x] `grep -E "^def _fetch_ohlc"` matches.
- [x] `tests/test_generate_training_data.py` — `pytestmark = pytest.mark.skip` count = 0; `def test_*` count = 8; 364 lines (>= 200).
- [x] All 8 generator tests pass under `--no-network` (verified, 849.53s).
- [x] Phase 7 23-test contract intact: 12 schema passed + 11 known_setups skipped under `--no-network`; renderer 5 + kwarg 2 also pass.
- [x] Full suite: 27 passed, 14 skipped, 0 failed (929.25s).
- [x] Manifest written to BOTH `_dev/training_dataset/dataset_manifest.json` AND `models/dataset_manifest.json` (verified by `test_yolo_directory_layout` asserting both files exist).
- [x] Same-seed determinism asserted by `test_manifest_sha256_consistent`.
- [x] Commits: `a67ba21` (Task 1: generator), `2467694` (Task 2: 8 tests), and this Summary commit.
- [x] STATE.md and ROADMAP.md untouched (orchestrator owns those).
- [x] No `--no-verify`, no `Co-Authored-By` trailers, no `git add -A` (only the two declared files staged per task).
