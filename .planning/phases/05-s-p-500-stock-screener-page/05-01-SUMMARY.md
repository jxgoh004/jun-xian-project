---
phase: 05-s-p-500-stock-screener-page
plan: 01
subsystem: data-pipeline
tags: [python, dcf, github-actions, yfinance, finviz, wikipedia, screener]
dependency_graph:
  requires: []
  provides: [docs/projects/screener/data.json, scripts/fetch_sp500.py, .github/workflows/nightly-screener.yml]
  affects: [screener-frontend]
tech_stack:
  added: [pandas.read_html (Wikipedia), requests (Wikipedia UA workaround)]
  patterns: [batch-dcf, nightly-ci-commit-back, cumulative-discount-factor]
key_files:
  created:
    - scripts/fetch_sp500.py
    - .github/workflows/nightly-screener.yml
    - docs/projects/screener/data.json
  modified: []
decisions:
  - "Wikipedia returns HTTP 403 for default urllib UA; fixed by downloading HTML via requests with a browser User-Agent before passing to pd.read_html"
  - "FinViz growth rate (EPS next 5Y) returned as decimal from get_growth_estimates(); multiplied by 100 to convert to percentage before DCF input"
  - "DCF uses cumulative discount factor (prev_df / (1+r)) matching JS computeIV exactly, NOT (1+r)**year"
  - "Workflow cron weekdays only (1-5) since S&P 500 data does not change on weekends"
metrics:
  duration: ~25 minutes
  completed: 2026-04-05
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 0
---

# Phase 5 Plan 01: S&P 500 Batch DCF Pipeline Summary

**One-liner:** 20-year cumulative-DF DCF batch script fetching ~503 S&P 500 tickers from Wikipedia via requests+pandas, reusing YahooFinanceFetcher/FinVizFetcher, with a nightly GitHub Actions commit-back workflow.

## What Was Built

### Task 1 — `scripts/fetch_sp500.py`

A standalone batch script that:

1. **Fetches S&P 500 tickers** from Wikipedia (`List_of_S%26P_500_companies`) using `requests` with a browser User-Agent (required to avoid HTTP 403) and `pd.read_html` to parse the HTML. Searches for the ticker column by name (case-insensitive `symbol`/`ticker` match) to survive Wikipedia table format changes. Normalises `.` to `-` (e.g. `BRK.B` → `BRK-B`).

2. **Per-ticker DCF calculation** reusing `YahooFinanceFetcher` and `FinVizFetcher` from the project root (added to `sys.path`). The DCF follows the **same logic as `api_server.py`** and matches the JS `computeIV` function in the calculator frontend exactly:
   - Cumulative discount factor: `prev_df / (1 + r)` — NOT `(1 + r) ** year`
   - Growth phases: years 1–5 = g1, 6–10 = g1/2, 11–20 = 4% fixed
   - Method selection: FCF when negative earnings or OCF inflated >1.5× NI, else OCF
   - Growth rate priority: FinViz 5Y EPS > Yahoo CF historical > Yahoo EPS historical > 5% default
   - Discount rate: beta lookup against `_DISCOUNT_TABLE_US` (copied from `api_server.py`)

3. **Output:** `docs/projects/screener/data.json` with `updated_at` (UTC ISO-8601) and `stocks` array. Each stock has 8 fields: `ticker`, `company_name`, `sector`, `current_price`, `intrinsic_value`, `discount_pct`, `method`, `valuation_label`.

4. **CLI flags:** `--limit N` restricts to first N tickers (local testing); `--seed` writes empty `{"updated_at": null, "stocks": []}` and exits.

5. **Rate limiting:** `time.sleep(0.5)` between tickers; FinViz failures silently caught; per-ticker exceptions caught and stored as null records.

### Task 2 — `.github/workflows/nightly-screener.yml`

GitHub Actions workflow that:
- Triggers on `schedule` (cron `0 6 * * 1-5` — 06:00 UTC weekdays) and `workflow_dispatch`
- `permissions: contents: write` for GITHUB_TOKEN git push
- Steps: checkout → setup-python 3.11 → `pip install -r requirements.txt` → `python scripts/fetch_sp500.py` → conditional commit (`git diff --staged --quiet || git commit`) → `git push`
- Empty-commit guard prevents workflow failures when data has not changed

### Seed File

`docs/projects/screener/data.json` is pre-populated with 3-stock test run output so the screener frontend can load before the first nightly Actions run.

## Verification Results

```
python scripts/fetch_sp500.py --limit 3
# → [1/3] MMM: IV=71.05, label=Highly Overvalued
# → [2/3] AOS: IV=84.01, label=Slightly Undervalued
# → [3/3] ABT: IV=128.19, label=Slightly Undervalued

python -c "import json; d=json.load(open('docs/projects/screener/data.json')); ..."
# → OK: data.json valid with 3 stocks

test -f .github/workflows/nightly-screener.yml && grep checks...
# → OK: workflow valid
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wikipedia HTTP 403 with default pandas urllib**
- **Found during:** Task 1 — first `python scripts/fetch_sp500.py --limit 3` run
- **Issue:** `pd.read_html(url)` uses Python's `urllib.request` which sends a generic user-agent; Wikipedia returns HTTP 403 Forbidden
- **Fix:** Added `import requests` download step inside `fetch_sp500_tickers()` — downloads the Wikipedia page with a Chrome browser User-Agent string, then passes the HTML string to `pd.read_html(io.StringIO(resp.text))`
- **Files modified:** `scripts/fetch_sp500.py` (fetch_sp500_tickers function only)
- **Commit:** f5731ad (included in same task commit)

## Known Stubs

None. The seed `data.json` contains real fetched data (3 stocks from the `--limit 3` test run), not placeholder values.

## Self-Check: PASSED

- `scripts/fetch_sp500.py` exists: FOUND
- `.github/workflows/nightly-screener.yml` exists: FOUND
- `docs/projects/screener/data.json` exists: FOUND
- Task 1 commit f5731ad: FOUND
- Task 2 commit 6665274: FOUND
