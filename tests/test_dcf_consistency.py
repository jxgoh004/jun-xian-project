"""The DCF exists twice: Python for the nightly screener, JavaScript for the
calculator page. These tests keep the two copies and the shared growth cap
in step (no network)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.fetch_sp500 import calculate_intrinsic_value
from shared.dcf_rules import GROWTH_CAP_PCT, MODEL_RULES, apply_growth_cap

ROOT = Path(__file__).resolve().parents[1]
CALCULATOR = ROOT / "docs" / "projects" / "calculator" / "index.html"

# (cash flow $M, growth 1-5 %, discount rate %, shares M, debt $M, cash $M)
CASES = [
    (195878.0, 19.78, 5.89, 7426.1946, 35481.0, 64294.0),   # large, net cash
    (304.979, 25.0, 6.63, 235.696543, 9749.592, 8257.468),  # at the cap, net debt
    (3629.0, -12.5, 8.11, 516.73, 14997.0, 5145.0),         # shrinking
    (1200.0, 0.0, 5.15, 80.0, 0.0, 0.0),                    # flat, no balance sheet
]


def test_growth_cap_rule():
    assert apply_growth_cap(GROWTH_CAP_PCT + 40) == (GROWTH_CAP_PCT, True)
    assert apply_growth_cap(GROWTH_CAP_PCT) == (GROWTH_CAP_PCT, False)
    assert apply_growth_cap(12.3) == (12.3, False)
    assert apply_growth_cap(-68.8) == (-68.8, False)  # no floor, by design
    assert apply_growth_cap(None) == (None, False)
    assert MODEL_RULES["growth_cap_pct"] == GROWTH_CAP_PCT


def test_calculator_does_not_hardcode_a_different_cap():
    html = CALCULATOR.read_text(encoding="utf-8")
    fallback = re.search(r"let growthCapPct = ([\d.]+);", html)
    assert fallback, "calculator no longer declares growthCapPct"
    assert float(fallback.group(1)) == GROWTH_CAP_PCT
    assert "growthCapMode = 'capped'" in html, "calculator must cap by default"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_python_and_javascript_dcf_agree():
    html = CALCULATOR.read_text(encoding="utf-8")
    match = re.search(r"function computeIV\(.*?\n}\n", html, re.S)
    assert match, "computeIV not found in the calculator page"
    script = (
        match.group(0)
        + "const cases = " + json.dumps(CASES) + ";\n"
        + "console.log(JSON.stringify(cases.map(([cf, g, r, sh, debt, cash]) =>"
        + " computeIV(cf, g / 100, g / 200, 0.04, r / 100, debt, cash, sh, 1).ivPS)));\n"
    )
    out = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True
    ).stdout
    js_values = json.loads(out)

    for case, js_iv in zip(CASES, js_values):
        cf, g, r, sh, debt, cash = case
        py_iv, err = calculate_intrinsic_value(cf, g, r, sh, debt, cash)
        assert err is None
        assert py_iv == pytest.approx(js_iv, abs=0.01), case


# ── Sector basis and plausibility rating ────────────────────────────────────

def test_sector_basis():
    from shared.dcf_rules import sector_basis
    assert sector_basis("Financial Services") == "earnings"
    assert sector_basis("Real Estate", "REIT - Residential") == "not_rated"
    # Real Estate also holds ordinary companies (brokers, data providers)
    assert sector_basis("Real Estate", "Real Estate Services") == "cash_flow"
    assert sector_basis("Real Estate") == "cash_flow"
    assert sector_basis("Technology") == "cash_flow"
    assert sector_basis(None) == "cash_flow"


def test_rate_result_thresholds():
    from shared.dcf_rules import (PLAUSIBLE_MAX_PRICE_MULTIPLE,
                                  PLAUSIBLE_MIN_PRICE_MULTIPLE, rate_result)
    price = 100.0
    assert rate_result("cash_flow", 150.0, price) == ("rated", None)
    assert rate_result("cash_flow", price * PLAUSIBLE_MAX_PRICE_MULTIPLE + 1, price) == (
        "low_confidence", "above_price_multiple")
    assert rate_result("cash_flow", price * PLAUSIBLE_MIN_PRICE_MULTIPLE - 1, price) == (
        "low_confidence", "below_price_multiple")
    assert rate_result("cash_flow", -5.0, price) == ("low_confidence", "negative_value")
    assert rate_result("cash_flow", None, price) == ("not_rated", "no_data")
    assert rate_result("not_rated", 150.0, price, "REIT - Office") == ("not_rated", "reit")


def test_financials_are_valued_on_earnings_without_net_debt():
    from scripts.fetch_sp500 import value_stock
    common = dict(method="ocf", ocf_m=-50000.0, fcf_m=-60000.0, ni_m=5000.0,
                  growth_applied_pct=8.0, discount_rate_pct=7.0, shares_millions=1000.0,
                  current_price=100.0)
    bank = value_stock(sector="Financial Services", debt_m=400000.0, cash_m=300000.0, **common)
    assert bank["method"] == "ni" and bank["basis"] == "earnings"
    expected, _ = calculate_intrinsic_value(5000.0, 8.0, 7.0, 1000.0, 0, 0)
    assert bank["intrinsic_value"] == expected  # debt and cash ignored
    assert bank["rating"] == "rated"

    # The same figures for an ordinary company go through cash flow and net debt
    other = value_stock(sector="Industrials", debt_m=400000.0, cash_m=300000.0, **common)
    assert other["method"] == "ocf" and other["intrinsic_value"] < 0
    assert (other["rating"], other["rating_reason"]) == ("low_confidence", "negative_value")


def test_reits_and_loss_makers_are_not_rated():
    from scripts.fetch_sp500 import value_stock
    args = dict(method="ocf", ocf_m=900.0, fcf_m=400.0, ni_m=300.0, growth_applied_pct=5.0,
                discount_rate_pct=7.0, shares_millions=100.0, debt_m=0.0, cash_m=0.0,
                current_price=50.0)
    reit = value_stock(sector="Real Estate", industry="REIT - Retail", **args)
    assert reit["intrinsic_value"] is None and reit["valuation_label"] == "N/A"
    assert (reit["rating"], reit["rating_reason"]) == ("not_rated", "reit")

    broker = value_stock(sector="Real Estate", industry="Real Estate Services", **args)
    assert broker["basis"] == "cash_flow" and broker["intrinsic_value"] is not None

    loss = value_stock(sector="Technology", dcf_not_applicable=True, **args)
    assert (loss["rating"], loss["rating_reason"]) == ("not_rated", "negative_earnings")


def test_snapshot_matches_the_rules():
    """The committed snapshot must be what the rules produce, not a stale copy."""
    from scripts.fetch_sp500 import value_stock
    snap = json.loads((ROOT / "docs/projects/screener/data.json").read_text(encoding="utf-8"))
    assert snap["model"] == json.loads(json.dumps(MODEL_RULES))
    for s in snap["stocks"]:
        if s.get("basis") is None:
            continue
        base = s["method"] if s["method"] in ("ocf", "fcf") else "ocf"
        neg = s["ni_ttm_m"] is not None and s["ni_ttm_m"] < 0
        v = value_stock(
            sector=s["sector"], industry=s["industry"], method=base, ocf_m=s["ocf_m"], fcf_m=s["fcf_m"],
            ni_m=s["ni_ttm_m"], growth_applied_pct=s["growth_applied_pct"],
            discount_rate_pct=s["discount_rate_pct"],
            shares_millions=s["shares_outstanding_m"], debt_m=s["debt_m"], cash_m=s["cash_m"],
            current_price=s["current_price"],
            dcf_not_applicable=neg and (s["fcf_m"] is None or s["fcf_m"] < 0),
        )
        for key in ("intrinsic_value", "rating", "rating_reason", "basis"):
            assert v[key] == s[key], (s["ticker"], key)
