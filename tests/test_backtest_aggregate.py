"""BT-01: aggregate D-09 four-slice rollup correctness."""
import pytest

from scripts.pattern_scanner.backtest import aggregate


def _record(ct: str, is_spring: bool, exit_reason: str, R: float, hold_days: int) -> dict:
    return {
        "confirmation_type": ct,
        "is_spring": is_spring,
        "exit_reason": exit_reason,
        "R": R,
        "hold_days": hold_days,
    }


@pytest.fixture
def records():
    return [
        _record("pin", True, "target", 2.0, 5),
        _record("pin", True, "stop", -1.0, 3),
        _record("pin", False, "target", 2.0, 8),
        _record("mark_up", False, "open", 0.5, 100),
        _record("mark_up", False, "stop", -1.0, 4),
        _record("ice_cream", True, "target", 2.0, 6),
    ]


def test_aggregate_groupings(records):
    # Slice 1: 'all'
    all_slice = aggregate(records, [])
    assert set(all_slice.keys()) == {"all"}
    cell = all_slice["all"]
    assert cell["n"] == 6
    assert cell["target_count"] == 3
    assert cell["stop_count"] == 2
    assert cell["open_count"] == 1
    assert cell["n_resolved"] == 5
    assert cell["win_rate"] == pytest.approx(3 / 5)
    assert cell["avg_return_r"] == pytest.approx((2.0 - 1.0 + 2.0 + 0.5 - 1.0 + 2.0) / 6)
    assert cell["median_hold_days"] == 5  # median of resolved [5,3,8,4,6] = 5
    assert set(cell.keys()) == {"n", "n_resolved", "win_rate", "avg_return_r", "median_hold_days",
                                 "target_count", "stop_count", "open_count"}

    # Slice 2: by_confirmation_type
    by_ct = aggregate(records, ["confirmation_type"])
    assert set(by_ct.keys()) == {"pin", "mark_up", "ice_cream"}
    assert sum(c["n"] for c in by_ct.values()) == 6
    assert by_ct["pin"]["n"] == 3
    assert by_ct["pin"]["target_count"] == 2

    # Slice 3: by_is_spring
    by_spring = aggregate(records, ["is_spring"])
    assert set(by_spring.keys()) == {"True", "False"}
    assert by_spring["True"]["n"] == 3
    assert by_spring["False"]["n"] == 3

    # Slice 4: by_type_x_spring
    by_cross = aggregate(records, ["confirmation_type", "is_spring"])
    assert "pin_True" in by_cross
    assert "pin_False" in by_cross
    assert "mark_up_False" in by_cross
    assert "ice_cream_True" in by_cross
    # Cells with n<1 omitted: there is no mark_up_True or ice_cream_False record.
    assert "mark_up_True" not in by_cross
    assert "ice_cream_False" not in by_cross
