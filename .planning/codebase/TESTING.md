# Testing Patterns

**Analysis Date:** 2026-03-17

## Test Framework

**Runner:**
- No formal test framework configured (no pytest.ini, setup.cfg, or tox.ini found)
- Tests are standalone Python scripts, not integrated into CI/CD

**Assertion Library:**
- No assertion library; uses print statements for verification
- Tests are manual/exploratory scripts rather than automated test suites

**Run Commands:**
```bash
python _dev/test_yahoo_finance.py              # Test Yahoo Finance data access
python _dev/test_finviz.py                     # Test FinViz scraping
python _dev/test_quarterly_balance_sheet.py    # Compare quarterly vs annual data
```

**Environment:**
- Tests require valid network access to external APIs (Yahoo Finance, FinViz)
- Tests are data-dependent, not deterministic
- No mocking framework used; tests hit live APIs

## Test File Organization

**Location:**
- Development tests in separate `_dev/` directory, not co-located with source
- Production code in root: `api_server.py`, `yahoo_finance_fetcher.py`, `finviz_fetcher.py`
- Test files never committed (listed in `.gitignore`)

**Naming:**
- Convention: `test_*.py` (e.g., `test_yahoo_finance.py`, `test_finviz.py`)
- Descriptive names indicate what they test

**Structure:**
```
_dev/
├── test_yahoo_finance.py           # API access validation
├── test_finviz.py                  # Web scraping validation
└── test_quarterly_balance_sheet.py # Data comparison tests
```

## Test Structure

**Suite Organization:**
The tests follow a simple procedural pattern without test frameworks:

```python
def test_yahoo_finance():
    """Test basic Yahoo Finance API access"""
    symbol = "AAPL"

    try:
        response = requests.get(url, headers={...})
        print(f"Status code: {response.status_code}")

        # Try yfinance library
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        print(f"yfinance library: Available")
        print(f"Sample data - AAPL current price: ${info.get('currentPrice', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yahoo_finance()
```

**Patterns:**
- Entry point: `if __name__ == "__main__":` block
- Test functions wrapped in try/except
- Results printed to stdout
- No assertions; visual inspection of output required

## Manual Testing Approach

**Test Yahoo Finance Access:**
- Location: `_dev/test_yahoo_finance.py`
- Tests two methods:
  1. Direct HTTP request to finance.yahoo.com
  2. Using yfinance library with sample ticker AAPL
- Output shows availability and sample data

**Test FinViz Web Scraping:**
- Location: `_dev/test_finviz.py`
- Tests both library-based and direct web scraping approaches
- Attempts multiple parsing strategies
- Prints found data types and table structures

**Test Quarterly vs Annual Data:**
- Location: `_dev/test_quarterly_balance_sheet.py`
- Compares quarterly and annual balance sheet methods
- Outputs side-by-side comparison with percentage differences
- Tests with multiple symbols: AAPL, MSFT, GOOGL

**Example test output:**
```python
# Actual test code from test_quarterly_balance_sheet.py
quarterly_debt = fetcher.get_total_debt_quarterly()
annual_debt = fetcher.get_total_debt_annual()

print(f"Quarterly Total Debt: ${quarterly_debt/1e6:.1f}M")
print(f"Annual Total Debt: ${annual_debt/1e6:.1f}M")
if isinstance(quarterly_debt, (int, float)) and isinstance(annual_debt, (int, float)):
    debt_diff = quarterly_debt - annual_debt
    debt_pct = (debt_diff / annual_debt) * 100 if annual_debt != 0 else 0
    print(f"Difference: ${debt_diff/1e6:.1f}M ({debt_pct:+.1f}%)")
```

## Testing Data Fetchers

**YahooFinanceFetcher Testing:**
- Primary method: `test_quarterly_balance_sheet.py` instantiates fetcher
  ```python
  fetcher = YahooFinanceFetcher(symbol)
  if not fetcher.fetch_all_data():
      print(f"Failed to fetch data for {symbol}")
      return
  ```
- Tests methods: `get_operating_cash_flow()`, `get_total_debt()`, `get_cash_and_short_term_investments()`
- Fallback logic verified through side-by-side comparison

**FinVizFetcher Testing:**
- `test_finviz.py` exercises both scraping approaches
- Tests parsing of various table formats
- Validates field extraction for financial metrics

## Mocking

**Framework:** No mocking framework used (no unittest.mock, pytest-mock, or responses library)

**Current Approach:**
- Tests hit live external APIs directly
- No fixtures or test data files used
- Relies on stable data from publicly accessible APIs

**What to Mock (if implementing automated tests):**
- HTTP requests to Yahoo Finance and FinViz (use `responses` library)
- File system operations (filesystem mocking)
- Time-dependent data (market hours, current date)

**What NOT to Mock:**
- Core calculation logic (safe_float, to_millions, beta_to_discount_rate)
- DataFrame operations (pandas is deterministic)
- String parsing routines

## Fixtures and Factories

**Test Data:**
- No fixture files found (no conftest.py, fixtures/ directory)
- Hardcoded test symbols: `AAPL`, `MSFT`, `GOOGL`
- Sample test data embedded in test scripts

**Location:**
- Test data exists only in test file logic
- CSV files in `_dev/` (AAPL_DCF_20yr_inputs.csv) are manual test inputs, not automated fixtures
- Excel files (`AAPL_DCF_Calculated.xlsx`) are verification artifacts

**Example from code:**
```python
# From test_quarterly_balance_sheet.py
def main():
    """Test with AAPL and a few other stocks"""
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']

    for symbol in test_symbols:
        try:
            test_balance_sheet_comparison(symbol)
            print("-" * 50)
        except Exception as e:
            print(f"Error testing {symbol}: {e}")
```

## Coverage

**Requirements:** No coverage tracking configured or enforced

**View Coverage:** Not applicable (no pytest-cov or coverage tool setup)

## Test Types

**Unit Tests:**
- Implicit through individual method testing in data fetcher classes
- `safe_float()`, `to_millions()`, `cap_growth()` utility functions can be unit tested
- Currently not formalized; only manual verification via test scripts

**Integration Tests:**
- `test_quarterly_balance_sheet.py` is an integration test
  - Tests full flow: instantiate fetcher → fetch data → extract specific fields → compare outputs
  - Validates that quarterly and annual data extraction work end-to-end

**API Integration Tests:**
- `test_yahoo_finance.py` validates library availability and API access
- `test_finviz.py` tests HTML parsing and data extraction from live website

**Manual/Exploratory Testing:**
- Developers run individual test scripts to verify data source availability
- Results printed and manually inspected
- Helps diagnose issues with external APIs

**E2E Tests:**
- Not implemented
- Would require testing the full application: API → data fetching → calculation → JSON response

## Current Testing Gaps

**What's tested:**
- External data source availability and accessibility
- Data parsing and extraction methods
- Quarterly vs annual data consistency

**What's not tested:**
- Core valuation calculation logic in `api_server.py`
- Flask API endpoints (no requests against /api/fetch-stock/{symbol})
- Error handling paths (invalid symbols, network timeouts)
- Edge cases (negative earnings, OCF inflation, etc.)
- Response format validation
- Discount rate calculation correctness
- Growth rate selection priority logic

## Test Infrastructure Recommendations

**To implement automated testing:**

1. **Use pytest** for test discovery and execution
   ```bash
   pip install pytest pytest-cov
   pytest tests/  # Run all tests
   pytest tests/ --cov=src  # With coverage
   ```

2. **Mock external API calls** with responses library
   ```python
   import responses
   @responses.activate
   def test_fetch_stock():
       responses.add(responses.GET, 'https://...')
   ```

3. **Co-locate tests** with source code or in structured tests/ directory
   ```
   src/
   ├── api_server.py
   └── tests/
       ├── test_api_server.py
       ├── test_yahoo_finance_fetcher.py
       └── test_finviz_fetcher.py
   ```

4. **Add pytest fixtures** in `tests/conftest.py` for common test data

5. **CI/CD integration** with GitHub Actions or similar to run tests on commits

---

*Testing analysis: 2026-03-17*
