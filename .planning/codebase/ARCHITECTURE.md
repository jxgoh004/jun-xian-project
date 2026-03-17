# Architecture

**Analysis Date:** 2026-03-17

## Pattern Overview

**Overall:** Layered monolith with client-server separation

**Key Characteristics:**
- Frontend is a single-page HTML/JavaScript application
- Backend is a Flask REST API serving the frontend and providing data ingestion
- Symmetric data flow: client fetches stock data, receives calculation-ready values, performs DCF computation locally
- Multi-source data aggregation from Yahoo Finance and FinViz with intelligent fallback/override logic
- Business logic split between backend (data fetching, method recommendation) and frontend (calculation, presentation)

## Layers

**Presentation Layer (Frontend):**
- Purpose: Single-page web application for data input, verification, and result display
- Location: `index.html`
- Contains: HTML structure, CSS styling, vanilla JavaScript for UI control and DCF calculations
- Depends on: Flask API at `/api/fetch-stock/<symbol>` and `/api/health`
- Used by: End user in web browser (localhost:5000 or Render deployment)

**API Layer (Backend):**
- Purpose: HTTP endpoints for data fetching, health checks, and static file serving
- Location: `api_server.py`
- Contains: Flask app with route handlers, CORS configuration, utility functions
- Depends on: YahooFinanceFetcher, FinVizFetcher modules
- Used by: Frontend JavaScript via fetch() calls

**Data Fetching Layer:**
- Purpose: Aggregate financial data from external sources and pre-process for the calculator
- Location: `yahoo_finance_fetcher.py`, `finviz_fetcher.py`
- Contains: Classes that fetch ticker data, parse responses, extract key metrics
- Depends on: yfinance library, requests/BeautifulSoup for web scraping
- Used by: API layer route handlers

## Data Flow

**Fetch Stock Data Flow:**

1. Frontend user enters ticker symbol and clicks "Fetch Data"
2. Frontend calls `GET /api/fetch-stock/AAPL`
3. API server instantiates YahooFinanceFetcher and FinVizFetcher
4. YahooFinanceFetcher calls yfinance library, extracts info, financials, cash flow, balance sheet
5. FinVizFetcher scrapes FinViz website with BeautifulSoup, extracts growth estimates and beta
6. API server applies business rules:
   - Detects negative earnings (NI < 0)
   - Detects OCF inflation (OCF > 1.5× NI Cont. Ops)
   - Recommends valuation method: FCF if negative earnings/OCF inflated, else OCF
   - Looks up discount rate from CAPM table based on beta and exchange
   - Prioritizes growth rate: FinViz 5Y EPS → Yahoo CF historical → Yahoo EPS historical → 5% default
7. API returns comprehensive JSON with all extracted values plus method recommendation
8. Frontend populates input form with returned data, shows verification panel
9. User can edit values before calculation

**Calculate Intrinsic Value Flow:**

1. Frontend user reviews verified data and clicks "Calculate"
2. Frontend reads all input fields (cash flow, debt, cash, shares, growth rates, discount rate)
3. Frontend calls computeIV() function:
   - Projects 20-year cash flows using growth rates by phase (1-5, 6-10, 11-20)
   - Calculates discount factors for each year
   - Discounts projected cash flows to present value
   - Sums PV across 20 years
4. Frontend adjusts per-share value:
   - Divides total PV by shares outstanding
   - Subtracts debt per share
   - Adds cash per share
   - Multiplies by exchange rate if non-USD currency
5. Frontend compares intrinsic value to last close price, calculates discount/premium percentage
6. Frontend displays comprehensive results: hero metrics, phase breakdown, year-by-year table, method comparison

**State Management:**

- `lastData`: Stores most recent API response to enable live method-switching and growth cap toggling
- `growthCapMode`: Tracks whether to use actual growth rate or cap at 25% (user toggleable)
- Form fields marked with `.auto-filled` class to distinguish user-entered from API-fetched values
- All calculation state is ephemeral; browser session holds UI state

## Key Abstractions

**YahooFinanceFetcher:**
- Purpose: Encapsulate yfinance API interactions and financial data extraction
- Examples: `yahoo_finance_fetcher.py` (class YahooFinanceFetcher)
- Pattern: Initialization with symbol, fetch_all_data() triggers data retrieval, getter methods extract specific metrics (OCF TTM, NI, shares, debt, etc.)

**FinVizFetcher:**
- Purpose: Encapsulate web scraping of FinViz website for growth estimates and beta
- Examples: `finviz_fetcher.py` (class FinVizFetcher)
- Pattern: Initialization with symbol, fetch_data() triggers HTTP request and HTML parsing, getter methods extract parsed values

**DCF Engine:**
- Purpose: Compute intrinsic value from projected cash flows, growth rates, and discount rate
- Examples: Frontend function `computeIV()` in `index.html` lines 1045-1056
- Pattern: Pure function, no state, returns object with totalPV and ivPS

**Verification Panel:**
- Purpose: Display fetched data with source attribution before calculation
- Examples: Frontend function `showVerifyPanel()` in `index.html` lines 914-1012
- Pattern: Grid display of metrics with source badges (YF=Yahoo, FV=FinViz, DEF=Default), warning banners for edge cases

## Entry Points

**Web Server Entry:**
- Location: `api_server.py` lines 282-288
- Triggers: `python api_server.py` (local) or `gunicorn api_server:app` (Render production)
- Responsibilities: Start Flask app on port 5000, enable CORS, serve static index.html

**Browser Entry:**
- Location: `index.html`
- Triggers: Opening http://localhost:5000 in browser or accessing Render-deployed URL
- Responsibilities: Load HTML/CSS, execute JavaScript, poll /api/health until server ready, show startup overlay, enable user interactions

**API Endpoints:**
- `GET /` - Serves index.html static file
- `GET /api/fetch-stock/<symbol>` - Returns stock data with method recommendations and growth estimates
- `GET /api/health` - Returns JSON status for server health checks

## Error Handling

**Strategy:** Graceful degradation with user feedback and fallback values

**Patterns:**

- **Network errors:** Frontend catches fetch() exceptions, displays error message, user can retry
- **Invalid ticker:** API returns 404 with error message, frontend shows error alert
- **Missing data:** All numerical fields use `safe_float()` to coerce None for invalid values; frontend checks for required fields before calculating
- **API unavailable:** Startup overlay detects server offline after 5 attempts, displays instructions to start server, continues polling for auto-reconnect
- **Fallback values:**
  - Default discount rate 6.00% if beta missing
  - Default growth rate 5.00% if no sources provide estimate
  - Annual OCF if quarterly data unavailable
  - Net Income if OCF unavailable as cash flow base

## Cross-Cutting Concerns

**Logging:**
- Backend: Print statements to console (e.g., "Fetching data for {symbol}...", error messages)
- Frontend: Browser console logs (limited; mostly implicit via fetch() failures)

**Validation:**
- Backend: safe_float() coerces values, validates against NaN/Inf; to_millions() converts units; cap_growth() constrains range
- Frontend: Required field checks before calculation; marked input fields with .auto-filled class to indicate source

**Authentication:**
- None. API is public-facing (CORS enabled), Yahoo Finance and FinViz are also public APIs with no auth required
- Designed for single-user deployment (localhost) or public web instance

**Currency Handling:**
- Backend: Stores values in USD/currency as-is from sources, returns currency code
- Frontend: Tracks currency symbol separately, applies exchange rate multiplier on final IV calculation
- Display: Currency picker for financial statement currency with exchange rate to listing currency

---

*Architecture analysis: 2026-03-17*
