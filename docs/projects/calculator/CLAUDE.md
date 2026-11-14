# Project: True Value Finder — Intrinsic Value Calculator

An interactive DCF (Discounted Cash Flow) calculator that computes a per-share intrinsic value estimate for any publicly traded stock. The user enters a ticker symbol; the app fetches live financial data and populates all inputs automatically, so the analysis takes seconds rather than hours.

## What it demonstrates

Jun Xian built this to show how finance domain knowledge can be encoded into a practical tool — not just a formula, but opinionated choices about method selection, growth rate sourcing, and discount rate derivation that a value investor would actually care about.

## How it works

1. **Data fetch** — the frontend calls `GET /api/fetch-stock/<symbol>` (Flask backend). The server pulls TTM/annual financials, beta, share count and analyst growth estimates from Yahoo Finance. (FinViz was retired as a source: it now blocks automated requests.)

2. **Method auto-selection** — the calculator picks the most appropriate cash flow base:
   - Operating Cash Flow (OCF) by default
   - Free Cash Flow (FCF) when earnings are negative or OCF > 1.5× Net Income
   - Net Income and Normalized FCF are available as manual alternatives
   This mirrors how an analyst would manually decide which line to discount.

   **Normalized FCF** = TTM OCF − average capex over every period Yahoo provides (TTM + up to four fiscal years). It smooths a temporary capex surge, such as a data-centre build-out, that would otherwise depress reported FCF. It is never auto-selected: whether capex is "growth" or "maintenance" is the user's judgment call. Computed in `YahooFinanceFetcher.get_normalized_free_cash_flow()`; not available when the page falls back to the nightly screener cache.

3. **20-year multi-phase DCF model**
   - Years 1–5: primary growth rate (sourced from Yahoo analyst EPS growth estimate → Yahoo historical → default 5%)
   - Years 6–10: half the primary rate (mean-reversion assumption)
   - Years 11–20: fixed 4% terminal growth
   - Intrinsic value = sum of discounted cash flows + terminal value, adjusted for net debt, divided by shares outstanding (all share classes — Yahoo's `impliedSharesOutstanding`, not the single-class `sharesOutstanding`)

4. **Beta-driven discount rate** — uses a CAPM-style lookup table keyed on beta, with separate tables for US and HK/China-listed stocks. Higher-beta companies are discounted more heavily.

5. **Verify panel** — after fetching, the UI surfaces key financial figures with source attribution so the user can sanity-check the auto-filled inputs before running the model.

## Key files

```
index.html                          # This page — all UI logic in vanilla JS
api_server.py                       # Flask endpoint: /api/fetch-stock/<symbol>
shared/fetchers/yahoo_finance.py    # Pulls financials, beta, share count, analyst growth
```

## UI layout

- **Search bar** — ticker input + Fetch button + Calculate button
- **Left column** — editable input fields (cash flow, growth rates, discount rate, shares, debt, cash)
- **Right column** — results: intrinsic value, margin of safety, 20-year cash flow table, source data verification panel
- **Server status badge** — shows whether the live Render backend is reachable; inputs can still be entered manually if offline

## Design choices worth noting

- All fields are editable after auto-fill — the calculator is a starting point, not a black box
- Growth rate is capped at 25% by default (toggle to "Actual" to remove the cap) to prevent model blow-up on high-growth outliers
- Shares the site-wide light neutral theme (`#edece7` ground, Host Grotesk, square corners, ink buttons); teal `#0d5c63` appears only in data marks, and green/red/yellow only where they carry valuation meaning
