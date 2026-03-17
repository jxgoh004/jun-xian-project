# Codebase Concerns

**Analysis Date:** 2026-03-17

## Tech Debt

**Overly Broad Exception Handling:**
- Issue: Multiple `except:` and `except Exception:` blocks that catch all exceptions without specific handling, masking real errors and making debugging difficult
- Files: `yahoo_finance_fetcher.py` (lines 313, 390, 410), `api_server.py` (lines 134, 199), `finviz_fetcher.py` (line 36)
- Impact: Failures silently propagate as `None` or default values, making it impossible to distinguish between missing data and genuine errors. Users receive incorrect valuations without warning.
- Fix approach: Catch specific exceptions (ValueError, AttributeError, KeyError). Log meaningful messages. Return sentinel values or error states that signal to the frontend that data is unreliable.

**Web Scraping Fragility (FinViz):**
- Issue: `finviz_fetcher.py` uses BeautifulSoup to parse HTML tables with fragile selector logic (lines 47-74). FinViz can change HTML structure without notice.
- Files: `finviz_fetcher.py` (lines 40-75, 153-201)
- Impact: FinViz growth and valuation data may silently fail to parse, falling back to Yahoo Finance or defaults without alerting user. No test coverage for parsing.
- Fix approach: Add unit tests with cached HTML fixtures. Implement health checks that verify parsing works before returning data. Consider using an API if available instead of scraping.

**Bare `pass` Statements:**
- Issue: Empty exception handlers that silently ignore errors
- Files: `yahoo_finance_fetcher.py` (lines 313, 390, 410)
- Impact: Errors in optional operations (FCF calculation, growth rate estimation) are swallowed, leading to degraded data quality without visibility.
- Fix approach: Replace with logging and explicit error returns.

**Console Print Debugging:**
- Issue: Print statements scattered throughout for logging instead of structured logging
- Files: `yahoo_finance_fetcher.py` (lines 21, 36, 380), `finviz_fetcher.py` (lines 24, 33, 37), `api_server.py` (lines 283-287)
- Impact: No way to control log verbosity in production. Print output goes to server stdout, not accessible to frontend. Hard to trace request lifecycle.
- Fix approach: Use Python logging module with appropriate levels. Consider sending error details back to frontend in response envelope.

## Known Bugs

**OCF Ratio Calculation Silent Failure:**
- Symptoms: When computing `ocf_to_ni_ratio` (line 251 in `api_server.py`), if `ni_cont_ops_m` is 0 or None, the ratio becomes None silently without notifying user that the ratio is unreliable
- Files: `api_server.py` (line 251)
- Trigger: Any stock with zero or near-zero continuing operations income, or when continuing ops data is unavailable
- Workaround: Frontend user must notice `null` in verify panel; no warning provided

**TTM Calculation Assumptions:**
- Symptoms: When less than 4 quarters of data are available, code annualizes partial data (lines 79-81 in `yahoo_finance_fetcher.py`). This creates inaccurate annualized values for recently-listed or newly-restructured companies.
- Files: `yahoo_finance_fetcher.py` (lines 74-81, 86-89, 134-137)
- Trigger: Small-cap stocks, SPACs, recent IPOs, companies with acquisitions/spinoffs
- Workaround: None; frontend doesn't warn that TTM is estimated, not actual

**Beta Lookup Returns Closest Row, Not Interpolation:**
- Symptoms: When beta falls between reference table values (e.g., beta=1.05 gets 1.00 row, not interpolated 1.00-1.10), discount rate may be off by 0.5-1%
- Files: `api_server.py` (lines 81-95)
- Trigger: Most stocks (actual beta rarely matches table thresholds exactly)
- Workaround: User can manually override discount rate in frontend

## Security Considerations

**User-Agent Spoofing in Web Scraper:**
- Risk: FinViz scraper presents a Chrome user-agent (line 15 in `finviz_fetcher.py`). If FinViz detects automated scraping, requests could be blocked or rate-limited without notice.
- Files: `finviz_fetcher.py` (line 15)
- Current mitigation: None; single hard-coded user-agent with no retry logic
- Recommendations: Implement exponential backoff on HTTP errors. Add circuit breaker to fail gracefully when FinViz is unavailable. Consider offering an alternative data source toggle on frontend.

**No Rate Limiting or Caching:**
- Risk: Each stock fetch triggers live requests to Yahoo Finance (via yfinance) and FinViz. No client-side or server-side caching. User could hammer the API with rapid requests, overloading external services.
- Files: `api_server.py` (lines 103, 191), no caching mechanism
- Current mitigation: FinViz has a 15-second timeout (line 26 in `finviz_fetcher.py`), but no request batching or deduplication
- Recommendations: Implement simple in-memory cache with 5-minute TTL per symbol. Add request deduplication. Consider rate limiting per symbol.

**No Input Validation on Ticker Symbol:**
- Risk: Ticker input is only `.strip().upper()` (line 100 in `api_server.py`). No regex validation. Could pass invalid symbols to external APIs unnecessarily.
- Files: `api_server.py` (line 100)
- Current mitigation: Yahoo Finance gracefully returns 404, but FinViz may behave unpredictably
- Recommendations: Validate ticker format (1-5 uppercase alphanumerics + optional exchange code) before calling external APIs

**JSON Response Contains All Raw Data:**
- Risk: Verify panel exposes calculated values without clear indication of reliability. User might trust a null value to mean "0" rather than "missing data".
- Files: `api_server.py` (lines 226-272)
- Current mitigation: Frontend shows "N/A" for null, but valuation inputs accept null silently
- Recommendations: Add explicit `reliability` or `data_quality` field to response indicating which metrics failed to fetch. Add warnings to frontend when critical inputs are missing.

## Performance Bottlenecks

**Sequential Fetching (Yahoo → FinViz):**
- Problem: API waits for Yahoo Finance to complete, then calls FinViz. If either service is slow, user waits 10-30+ seconds.
- Files: `api_server.py` (lines 103-104, 190-200)
- Cause: Fetchers are called sequentially, not in parallel
- Improvement path: Use asyncio or threading to fetch from both sources simultaneously. Return partial data (Yahoo-only) after 10 seconds even if FinViz is slow.

**Parsing All FinViz Tables Unconditionally:**
- Problem: FinViz parser loops through all tables on page twice (lines 49-74 in `finviz_fetcher.py`), parsing irrelevant data even if key metrics are found early
- Files: `finviz_fetcher.py` (lines 40-75)
- Cause: No early termination or indexed lookup
- Improvement path: Cache parsed data. Return immediately when all required fields are found.

**Inefficient DataFrame Operations:**
- Problem: `estimate_growth_rates()` loads entire annual/quarterly financials, then iterates through rows searching for specific labels (lines 334-381 in `yahoo_finance_fetcher.py`)
- Files: `yahoo_finance_fetcher.py` (lines 334-381)
- Cause: Linear search through labels; no caching between method calls
- Improvement path: Cache ticker financials on first fetch. Use `.loc[]` directly with `.get()` instead of looping.

## Fragile Areas

**Data Fallback Chain Complexity:**
- Files: `yahoo_finance_fetcher.py` (entire module), `api_server.py` (lines 119-175)
- Why fragile: Seven-level fallback chain for cash flow (quarterly TTM → quarterly annualized → annual → net income proxy, etc.). If one source is partially missing (e.g., quarterly data exists but is empty), code may skip to wrong level without warning.
- Safe modification: Add test fixtures for each known data shape (full quarterly, partial quarterly, annual-only, all missing). Document expected behavior for each case.
- Test coverage: No unit tests for individual fallback paths. Growth estimation, debt lookup, cash position lookup are untested.

**FinViz HTML Parsing Without Schema:**
- Files: `finviz_fetcher.py` (entire module)
- Why fragile: Parsing relies on hard-coded table class names and cell order. No validation that parsed output matches expected structure. If FinViz adds a cell or reorders columns, parsing silently fails or returns wrong values.
- Safe modification: Add schema validation after parsing. Define expected keys and types. Reject partial results. Add logging for missing fields.
- Test coverage: Zero tests. No cached HTML fixtures to verify parser behavior.

**Division by Zero Risk:**
- Files: `api_server.py` (line 251: `ocf_m / ni_cont_ops_m`)
- Why fragile: Code checks `ni_cont_ops_m > 0` but doesn't guard against exact zero or very small values that could cause extreme ratios.
- Safe modification: Add epsilon check for near-zero divisors. Return None explicitly instead of computing invalid ratios.
- Test coverage: No test for this edge case.

## Scaling Limits

**Single-File HTML Serving:**
- Current capacity: `index.html` is 61KB (single 61,343-byte file). Served statically from Flask, not gzipped or minified.
- Limit: Fine for individual users, but at scale (100+ concurrent), each browser downloads full uncompressed file
- Scaling path: Minify CSS/JS. Serve with gzip compression. Split into separate JS/CSS files. Add caching headers.

**No Database — All Data Transient:**
- Current capacity: API calculates valuations on-demand. No caching of historical calculations, no audit trail, no user history.
- Limit: Cannot scale to multi-user platform. Each user must refetch all data every time.
- Scaling path: Add SQLite (or Postgres) for caching fetched data + historical calculations. Implement user sessions if multi-user needed.

**Synchronous Request Handling:**
- Current capacity: Flask handles one request at a time (unless run with gunicorn workers). A slow external API call blocks other users.
- Limit: 5-10 concurrent users before noticeable slowdown
- Scaling path: Deploy with gunicorn workers (already configured in `Procfile`). Add async/await to fetchers. Implement queue system for slow operations.

## Dependencies at Risk

**yfinance Instability:**
- Risk: yfinance is a reverse-engineered Yahoo Finance client with no official API contract. Yahoo can change response format without notice. Maintenance is sporadic (last major update ~6 months ago).
- Impact: Core calculation data could break suddenly if Yahoo changes backend
- Migration plan: Add fallback to IEX Cloud, Alpha Vantage, or Finnhub (paid APIs). Cache responses aggressively. Monitor error rates daily.

**BeautifulSoup4 Web Scraping:**
- Risk: FinViz HTML structure changes frequently. Scraper was likely written for a specific FinViz layout. Changes break silently.
- Impact: FinViz growth estimates fail, fall back to Yahoo estimates without warning
- Migration plan: Contact FinViz for API access. Use data provider with stable API (yfinance, Alpha Vantage). Remove scraper dependency entirely if FinViz data is non-critical.

**Python 3.x Compatibility:**
- Risk: No `python_requires` in any setup config. Assumes Python 3.8+. Tested on Windows only.
- Impact: Deployment to Python 3.11+ or different OS may fail silently
- Migration plan: Add `.python-version` or `Procfile` version pin. Test on Python 3.11 and 3.12. Add CI/CD checks.

## Missing Critical Features

**No Error Budget or User Feedback:**
- Problem: If Yahoo Finance is down, user sees generic 404 "Could not fetch data". No way to distinguish network error from invalid ticker.
- Blocks: Cannot implement error retry logic on frontend. User doesn't know if they should retry or try different ticker.
- Fix: Return detailed error codes from API. Distinguish `invalid_symbol`, `service_unavailable`, `rate_limited`, etc.

**No Confidence Intervals or Uncertainty Quantification:**
- Problem: Valuation output is single point estimate (e.g., $45.20). No indication of range or sensitivity to inputs.
- Blocks: User cannot assess reliability of estimate or adjust high-risk inputs
- Fix: Calculate 10th/90th percentile valuations. Show sensitivity to discount rate and growth assumptions.

**No Multi-Year Historical Tracking:**
- Problem: Cannot compare today's calculated intrinsic value vs. previous calculations for same stock.
- Blocks: Cannot validate model accuracy. Cannot identify stocks becoming over/undervalued over time.
- Fix: Store calculation results to database keyed by (symbol, date). Add time-series chart to frontend.

## Test Coverage Gaps

**No Unit Tests for Data Fetchers:**
- What's not tested: Yahoo Finance parsing, FinViz parsing, growth rate calculation, discount rate lookup
- Files: `yahoo_finance_fetcher.py`, `finviz_fetcher.py`, `api_server.py`
- Risk: Changes to code break silently. Fallback logic untested. New developer doesn't know expected behavior.
- Priority: **High** — valuation correctness depends on these modules

**No Integration Tests for Calculation Pipeline:**
- What's not tested: Full flow from symbol input → data fetch → valuation output. No test fixtures with known-good data.
- Files: `api_server.py` (entire `/api/fetch-stock/` endpoint)
- Risk: End-to-end failures discovered only in production. Cannot verify fix without manual testing.
- Priority: **High** — critical user-facing feature

**No Edge Case Coverage:**
- What's not tested: Invalid tickers, missing data fields, negative earnings, extreme beta values, division by zero, empty FinViz response
- Files: All files
- Risk: Users encounter unhandled edge cases with cryptic errors or silent failures
- Priority: **Medium** — improves robustness

**No Performance Tests:**
- What's not tested: API response time under load, timeout behavior, slow network simulation
- Files: `api_server.py`
- Risk: Deployment to slow network (mobile, international) causes silent timeouts
- Priority: **Low** — affects user experience but not correctness

---

*Concerns audit: 2026-03-17*
