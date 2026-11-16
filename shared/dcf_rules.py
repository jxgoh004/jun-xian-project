"""Model rules shared by every tool that runs the 20-year DCF.

The nightly screener (scripts/fetch_sp500.py) and the calculator API
(api_server.py) import from here, and both publish MODEL_RULES in their JSON
so the pages read the same numbers instead of hard-coding their own.
"""

# Years 1-5 growth is capped here before it enters the DCF. Analyst and FinViz
# estimates above this compound into valuations many times the share price.
# There is deliberately no floor: a shrinking company should be valued as one.
GROWTH_CAP_PCT = 25.0

# A cash-flow DCF does not fit every business.
#   - Banks, insurers and asset managers: operating cash flow is dominated by
#     deposits, claims and client money, and debt is raw material rather than
#     financing. They are valued on net income with no debt or cash adjustment.
#   - REITs: the meaningful figure is funds from operations, which the free data
#     sources do not provide. They are not rated.
EARNINGS_BASIS_SECTORS = ("Financial Services",)
NOT_RATED_SECTORS = {"Real Estate": "reit"}

# A result this far from the market price says more about the inputs than the
# stock. It is still published, but flagged and kept out of the default ranking.
PLAUSIBLE_MAX_PRICE_MULTIPLE = 3.0
PLAUSIBLE_MIN_PRICE_MULTIPLE = round(1 / 3, 4)

MODEL_RULES = {
    "growth_cap_pct": GROWTH_CAP_PCT,
    "earnings_basis_sectors": list(EARNINGS_BASIS_SECTORS),
    "not_rated_sectors": NOT_RATED_SECTORS,
    "plausible_max_price_multiple": PLAUSIBLE_MAX_PRICE_MULTIPLE,
    "plausible_min_price_multiple": PLAUSIBLE_MIN_PRICE_MULTIPLE,
}


def sector_basis(sector):
    """How a sector is valued: 'cash_flow', 'earnings' or 'not_rated'."""
    if sector in NOT_RATED_SECTORS:
        return "not_rated"
    if sector in EARNINGS_BASIS_SECTORS:
        return "earnings"
    return "cash_flow"


def rate_result(basis, intrinsic_value, price, sector=None):
    """Return (rating, reason) for a valuation.

    rating is 'rated', 'low_confidence' or 'not_rated'; reason is None when rated.
    """
    if basis == "not_rated":
        return "not_rated", NOT_RATED_SECTORS.get(sector, "sector")
    if intrinsic_value is None or price is None or price <= 0:
        return "not_rated", "no_data"
    if intrinsic_value <= 0:
        return "low_confidence", "negative_value"
    if intrinsic_value > price * PLAUSIBLE_MAX_PRICE_MULTIPLE:
        return "low_confidence", "above_price_multiple"
    if intrinsic_value < price * PLAUSIBLE_MIN_PRICE_MULTIPLE:
        return "low_confidence", "below_price_multiple"
    return "rated", None


def apply_growth_cap(growth_pct):
    """Return (rate to use in the DCF, whether the cap changed it).

    growth_pct is a percentage (13.12 means 13.12%). None passes through.
    """
    if growth_pct is None:
        return None, False
    if growth_pct > GROWTH_CAP_PCT:
        return GROWTH_CAP_PCT, True
    return growth_pct, False
