# Technology Stack

**Analysis Date:** 2026-03-17

## Languages

**Primary:**
- Python 3 - Backend API server and financial data fetchers

**Secondary:**
- HTML5 - Frontend markup and static UI
- JavaScript (vanilla) - Frontend interactivity and calculations
- CSS3 - Frontend styling

## Runtime

**Environment:**
- Python 3.x (specified in venv)
- Browser environment for frontend (modern ES6+ support)

**Package Manager:**
- pip (Python)
- Lockfile: requirements.txt present

## Frameworks

**Core:**
- Flask 3.1.3 - REST API server for stock data endpoints
- Flask-CORS 6.0.2 - CORS handling for cross-origin requests

**Data Processing:**
- pandas 2.3.2 - Financial data manipulation and analysis
- numpy 2.3.3 - Numerical computing for calculations

**Web Scraping:**
- beautifulsoup4 4.13.5 - HTML parsing for FinViz data extraction
- lxml 6.0.1 - XML/HTML parser backend for BeautifulSoup

**HTTP Client:**
- requests 2.32.5 - HTTP library for external API calls

**Deployment:**
- gunicorn 23.0.0 - WSGI HTTP Server for production deployment

## Key Dependencies

**Critical:**
- yfinance 0.2.65 - Yahoo Finance data fetching SDK; fetches stock info, financial statements, cash flow, balance sheet, quarterly data
- beautifulsoup4 4.13.5 - Web scraping FinViz.com for EPS growth estimates and beta values
- requests 2.32.5 - HTTP requests to FinViz; enables web scraping of financial metrics

**Infrastructure:**
- Flask 3.1.3 - Serves REST API `/api/fetch-stock/<symbol>` and static HTML
- gunicorn 23.0.0 - Production WSGI server for Render deployment

## Configuration

**Environment:**
- Development: Flask development server on http://localhost:5000
- Production: Render deployment using Procfile
- Static files served from project root (index.html)
- CORS enabled for all origins via flask-cors

**Build:**
- Procfile: `web: gunicorn api_server:app`
- No build step; application runs as pure Python + static HTML

## Platform Requirements

**Development:**
- Python 3.x with pip
- Virtual environment (venv directory present)
- Recommended: Windows batch file start_server.bat for local execution

**Production:**
- Render deployment platform
- Python buildpack support
- Environment variables: None currently required (all hardcoded, no API keys used)

---

*Stack analysis: 2026-03-17*
