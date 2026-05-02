# Jun Xian's Portfolio — AI × Finance

This repository is Jun Xian's personal portfolio. Its purpose is to demonstrate how domain expertise in finance can be paired with AI to build tools that are actually useful — not demos, but things a value investor would open on a real research day.

The primary audience is **people evaluating Jun Xian**: recruiters, collaborators, or anyone who wants to understand how he thinks. Every decision — what to build, how to structure it, what to automate — should serve that goal.

## The through-line

Jun Xian's interest is in identifying manual, judgment-heavy processes where AI can meaningfully reduce friction or surface insight that would otherwise require hours of work. The projects here share a common idea: **investment research is a domain where a lot of the groundwork is tedious and repeatable, and AI should handle that so the human can focus on the judgment call at the end.**

Each project encodes real finance domain knowledge — not just "call an API and display the result", but deliberate choices about methodology, data sourcing, and what the output should actually mean.

## Projects

### 1. Interactive DCF Calculator (`docs/projects/calculator/`)
Computes intrinsic value per share for any stock using a 20-year multi-phase DCF model. Live financial data is fetched and all inputs are auto-filled — the user can review and adjust before running the model. Demonstrates: finance domain encoding, data pipeline design, interactive UX.
→ See `docs/projects/calculator/CLAUDE.md` for full detail.

### 2. AI Economic Moat Analyzer (`docs/projects/moat/`)
Evaluates a company's competitive durability across 5 dimensions (Brand Loyalty, Barriers to Entry, Switching Costs, Network Effects, Economies of Scale) using parallel AI agents with live web search. A synthesizer agent combines the results into a verdict and narrative. Demonstrates: multi-agent orchestration, prompt engineering, parallel async execution, structured output.
→ See `docs/projects/moat/CLAUDE.md` for full detail.

### 3. S&P 500 DCF Screener (`docs/projects/screener/`)
Runs the same DCF model as the calculator across all ~500 S&P 500 companies via a batch pipeline, and presents results as a filterable, sortable table. Clicking a row opens a per-stock overview with a spider chart, financial snapshot, and embedded price chart. Demonstrates: batch pipeline design, static-site data architecture, data visualisation.
→ See `docs/projects/screener/CLAUDE.md` for full detail.

## Tech stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3 · Flask 3.1.3 · Flask-CORS · Gunicorn |
| Data | yfinance · FinViz (BeautifulSoup scraper) |
| AI | OpenAI Responses API · `web_search` tool · `gpt-5.4-nano` |
| Frontend | Vanilla HTML/CSS/JS · two distinct dark themes |
| Deployment | Heroku (live backend) · GitHub Pages (static portfolio) |

## Repository layout

```
api_server.py                  # Flask API — live backend for the calculator
yahoo_finance_fetcher.py        # TTM/annual financials from Yahoo Finance
finviz_fetcher.py              # Valuation metrics + beta from FinViz

economic-moat/
  moat_analyzer.py             # Async orchestrator: 5 criterion agents + synthesizer
  moat_prompts.py              # System prompts for each criterion
  run_moat_analysis.py         # Batch runner with 30-day result cache

scripts/
  fetch_sp500.py               # Batch DCF across ~500 S&P 500 tickers → data.json

docs/                          # GitHub Pages root
  index.html                   # Portfolio landing page
  projects/
    calculator/                # Interactive DCF calculator (calls live backend)
    moat/                      # AI moat analysis viewer (static, reads data.json)
    screener/                  # S&P 500 screener + per-stock overview (static)
```

## API endpoints (live backend)

- `GET /` → serves `index.html`
- `GET /api/fetch-stock/<symbol>` → financial data JSON (Yahoo + FinViz)
- `GET /api/health` → server status

---

## MCP Tools: code-review-graph

> **Status: MCP server connected.** Repo registered as `jun-xian-portfolio` (79 nodes, 774 edges). Prefer graph tools over Grep/Glob/Read:

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |
