# Project: True Value Finder — Intrinsic Value Calculator

An interactive DCF (Discounted Cash Flow) calculator that computes a per-share intrinsic value estimate for any publicly traded stock. The user enters a ticker symbol; the app fetches live financial data and populates all inputs automatically, so the analysis takes seconds rather than hours.

## What it demonstrates

Jun Xian built this to show how finance domain knowledge can be encoded into a practical tool — not just a formula, but opinionated choices about method selection, growth rate sourcing, and discount rate derivation that a value investor would actually care about.

## How it works

1. **Data fetch** — the frontend calls `GET /api/fetch-stock/<symbol>` (Flask backend). The server pulls TTM/annual financials, beta, share count and analyst growth estimates from Yahoo Finance. FinViz blocks automated requests from the API host, so the API never calls it.

2. **Method auto-selection** — the calculator picks the most appropriate cash flow base:
   - Operating Cash Flow (OCF) by default
   - Free Cash Flow (FCF) when earnings are negative or OCF > 1.5× Net Income
   - Net Income and Normalized FCF are available as manual alternatives
   This mirrors how an analyst would manually decide which line to discount.

   **Normalized FCF** = TTM OCF − average capex over every period Yahoo provides (TTM + up to four fiscal years). It smooths a temporary capex surge, such as a data-centre build-out, that would otherwise depress reported FCF. It is never auto-selected: whether capex is "growth" or "maintenance" is the user's judgment call. Computed in `YahooFinanceFetcher.get_normalized_free_cash_flow()`; not available when the page falls back to the nightly screener cache.

3. **20-year multi-phase DCF model**
   - Years 1–5: primary growth rate (S&P 500 tickers: FinViz 5Y EPS estimate, taken from the nightly screener snapshot `../screener/calculator_cache.json` when its `growth_source` is `finviz_5y`; otherwise Yahoo analyst EPS growth estimate → Yahoo historical → default 5%)
   - Years 6–10: half the primary rate (mean-reversion assumption)
   - Years 11–20: fixed 4% terminal growth
   - Intrinsic value = sum of discounted cash flows + terminal value, adjusted for net debt, divided by shares outstanding (all share classes — Yahoo's `impliedSharesOutstanding`, not the single-class `sharesOutstanding`)

4. **Beta-driven discount rate** — uses a CAPM-style lookup table keyed on beta, with separate tables for US and HK/China-listed stocks. Higher-beta companies are discounted more heavily.

5. **Verify panel** — after fetching, the UI surfaces key financial figures with source attribution so the user can sanity-check the auto-filled inputs before running the model.

## Data flow for growth

The page calls the live API first. If the ticker is in the nightly screener snapshot with a FinViz-sourced growth rate, that rate replaces the API's Yahoo estimate (`applyScreenerGrowth`). The snapshot is also the fallback when the live server is offline, and it fills in beta, discount rate, company name, sector and industry when the live API returns them empty (`fillGapsFromSnapshot`) — Yahoo sometimes withholds the company profile from the API host. A link under the growth field opens FinViz so users can enter a figure by hand.

## Currencies

Statements are in the company's reporting currency (`currency`); the share price is in the listing currency (`trading_currency`). They differ for foreign filers — TSM reports in TWD and trades in USD, Tencent reports in CNY and trades in HKD. The API returns `exchange_rate` (one unit of reporting currency in listing currency, from Yahoo's `XXXYYY=X` pair) and the page fills the Exchange Rate field with it, so the per-share value is comparable to the price. The field resets to 1 on every fetch. If the rate cannot be fetched the page shows an "Enter exchange rate" warning.

## Free cash flow basis

`fcf_millions` is trailing twelve months (last four quarters of Yahoo's Free Cash Flow row, or OCF − capex), matching OCF. It falls back to the latest fiscal year for companies without four quarterly periods inside a year (half-yearly filers); `fcf_basis` is `"ttm"` or `"annual"` and the verify panel labels it accordingly. The nightly screener uses the same getter.

## Growth inputs

Typing a Years 1–5 rate sets Years 6–10 to half of it, until the user types their own Years 6–10 figure. A new fetch or the cap toggle restores the link.

## When Yahoo withholds the company profile

Yahoo rate-limits its company-profile endpoint (HTTP 429) for the API host's shared address, while the price and statement endpoints keep answering. The API therefore does not depend on the profile:

- **Name, exchange, trading currency** — from price-chart metadata; **sector, industry** — from Yahoo's search endpoint (`YahooFinanceFetcher.get_profile()`).
- **Beta** — computed from five years of monthly returns against the S&P 500 (`get_beta()`, returned with `beta_source: "computed"`). Close to Yahoo's figure for US stocks; can differ noticeably for foreign companies.
- **Reporting currency** — read from the currency tag on Yahoo's statements endpoint (`_statement_currency()`), which yfinance otherwise discards. Only if that also fails does the API return the trading currency with `currency_unverified: true`, and the page shows a "Reporting currency unconfirmed" warning (suppressed for S&P 500 tickers, which report in USD).
- **Analyst growth** — unavailable; falls back to historical growth (S&P 500 tickers still get FinViz via the screener snapshot).

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
