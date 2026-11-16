"""
Flask API Server — Intrinsic Value Calculator
Fetches stock data from Yahoo Finance
and returns it as JSON for the web frontend.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import math
import os

from shared.fetchers import YahooFinanceFetcher
from shared.dcf_rules import GROWTH_CAP_PCT, MODEL_RULES, sector_basis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


def safe_float(val):
    """Return val as float, or None if invalid/NaN."""
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def to_millions(val):
    """Convert raw value (in units) to millions."""
    f = safe_float(val)
    return round(f / 1_000_000, 2) if f is not None else None


def to_millions_shares(val):
    """Convert shares (in units) to millions."""
    f = safe_float(val)
    return round(f / 1_000_000, 4) if f is not None else None


# Discount rate lookup tables keyed by beta threshold value.
# The boundary values (0.80 and 1.60) act as sentinels for < and > rows.
_DISCOUNT_TABLE_US = [
    (0.80, 5.15),
    (1.00, 5.89),
    (1.10, 6.26),
    (1.20, 6.63),
    (1.30, 7.00),
    (1.40, 7.37),
    (1.50, 7.74),
    (1.60, 8.11),
]

_DISCOUNT_TABLE_HK = [
    (0.80,  7.88),
    (1.00,  9.36),
    (1.10, 10.10),
    (1.20, 10.84),
    (1.30, 11.58),
    (1.40, 12.32),
    (1.50, 13.07),
    (1.60, 13.81),
]

# Exchanges that use the China/HK table
_HK_EXCHANGES = {'HKG', 'HKSE', 'SHH', 'SHZ'}


def beta_to_discount_rate(beta, exchange=""):
    """
    Look up the discount rate from the CAPM reference table by finding
    the beta threshold closest to the given beta value.
    Uses the China/HK table when the exchange is a HK/China exchange,
    otherwise uses the US table.
    """
    if beta is None:
        return 6.00  # conservative default

    table = _DISCOUNT_TABLE_HK if exchange.upper() in _HK_EXCHANGES else _DISCOUNT_TABLE_US

    # Find the row whose threshold is closest to the actual beta
    closest_rate = min(table, key=lambda row: abs(row[0] - beta))[1]
    return closest_rate


@app.route("/api/fetch-stock/<symbol>", methods=["GET"])
def fetch_stock(symbol):
    symbol = symbol.strip().upper()

    # ── 1. Yahoo Finance ──────────────────────────────────────────────────────
    yf = YahooFinanceFetcher(symbol)
    if not yf.fetch_all_data():
        return jsonify({"error": f"Could not fetch data for '{symbol}'. Check the ticker symbol."}), 404

    # Company meta — falls back to other Yahoo endpoints when the profile is withheld
    profile       = yf.get_profile()
    company_name  = profile["name"] or symbol
    sector        = profile["sector"] or "N/A"
    industry      = profile["industry"] or "N/A"
    exchange      = profile["exchange"] or ""
    # Statements are in the reporting currency; the share price is in the trading
    # currency. If the reporting currency can't be determined we fall back to the
    # trading currency and flag it as unconfirmed.
    trading_currency    = profile["trading_currency"]
    currency            = profile["financial_currency"] or trading_currency or "USD"
    currency_unverified = profile["financial_currency"] is None
    # Reporting → trading currency, so the per-share value can be compared to price
    exchange_rate = None
    if not currency_unverified:
        exchange_rate = yf.get_exchange_rate(currency, trading_currency or currency)
        if exchange_rate is not None:
            exchange_rate = round(exchange_rate, 6)

    # Price
    current_price = safe_float(yf.get_last_price())

    # Shares outstanding (in millions)
    shares_raw = yf.get_total_shares_outstanding()  # all share classes
    shares_millions = to_millions_shares(shares_raw)

    # Guard: yfinance returns an empty object for invalid tickers without raising.
    # Reject if the response has no price and no shares — minimum viable data.
    if current_price is None and shares_millions is None and company_name == symbol:
        return jsonify({"error": f"No data found for '{symbol}'. Check the ticker symbol."}), 404

    # Cash flow values (in millions)
    ocf_raw          = yf.get_operating_cash_flow()           # TTM Operating Cash Flow
    ni_cont_ops_raw  = yf.get_net_income_continuing_ops_ttm() # TTM Net Income from Continuing Ops
    fcf_raw, fcf_basis = yf.get_free_cash_flow_with_basis()  # TTM, else latest fiscal year

    # Net income (for the "Discounted Net Income" method) — annual fallback
    ni_raw = None
    try:
        fin = yf.financials
        if fin is not None and not fin.empty and "Net Income" in fin.index:
            ni_raw = fin.loc["Net Income"].iloc[0]
    except Exception:
        ni_raw = None

    ocf_m         = to_millions(ocf_raw)          if ocf_raw         not in (None, "N/A") else None
    ni_cont_ops_m = to_millions(ni_cont_ops_raw)  if ni_cont_ops_raw not in (None, "N/A") else None
    ni_m          = to_millions(ni_raw)            if ni_raw          not in (None, "N/A") else None
    fcf_m         = to_millions(fcf_raw)           if fcf_raw         not in (None, "N/A") else None

    # ── Normalized FCF (TTM OCF − average capex over available periods) ──────
    # Offered as an alternative basis; never auto-selected.
    normalized_fcf_m = avg_capex_m = None
    capex_history    = []
    try:
        nfcf = yf.get_normalized_free_cash_flow()
    except Exception:
        nfcf = None
    if nfcf:
        normalized_fcf_m = to_millions(nfcf["normalized_fcf"])
        avg_capex_m      = to_millions(nfcf["avg_capex"])
        capex_history    = [
            {"period": p["period"], "capex_millions": to_millions(p["capex"])}
            for p in nfcf["capex_periods"]
        ]

    # ── Negative earnings detection ───────────────────────────────────────────
    negative_earnings = (
        (ni_m is not None and ni_m < 0)
        or (ni_cont_ops_m is not None and ni_cont_ops_m < 0)
    )
    fcf_is_negative = fcf_m is not None and fcf_m < 0

    # ── OCF inflation detection (OCF > 1.5× NI from Continuing Ops) ──────────
    ocf_inflated = (
        ocf_m is not None
        and ni_cont_ops_m is not None
        and ni_cont_ops_m > 0
        and ocf_m > 1.5 * ni_cont_ops_m
    )

    # ── Recommend valuation method ────────────────────────────────────────────
    if negative_earnings:
        recommended_method = "fcf"
        switch_reason      = "negative_earnings"
    elif ocf_inflated:
        recommended_method = "fcf"
        switch_reason      = "ocf_inflated"
    else:
        recommended_method = "ocf"
        switch_reason      = None

    # Sector basis (shared/dcf_rules.py): financials are valued on net income
    # with no debt or cash adjustment; the page applies that when basis is
    # "earnings". REITs come back as "not_rated" and the page warns.
    basis = sector_basis(sector)
    if basis == "earnings":
        recommended_method = "ni"
        switch_reason      = "financial_sector"

    auto_switch_to_fcf  = recommended_method == "fcf"
    # DCF is not applicable when all earnings bases are negative
    dcf_not_applicable  = negative_earnings and (fcf_m is None or fcf_is_negative)

    debt_raw  = yf.get_total_debt()
    cash_raw  = yf.get_cash_and_short_term_investments()
    debt_m    = to_millions(debt_raw) if debt_raw not in (None, "N/A") else None
    cash_m    = to_millions(cash_raw) if cash_raw not in (None, "N/A") else None

    # Growth rates — Yahoo Finance historical
    growth_rates = yf.estimate_growth_rates()
    yf_growth_cf  = safe_float(growth_rates.get("cash_flow_growth"))
    yf_growth_eps = safe_float(growth_rates.get("eps_growth"))

    # Analyst consensus EPS growth (Yahoo)
    yf_analyst = yf.get_analyst_growth_estimate()

    beta_info   = yf.get_beta()
    beta        = safe_float(beta_info["beta"]) if beta_info else None
    beta_source = beta_info["source"] if beta_info and beta is not None else None

    # ── 2. Decide best growth rate ────────────────────────────────────────────
    # Priority: Yahoo analyst estimate → Yahoo CF historical → Yahoo EPS historical
    #           → 5% default
    # No cap applied — the frontend lets the user choose between actual and ≤25%
    if yf_analyst is not None:
        growth_1_5_pct  = round(yf_analyst["rate"] * 100, 2)
        growth_source   = ("Yahoo Finance (analyst long-term EPS growth)"
                           if yf_analyst["basis"] == "long_term"
                           else "Yahoo Finance (analyst EPS growth, next fiscal year)")
    elif yf_growth_cf is not None:
        growth_1_5_pct  = round(yf_growth_cf * 100, 2)
        growth_source   = "Yahoo Finance (historical CF growth)"
    elif yf_growth_eps is not None:
        growth_1_5_pct  = round(yf_growth_eps * 100, 2)
        growth_source   = "Yahoo Finance (historical EPS growth)"
    else:
        growth_1_5_pct  = 5.0
        growth_source   = "Default (5%)"

    growth_6_10_pct  = round(growth_1_5_pct / 2, 2)
    growth_11_20_pct = 4.0   # Fixed long-term rate per the Excel model

    # Best beta, then look up discount rate from reference table
    best_beta = beta
    discount_rate_pct = beta_to_discount_rate(best_beta, exchange)

    # ── 3. Build response ─────────────────────────────────────────────────────
    result = {
        # Company
        "symbol":       symbol,
        "company_name": company_name,
        "sector":       sector,
        "industry":     industry,
        "currency":     currency,
        "exchange":     exchange,

        # Price & shares
        "current_price":    safe_float(current_price),
        "shares_millions":  shares_millions,

        # Cash flow inputs (in millions)
        "ocf_millions":         ocf_m,
        "ni_cont_ops_millions": ni_cont_ops_m,
        "ni_millions":          ni_m,
        "fcf_millions":         fcf_m,
        "fcf_basis":            fcf_basis if fcf_m is not None else None,  # "ttm" | "annual"
        "normalized_fcf_millions": normalized_fcf_m,
        "avg_capex_millions":      avg_capex_m,
        "capex_history":           capex_history,

        # Method recommendation
        "recommended_method": recommended_method,
        "basis":              basis,   # "cash_flow" | "earnings" | "not_rated"
        "model":              MODEL_RULES,
        "auto_switch_to_fcf": auto_switch_to_fcf,
        "switch_reason":      switch_reason,
        "negative_earnings":  negative_earnings,
        "dcf_not_applicable": dcf_not_applicable,
        "ocf_to_ni_ratio":    round(ocf_m / ni_cont_ops_m, 2) if (ocf_m and ni_cont_ops_m and ni_cont_ops_m > 0) else None,

        # Balance sheet (in millions)
        "debt_millions": debt_m,
        "cash_millions": cash_m,

        # Growth rates (as percentages, e.g. 13.12 means 13.12%)
        "growth_1_5_pct":    growth_1_5_pct,
        "growth_6_10_pct":   growth_6_10_pct,
        "growth_11_20_pct":  growth_11_20_pct,
        "growth_source":     growth_source,
        # The page caps Years 1-5 at this by default; growth_1_5_pct is the source figure
        "growth_cap_pct":    GROWTH_CAP_PCT,

        # Discount
        "beta":              safe_float(best_beta),
        "beta_source":       beta_source,   # "yahoo" | "computed" | None
        "discount_rate_pct": discount_rate_pct,

        # True when Yahoo withheld the reporting currency and `currency` is the
        # trading currency instead — wrong for foreign filers listed in the US
        "currency_unverified": currency_unverified,
        # Currency the share price is quoted in, and the rate that converts one
        # unit of `currency` into it (None when it could not be fetched)
        "trading_currency":    trading_currency or currency,
        "exchange_rate":       exchange_rate,

        # Data source flags
        "sources": {
            "yahoo_finance": True,
        }
    }

    return jsonify(result)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Intrinsic Value API is running."})


if __name__ == "__main__":
    print("=" * 60)
    print("  Intrinsic Value API Server")
    print("  Running at http://localhost:5000")
    print("  Open index.html in your browser to use the calculator")
    print("=" * 60)
    app.run(debug=False, port=5000, host="0.0.0.0")
