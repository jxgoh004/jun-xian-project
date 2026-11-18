"""
moat_scoring.py — The deterministic half of the moat rating.

The AI agents gather evidence and score each moat source. Everything that
turns those scores into a published rating lives here, in plain code, so the
same inputs always give the same label:

  1. build_fact_sheet()      reported financials the agents must start from
  2. assess_financials()     do the numbers confirm a moat exists?
  3. compute_rating()        strongest sources, minus the bear-case haircut,
                             capped by the financial evidence

Method (after Morningstar / Pat Dorsey): a moat needs one or two strong
sources, not a high average across all five, and it only counts if it shows
up as durable returns on capital.
"""

METHODOLOGY_VERSION = 2

TAX_RATE = 0.21            # flat rate used for the approximate ROIC
TOP_SOURCE_WEIGHTS = (0.6, 0.4)
MAX_HAIRCUT = 1.0
ERODING_HAIRCUT = 0.7     # a haircut this large means the moat is being breached
MIN_VALID_CRITERIA = 3     # below this the rating is not published
# Cash is not capital at work in the business, so it is taken out of invested
# capital. The floor stops a cash-heavy balance sheet from shrinking the
# denominator towards zero: cash can at most halve it (double the ROIC).
MIN_INVESTED_SHARE = 0.5
# Cash is not capital at work in the business, so it is taken out of invested
# capital. The floor stops a cash-heavy balance sheet from shrinking the
# denominator towards zero: cash can at most halve it (double the ROIC).
MIN_INVESTED_SHARE = 0.5

# Score ceiling by strength of the financial evidence.
EVIDENCE_CAPS = {
    "strong":   10.0,      # no cap
    "adequate": 7.4,       # at most Wide-Narrow
    "unknown":  7.4,
    "weak":     5.9,       # at most Narrow
}

# Set from the spread of the first full S&P 500 run (Nov 2026): the original
# 8.0 / 7.0 bars put 4 of 503 stocks at Wide and two-thirds at Narrow.
MOAT_THRESHOLDS = [
    (7.5, "Wide"),
    (6.8, "Wide-Narrow"),
    (5.0, "Narrow"),
    (4.0, "Narrow-None"),
]


def label_for(score: float) -> str:
    for floor, label in MOAT_THRESHOLDS:
        if score >= floor:
            return label
    return "None"


# ---------------------------------------------------------------------------
# Fact sheet
# ---------------------------------------------------------------------------

def _pct(numerator, denominator):
    if numerator is None or not denominator:
        return None
    return round(100.0 * numerator / denominator, 1)


def _margins(numerators, revenues):
    return [_pct(n, r) for n, r in zip(numerators, revenues)]


def invested_capital(equity: float, debt: float | None, cash: float | None) -> float:
    """Equity plus debt, less cash and short-term investments (floored)."""
    gross = equity + (debt or 0.0)
    return max(gross - (cash or 0.0), MIN_INVESTED_SHARE * gross)


def invested_capital(equity: float, debt: float | None, cash: float | None) -> float:
    """Equity plus debt, less cash and short-term investments (floored)."""
    gross = equity + (debt or 0.0)
    return max(gross - (cash or 0.0), MIN_INVESTED_SHARE * gross)


def build_fact_sheet(stock: dict) -> dict:
    """Derive moat-relevant metrics from one screener record."""
    trends = stock.get("trends") or {}
    labels = trends.get("years") or []
    # Annual columns only: the trailing "TTM" column often repeats the last year.
    idx = [i for i, y in enumerate(labels) if y != "TTM"]
    years = [labels[i] for i in idx]

    def series(name):
        values = trends.get(name) or []
        return [values[i] if i < len(values) else None for i in idx]

    revenue = series("revenue")
    op_income = series("operating_income")
    net_income = series("net_income")
    fcf = series("free_cash_flow")

    cagr = None
    known = [(i, r) for i, r in enumerate(revenue) if r and r > 0]
    if len(known) >= 2:
        (i0, r0), (i1, r1) = known[0], known[-1]
        if i1 > i0:
            cagr = round(100.0 * ((r1 / r0) ** (1.0 / (i1 - i0)) - 1.0), 1)

    bvps = stock.get("book_value_per_share")
    shares = stock.get("shares_outstanding_m")
    equity = bvps * shares if bvps is not None and shares else None
    debt = stock.get("debt_m")

    roic = None
    latest_op = next((v for v in reversed(op_income) if v is not None), None)
    if latest_op is not None and equity is not None:
        invested = invested_capital(equity, debt, stock.get("cash_m"))
        if invested > 0:
            roic = round(100.0 * latest_op * (1.0 - TAX_RATE) / invested, 1)

    roe = stock.get("return_on_equity")
    roe = round(100.0 * roe, 1) if roe is not None else None

    return {
        "sector":               stock.get("sector"),
        "industry":             stock.get("industry"),
        "years":                years,
        "revenue_m":            revenue,
        "revenue_cagr_pct":     cagr,
        "operating_margin_pct": _margins(op_income, revenue),
        "net_margin_pct":       _margins(net_income, revenue),
        "fcf_margin_pct":       _margins(fcf, revenue),
        "roic_approx_pct":      roic,
        "roe_pct":              roe,
        "debt_to_equity_pct":   stock.get("debt_to_equity"),
        "market_cap_m":         stock.get("market_cap_m"),
    }


def format_fact_sheet(sheet: dict) -> str:
    """Render the fact sheet as text for an agent prompt."""
    def row(values, suffix="%"):
        return ", ".join("n/a" if v is None else f"{v}{suffix}" for v in values) or "n/a"

    def one(value, suffix="%"):
        return "n/a" if value is None else f"{value}{suffix}"

    years = ", ".join(str(y) for y in sheet["years"]) or "n/a"
    revenue = ", ".join(
        "n/a" if v is None else f"{v / 1000.0:,.1f}" for v in sheet["revenue_m"]
    ) or "n/a"
    return "\n".join([
        "Reported financials (Yahoo Finance, fiscal years, oldest first):",
        f"  Fiscal years:           {years}",
        f"  Revenue (USD bn):       {revenue}",
        f"  Revenue growth (CAGR):  {one(sheet['revenue_cagr_pct'])}",
        f"  Operating margin:       {row(sheet['operating_margin_pct'])}",
        f"  Net margin:             {row(sheet['net_margin_pct'])}",
        f"  Free cash flow margin:  {row(sheet['fcf_margin_pct'])}",
        f"  Return on invested capital (approx., latest year): {one(sheet['roic_approx_pct'])}",
        f"  Return on equity (trailing):                       {one(sheet['roe_pct'])}",
        f"  Debt to equity:         {one(sheet['debt_to_equity_pct'])}",
    ])


# ---------------------------------------------------------------------------
# Financial confirmation
# ---------------------------------------------------------------------------

def _all_positive(values):
    known = [v for v in values if v is not None]
    return bool(known) and all(v > 0 for v in known)


def _mostly_positive(values):
    """Positive in every year but at most one — tolerates a single one-off charge."""
    known = [v for v in values if v is not None]
    return len(known) >= 2 and sum(1 for v in known if v <= 0) <= 1


def _stable(values, floor=0.7):
    """True when the weakest year is at least `floor` of the best year."""
    known = [v for v in values if v is not None]
    if len(known) < 2 or min(known) <= 0:
        return False
    return min(known) / max(known) >= floor


def _rising(values, floor=0.7):
    """
    True when margins (oldest year first) ended above where they started and
    within `floor` of their best year. A wide spread caused by margins climbing
    is not the instability the moat test is looking for.
    """
    known = [v for v in values if v is not None]
    if len(known) < 2 or min(known) <= 0:
        return False
    return known[-1] > known[0] and known[-1] / max(known) >= floor


def assess_financials(sheet: dict) -> dict:
    """
    Classify how well the reported numbers support a moat.

    Returns {"tier": strong|adequate|weak|unknown, "reasons": [...]}.
    Banks and insurers are judged on return on equity and net margin, because
    operating income and free cash flow are not meaningful for them.
    """
    is_financial = sheet.get("sector") == "Financial Services"
    if is_financial:
        returns, returns_name = sheet["roe_pct"], "Return on equity"
        margins, margin_name = sheet["net_margin_pct"], "net margin"
        cash_ok = True
    else:
        returns, returns_name = sheet["roic_approx_pct"], "Return on invested capital"
        if returns is None and sheet["roe_pct"] is not None and sheet["roe_pct"] > 0:
            returns, returns_name = sheet["roe_pct"], "Return on equity"
        margins, margin_name = sheet["operating_margin_pct"], "operating margin"
        cash_ok = _all_positive(sheet["fcf_margin_pct"])

    # "Adequate" means returns at or above a typical large-company cost of capital.
    strong_bar, adequate_bar = (15.0, 10.0) if is_financial else (15.0, 7.0)
    profitable = _all_positive(margins)
    mostly_profitable = profitable or _mostly_positive(margins)
    stable = _stable(margins)
    rising = not stable and _rising(margins)
    reasons = []

    if not any(v is not None for v in margins):
        return {"tier": "unknown",
                "reasons": [f"No {margin_name} history available to confirm the moat."]}

    if returns is None:
        reasons.append("Returns on capital could not be measured from reported figures.")
    else:
        reasons.append(f"{returns_name} {returns}%.")
    reasons.append(
        f"{margin_name.capitalize()} positive in every year."
        if profitable else f"{margin_name.capitalize()} negative or missing in at least one year."
    )
    if profitable:
        reasons.append(
            f"{margin_name.capitalize()} stable across the period." if stable
            else f"{margin_name.capitalize()} rose across the period and ended near its high." if rising
            else f"{margin_name.capitalize()} swings widely across the period."
        )
    if not is_financial:
        reasons.append(
            "Free cash flow positive in every year."
            if cash_ok else "Free cash flow negative or missing in at least one year."
        )

    if returns is None:
        tier = "adequate" if profitable and cash_ok else "weak"
    elif returns >= strong_bar and profitable and (stable or rising) and cash_ok:
        tier = "strong"
    elif returns >= adequate_bar and mostly_profitable:
        tier = "adequate"
    else:
        tier = "weak"
    return {"tier": tier, "reasons": reasons}


# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------

def compute_rating(criteria: dict, financials: dict, haircut: float) -> dict:
    """
    Combine criterion scores, the bear-case haircut and the financial cap.

    criteria:   {key: {"score": float | None, ...}} — failed agents carry None
    financials: output of assess_financials()
    haircut:    points the skeptic agent takes off (clamped to 0..MAX_HAIRCUT)
    """
    valid = sorted(
        ((v["score"], k) for k, v in criteria.items() if v.get("score") is not None),
        reverse=True,
    )
    if len(valid) < MIN_VALID_CRITERIA:
        raise ValueError(
            f"only {len(valid)} of {len(criteria)} criterion agents succeeded; rating withheld"
        )

    top = valid[: len(TOP_SOURCE_WEIGHTS)]
    weights = TOP_SOURCE_WEIGHTS[: len(top)]
    source_score = sum(w * s for w, (s, _) in zip(weights, top)) / sum(weights)

    haircut = max(0.0, min(MAX_HAIRCUT, float(haircut or 0.0)))
    cap = EVIDENCE_CAPS[financials["tier"]]
    uncapped = max(0.0, source_score - haircut)
    score = round(min(cap, uncapped), 1)

    # Trend follows the direction of the sources the rating rests on. The
    # skeptic is prompted to find problems, so it does not get to set the
    # trend; only a material haircut can pull it to "eroding".
    directions = [criteria[k].get("trend", "stable") for _, k in top]
    if haircut >= ERODING_HAIRCUT or "weakening" in directions:
        trend = "eroding"
    elif all(d == "strengthening" for d in directions) and haircut <= 0.3:
        trend = "widening"
    else:
        trend = "stable"

    return {
        "overall_score":  score,
        "overall_moat":   label_for(score),
        "moat_trend":     trend,
        "scoring": {
            "top_sources":  [k for _, k in top],
            "source_score": round(source_score, 1),
            "haircut":      round(haircut, 1),
            "cap":          cap,
            "capped":       uncapped > cap,
        },
    }
