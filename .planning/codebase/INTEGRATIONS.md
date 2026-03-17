# External Integrations

**Analysis Date:** 2026-03-17

## APIs & External Services

**Financial Data Sources:**
- Yahoo Finance - Primary source for all stock financial data
  - SDK/Client: yfinance 0.2.65
  - Usage: `api_server.py` line 103-178, `yahoo_finance_fetcher.py`
  - Data provided: stock info, current price, shares outstanding, financial statements (annual), cash flow (annual + quarterly), balance sheet (annual + quarterly), EPS, beta, market cap, debt, cash equivalents
  - Fallback data chain: Quarterly > Annual > Info API fields
  - Special case: 10-year Treasury yield fetched as `^TNX` symbol for discount rate calculation
  - Auth: None required (public API)

- FinViz - Secondary/optional data source for growth estimates and beta refinement
  - SDK/Client: requests + beautifulsoup4 (custom scraper)
  - Usage: `api_server.py` line 185-200, `finviz_fetcher.py` (custom implementation)
  - Website: https://finviz.com/quote.ashx?t=
  - Data provided: EPS growth (next 5 years), beta values, valuation metrics, market cap, growth estimates
  - User-Agent: Mozilla/5.0 Chrome 91.0 (spoofed to avoid blocking)
  - Timeout: 15 seconds per request
  - Auth: None required (public website, HTML scraping)
  - Note: Optional integration - if FinViz fails to fetch, app continues with Yahoo Finance data only

## Data Storage

**Databases:**
- None - Stateless application

**File Storage:**
- Local filesystem only - Static HTML/CSS/JavaScript served from project root
- Location: `index.html` at project root
- No persistent data storage

**Caching:**
- None - Data fetched fresh on each API request
- No in-memory caching between requests

## Authentication & Identity

**Auth Provider:**
- None required

**Implementation:**
- No authentication mechanism; endpoints are public
- CORS enabled for all origins via flask-cors
- Stateless API design (no sessions or tokens)

## Monitoring & Observability

**Error Tracking:**
- None configured

**Logs:**
- Console output only (print statements in Python code)
- Locations: `api_server.py` line 104, 136; `yahoo_finance_fetcher.py` line 21, 36; `finviz_fetcher.py` line 24, 37
- No persistent logging to files
- HTTP status codes returned in API responses

## CI/CD & Deployment

**Hosting:**
- Render platform (referenced in recent commits)
- Deployment method: Git push (Render auto-deploys from git)

**CI Pipeline:**
- None detected - direct deployment via Render

**Deployment Configuration:**
- Procfile: `web: gunicorn api_server:app`
- Commits show progression: "Prepare for Render deployment" → "Point frontend to deployed API" → "Fix API URL to correct Render deployment"
- Frontend API endpoint switches between localhost (dev) and deployed URL (prod) via JavaScript `window.location.hostname` detection

## Environment Configuration

**Required env vars:**
- None currently - all connections use defaults or are public APIs

**Secrets location:**
- No secrets required
- CORS policy: Open (no API key needed for external calls)

## Webhooks & Callbacks

**Incoming:**
- `/api/health` - Health check endpoint for server status verification
  - Location: `api_server.py` line 277-279
  - Response: `{"status": "ok", "message": "Intrinsic Value API is running."}`

**Outgoing:**
- None

## API Endpoints

**Public REST API:**

`GET /` - Serves static index.html
- Response: HTML file

`GET /api/health` - Health check
- Response: `{"status": "ok", "message": "..."}`

`GET /api/fetch-stock/<symbol>` - Fetch stock data for intrinsic value calculation
- Parameters: symbol (stock ticker, e.g., AAPL)
- Response: JSON object containing:
  - Company data: symbol, company_name, sector, industry, currency, exchange
  - Price data: current_price, shares_millions
  - Financial metrics: ocf_millions, ni_cont_ops_millions, ni_millions, fcf_millions, debt_millions, cash_millions
  - Growth rates: growth_1_5_pct, growth_6_10_pct, growth_11_20_pct, growth_source
  - Discount rate: beta, discount_rate_pct
  - Method recommendation: recommended_method, auto_switch_to_fcf, switch_reason, negative_earnings, dcf_not_applicable
  - Data sources: yahoo_finance (bool), finviz (bool)
- Error response: `{"error": "message"}` with 404 status code

## Data Flow Architecture

**Stock Data Fetch Flow:**

1. Frontend (`index.html`) submits ticker via `GET /api/fetch-stock/{TICKER}`
2. Flask endpoint (`api_server.py` line 98-274):
   - Instantiate `YahooFinanceFetcher(symbol)` → fetches all Yahoo Finance data
   - Extract: company info, current price, shares, cash flows, balance sheet data
   - Detect negative earnings or inflated OCF ratios
   - Recommend valuation method (OCF vs FCF based on earnings quality)
   - Attempt `FinVizFetcher(symbol)` for enhanced growth estimates and beta
   - Priority growth rate: FinViz 5Y EPS > Yahoo historical CF > Yahoo historical EPS > 5% default
   - Beta priority: FinViz beta > Yahoo Finance beta
   - Look up discount rate from hardcoded CAPM reference tables by beta threshold
   - Return unified JSON response to frontend
3. Frontend JavaScript parses response, populates input fields, user can edit before calculating intrinsic value

**Data Source Priority:**

- Yahoo Finance quarterly > Yahoo Finance annual > Info API (cash flow, debt, cash)
- FinViz growth estimates (5Y EPS) > Yahoo historical growth > 5% default
- FinViz beta > Yahoo beta > None (returns in response for user awareness)
- Exchange detection: HKG/HKSE/SHH/SHZ triggers HK discount table; others use US table

---

*Integration audit: 2026-03-17*
