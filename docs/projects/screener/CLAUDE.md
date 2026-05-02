# Project: S&P 500 DCF Screener

A pre-computed stock screener that runs the same DCF model as the interactive calculator across all ~500 S&P 500 companies and presents the results as a filterable, sortable table. The goal is to let someone quickly scan for potentially undervalued stocks without manually running each one through the calculator.

## What it demonstrates

The screener shows the same DCF methodology operating at scale — a batch pipeline that fetches financials for every S&P 500 ticker, applies the same opinionated model choices (method selection, beta-driven discount rate, multi-phase growth), and produces a static snapshot that loads instantly in the browser with no backend required.

## How it works

1. **Batch pipeline** (`scripts/fetch_sp500.py`) — fetches all S&P 500 tickers from Wikipedia, then for each ticker:
   - Pulls financials via `YahooFinanceFetcher` and `FinVizFetcher`
   - Applies the same 20-year multi-phase DCF logic as the calculator
   - Computes discount percentage vs. current price and a valuation label
   - Writes all results to `docs/projects/screener/data.json`

2. **Static data snapshot** — `data.json` is committed to the repo and served via GitHub Pages. It contains per-stock fields: ticker, company name, sector, current price, intrinsic value, discount %, DCF method used, and a full set of financial metrics (P/E, beta, ROE, debt/equity, etc.)

3. **Stock overview page** (`stock.html`) — clicking a screener row deep-links to a per-stock page that shows:
   - Key financial snapshot (market cap, P/E, EPS, book value, etc.)
   - Spider/radar chart across 5 dimensions (valuation, profitability, growth, financial health, momentum)
   - Embedded TradingView price chart
   - DCF result summary

## Key files

```
scripts/fetch_sp500.py              # Batch DCF runner — regenerates data.json
docs/projects/screener/
  index.html                        # Screener table UI
  stock.html                        # Per-stock overview page
  data.json                         # Static snapshot of ~500 S&P 500 DCF results
```

## UI layout (index.html)

- **Search + filters** — text search by ticker/company, sector dropdown, sort by discount % or other metrics
- **Results table** — each row shows ticker, company, sector, current price, intrinsic value, discount %, valuation label (Undervalued / Fair / Overvalued / Highly Overvalued), and key ratios
- Clicking a row navigates to `stock.html?ticker=<SYMBOL>`

## Design notes

- The screener is a **read-only, static page** — all filtering and sorting is done client-side in JS against the loaded JSON. No backend call needed
- The batch script is run periodically (nightly via GitHub Actions or manually) to keep the snapshot fresh
- Valuation labels are derived from the discount percentage: heavily negative means overvalued; positive means the model sees upside
- The same dark theme as the moat page (`#080c12`, `Syne` + `DM Sans`) — these two tools are visually paired as the "analytical" side of the portfolio, distinct from the interactive calculator's warmer gold-accented theme
