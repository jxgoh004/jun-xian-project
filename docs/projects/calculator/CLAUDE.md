# Project: True Value Finder — Intrinsic Value Calculator

An interactive DCF (Discounted Cash Flow) calculator that computes a per-share intrinsic value estimate for any publicly traded stock. The user enters a ticker symbol; the app fetches live financial data and populates all inputs automatically, so the analysis takes seconds rather than hours.

## What it demonstrates

Jun Xian built this to show how finance domain knowledge can be encoded into a practical tool — not just a formula, but opinionated choices about method selection, growth rate sourcing, and discount rate derivation that a value investor would actually care about.

## How it works

1. **Data fetch** — the frontend calls `GET /api/fetch-stock/<symbol>` (Flask backend). The server pulls TTM/annual financials from Yahoo Finance and valuation metrics + beta from FinViz.

2. **Method auto-selection** — the calculator picks the most appropriate cash flow base:
   - Operating Cash Flow (OCF) when earnings are negative or OCF > 1.5× Net Income
   - Free Cash Flow (FCF) otherwise, with Net Income as fallback
   This mirrors how an analyst would manually decide which line to discount.

3. **20-year multi-phase DCF model**
   - Years 1–5: primary growth rate (sourced from FinViz 5Y estimate → Yahoo historical → default 5%)
   - Years 6–10: half the primary rate (mean-reversion assumption)
   - Years 11–20: fixed 4% terminal growth
   - Intrinsic value = sum of discounted cash flows + terminal value, adjusted for net debt, divided by shares outstanding

4. **Beta-driven discount rate** — uses a CAPM-style lookup table keyed on beta, with separate tables for US and HK/China-listed stocks. Higher-beta companies are discounted more heavily.

5. **Verify panel** — after fetching, the UI surfaces key financial figures with source attribution (Yahoo vs. FinViz) so the user can sanity-check the auto-filled inputs before running the model.

## Key files

```
index.html                    # This page — all UI logic in vanilla JS
api_server.py                 # Flask endpoint: /api/fetch-stock/<symbol>
yahoo_finance_fetcher.py      # Pulls TTM/annual financials
finviz_fetcher.py             # Pulls beta, P/E, 5Y growth estimate
```

## UI layout

- **Search bar** — ticker input + Fetch button + Calculate button
- **Left column** — editable input fields (cash flow, growth rates, discount rate, shares, debt, cash)
- **Right column** — results: intrinsic value, margin of safety, 20-year cash flow table, source data verification panel
- **Server status badge** — shows whether the live Heroku backend is reachable; inputs can still be entered manually if offline

## Design choices worth noting

- All fields are editable after auto-fill — the calculator is a starting point, not a black box
- Growth rate is capped at 25% by default (toggle to "Actual" to remove the cap) to prevent model blow-up on high-growth outliers
- The dark GitHub-inspired theme (gold accent `#E8A838`, `DM Sans` + `Instrument Serif` typography) is intentional — it signals a developer-built tool, not a generic fintech dashboard
