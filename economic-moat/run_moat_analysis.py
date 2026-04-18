"""
run_moat_analysis.py — Monthly Economic Moat Batch Runner

Reads tickers from the existing screener data.json, runs moat analysis for
each company via moat_analyzer.py, and writes results to:
  - docs/projects/moat/data.json        (full moat reports)
  - docs/projects/screener/data.json    (patched with moat + moat_score fields)

Usage:
    python economic-moat/run_moat_analysis.py              # all S&P 500 stocks
    python economic-moat/run_moat_analysis.py --limit 5    # test run (first 5)
    python economic-moat/run_moat_analysis.py --ticker AAPL  # single stock
    python economic-moat/run_moat_analysis.py --seed       # write empty data.json and exit
    python economic-moat/run_moat_analysis.py --force      # re-analyse even if < 30 days old

Requires:
    OPENAI_API_KEY environment variable
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Allow running from project root or from economic-moat/
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PROJ_ROOT  = os.path.dirname(_THIS_DIR)
sys.path.insert(0, _THIS_DIR)   # so moat_analyzer / moat_prompts resolve

from moat_analyzer import analyze_company

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCREENER_DATA   = os.path.join(_PROJ_ROOT, "docs", "projects", "screener", "data.json")
MOAT_OUTPUT_DIR = os.path.join(_PROJ_ROOT, "docs", "projects", "moat")
MOAT_DATA       = os.path.join(MOAT_OUTPUT_DIR, "data.json")

STALE_DAYS = 30   # re-analyse if older than this


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def is_fresh(analyzed_at: str | None, stale_days: int = STALE_DAYS) -> bool:
    """Return True if the record was analysed within stale_days."""
    if not analyzed_at:
        return False
    try:
        ts = datetime.fromisoformat(analyzed_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - ts < timedelta(days=stale_days)
    except ValueError:
        return False


def build_moat_index(moat_data: dict) -> dict:
    """Build a ticker → record lookup from existing moat data.json."""
    return {s["ticker"]: s for s in moat_data.get("stocks", [])}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def write_seed() -> None:
    os.makedirs(MOAT_OUTPUT_DIR, exist_ok=True)
    seed = {"updated_at": None, "stocks": []}
    write_json(MOAT_DATA, seed)
    print(f"Seed moat data.json written to {MOAT_DATA}")


# ---------------------------------------------------------------------------
# Patch screener data.json with moat fields
# ---------------------------------------------------------------------------

def patch_screener(moat_index: dict) -> None:
    """Add/update moat and moat_score fields in the screener data.json."""
    if not os.path.exists(SCREENER_DATA):
        print(f"[warn] Screener data not found at {SCREENER_DATA} - skipping patch.")
        return

    screener = load_json(SCREENER_DATA)
    for stock in screener.get("stocks", []):
        ticker = stock.get("ticker")
        if ticker in moat_index:
            record = moat_index[ticker]
            stock["moat"]       = record.get("overall_moat", None)
            stock["moat_score"] = record.get("overall_score", None)
        elif "moat" not in stock:
            stock["moat"]       = None
            stock["moat_score"] = None

    write_json(SCREENER_DATA, screener)
    print(f"Screener data.json patched with moat fields -> {SCREENER_DATA}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run(args: argparse.Namespace) -> None:
    # Load existing moat data
    if os.path.exists(MOAT_DATA):
        moat_data = load_json(MOAT_DATA)
    else:
        moat_data = {"updated_at": None, "stocks": []}

    moat_index = build_moat_index(moat_data)

    # Determine tickers to process
    if args.ticker:
        ticker = args.ticker.strip().upper()
        if not os.path.exists(SCREENER_DATA):
            print(f"[error] Screener data not found. Cannot look up company details for {ticker}.")
            sys.exit(1)
        screener = load_json(SCREENER_DATA)
        stock_map = {s["ticker"]: s for s in screener.get("stocks", [])}
        if ticker not in stock_map:
            print(f"[error] {ticker} not found in screener data.json.")
            sys.exit(1)
        work_list = [stock_map[ticker]]
    else:
        if not os.path.exists(SCREENER_DATA):
            print(f"[error] Screener data not found at {SCREENER_DATA}.")
            sys.exit(1)
        screener  = load_json(SCREENER_DATA)
        work_list = screener.get("stocks", [])
        if args.limit:
            work_list = work_list[: args.limit]

    total = len(work_list)
    print(f"Processing {total} ticker(s)...\n")

    updated = 0
    skipped = 0

    for i, stock in enumerate(work_list, start=1):
        ticker       = stock["ticker"]
        company_name = stock.get("company_name", ticker)
        sector       = stock.get("sector", "N/A")
        industry     = stock.get("industry", "N/A")

        existing = moat_index.get(ticker)
        if not args.force and existing and is_fresh(existing.get("analyzed_at")):
            print(f"[{i}/{total}] {ticker}: skipped (fresh, < {STALE_DAYS} days old)")
            skipped += 1
            continue

        print(f"[{i}/{total}] {ticker}: analysing {company_name}...")
        try:
            result = await analyze_company(ticker, company_name, sector, industry)
            moat_index[ticker] = result
            updated += 1
            moat_label = result["overall_moat"]
            score      = result["overall_score"]
            print(f"[{i}/{total}] {ticker}: {moat_label} ({score}) OK")
        except Exception as exc:
            print(f"[{i}/{total}] {ticker}: ERROR - {exc}", file=sys.stderr)

        # Rate limiting — 1 s between stocks to avoid API throttling
        if i < total:
            time.sleep(1)

    # Rebuild moat data.json
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    moat_data  = {
        "updated_at": updated_at,
        "stocks":     list(moat_index.values()),
    }
    write_json(MOAT_DATA, moat_data)
    print(f"\nMoat data written -> {MOAT_DATA}")

    # Patch screener
    patch_screener(moat_index)

    print(f"\nDone. updated={updated}, skipped={skipped}, total={total}")
    print(f"updated_at: {updated_at}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monthly Economic Moat batch analysis for S&P 500 stocks."
    )
    parser.add_argument(
        "--ticker", type=str, default=None,
        metavar="TICKER",
        help="Analyse a single ticker (e.g. AAPL) instead of the full list.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        metavar="N",
        help="Process only the first N tickers (for testing).",
    )
    parser.add_argument(
        "--seed", action="store_true",
        help="Write an empty seed moat data.json and exit.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-analyse all tickers even if their data is still fresh.",
    )
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("[error] OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    if args.seed:
        write_seed()
        return

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
