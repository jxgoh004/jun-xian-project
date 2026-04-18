"""
fetch_sp500.py — S&P 500 batch DCF script

Fetches all S&P 500 tickers from Wikipedia, computes DCF intrinsic values
using the same logic as api_server.py and the calculator's computeIV function,
and writes a static data.json snapshot to docs/projects/screener/data.json.

Usage:
    python scripts/fetch_sp500.py             # process all ~500 tickers
    python scripts/fetch_sp500.py --limit 10  # process first 10 tickers (testing)
    python scripts/fetch_sp500.py --seed       # write empty seed file only
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime

import pandas as pd

# Add project root to sys.path so fetcher modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yahoo_finance_fetcher import YahooFinanceFetcher
from finviz_fetcher import FinVizFetcher

# ---------------------------------------------------------------------------
# Discount-rate lookup table (copied from api_server.py)
# ---------------------------------------------------------------------------

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


def beta_to_discount_rate(beta):
    """Return the closest US discount rate for a given beta. Default 6.00 when beta is None."""
    if beta is None:
        return 6.00
    return min(_DISCOUNT_TABLE_US, key=lambda row: abs(row[0] - beta))[1]


# ---------------------------------------------------------------------------
# DCF engine — must match the JS computeIV function exactly
# ---------------------------------------------------------------------------

def calculate_intrinsic_value(cash_flow_m, growth_1_5_pct, discount_rate_pct,
                               shares_millions, debt_m, cash_m):
    """
    Compute per-share intrinsic value using a 20-year DCF model.

    Matches docs/projects/calculator/index.html computeIV exactly:
      - cumulative discount factor: prev_df / (1 + r)   NOT (1+r)**year
      - growth phases: years 1-5 = g1, years 6-10 = g2 (=g1/2), years 11-20 = g3 (=4%)
      - all monetary inputs in millions; result is per-share in USD

    Returns:
        (float, None)  on success
        (None, str)    on failure, with an error reason string
    """
    if cash_flow_m is None or shares_millions is None or shares_millions <= 0:
        return None, "missing_inputs"

    g1 = growth_1_5_pct / 100
    g2 = g1 / 2
    g3 = 0.04
    r = discount_rate_pct / 100

    prev_cf = cash_flow_m
    prev_df = 1.0
    total_pv = 0.0

    for yr in range(1, 21):
        g = g1 if yr <= 5 else (g2 if yr <= 10 else g3)
        proj = prev_cf * (1 + g)
        df = prev_df / (1 + r)
        total_pv += proj * df
        prev_cf = proj
        prev_df = df

    debt_adj = (debt_m or 0)
    cash_adj = (cash_m or 0)
    iv_per_share = (total_pv / shares_millions
                    - debt_adj / shares_millions
                    + cash_adj / shares_millions)
    return round(iv_per_share, 2), None


# ---------------------------------------------------------------------------
# Valuation label (per D-14)
# ---------------------------------------------------------------------------

def compute_valuation_label(intrinsic_value, current_price):
    """
    Derive discount_pct and a human-readable valuation label.

    Returns:
        (discount_pct: float, label: str)
        discount_pct can be negative (stock is trading above IV).
    """
    if intrinsic_value is None or intrinsic_value <= 0 or current_price is None:
        return None, "N/A"

    discount_pct = round((intrinsic_value - current_price) / intrinsic_value * 100, 2)

    if discount_pct > 30:
        label = "Highly Undervalued"
    elif discount_pct > 10:
        label = "Slightly Undervalued"
    elif discount_pct >= -10:
        label = "Fairly Valued"
    elif discount_pct >= -30:
        label = "Slightly Overvalued"
    else:
        label = "Highly Overvalued"

    return discount_pct, label


# ---------------------------------------------------------------------------
# Ticker fetcher
# ---------------------------------------------------------------------------

def fetch_sp500_tickers():
    """
    Fetch the current S&P 500 constituent list from Wikipedia.
    Searches for a column whose name contains 'symbol' or 'ticker'
    (case-insensitive) to survive Wikipedia table format changes.

    Returns a list of normalised ticker strings (e.g. 'BRK-B').
    """
    import io
    import requests as req_lib

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    # Wikipedia returns 403 for the default urllib user-agent; use a browser UA.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    resp = req_lib.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]

    # Find ticker column defensively
    ticker_col = None
    for col in df.columns:
        if "symbol" in col.lower() or "ticker" in col.lower():
            ticker_col = col
            break

    if ticker_col is None:
        raise ValueError(
            f"Could not find ticker column in Wikipedia table. "
            f"Columns found: {list(df.columns)}"
        )

    tickers = df[ticker_col].astype(str).tolist()
    # Normalise BRK.B -> BRK-B for Yahoo Finance compatibility
    return [t.replace(".", "-") for t in tickers]


# ---------------------------------------------------------------------------
# Per-ticker processing
# ---------------------------------------------------------------------------

def safe_float(value):
    """Return float or None; swallow non-numeric sentinels and NaN/Inf."""
    if value is None or value == "N/A":
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def to_millions(value):
    """Convert a raw value to millions, or None if unusable."""
    f = safe_float(value)
    if f is None:
        return None
    return f / 1_000_000


def process_ticker(ticker, index, total):
    """
    Fetch data for one ticker and return a dict matching the data.json schema.

    Fields returned:
        ticker, company_name, sector, current_price,
        intrinsic_value, discount_pct, method, valuation_label
    """
    null_record = {
        "ticker": ticker,
        "company_name": ticker,
        "sector": "N/A",
        "current_price": None,
        "intrinsic_value": None,
        "discount_pct": None,
        "method": "N/A",
        "valuation_label": "N/A",
    }

    # ── Yahoo Finance ────────────────────────────────────────────────────────
    yf = YahooFinanceFetcher(ticker)
    if not yf.fetch_all_data():
        print(f"[{index}/{total}] {ticker}: fetch failed (Yahoo)")
        return null_record

    info = yf.info or {}

    company_name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector") or "N/A"

    current_price = safe_float(
        info.get("currentPrice") or info.get("previousClose")
    )

    shares_raw = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
    shares_millions = to_millions(shares_raw)

    ocf_raw = yf.get_operating_cash_flow()
    ni_cont_ops_raw = yf.get_net_income_continuing_ops_ttm()
    fcf_raw = yf.get_free_cash_flow()

    ocf_m = to_millions(ocf_raw) if ocf_raw not in (None, "N/A") else None
    ni_cont_ops_m = to_millions(ni_cont_ops_raw) if ni_cont_ops_raw not in (None, "N/A") else None
    fcf_m = to_millions(fcf_raw) if fcf_raw not in (None, "N/A") else None

    debt_raw = yf.get_total_debt()
    cash_raw = yf.get_cash_and_short_term_investments()
    debt_m = to_millions(debt_raw) if debt_raw not in (None, "N/A") else None
    cash_m = to_millions(cash_raw) if cash_raw not in (None, "N/A") else None

    growth_rates = yf.estimate_growth_rates()
    yf_growth_cf = safe_float(growth_rates.get("cash_flow_growth"))
    yf_growth_eps = safe_float(growth_rates.get("eps_growth"))

    beta = safe_float(info.get("beta"))

    # ── FinViz (optional — enhances growth rate and beta) ────────────────────
    finviz_growth_5y = None
    finviz_beta = None

    try:
        fv = FinVizFetcher(ticker)
        if fv.fetch_data():
            fv_growth = fv.get_growth_estimates()
            finviz_growth_5y = safe_float(
                fv_growth.get("EPS Growth Next 5 Years")
            )
            fv_val = fv.get_valuation_metrics()
            finviz_beta = safe_float(fv_val.get("Beta"))
    except Exception:
        pass  # FinViz failures are expected and silently ignored

    # ── Method selection (mirrors api_server.py exactly) ────────────────────
    # ni_m is not used for method selection here; we only need ni_cont_ops_m
    negative_earnings = (
        (ni_cont_ops_m is not None and ni_cont_ops_m < 0)
    )
    fcf_is_negative = fcf_m is not None and fcf_m < 0

    ocf_inflated = (
        ocf_m is not None
        and ni_cont_ops_m is not None
        and ni_cont_ops_m > 0
        and ocf_m > 1.5 * ni_cont_ops_m
    )

    if negative_earnings:
        method = "fcf"
    elif ocf_inflated:
        method = "fcf"
    else:
        method = "ocf"

    dcf_not_applicable = negative_earnings and (fcf_m is None or fcf_is_negative)

    # ── Select cash flow base ────────────────────────────────────────────────
    if method == "fcf":
        cash_flow_m = fcf_m
    else:
        cash_flow_m = ocf_m

    # ── Growth rate priority ─────────────────────────────────────────────────
    # FinViz 5Y EPS (as decimal from get_growth_estimates) -> multiply by 100 for pct
    # Yahoo CF growth (as decimal) -> multiply by 100 for pct
    # Yahoo EPS growth (as decimal) -> multiply by 100 for pct
    # Default 5.0
    if finviz_growth_5y is not None:
        growth_1_5_pct = round(finviz_growth_5y * 100, 2)
    elif yf_growth_cf is not None:
        growth_1_5_pct = round(yf_growth_cf * 100, 2)
    elif yf_growth_eps is not None:
        growth_1_5_pct = round(yf_growth_eps * 100, 2)
    else:
        growth_1_5_pct = 5.0

    # ── Discount rate ────────────────────────────────────────────────────────
    best_beta = finviz_beta if finviz_beta is not None else beta
    discount_rate_pct = beta_to_discount_rate(best_beta)

    # ── DCF calculation ──────────────────────────────────────────────────────
    if dcf_not_applicable or cash_flow_m is None:
        intrinsic_value = None
        discount_pct = None
        valuation_label = "N/A"
    else:
        intrinsic_value, err = calculate_intrinsic_value(
            cash_flow_m=cash_flow_m,
            growth_1_5_pct=growth_1_5_pct,
            discount_rate_pct=discount_rate_pct,
            shares_millions=shares_millions,
            debt_m=debt_m,
            cash_m=cash_m,
        )
        if err:
            intrinsic_value = None
            discount_pct = None
            valuation_label = "N/A"
        else:
            discount_pct, valuation_label = compute_valuation_label(
                intrinsic_value, current_price
            )

    result_str = (
        f"IV={intrinsic_value}, label={valuation_label}"
        if intrinsic_value is not None
        else "IV=N/A"
    )
    print(f"[{index}/{total}] {ticker}: {result_str}")

    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "current_price": current_price,
        "intrinsic_value": intrinsic_value,
        "discount_pct": discount_pct,
        "method": method,
        "valuation_label": valuation_label,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch S&P 500 data and compute DCF intrinsic values."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N tickers (for local testing).",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Write an empty seed data.json and exit immediately.",
    )
    args = parser.parse_args()

    # Determine output path relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "docs", "projects", "screener")
    output_path = os.path.join(output_dir, "data.json")

    os.makedirs(output_dir, exist_ok=True)

    if args.seed:
        seed_data = {"updated_at": None, "stocks": []}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(seed_data, f, indent=2)
        print(f"Seed data.json written to {output_path}")
        return

    # Preserve moat fields from the existing screener data before overwriting
    existing_moat = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, encoding="utf-8") as f:
                existing = json.load(f)
            existing_moat = {
                s["ticker"]: {"moat": s.get("moat"), "moat_score": s.get("moat_score")}
                for s in existing.get("stocks", [])
                if s.get("moat") is not None or s.get("moat_score") is not None
            }
        except Exception:
            pass

    # Fetch ticker list
    print("Fetching S&P 500 ticker list from Wikipedia...")
    tickers = fetch_sp500_tickers()
    print(f"Found {len(tickers)} tickers.")

    if args.limit is not None:
        tickers = tickers[: args.limit]
        print(f"Limiting to first {len(tickers)} tickers.")

    total = len(tickers)
    stocks = []

    for i, ticker in enumerate(tickers, start=1):
        try:
            record = process_ticker(ticker, i, total)
        except Exception as exc:
            print(f"[{i}/{total}] {ticker}: unexpected error — {exc}")
            record = {
                "ticker": ticker,
                "company_name": ticker,
                "sector": "N/A",
                "current_price": None,
                "intrinsic_value": None,
                "discount_pct": None,
                "method": "N/A",
                "valuation_label": "N/A",
            }

        if ticker in existing_moat:
            record["moat"]       = existing_moat[ticker]["moat"]
            record["moat_score"] = existing_moat[ticker]["moat_score"]

        stocks.append(record)

        # Rate limiting — avoid Yahoo Finance 429 errors
        if i < total:
            time.sleep(0.5)

    updated_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    output = {"updated_at": updated_at, "stocks": stocks}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. {len(stocks)} stocks written to {output_path}")
    print(f"updated_at: {updated_at}")


if __name__ == "__main__":
    main()
