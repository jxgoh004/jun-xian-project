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
