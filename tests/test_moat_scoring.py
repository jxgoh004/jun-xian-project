"""Rules that turn agent scores into the published moat rating."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "economic-moat"))

import moat_scoring as ms  # noqa: E402


def _criteria(*scores):
    return {f"c{i}": {"score": s} for i, s in enumerate(scores)}


def _stock(op_income, roe=0.30, sector="Technology"):
    revenue = [100.0] * len(op_income)
    return {
        "sector": sector, "return_on_equity": roe,
        "book_value_per_share": 1.0, "shares_outstanding_m": 100.0, "debt_m": 0.0,
        "trends": {
            "years": [2022, 2023, 2024, 2025, "TTM"][-len(op_income) - 1:],
            "revenue": revenue + [100.0],
            "operating_income": op_income + [op_income[-1]],
            "net_income": op_income + [op_income[-1]],
            "free_cash_flow": op_income + [op_income[-1]],
        },
    }


def _tier(stock):
    return ms.assess_financials(ms.build_fact_sheet(stock))["tier"]


def test_one_dominant_source_is_enough():
    # A plain average of these would be 4.6 ("Narrow-None").
    rating = ms.compute_rating(_criteria(9.5, 7.0, 3.0, 2.0, 1.5), {"tier": "strong"}, 0.0)
    assert rating["overall_score"] == 8.5
    assert rating["overall_moat"] == "Wide"


def test_weak_financials_cap_the_rating_at_narrow():
    rating = ms.compute_rating(_criteria(9.5, 9.0, 8.0, 8.0, 8.0), {"tier": "weak"}, 0.0)
    assert rating["overall_score"] == 5.9
    assert rating["overall_moat"] == "Narrow"
    assert rating["scoring"]["capped"] is True


def test_haircut_is_clamped():
    rating = ms.compute_rating(_criteria(9.0, 9.0, 5.0), {"tier": "strong"}, 5.0)
    assert rating["scoring"]["haircut"] == ms.MAX_HAIRCUT
    assert rating["overall_score"] == 8.0


def test_failed_agents_are_excluded_not_zeroed():
    rating = ms.compute_rating(_criteria(8.0, 8.0, 6.0, None, None), {"tier": "strong"}, 0.0)
    assert rating["overall_score"] == 8.0


def test_rating_withheld_when_too_few_agents_succeed():
    with pytest.raises(ValueError):
        ms.compute_rating(_criteria(8.0, 8.0, None, None, None), {"tier": "strong"}, 0.0)


def test_financial_tiers():
    assert _tier(_stock([30.0, 31.0, 32.0, 33.0])) == "strong"
    assert _tier(_stock([8.0, -40.0, 20.0, 19.0])) == "adequate"   # one bad year tolerated
    assert _tier(_stock([20.0, 15.0, 50.0, 60.0])) == "strong"     # wide spread, but rising
    assert _tier(_stock([60.0, 50.0, 15.0, 20.0])) == "adequate"   # same spread, falling
    assert _tier(_stock([20.0, 60.0, 30.0, 25.0])) == "adequate"   # spiked, then gave it back
    assert _tier(_stock([-5.0, -4.0, 3.0, 4.0])) == "weak"
    assert _tier(_stock([None, None, None, None])) == "unknown"


def test_cash_is_excluded_from_invested_capital():
    assert ms.invested_capital(600.0, 100.0, 200.0) == 500.0
    assert ms.invested_capital(600.0, 100.0, 650.0) == 350.0   # floored at half
    assert ms.invested_capital(600.0, None, None) == 600.0


def test_cash_is_excluded_from_invested_capital():
    assert ms.invested_capital(600.0, 100.0, 200.0) == 500.0
    assert ms.invested_capital(600.0, 100.0, 650.0) == 350.0   # floored at half
    assert ms.invested_capital(600.0, None, None) == 600.0


def test_labels():
    assert [ms.label_for(s) for s in (7.5, 7.4, 6.8, 6.7, 5.0, 4.0, 3.9)] == [
        "Wide", "Wide-Narrow", "Wide-Narrow", "Narrow", "Narrow", "Narrow-None", "None",
    ]


def test_trend_follows_strongest_sources():
    def trend(directions, haircut):
        criteria = {f"c{i}": {"score": 9.0 - i, "trend": d} for i, d in enumerate(directions)}
        return ms.compute_rating(criteria, {"tier": "strong"}, haircut)["moat_trend"]

    assert trend(["strengthening", "strengthening", "weakening"], 0.2) == "widening"
    assert trend(["strengthening", "strengthening", "stable"], 0.5) == "stable"
    assert trend(["strengthening", "weakening", "stable"], 0.0) == "eroding"
    assert trend(["stable", "stable", "stable"], 0.7) == "eroding"
    assert trend(["stable", "stable", "stable"], 0.6) == "stable"
