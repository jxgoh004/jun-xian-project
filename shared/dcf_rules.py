"""Model rules shared by every tool that runs the 20-year DCF.

The nightly screener (scripts/fetch_sp500.py) and the calculator API
(api_server.py) import from here, and both publish MODEL_RULES in their JSON
so the pages read the same numbers instead of hard-coding their own.
"""

# Years 1-5 growth is capped here before it enters the DCF. Analyst and FinViz
# estimates above this compound into valuations many times the share price.
# There is deliberately no floor: a shrinking company should be valued as one.
GROWTH_CAP_PCT = 25.0

MODEL_RULES = {"growth_cap_pct": GROWTH_CAP_PCT}


def apply_growth_cap(growth_pct):
    """Return (rate to use in the DCF, whether the cap changed it).

    growth_pct is a percentage (13.12 means 13.12%). None passes through.
    """
    if growth_pct is None:
        return None, False
    if growth_pct > GROWTH_CAP_PCT:
        return GROWTH_CAP_PCT, True
    return growth_pct, False
