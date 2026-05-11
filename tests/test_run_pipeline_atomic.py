"""Phase 10 D-17 / PIPE-02: atomic JSON write protocol.

RED (Wave 0): imports `_atomic_write_json` from `scripts.pattern_scanner.run_pipeline`
which does not yet exist on disk. Plan 10-04 creates it.

The contract this file locks:
  _atomic_write_json(path: Path, obj: dict) -> None
  Writes via temp + os.replace so a reader sees either the old file or the
  new file, never a partially-written intermediate. A pre-existing `.tmp`
  scratch file from a previous crashed run MUST be overwritten and then
  removed during the next successful write.
"""
from __future__ import annotations

import json

from scripts.pattern_scanner.run_pipeline import _atomic_write_json  # noqa: E402


def test_atomic_write_protocol(tmp_path):
    """PIPE-02: simulated mid-write does not leave a partial JSON file visible.

    Setup: pre-create a corrupted `data.json.tmp` (as if a previous run was
    killed mid-write). Action: call `_atomic_write_json` with the final path.
    Post-conditions:
      - The final `data.json` exists and parses as valid JSON.
      - The pre-existing `.tmp` file is gone (overwritten by the new write
        and then renamed into place via os.replace).
    """
    final = tmp_path / "data.json"
    tmp = tmp_path / "data.json.tmp"

    # 1. Pre-condition: simulate a half-baked .tmp from a crashed previous run.
    tmp.write_text('{"partial":')  # invalid JSON, no closing brace
    assert not final.exists()

    # 2. Normal atomic write — the .tmp file is overwritten then renamed.
    _atomic_write_json(
        final,
        {"detections": [], "pipeline_status": {"completed": True}},
    )

    # 3. Post-conditions: final exists, is valid JSON, and the .tmp is gone.
    assert final.exists()
    payload = json.loads(final.read_text())
    assert payload["pipeline_status"]["completed"] is True
    assert not tmp.exists()
