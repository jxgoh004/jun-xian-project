# Codebase Structure

**Analysis Date:** 2026-03-17

## Directory Layout

```
Auto Intrinsic Value/
├── .git/                       # Git repository
├── .gitignore                  # Git ignore rules
├── .planning/                  # GSD planning documents (generated)
│   └── codebase/               # Architecture and analysis docs
├── _dev/                       # Development workspace (not deployed)
│   ├── *.py                    # Testing and analysis scripts
│   ├── *.xlsx                  # Excel reference models
│   ├── *.csv                   # Sample data files
│   └── development_notes.md    # Project notes
├── img/                        # Images (likely screenshots or icons)
├── venv/                       # Python virtual environment (not committed)
├── index.html                  # Single-page web application (frontend)
├── api_server.py               # Flask API server (backend entry point)
├── yahoo_finance_fetcher.py    # YahooFinanceFetcher class (data layer)
├── finviz_fetcher.py           # FinVizFetcher class (data layer)
├── requirements.txt            # Python dependencies
├── Procfile                    # Heroku/Render deployment config
├── start_server.bat            # Windows batch script to start local server
└── README.md (implied)         # Project documentation (not yet created)
```

## Directory Purposes

**Root directory:**
- Purpose: Main project files and entry points
- Contains: Frontend HTML, backend Python, config files, launch script
- Key files: `index.html` (frontend), `api_server.py` (backend), `requirements.txt` (dependencies)

**.planning/codebase/:**
- Purpose: GSD-generated architecture and analysis documents
- Contains: Markdown files describing architecture, structure, conventions, testing, concerns
- Key files: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**_dev/:**
- Purpose: Development workspace and research artifacts
- Contains: Test scripts, reference Excel models, data samples, development notes
- Generated: No (developer-maintained)
- Committed: Yes (for reference and reproducibility)
- Key files:
  - `test_yahoo_finance.py`: Tests YahooFinanceFetcher with sample tickers
  - `test_finviz.py`: Tests FinVizFetcher scraping logic
  - `AAPL_DCF_20yr_inputs.csv`: Sample input data
  - `True Value Finder - Intrinsic Value Calculator_Updated.xlsx`: Reference Excel model

**img/:**
- Purpose: Project images (screenshots, icons, logos)
- Contains: PNG/JPG image files
- Generated: No
- Committed: Yes

**venv/:**
- Purpose: Python virtual environment for isolated dependency management
- Contains: Python interpreter, installed packages from requirements.txt
- Generated: Yes (by `python -m venv venv`)
- Committed: No (.gitignore excludes venv/)

## Key File Locations

**Entry Points:**

- `index.html`: Frontend entry point — opened in browser, contains all HTML, CSS, and JavaScript
- `api_server.py` lines 282-288: Backend entry point — starts Flask app on localhost:5000
- `start_server.bat`: Windows batch script to activate venv and start api_server.py

**Configuration:**

- `requirements.txt`: Python package versions (Flask, yfinance, BeautifulSoup4, etc.)
- `Procfile`: Deployment configuration for Heroku/Render — specifies `gunicorn api_server:app` as web process

**Core Logic:**

- `index.html` lines 706-1313: JavaScript for UI control, data fetching, DCF calculation, result rendering
- `api_server.py` lines 98-274: `/api/fetch-stock/<symbol>` endpoint with data aggregation and method recommendation logic
- `yahoo_finance_fetcher.py`: YahooFinanceFetcher class with methods to extract OCF, NI, shares, debt, cash, growth rates
- `finviz_fetcher.py`: FinVizFetcher class with web scraping and financial data parsing

**Testing:**

- `_dev/test_yahoo_finance.py`: Unit tests for YahooFinanceFetcher
- `_dev/test_finviz.py`: Unit tests for FinVizFetcher
- No automated test runner configured (manual testing via `_dev/` scripts)

## Naming Conventions

**Files:**

- Backend modules: `snake_case.py` (e.g., `api_server.py`, `yahoo_finance_fetcher.py`)
- Frontend: Single `index.html` file
- Config: All caps with dots (e.g., `Procfile`, `requirements.txt`)
- Batch scripts: `PascalCase.bat` (e.g., `start_server.bat`)
- CSV/Excel samples: `SYMBOL_DESCRIPTION.csv` or `.xlsx` (e.g., `AAPL_DCF_20yr_inputs.csv`)

**JavaScript (in index.html):**

- Functions: camelCase (e.g., `fetchStockData()`, `computeIV()`, `showVerifyPanel()`)
- DOM element IDs: kebab-case (e.g., `tickerInput`, `verifyPanel`, `serverDot`)
- Classes: kebab-case (e.g., `.auto-filled`, `.row-phase`, `.step-box`)
- Variables: camelCase (e.g., `lastData`, `growthCapMode`, `verdictClass`)

**Python (in backend):**

- Functions: snake_case (e.g., `safe_float()`, `to_millions()`, `fetch_all_data()`)
- Classes: PascalCase (e.g., `YahooFinanceFetcher`, `FinVizFetcher`)
- Module-level variables: UPPER_CASE (e.g., `BASE_DIR`, `_DISCOUNT_TABLE_US`)
- Private methods: Leading underscore (e.g., `_parse_financial_data()`)

**Directories:**

- Source modules: root level, snake_case
- Dev workspace: `_dev/` prefix for development-only code
- Planning docs: `.planning/codebase/` with UPPERCASE filenames

## Where to Add New Code

**New Feature (e.g., add new valuation method):**
- Backend logic: Add method detection in `api_server.py` fetch_stock() function around line 158-170
- Frontend method option: Add <option> to `index.html` line 508-512 select element
- Frontend calculation: Extend `computeIV()` function in `index.html` lines 1045-1056 if needed, or add new function
- Tests: Add test case in `_dev/test_yahoo_finance.py` or new test file

**New Data Source (e.g., integrate Alpha Vantage):**
- Implementation: Create new file `alpha_vantage_fetcher.py` following YahooFinanceFetcher pattern (class, fetch_all_data(), getter methods)
- Integration: Import in `api_server.py`, instantiate and call in fetch_stock() endpoint
- Fallback: Implement as enhancement to existing sources (fallback if primary sources fail)

**New API Endpoint:**
- Add route handler in `api_server.py` using @app.route() decorator (see line 98, 277 for examples)
- Call from frontend using fetch() in `index.html` JavaScript (see line 833 for example)
- Consider CORS implications if adding new methods/paths

**Frontend Component (e.g., new results section):**
- HTML template: Add structure in `index.html` (e.g., new <div class="card"> after line 1295)
- CSS styling: Add rules in `<style>` block `index.html` lines 7-460 using existing CSS variables and pattern
- JavaScript: Add renderer function or inline generation (see buildMethodComparison() pattern lines 1058-1099)

**Utilities / Helpers:**
- Shared calculation logic: Add function to `index.html` JavaScript block (lines 706-1313)
- Backend utilities: Add function or class to `api_server.py`
- Data transformation: Implement in fetcher classes (yahoo_finance_fetcher.py or finviz_fetcher.py)

## Special Directories

**_dev/:**
- Purpose: Development workspace with testing scripts, reference models, sample data
- Generated: No (maintained by developers)
- Committed: Yes (intentional — provides research artifacts and test data)
- Not deployed: .gitignore could exclude this, but currently it's committed for reference

**venv/:**
- Purpose: Python virtual environment
- Generated: Yes (created by `python -m venv venv`)
- Committed: No (.gitignore excludes it)
- When to recreate: `pip install -r requirements.txt` after environment setup or when dependencies update

**.planning/codebase/:**
- Purpose: GSD-generated documentation (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by `/gsd:map-codebase` command)
- Committed: Yes (for team reference)
- How to update: Regenerate with `/gsd:map-codebase arch` when architecture changes

**.git/:**
- Purpose: Git version control metadata
- Generated: Yes (git init)
- Committed: Not applicable (version control directory)

---

*Structure analysis: 2026-03-17*
