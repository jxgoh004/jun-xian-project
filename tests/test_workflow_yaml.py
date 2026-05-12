"""PIPE-04 static-lint coverage for the nightly pattern-scanner workflow.

These tests run offline and verify two invariants that the CI workflow encodes:
  1. The cron schedule is `0 7 * * 1-5` (07:00 UTC weekdays — 1h after the
     DCF screener at 06:00 UTC, per Phase 10 D-23).
  2. `requirements.txt` does NOT contain `torch` or `ultralytics` (Phase 8
     D-20 invariant inherited by Phase 10 — training deps are offline-only).
"""

from __future__ import annotations

import os

import yaml

WORKFLOW_PATH = ".github/workflows/nightly-pattern-scanner.yml"
REQUIREMENTS_PATH = "requirements.txt"


def test_workflow_cron() -> None:
    """The nightly pattern-scanner runs at 07:00 UTC on weekdays only."""
    assert os.path.exists(WORKFLOW_PATH), f"missing workflow: {WORKFLOW_PATH}"
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    # PyYAML parses the YAML key `on:` as the Python boolean True. Accept either
    # for compatibility with future PyYAML behaviour changes.
    triggers = workflow.get("on") or workflow.get(True)
    assert triggers is not None, "workflow has no `on` triggers"
    schedule = triggers.get("schedule")
    assert schedule, "workflow has no schedule trigger"
    assert schedule[0]["cron"] == "0 7 * * 1-5", (
        f"expected cron '0 7 * * 1-5' (07:00 UTC weekdays), got {schedule[0]['cron']!r}"
    )

    # workflow_dispatch must remain present for manual smoke testing.
    assert "workflow_dispatch" in triggers, "workflow_dispatch trigger missing"


def test_workflow_invokes_run_pipeline_module() -> None:
    """The CI step must run the package module, not a bare script path."""
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "python -m scripts.pattern_scanner.run_pipeline" in content, (
        "workflow does not invoke the run_pipeline module"
    )
    assert "--tickers all" in content
    assert "--window-days 20" in content
    assert "--out-dir docs/projects/patterns" in content


def test_workflow_commits_three_paths() -> None:
    """The commit step must add data.json, stats.json, AND charts/."""
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "docs/projects/patterns/data.json" in content
    assert "docs/projects/patterns/stats.json" in content
    assert "docs/projects/patterns/charts/" in content


def test_requirements_has_no_training_deps() -> None:
    """PIPE-04 invariant: production CI must not install torch / ultralytics."""
    assert os.path.exists(REQUIREMENTS_PATH), f"missing {REQUIREMENTS_PATH}"
    with open(REQUIREMENTS_PATH, encoding="utf-8") as f:
        deps = f.read().lower()
    assert "torch" not in deps, "requirements.txt must not include torch (PIPE-04)"
    assert "ultralytics" not in deps, (
        "requirements.txt must not include ultralytics (PIPE-04)"
    )
