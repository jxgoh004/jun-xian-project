# Codebase Concerns

**Analysis Date:** 2026-04-11

## Tech Debt

**Overly Broad Exception Handling:**
- Issue: Multiple bare `except:` and `except Exception:` blocks that catch all exceptions without specific handling, masking real errors and making debugging difficult
- Files: `yahoo_finance_fetcher.py` (lines 317, 394, 414), `api_server.py` (lines 134, 211), `finviz_fetcher.py` (line 36), `scripts/fetch_sp500.py` (lines 271, 415)
- Impact: Failures silently propagate as `None` or default values, making it impossible to distinguish between missing data and genuine errors. Users receive incorrect valuations without warning.
- Fix approach: Catch specific exceptions (ValueError, AttributeError, KeyError). Log meaningful messages. Return sentinel values or error states that signal to the frontend that data is unreliable.

**Web Scraping Fragility (FinViz):**
- Issue: `finviz_fetcher.py` uses BeautifulSoup to parse HTML tables with fragile selector logic (lines 47-74). FinViz can change HTML structure without notice. The scraper targets the class `snapshot-table2`, which is an internal FinViz implementation detail.
- Files: `finviz_fetcher.py` (lines 40-75, 153-201)
- Impact: FinViz growth and valuation data may silently fail to parse, falling back to Yahoo Finance or defaults without alerting user. No test coverage for parsing. Any FinViz layout update breaks the integration silently.
- Fix approach: Add unit tests with cached HTML fixtures. Implement health checks that verify parsing works before returning data. Consider using an API if available instead of scraping.

**Bare `pass` Statements in Exception Handlers:**
- Issue: Empty exception handlers that silently ignore errors
- Files: `yahoo_finance_fetcher.py` (lines 317, 394, 414)
- Impact: Errors in optional operations (FCF calculation, growth rate estimation) are swallowed, leading to degraded data quality without visibility.
- Fix approach: Replace with logging and explicit error returns.

**Console Print Debugging:**
- Issue: Print statements used for logging instead of structured logging (`logging` module)
- Files: `yahoo_finance_fetcher.py` (lines 23, 38, 384), `finviz_fetcher.py` (lines 24, 33, 37), `api_server.py` (lines 295-299), `scripts/fetch_sp500.py` (lines 349, 400, 403, 412)
- Impact: No way to control log verbosity in production. Print output goes to server stdout — not accessible to frontend. Hard to trace request lifecycle. Gunicorn swallows stdout unless log level configured.
- Fix approach: Use Python `logging` module with appropriate levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Configure log level via environment variable.

**Gunicorn Deployed Without Worker Configuration:**
- Issue: `Procfile` runs gunicorn with no worker count, timeout, or keepalive settings: `web: gunicorn api_server:app`
- Files: `Procfile` (line 1)
- Impact: Gunicorn defaults to 1 worker with 30-second timeout. A single slow Yahoo Finance or FinViz request blocks all other users. Render.com free tier will kill the dyno after 30 seconds idle.
- Fix approach: Set `--workers 2 --timeout 120 --preload`. Or use `gunicorn.conf.py`.

**Duplicated DCF Logic Across Python and JavaScript:**
- Issue: The DCF calculation is implemented twice — in `scripts/fetch_sp500.py` (`calculate_intrinsic_value`) and in `docs/projects/calculator/index.html` (`computeIV`). The discount table is also duplicated between `api_server.py` and `scripts/fetch_sp500.py`.
- Files: `scripts/fetch_sp500.py` (lines 57-96, 34-43), `api_server.py` (lines 55-64), `docs/projects/calculator/index.html` (lines 1038-1048)
- Impact: Any bug fix or model change must be applied in multiple places. The Python and JS implementations currently match, but future drift is likely.
- Fix approach: Make the screener script call the Flask API for IV calculation, or extract the Python DCF engine into a shared utility module imported by both `api_server.py` and `scripts/fetch_sp500.py`.

**Negative Earnings Detection Differs Between api_server.py and fetch_sp500.py:**
- Issue: `api_server.py` (line 143) checks `ni_m < 0 OR ni_cont_ops_m < 0` for negative earnings, while `scripts/fetch_sp500.py` (line 277) only checks `ni_cont_ops_m < 0`. This means the batch screener may apply DCF to stocks the live calculator correctly marks as N/A.
- Files: `api_server.py` (lines 142-145), `scripts/fetch_sp500.py` (lines 276-279)
- Impact: Screener `data.json` may show intrinsic values for stocks that the live calculator cannot calculate, causing misleading data for users who click through.
- Fix approach: Extract the negative-earnings decision into a shared utility function and use it in both places.

## Known Bugs

**OCF Ratio Calculation Near-Zero Divisor Risk:**
- Symptoms: `ocf_to_ni_ratio` in `api_server.py` divides `ocf_m` by `ni_cont_ops_m` inside a ternary. If `ni_cont_ops_m` is extremely small (e.g., 0.01), ratio becomes enormous, causing OCF-inflated flag to trigger incorrectly.
- Files: `api_server.py` (line 263)
- Trigger: Companies with near-breakeven continuing operations income
- Workaround: User manually changes method in frontend; no warning provided

**TTM Annualisation of Partial Quarters:**
- Symptoms: When less than 4 quarters of data are available, code annualises partial data (e.g., 1 quarter × 4). This produces inflated values for recently listed or recently restructured companies.
- Files: `yahoo_finance_fetcher.py` (lines 79-85, 86-93, 139-141)
- Trigger: Small-cap stocks, SPACs, recent IPOs, companies with acquisitions/spinoffs
- Workaround: None. Frontend does not warn that TTM is estimated.

**Beta Lookup Uses Nearest-Threshold, Not Interpolation:**
- Symptoms: A stock with beta=1.05 gets the 1.00 row rate (5.89%) rather than an interpolated value between 1.00 and 1.10. Discount rate may be off by 0.3-0.5%.
- Files: `api_server.py` (lines 81-95), `scripts/fetch_sp500.py` (lines 46-50)
- Trigger: All stocks (actual beta rarely matches table thresholds exactly)
- Workaround: User can manually override discount rate in frontend

**Screener Shows N/A for ~11% of Stocks:**
- Symptoms: Current `data.json` (2026-04-10) has 57 stocks with `valuation_label: "N/A"` and 7 with `intrinsic_value: null` out of 503 stocks. These are silently presented in the screener without explanation.
- Files: `docs/projects/screener/data.json`, `scripts/fetch_sp500.py` (lines 210-219)
- Trigger: Negative earnings + negative FCF (dcf_not_applicable=true), missing data from Yahoo Finance fetch failures
- Workaround: User must understand DCF limitations; no tooltip or explanation shown for N/A rows

**Screener iframe Loads with No Ticker Param on Direct Navigation:**
- Symptoms: When `#calculator` is the initial hash on page load (e.g., direct link or bookmark), the calculator iframe is created without a `?ticker=` parameter. But when navigating from screener via `postMessage`, `pendingTicker` is correctly passed.
- Files: `docs/index.html` (lines 267-283) — first-paint path does not check `pendingTicker`
- Trigger: None in normal use (screener→calculator flow works). Bug affects only hypothetical direct links to calculator pre-populated with a ticker.
- Workaround: Not applicable to current user flow

## Security Considerations

**`postMessage` Uses Wildcard Target Origin (`'*'`):**
- Risk: `docs/projects/screener/index.html` sends `window.parent.postMessage({type:'navigate', ...}, '*')`. The wildcard allows any parent page — not just the portfolio page — to receive the message. If the screener is embedded in a malicious site, ticker data leaks.
- Files: `docs/projects/screener/index.html` (lines 470-473)
- Current mitigation: Message is limited to ticker name (low sensitivity). Parent validates `type` and `project`.
- Recommendations: Replace `'*'` with explicit origin (e.g., `'https://gohjunxian.github.io'` or `window.location.origin` of the parent during development).

**`window.addEventListener('message', ...)` Does Not Validate Origin:**
- Risk: `docs/index.html` listens for `postMessage` events but does not check `e.origin`. A cross-origin page could post a `{type:'navigate', project:'calculator', ticker:'...'}` message and cause navigation or inject a ticker string into the iframe URL.
- Files: `docs/index.html` (lines 329-336)
- Current mitigation: Ticker is URL-encoded before injecting into iframe `src` (line 296), preventing path traversal. Navigation is limited to known `projects` keys.
- Recommendations: Add `if (e.origin !== 'expected-origin') return;` guard before processing any `postMessage` event.

**API Data Interpolated into innerHTML Without Sanitization:**
- Risk: `docs/projects/calculator/index.html` interpolates API response fields (`d.company_name`, `d.sector`, `d.industry`, `d.exchange`, `d.growth_source`) directly into HTML template strings via `grid.innerHTML = ...` (lines 983-988) and `resultsPanel.innerHTML = ...` (line 1192). If the Yahoo Finance or FinViz response contains `<script>` tags or HTML characters, they are injected unsanitized.
- Files: `docs/projects/calculator/index.html` (lines 967-988, 1192-1245)
- Current mitigation: Yahoo Finance company names are unlikely to contain HTML. FinViz is scraped text. Low practical risk today.
- Recommendations: Use `document.createTextNode` or `textContent` for user-visible strings. Or sanitize with a function that escapes `<`, `>`, `&`, `"` before interpolation.

**Flask CORS Fully Open:**
- Risk: `CORS(app)` with no origin restriction (line 17 in `api_server.py`) allows any website to call the API. This enables third parties to proxy API requests through the user's browser.
- Files: `api_server.py` (line 17)
- Current mitigation: API only reads data from public sources and returns read-only financial calculations. No user data is stored.
- Recommendations: Restrict CORS origin to the portfolio GitHub Pages domain: `CORS(app, origins=["https://gohjunxian.github.io"])`.

**User-Agent Spoofing in FinViz Scraper:**
- Risk: `finviz_fetcher.py` presents a Chrome user-agent (line 15). FinViz ToS prohibits automated scraping; detection could block the IP or result in legal risk.
- Files: `finviz_fetcher.py` (lines 14-17)
- Current mitigation: Single request per stock fetch, no retry loop. Scraper is "optional" — failures are caught and ignored.
- Recommendations: Implement exponential backoff on HTTP 429/403. Add circuit breaker to fail gracefully. Evaluate FinViz Elite API or alternative data source.

**No Rate Limiting or Caching on the Flask API:**
- Risk: Each `/api/fetch-stock/<symbol>` call triggers live HTTP requests to Yahoo Finance and FinViz. No per-client or per-symbol rate limiting. A user could spam requests to exhaust external API quotas.
- Files: `api_server.py` (no caching mechanism present)
- Current mitigation: FinViz has a 15-second timeout (line 26 in `finviz_fetcher.py`). Yahoo Finance has implicit rate limiting via `curl_cffi`.
- Recommendations: Add in-memory TTL cache (e.g., `cachetools.TTLCache`) keyed by symbol with 5-minute expiry. Add per-IP request throttling.

**No Input Validation on Ticker Symbol:**
- Risk: Symbol is only `.strip().upper()` (line 100 in `api_server.py`). No regex validation. Could pass special characters to external APIs unnecessarily.
- Files: `api_server.py` (line 100)
- Current mitigation: Yahoo Finance gracefully returns empty data for invalid symbols. FinViz returns HTTP 404.
- Recommendations: Validate format with regex `^[A-Z0-9.\-]{1,10}$` before calling external APIs.

## Performance Bottlenecks

**Sequential Fetching (Yahoo Finance → FinViz):**
- Problem: API waits for Yahoo Finance to complete before calling FinViz. If either service is slow, user waits 10-30+ seconds.
- Files: `api_server.py` (lines 103-212)
- Cause: Fetchers are called sequentially in a single thread
- Improvement path: Use `concurrent.futures.ThreadPoolExecutor` or `asyncio` to fetch from both sources simultaneously. Return partial data (Yahoo-only) after 10 seconds if FinViz is slow.

**Full HTML Table Parsing on Every FinViz Request:**
- Problem: FinViz parser loops through all tables on the page twice (lines 49-74 in `finviz_fetcher.py`) even when all required fields are found early. No early exit.
- Files: `finviz_fetcher.py` (lines 40-75)
- Cause: No early termination or indexed lookup
- Improvement path: Track required fields and break table iteration once all found. Cache parsed `self.data` to avoid re-parsing within a single request.

**Inefficient DataFrame Row Search in Growth Rate Estimation:**
- Problem: `estimate_growth_rates()` loads entire annual/quarterly financial DataFrames and searches rows in a Python for-loop looking for row names.
- Files: `yahoo_finance_fetcher.py` (lines 338-381)
- Cause: Linear row-name search; no caching between method calls within a single request
- Improvement path: Use `df.index.intersection(['Operating Cash Flow', ...])` for set-based lookup. Cache fetched DataFrames — currently, `self.cash_flow` is fetched in `fetch_all_data()` but individual methods defensively call `fetch_all_data()` again if `None`.

**Nightly Batch Script Processes All 503 Tickers Sequentially:**
- Problem: `fetch_sp500.py` processes all S&P 500 stocks one-by-one with a 0.5-second sleep between each, taking roughly 5-10 minutes per run minimum. FinViz is called separately for each ticker.
- Files: `scripts/fetch_sp500.py` (lines 411-431)
- Cause: Sequential loop by design to avoid rate-limiting
- Improvement path: Use a thread pool with conservative concurrency (e.g., 3-5 workers). Separate Yahoo and FinViz fetches to allow interleaving. Checkpoint progress to resume failed runs.

## Fragile Areas

**Seven-Level Fallback Chain for Cash Flow Data:**
- Files: `yahoo_finance_fetcher.py` (entire module), `api_server.py` (lines 119-175)
- Why fragile: Quarterly TTM → quarterly annualised → annual OCF → NI proxy → annual NI → info dict. If quarterly data exists but has unexpected column names, code silently skips to wrong level. All fallback paths produce the same API response shape regardless of which level fired.
- Safe modification: Add test fixtures for each known data shape. Document expected behavior for each fallback level. Add a `data_source_level` field to the API response so the frontend can show data provenance.
- Test coverage: No unit tests for individual fallback paths.

**FinViz HTML Parsing Without Schema Validation:**
- Files: `finviz_fetcher.py` (entire module)
- Why fragile: Parsing relies on hard-coded table class names (`snapshot-table2`) and href patterns (`sec_`, `ind_`). No validation that parsed output matches expected structure. If FinViz adds a column or reorders cells, parsing silently returns wrong values or empty dict.
- Safe modification: Add schema validation after parsing. Define minimum required keys and types. Reject partial results. Log missing fields at WARNING level.
- Test coverage: Zero tests. No cached HTML fixtures.

**Division by Zero in OCF-to-NI Ratio:**
- Files: `api_server.py` (line 263)
- Why fragile: Code guards `ni_cont_ops_m > 0` but not against extremely small positive values (e.g., 0.001) that produce ratios of 50,000×, incorrectly triggering OCF-inflated detection.
- Safe modification: Add epsilon threshold: only compute ratio when `ni_cont_ops_m > 1.0` (i.e., at least $1M continuing ops income).
- Test coverage: No test for near-zero or very small NI edge case.

**Render.com Free Tier Spin-Down:**
- Files: `docs/projects/calculator/index.html` (lines 731-763)
- Why fragile: The calculator polls `api/health` every 3 seconds until the server responds. Render.com free tier sleeps instances after 15 minutes of inactivity, causing a 30-60 second cold start. During spin-up, the overlay shows correctly. But if the server takes >30 seconds (Render's gunicorn default timeout), the first request may timeout before the worker is ready.
- Safe modification: Increase gunicorn `--timeout 120` in Procfile. The overlay already handles this gracefully — the fix is server-side.
- Test coverage: Cannot be tested locally.

**`data.json` Served as Static File — No Staleness Detection:**
- Files: `docs/projects/screener/index.html` (lines 539-556), `docs/projects/screener/data.json`
- Why fragile: Screener fetches `data.json` with no Cache-Control headers. GitHub Pages serves static files with long-lived cache. If the nightly workflow fails silently (e.g., Yahoo Finance down), users see stale data without any staleness warning. The `updated_at` timestamp is displayed but there is no programmatic check against current date.
- Safe modification: Compare `updated_at` to today's date on load. If data is more than 3 days old, show a stale-data banner.
- Test coverage: No test for stale data display.

## Scaling Limits

**Monolithic Single-File HTML:**
- Current capacity: Calculator HTML is 1,315 lines / ~61KB unminified with all CSS, JS, and HTML inlined. Served by Flask or GitHub Pages without gzip.
- Limit: Acceptable at current scale. At 100+ concurrent users, each downloading 61KB uncompressed adds latency.
- Scaling path: Minify CSS/JS. Serve with gzip compression. Split into separate CSS/JS files with cache-busting query strings.

**No Database — All Data Transient:**
- Current capacity: API calculates valuations on-demand. No caching of historical calculations, no audit trail.
- Limit: Cannot scale to multi-user platform. Each user must refetch all data every time. Cannot validate model accuracy over time.
- Scaling path: Add SQLite (or Postgres on Render) for caching fetched data. Implement per-symbol TTL cache in memory as near-term fix.

**Gunicorn Defaults to 1 Worker:**
- Current capacity: `Procfile` runs gunicorn without `--workers` flag. Single worker handles one request at a time. A 30-second fetch blocks all users.
- Limit: 2-3 concurrent users before noticeable queuing
- Scaling path: `web: gunicorn api_server:app --workers 2 --timeout 120` (1 worker per CPU, Render free tier has 0.1 vCPU)

## Dependencies at Risk

**yfinance Reverse-Engineered Client:**
- Risk: yfinance has no official API contract. Yahoo can break the client by changing their response format, authentication, or rate-limiting strategy. The library has historically broken multiple times per year.
- Impact: Core calculation data could break suddenly if Yahoo changes backend
- Migration plan: Add fallback to IEX Cloud, Alpha Vantage, or Finnhub (paid APIs). Cache responses aggressively. Monitor GitHub issues for yfinance.

**BeautifulSoup4 HTML Scraping of FinViz:**
- Risk: FinViz HTML structure changes break the scraper silently. The scraper was written for a specific FinViz layout version.
- Impact: FinViz growth estimates fail; fall back to Yahoo estimates without warning. Screener data quality degrades silently.
- Migration plan: Contact FinViz for API access. Use an alternative with stable API. Remove scraper dependency if FinViz data is non-critical (it is currently "optional").

**No Python Version Pin:**
- Risk: `requirements.txt` pins package versions but `Procfile` does not specify Python version. Render may upgrade Python runtime automatically.
- Impact: Package compatibility issues could break deployment silently
- Migration plan: Add `runtime.txt` with `python-3.11.x` to pin Render's Python version.

**CAPM Reference Table Uses June 2023 Data:**
- Risk: The beta-to-discount-rate table hardcoded in `api_server.py`, `scripts/fetch_sp500.py`, and displayed in the calculator UI references market risk premia from June 2023 (RF 2.19%, MRP 3.70% for US). These change annually.
- Files: `api_server.py` (lines 55-76), `scripts/fetch_sp500.py` (lines 34-43), `docs/projects/calculator/index.html` (lines 654-691)
- Impact: Discount rates may be systematically too low if risk-free rate has risen since 2023 (it was ~4-5% in 2024-2025)
- Migration plan: Fetch current 10-year Treasury rate dynamically, or document a manual update process for the table.

## Missing Critical Features

**No Structured Error Codes from API:**
- Problem: If Yahoo Finance is unavailable, user sees generic `"Could not fetch data for 'XYZ'"`. No distinction between invalid ticker, service down, or rate-limited.
- Blocks: Cannot implement intelligent retry logic in frontend. User doesn't know whether to retry or try a different symbol.
- Fix: Return structured error object `{error_code: "service_unavailable" | "invalid_symbol" | "rate_limited", message: "..."}` from API.

**No Confidence Intervals or Sensitivity Analysis:**
- Problem: Valuation output is a single point estimate (e.g., $45.20). No indication of range or sensitivity to inputs.
- Blocks: User cannot assess reliability of estimate or stress-test growth assumptions.
- Fix: Calculate ±2% growth scenario bounds. Show sensitivity table for discount rate ±1%. Already has the DCF engine — this is a frontend-only addition.

**No Staleness Warning on Screener Data:**
- Problem: If the nightly GitHub Actions workflow fails silently, screener shows data from previous days without any visual warning. `updated_at` timestamp is shown but not checked programmatically.
- Files: `docs/projects/screener/index.html` (lines 496-514)
- Fix: In `displayUpdatedAt()`, compute days since `updated_at` and show banner if >2 business days old.

## Test Coverage Gaps

**No Unit Tests for Data Fetchers:**
- What's not tested: Yahoo Finance parsing, FinViz parsing, growth rate calculation, discount rate lookup, TTM annualisation logic, fallback chain behavior
- Files: `yahoo_finance_fetcher.py`, `finviz_fetcher.py`, `api_server.py`
- Risk: Changes to code break silently. Fallback logic untested. New developer doesn't know expected behavior.
- Priority: **High** — valuation correctness depends on these modules

**No Integration Tests for Calculation Pipeline:**
- What's not tested: Full flow from symbol input → data fetch → valuation output. No test fixtures with known-good data for specific tickers.
- Files: `api_server.py` (`/api/fetch-stock/` endpoint)
- Risk: End-to-end failures discovered only in production. Cannot verify bug fixes without manual testing.
- Priority: **High** — critical user-facing feature

**No Tests for Negative Earnings Detection Divergence:**
- What's not tested: Whether `api_server.py` and `scripts/fetch_sp500.py` produce consistent results for the same ticker with negative earnings
- Files: `api_server.py` (lines 142-145), `scripts/fetch_sp500.py` (lines 276-279)
- Risk: Screener shows intrinsic values the calculator refuses to compute, misleading users
- Priority: **High** — data consistency concern

**No Edge Case Coverage:**
- What's not tested: Invalid tickers, missing data fields, negative earnings, extreme beta values, division by zero, empty FinViz response, less-than-4-quarter TTM data
- Files: All Python files
- Risk: Users encounter unhandled edge cases with cryptic errors or silent failures
- Priority: **Medium** — improves robustness

**No Performance or Load Tests:**
- What's not tested: API response time under concurrent load, timeout behavior on slow network, Render cold-start simulation
- Files: `api_server.py`
- Risk: Deployment to Render free tier behaves differently than localhost; silent timeout failures
- Priority: **Low** — affects user experience, not correctness

---

*Concerns audit: 2026-04-11*
