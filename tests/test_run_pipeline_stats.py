"""Phase 10 D-11: stats.json fallback chain + is_spring key normalization.

RED (Wave 0): imports `build_stats_json` from `scripts.pattern_scanner.run_pipeline`
which does not yet exist on disk. Plan 10-04 creates it.

Contract this file locks:
  build_stats_json(aggregates: dict) -> dict
    Output keys:
      - fallback_order: ["by_type_x_spring", "by_confirmation_type", "all"]
      - n_floor: 10
      - stats: {all, by_type_x_spring, by_confirmation_type, ...}
    The function emits the documented fallback chain as metadata; the chain
    itself is walked client-side by the Phase 11 frontend.
  Key normalization (RESEARCH L868): by_type_x_spring keys MUST be
    `{confirmation_type}_{spring|extended}` — never raw `pin_True` /
    `mark_up_False`. Either build_stats_json renames upstream or accepts
    already-normalized keys; the public stats.json output never carries
    `_True` / `_False`.
"""
from __future__ import annotations

from scripts.pattern_scanner.run_pipeline import build_stats_json  # noqa: E402


def _cell(
    n,
    win_rate=0.4,
    avg_return_r=0.0,
    median_hold_days=3,
    target_count=1,
    stop_count=1,
    open_count=0,
    n_resolved=None,
):
    """Build an `aggregate()` cell with the keys Phase 9 emits.

    Source: scripts/pattern_scanner/backtest.py L266-275.
    """
    return {
        "n": n,
        "n_resolved": n_resolved if n_resolved is not None else n,
        "win_rate": win_rate,
        "avg_return_r": avg_return_r,
        "median_hold_days": median_hold_days,
        "target_count": target_count,
        "stop_count": stop_count,
        "open_count": open_count,
    }


def _aggs(by_type_x_spring=None, by_confirmation_type=None, all_cell=None):
    """Build the aggregates dict shape that `_backtest_aggregates.json` carries."""
    return {
        "all": all_cell or _cell(80, win_rate=0.359),
        "by_confirmation_type": by_confirmation_type or {},
        "by_is_spring": {},
        "by_type_x_spring": by_type_x_spring or {},
    }


def test_stats_json_falls_back_to_by_confirmation_type_when_sparse():
    """D-11: sparse `by_type_x_spring` cell (n<10) -> fallback metadata emitted.

    The fallback chain is documented data in the output; client-side resolves it.
    """
    aggs = _aggs(
        by_type_x_spring={"pin_spring": _cell(5)},  # sparse
        by_confirmation_type={"pin": _cell(17)},  # sufficient
    )

    out = build_stats_json(aggs)

    assert out["fallback_order"] == [
        "by_type_x_spring",
        "by_confirmation_type",
        "all",
    ]
    assert out["n_floor"] == 10
    assert out["stats"]["by_type_x_spring"]["pin_spring"]["n"] == 5
    assert out["stats"]["by_confirmation_type"]["pin"]["n"] == 17


def test_stats_json_falls_back_to_all_when_both_sparse():
    """D-11 ultimate fallback: both finer cuts sparse -> `all` block preserved.

    Asserts every cell key from Phase 9's aggregate() L266-275 is present
    on the `all` block — that block is the last-resort denominator the
    Phase 11 drilldown shows when both finer cuts are too thin.
    """
    aggs = _aggs(
        by_type_x_spring={"pin_spring": _cell(2)},
        by_confirmation_type={"pin": _cell(3)},
        all_cell=_cell(80, win_rate=0.359),
    )

    out = build_stats_json(aggs)

    assert out["stats"]["all"]["n"] == 80
    required = {
        "n",
        "n_resolved",
        "win_rate",
        "avg_return_r",
        "median_hold_days",
        "target_count",
        "stop_count",
        "open_count",
    }
    assert required.issubset(out["stats"]["all"].keys())


def test_stats_json_normalizes_is_spring_keys():
    """RESEARCH L868: `pin_True` -> `pin_spring`, `mark_up_False` -> `mark_up_extended`.

    Phase 9's aggregate() str-coerces is_spring to "True"/"False" so the raw
    composite keys are `pin_True` / `mark_up_False`. Phase 10 must normalize
    to `{confirmation_type}_{spring|extended}` before writing stats.json.

    Whether build_stats_json renames internally OR accepts already-normalized
    input from export_aggregates.py is implementation-discretion. The public
    output contract: stats.json keys NEVER carry `_True` / `_False`.
    """
    aggs = _aggs(
        by_type_x_spring={"pin_True": _cell(12), "mark_up_False": _cell(15)}
    )

    out = build_stats_json(aggs)
    keys = set(out["stats"]["by_type_x_spring"].keys())

    assert "pin_True" not in keys
    assert "mark_up_False" not in keys
    assert "pin_spring" in keys
    assert "mark_up_extended" in keys
