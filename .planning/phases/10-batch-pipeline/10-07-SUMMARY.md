---
plan: 10-07
phase: 10-batch-pipeline
status: complete (awaiting human checkpoint)
completed_at: 2026-05-12
---

# Plan 10-07 — GHA Nightly Workflow + PIPE-04 Static Lint + ROADMAP Closeout

Wave 5 capstone. Lands the production CI workflow that runs the orchestrator nightly at 07:00 UTC, the static-lint test that pins the PIPE-04 invariant (no torch / ultralytics in `requirements.txt`), and finalizes the Phase 10 ROADMAP entry. The plan is `autonomous: false` — Task 4 (manual `workflow_dispatch` from the Actions UI on the merge branch) is the human checkpoint that confirms PIPE-01 success criterion 1 (a real GHA runner produces a non-empty `data.json` with `pipeline_status.completed = true`).

## What was built

### `.github/workflows/nightly-pattern-scanner.yml`
Mirrors `.github/workflows/nightly-screener.yml` line-for-line with the three documented deltas:
- **Delta 1 — cron:** `0 7 * * 1-5` (07:00 UTC weekdays — 1h after the DCF screener at 06:00 UTC, per D-23).
- **Delta 2 — invocation:** `python -m scripts.pattern_scanner.run_pipeline --tickers all --window-days 20 --out-dir docs/projects/patterns`.
- **Delta 3 — git add paths:** three paths instead of one — `docs/projects/patterns/data.json docs/projects/patterns/stats.json docs/projects/patterns/charts/`.

Trigger set: `schedule` (cron) + `workflow_dispatch` (manual). Runner: `ubuntu-latest`. Python: `3.11` via `actions/setup-python@v5`. Bot identity: `github-actions[bot] <github-actions[bot]@users.noreply.github.com>` — exactly mirroring `nightly-screener.yml` (D-22 / D-24). `permissions: contents: write` for the push.

### `tests/test_workflow_yaml.py`
Four offline assertions:
1. `test_workflow_cron` — YAML parses, cron is `0 7 * * 1-5`, `workflow_dispatch` trigger present. Compatible with PyYAML's behaviour of parsing the `on:` key as boolean `True` (defensive fallback).
2. `test_workflow_invokes_run_pipeline_module` — workflow runs `python -m scripts.pattern_scanner.run_pipeline …` with the three required flags (`--tickers all`, `--window-days 20`, `--out-dir docs/projects/patterns`).
3. `test_workflow_commits_three_paths` — commit step adds all three artifacts (`data.json`, `stats.json`, `charts/`).
4. `test_requirements_has_no_training_deps` — PIPE-04 invariant: `torch` and `ultralytics` are NOT in `requirements.txt`.

### `.planning/ROADMAP.md`
- Phase 10 row: `**Plans**: TBD` → `**Plans**: 7 plans (10-01..10-07)`.
- Phase Progress Tracking table: `| 10. Batch Pipeline | 0/? | Not started | — |` → `| 10. Batch Pipeline | 0/7 | In progress | — |`. The completion checkbox + final status update are owned by the post-execution workflow (`verify_phase_goal` → `update_roadmap`).

## Verification

```
pytest tests/test_workflow_yaml.py -v
```

| Test | Result |
|------|--------|
| `test_workflow_cron` | ✓ PASSED |
| `test_workflow_invokes_run_pipeline_module` | ✓ PASSED |
| `test_workflow_commits_three_paths` | ✓ PASSED |
| `test_requirements_has_no_training_deps` | ✓ PASSED |

PIPE-04 invariant confirmed: `torch=False`, `ultralytics=False` in `requirements.txt`.

## Human checkpoint (Task 4 — gating PIPE-01)

The only Phase 10 success criterion that cannot be verified offline is the actual GHA run. Required steps for the human reviewer:

1. Push this branch and create a merge PR (or merge to `main` if working on `main`).
2. Navigate to **Actions → Nightly Pattern Scanner Data → Run workflow** and trigger a manual `workflow_dispatch` on the merge branch.
3. Confirm:
   - The run finishes with a green check.
   - The bot's commit contains a non-empty `docs/projects/patterns/data.json`.
   - At least one annotated PNG was written under `docs/projects/patterns/charts/` (or, if no S&P 500 tickers have an in-window detection right now, an empty `charts/` directory with `detections: []` and `pipeline_status.completed = true` in data.json is also acceptable).
   - `pipeline_status.completed = true` in data.json — PIPE-01 success criterion 1.

Until that checkpoint is signed off, Phase 10 stays in `In progress` in the ROADMAP. The phase verifier (`gsd-verifier`) treats this as `human_needed` until manually confirmed.

## Deviations from plan

None at the code level. The YAML follows the `nightly-screener.yml` template line-for-line with only the three documented deltas; the test file matches the VALIDATION.md contract; the ROADMAP edit is the exact substitution specified.

## Self-Check: PASSED (offline portion)

- Workflow YAML valid (PyYAML parses cleanly).
- All 4 static-lint tests GREEN.
- PIPE-04 invariant: no torch / ultralytics in requirements.txt.
- ROADMAP Phase 10 row updated to `7 plans (10-01..10-07)`.
- No `Co-Authored-By: Claude` trailers in any commit.
- **Manual `workflow_dispatch` confirmation pending** — owned by the human reviewer per `autonomous: false`.
