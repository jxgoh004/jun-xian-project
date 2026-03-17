# Coding Conventions

**Analysis Date:** 2026-03-17

## Naming Patterns

**Files:**
- Snake case with descriptive names: `api_server.py`, `yahoo_finance_fetcher.py`, `finviz_fetcher.py`
- Test files follow naming convention: `test_*.py` (e.g., `test_yahoo_finance.py`)

**Functions:**
- Snake case for all functions: `safe_float()`, `to_millions()`, `fetch_all_data()`, `get_operating_cash_flow()`
- Getter methods use `get_*` prefix: `get_current_price()`, `get_shares_outstanding()`, `get_total_debt()`
- Private methods use `_*` prefix: `_parse_financial_data()`, `_parse_financial_value()`

**Variables:**
- Snake case for all variables: `shares_raw`, `current_price`, `growth_1_5_pct`
- Constants use UPPER_SNAKE_CASE: `_DISCOUNT_TABLE_US`, `_DISCOUNT_TABLE_HK`, `_HK_EXCHANGES`
- Suffixes indicate units: `*_raw` for raw API values, `*_m` for millions, `*_pct` for percentages
- Dictionary keys use lowercase with spaces: `"longName"`, `"currentPrice"`, `"Operating Cash Flow"`

**Types/Classes:**
- PascalCase for class names: `YahooFinanceFetcher`, `FinVizFetcher`
- Type hints used in function signatures: `def __init__(self, symbol: str):`, `def _parse_financial_value(self, value_str: str) -> Optional[float]:`

## Code Style

**Formatting:**
- No automatic formatter configured; use standard PEP 8 spacing
- Line length: practical default around 100-120 characters (no enforced limit detected)
- Spacing around operators: consistent spaces around `=`, `<`, `>`, `*`, `/`

**Linting:**
- No linter configured (no `.eslintrc`, `.pylintrc`, or similar found)
- No pre-commit hooks configured
- Code follows loose PEP 8 conventions but not strictly enforced

**Indentation:**
- 4 spaces for all indentation levels (Python standard)

## Import Organization

**Order:**
1. Standard library imports: `import math`, `import os`, `import requests`
2. Third-party framework imports: `from flask import Flask, jsonify, request, send_from_directory`
3. Third-party data/API imports: `import yfinance as yf`, `import pandas as pd`, `from bs4 import BeautifulSoup`
4. Local imports: `from yahoo_finance_fetcher import YahooFinanceFetcher`

**Path Aliases:**
- No path aliases configured
- Imports are relative to project root or use absolute module names

**Examples from codebase:**
- `api_server.py`: Standard imports first, then Flask, then local imports
- `yahoo_finance_fetcher.py`: Standard library (yfinance, pandas, datetime), then local imports
- `finviz_fetcher.py`: Requests and BeautifulSoup, then typing for type hints

## Error Handling

**Patterns:**
- Try/except with broad exception catching for external API calls:
  ```python
  try:
      fv = FinVizFetcher(symbol)
      if fv.fetch_data():
          # process data
  except Exception:
      pass  # Silent failure for optional data sources
  ```

- Explicit exception handling for data validation:
  ```python
  try:
      f = float(val)
      return None if (math.isnan(f) or math.isinf(f)) else f
  except (TypeError, ValueError):
      return None
  ```

- Return sentinel values for missing data:
  - `'N/A'` string for unprocessed values
  - `None` for invalid or missing numeric data
  - Empty dictionaries `{}` for missing sections

- HTTP error responses use Flask's `jsonify()` with status codes:
  ```python
  return jsonify({"error": f"Could not fetch data for '{symbol}'..."}), 404
  ```

**Fallback Strategy:**
- Prioritize primary data source, fall back to secondary:
  - Try Yahoo Finance quarterly data first, fall back to annual data
  - Try FinViz data if available, fall back to Yahoo Finance
  - Offer default values (e.g., 5% default growth rate)

## Logging

**Framework:** No logging framework configured; uses `print()` for debugging

**Patterns:**
- Print statements for status messages during data fetching:
  ```python
  print(f"Fetching data for {self.symbol}...")
  print(f"Error fetching data: {e}")
  ```

- Print summaries in `print_summary()` methods:
  ```python
  print(f"=== {self.symbol} - Financial Data Summary ===")
  ```

- Flask startup messages to stdout:
  ```python
  print("=" * 60)
  print("  Intrinsic Value API Server")
  ```

## Comments

**When to Comment:**
- Explain non-obvious logic or business rules
- Mark major sections with visual separators: `# ── Section Name ─────────────`
- Document fallback strategies and data source priorities
- Add inline comments for complex calculations or field mappings

**Style:**
- Single-line comments use `#` with space
- Block comments use visual dividers with dashes for major sections
- Comments placed above code they describe

**Examples from codebase:**
```python
# Discount rate lookup tables keyed by beta threshold value.
# The boundary values (0.80 and 1.60) act as sentinels for < and > rows.
_DISCOUNT_TABLE_US = [...]

# ── 1. Yahoo Finance ──────────────────────────────────────────────────────
yf = YahooFinanceFetcher(symbol)

# Priority: FinViz 5Y EPS estimate → Yahoo CF historical → Yahoo EPS historical → 5% default
```

**Docstrings:**
- Functions include docstrings with single-line descriptions:
  ```python
  def safe_float(val):
      """Return val as float, or None if invalid/NaN."""
  ```

- Class docstrings describe purpose:
  ```python
  class YahooFinanceFetcher:
      """Fetches financial data from Yahoo Finance for intrinsic value calculations"""
  ```

## Function Design

**Size:**
- Typical function length: 15-40 lines
- Helper functions kept concise: `safe_float()` (7 lines), `to_millions()` (4 lines)
- Main API endpoint `fetch_stock()` is longest at ~180 lines, designed as logical sequence

**Parameters:**
- Generally 1-2 parameters per function
- Use optional parameters with defaults for configuration:
  ```python
  def cap_growth(val, lo=0.01, hi=0.25):
  ```

**Return Values:**
- Functions return data structures:
  - Dictionaries for API responses: `{"symbol": "...", "current_price": ...}`
  - Lists of tuples for lookup tables
  - Booleans for success/failure: `return True` / `return False`
  - None for invalid/missing values in data processing

## Module Design

**Exports:**
- Classes are primary exports: `YahooFinanceFetcher`, `FinVizFetcher`
- Flask app instance `app` is exported for WSGI servers
- Helper functions are module-level utilities, not encapsulated in classes

**Barrel Files:**
- Not used; each module has single responsibility

**Organization:**
- `api_server.py`: Flask app setup, helper functions, API routes
- `yahoo_finance_fetcher.py`: YahooFinanceFetcher class with all data fetching methods
- `finviz_fetcher.py`: FinVizFetcher class with web scraping and parsing

**Instance Methods vs Standalone:**
- Data fetching wrapped in classes (`YahooFinanceFetcher`, `FinVizFetcher`)
- Utility functions at module level (`safe_float()`, `to_millions()`, `beta_to_discount_rate()`)
- Each class instance represents a single stock symbol

## Type Annotations

**Usage:**
- Type hints present in FinVizFetcher: `def __init__(self, symbol: str):`
- Return type hints used: `-> Optional[float]`, `-> Dict[str, Any]`, `-> bool`
- Not used in YahooFinanceFetcher or api_server (inconsistent adoption)

**Pattern:**
- When used, follows Python 3.5+ style with `from typing import` imports
- Optional types use `Optional[Type]` for values that can be None

## Data Validation

**Pattern:**
- Validate numeric data with `safe_float()` utility
- Check for NaN/Infinity values explicitly
- Return `None` for invalid data, allowing optional chaining
- Coerce financial metric strings with `_parse_financial_value()` (handles K, M, B suffixes)

**Examples:**
```python
def safe_float(val):
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None
```

---

*Convention analysis: 2026-03-17*
