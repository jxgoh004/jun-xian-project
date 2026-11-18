"""
run_moat_analysis.py — Economic Moat Batch Runner

Reads tickers from the existing screener data.json, runs moat analysis for
each company via moat_analyzer.py, and writes results to:
  - docs/projects/moat/data.json        (full moat reports)
  - docs/projects/screener/data.json    (patched with moat + moat_score fields)

Stocks that are due (never rated, rated under an older methodology, or older
than STALE_DAYS) are processed most-undervalued first, because the moat matters
most where the DCF says a stock is cheap. --limit caps how many due stocks one
run processes, so repeated runs work through the whole index.

Usage:
    python economic-moat/run_moat_analysis.py              # every due stock
    python economic-moat/run_moat_analysis.py --limit 5    # the 5 most urgent due stocks
    python economic-moat/run_moat_analysis.py --ticker AAPL,MSFT  # named stocks, always re-run
    python economic-moat/run_moat_analysis.py --seed       # write empty data.json and exit
    python economic-moat/run_moat_analysis.py --force      # treat every stock as due

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
from moat_scoring import METHODOLOGY_VERSION

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCREENER_DATA   = os.path.join(_PROJ_ROOT, "docs", "projects", "screener", "data.json")
MOAT_OUTPUT_DIR = os.path.join(_PROJ_ROOT, "docs", "projects", "moat")
MOAT_DATA       = os.path.join(MOAT_OUTPUT_DIR, "data.json")

STALE_DAYS = 90   # moats move slowly; re-analyse if older than this


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


def is_fresh(record: dict | None, stale_days: int = STALE_DAYS) -> bool:
    """True if the record uses the current methodology and is within stale_days."""
    if not record or record.get("methodology") != METHODOLOGY_VERSION:
        return False
    analyzed_at = record.get("analyzed_at")
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


def urgency(stock: dict, moat_index: dict) -> tuple:
    """Sort key: unrated stocks first, then the most undervalued."""
    discount = stock.get("discount_pct")
    return (
        stock["ticker"] in moat_index,
        -(discount if discount is not None else float("-inf")),
    )


def save(moat_index: dict) -> str:
    """Write the moat data.json and return its timestamp."""
    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(MOAT_DATA, {"updated_at": updated_at, "stocks": list(moat_index.values())})
    return updated_at


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

    if not os.path.exists(SCREENER_DATA):
        print(f"[error] Screener data not found at {SCREENER_DATA}.")
        sys.exit(1)
    stocks = load_json(SCREENER_DATA).get("stocks", [])

    # Determine tickers to process
    skipped = 0
    if args.ticker:
        stock_map = {s["ticker"]: s for s in stocks}
        wanted    = [t.strip().upper() for t in args.ticker.split(",") if t.strip()]
        missing   = [t for t in wanted if t not in stock_map]
        if missing:
            print(f"[error] not found in screener data.json: {', '.join(missing)}")
            sys.exit(1)
        work_list = [stock_map[t] for t in wanted]
    else:
        due = [s for s in stocks if args.force or not is_fresh(moat_index.get(s["ticker"]))]
        skipped = len(stocks) - len(due)
        due.sort(key=lambda s: urgency(s, moat_index))
        work_list = due[: args.limit] if args.limit else due
        print(f"{len(due)} stock(s) due, {skipped} fresh (< {STALE_DAYS} days, current methodology).")

    total = len(work_list)
    print(f"Processing {total} ticker(s)...\n")

    updated = 0
    failed  = 0
    totals  = {"input_tokens": 0, "output_tokens": 0, "web_searches": 0, "page_opens": 0,
               "standard_tier_retries": 0}

    for i, stock in enumerate(work_list, start=1):
        ticker = stock["ticker"]
        print(f"[{i}/{total}] {ticker}: analysing {stock.get('company_name', ticker)}...")
        try:
            result = await analyze_company(stock)
            moat_index[ticker] = result
            updated += 1
            for field in totals:
                totals[field] += result["usage"][field]
            print(
                f"[{i}/{total}] {ticker}: {result['overall_moat']} ({result['overall_score']}), "
                f"trend {result['moat_trend']}, "
                f"financial evidence {result['financial_evidence']['tier']} OK"
            )
            save(moat_index)   # after every stock, so an interrupted run keeps its work
        except Exception as exc:
            failed += 1
            print(f"[{i}/{total}] {ticker}: ERROR - {exc} (previous rating kept)", file=sys.stderr)

        # Rate limiting — 1 s between stocks to avoid API throttling
        if i < total:
            time.sleep(1)

    updated_at = save(moat_index)
    print(f"\nMoat data written -> {MOAT_DATA}")

    # Patch screener
    patch_screener(moat_index)

    print(f"\nDone. updated={updated}, failed={failed}, fresh={skipped}, processed={total}")
    if updated:
        print(
            f"Usage: {totals['input_tokens']:,} input tokens, "
            f"{totals['output_tokens']:,} output tokens, {totals['web_searches']} web searches "
            f"(per stock: {totals['input_tokens'] // updated:,} in, "
            f"{totals['output_tokens'] // updated:,} out, "
            f"{totals['web_searches'] / updated:.1f} searches, "
            f"{totals['page_opens'] / updated:.1f} page opens); "
            f"{totals['standard_tier_retries']} call(s) fell back to the standard tier"
        )
    print(f"updated_at: {updated_at}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Economic Moat batch analysis for S&P 500 stocks."
    )
    parser.add_argument(
        "--ticker", type=str, default=None,
        metavar="TICKERS",
        help="Analyse these tickers (comma-separated, e.g. AAPL,MSFT), fresh or not.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        metavar="N",
        help="Process at most N due tickers, most urgent first.",
    )
    parser.add_argument(
        "--seed", action="store_true",
        help="Write an empty seed moat data.json and exit.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Treat every ticker as due, even if its rating is still fresh.",
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
