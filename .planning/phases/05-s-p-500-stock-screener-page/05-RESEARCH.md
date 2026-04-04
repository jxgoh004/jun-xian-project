# Phase 5: S&P 500 Stock Screener Page - Research

**Researched:** 2026-04-05
**Domain:** GitHub Actions CI/CD, vanilla JS table UI, Python batch scripting, postMessage cross-frame communication
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data Pipeline**
- D-01: GitHub Actions cron job runs nightly. The job runs a Python script in-workflow that imports the existing `yahoo_finance_fetcher.py` and `finviz_fetcher.py` modules directly (not via the Render API). It reuses the same DCF calculation logic from `api_server.py`.
- D-02: S&P 500 constituent list is fetched dynamically from Wikipedia via `pandas.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')`. Updates automatically after quarterly rebalances. No hardcoded ticker list.
- D-03: Wikipedia tickers are normalized to Yahoo Finance format before fetching (e.g., `BRK.B` to `BRK-B`, `BF.B` to `BF-B`). The normalized Yahoo-format ticker is stored in `data.json` so the screener and calculator always use the same ticker format.
- D-04: The snapshot is stored as `docs/projects/screener/data.json` and auto-committed to the `main` branch by the GitHub Actions workflow. The screener frontend fetches this static file directly from GitHub Pages — zero latency, no backend call at runtime.
- D-05: Metrics stored per stock in `data.json`: `ticker`, `company_name`, `sector`, `current_price`, `intrinsic_value`, `discount_pct`, `method` (ocf/fcf), `valuation_label`. Any stock where the DCF calculation fails or returns null is stored with `null` intrinsic value and `valuation_label: "N/A"`.

**DCF Calculation**
- D-06: Use the same auto-selection logic as `api_server.py`: OCF by default; switch to FCF if negative earnings or inflated OCF (>1.5x net income). `method` field records which was used.
- D-07: The intrinsic value calculation uses the same growth rate priority chain as `api_server.py`: FinViz 5Y EPS estimate then Yahoo CF historical then Yahoo EPS historical then 5% default. Same discount rate lookup table from beta.

**Screener Features**
- D-08: Show all ~500 stocks in the table by default on load (render all rows at once — no pagination).
- D-09: Search: filter rows by ticker symbol or company name (case-insensitive substring match).
- D-10: Sector filter: dropdown populated from unique sectors in `data.json`. Selecting a sector filters the table to that sector only.
- D-11: Search and sector filter compose — a user can search "Apple" within "Technology".

**Display Format**
- D-12: Sortable table. Columns: Ticker | Company | Sector | Price | Intrinsic Value | Discount % | Method | Valuation Label. Clicking a column header sorts ascending; clicking again sorts descending.
- D-13: Default sort: by Discount % descending (most undervalued first).
- D-14: Valuation label thresholds (based on discount % = (intrinsic_value - current_price) / intrinsic_value x 100): Highly Undervalued > 30%, Slightly Undervalued 10-30%, Fairly Valued -10% to +10%, Slightly Overvalued -10% to -30%, Highly Overvalued < -30%, N/A for negative earnings + FCF.
- D-15: Valuation label shown as a colour-coded badge (green for undervalued, grey for fairly valued, red for overvalued) matching the existing dark theme palette.

**Calculator Link-Through**
- D-16: Clicking a stock row navigates to the intrinsic value calculator with ticker pre-filled. Implementation: screener iframe calls `window.parent.postMessage({ type: 'navigate', project: 'calculator', ticker: 'AAPL' }, '*')`. Parent page listens, navigates to `#calculator`, passes ticker via `projects/calculator/index.html?ticker=AAPL`.
- D-17: The calculator frontend reads `?ticker=` from `location.search` on load and auto-fills the ticker input field (and optionally auto-submits).

**Portfolio Integration**
- D-18: Add screener project card to `docs/index.html` projects grid. Same `.card[data-project]` pattern. Tags: `Python`, `JavaScript`, `Finance`, `Data`.
- D-19: Register screener in `projects` JS object: `screener: 'projects/screener/index.html'`.
- D-20: Screener project directory: `docs/projects/screener/`. Contains `index.html` and `data.json`.

**Styling**
- D-21: Screener `index.html` uses the same dark-theme CSS variables (`--bg`, `--surface`, `--border`, `--accent`, `--text`, `--text-bright`, `--text-dim`). Vanilla JavaScript, no framework.

### Claude's Discretion
- Table row hover state, sticky header behaviour, mobile table responsiveness (horizontal scroll or column hiding).
- Exact badge colour values for valuation labels (must remain legible on `--surface` background).
- GitHub Actions workflow name, trigger time (UTC), and Python version.
- Error state UI when `data.json` fails to load.
- Last-updated timestamp display (show when data was last refreshed).

### Deferred Ideas (OUT OF SCOPE)
- Additional screening metrics (P/E, market cap, dividend yield, beta, revenue growth)
- Advanced multi-criteria filtering (e.g., "Technology sector AND discount > 20%")
- Historical intrinsic value trend per stock
- Dark/light mode toggle
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHOW-04 (new) | S&P 500 screener card appears in portfolio home page project grid | Portfolio integration pattern from existing `.card[data-project]` markup at `docs/index.html:201` |
| NAV-03 (new) | Clicking screener card loads screener in-page via existing hash routing | `projects` object extension at `docs/index.html:232`; postMessage pattern for screener-to-parent navigation |
| SCREENER-01 | Sortable, searchable, sector-filterable table of ~500 S&P 500 stocks | Vanilla JS sort/filter pattern; no external dependencies needed |
| SCREENER-02 | Pre-calculated DCF intrinsic value data served from static `data.json` | GitHub Actions nightly workflow; pandas Wikipedia fetch; DCF logic extracted from `api_server.py` and calculator frontend |
| SCREENER-03 | Clicking a row navigates parent to calculator with ticker pre-filled | postMessage (D-16) + URL query param (D-17); `tickerInput` element at `calculator/index.html:498` |
| SCREENER-04 | Nightly GitHub Actions workflow keeps data fresh | `.github/workflows/` YAML file; git commit-back pattern using `GITHUB_TOKEN` |

Note: Phase 5 has no pre-existing requirement IDs in REQUIREMENTS.md — these IDs are proposed here for the planner's use.
</phase_requirements>

---

## Summary

Phase 5 has two distinct delivery areas: a **nightly data pipeline** (Python + GitHub Actions) and a **screener frontend** (vanilla JS table + parent-frame integration). Neither area requires new dependencies beyond what is already in `requirements.txt` and the existing HTML/CSS/JS stack.

The data pipeline extracts the DCF calculation logic that currently lives inline in `api_server.py` into a standalone batch script. The script imports the existing `yahoo_finance_fetcher.py` and `finviz_fetcher.py` modules unchanged and runs the same OCF/FCF selection and growth rate priority chain for each of ~500 tickers. The nightly GitHub Actions job executes this script, writes `docs/projects/screener/data.json`, and commits it back to `main` using the standard `GITHUB_TOKEN`. The DCF intrinsic value formula is not directly implemented in `api_server.py` — the API returns raw inputs (OCF/FCF, growth rates, discount rate, shares, debt, cash) and the calculator's JavaScript frontend performs the final DCF calculation. The batch script must implement the same formula in Python; this is the primary logic gap to close.

The screener frontend is a single `docs/projects/screener/index.html` file. It fetches `data.json` (a static sibling file), renders all ~500 rows into a `<table>`, and supports in-place client-side sort and filter with no virtual scrolling or pagination required. The link-through to the calculator uses the `postMessage` API already wired into the parent `docs/index.html`; the calculator side needs a one-time addition to read `?ticker=` from `location.search` on load.

**Primary recommendation:** Implement the DCF formula in the batch script first (it is the only true unknown), verify it produces the same intrinsic values as the interactive calculator for a known ticker, then build the screener UI and GitHub Actions workflow around it.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yfinance | 0.2.65 (pinned in requirements.txt) | Yahoo Finance data fetching | Already used by the project |
| pandas | 2.3.2 (pinned) | Wikipedia table parse (`read_html`), data manipulation | Already used; `read_html` is the canonical way to parse the Wikipedia S&P 500 table |
| requests | 2.32.5 (pinned) | HTTP for FinViz fetching | Already used by `finviz_fetcher.py` |
| beautifulsoup4 | 4.13.5 (pinned) | FinViz HTML parsing | Already used by `finviz_fetcher.py` |
| lxml | 6.0.1 (pinned) | Parser backend for pandas `read_html` | Already present in requirements.txt; required for `read_html` to work |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| actions/checkout | v4 | GitHub Actions repo checkout | Every GitHub Actions job that needs repo files |
| actions/setup-python | v5 | GitHub Actions Python environment setup | Python workflows in Actions |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Render-all-rows vanilla JS table | Virtual scrolling (e.g., TanStack Virtual) | 500 rows at ~60 bytes of DOM per row is ~30KB DOM — negligible. Virtual scroll adds JS complexity for no benefit at this scale. |
| pandas `read_html` for Wikipedia | Hardcoded ticker list | `read_html` auto-updates after quarterly rebalances per D-02. Hardcoded list requires manual maintenance. |
| `window.postMessage` for navigation | Direct `window.parent.location.hash` manipulation | `postMessage` is safer (no cross-origin issues if domain changes), matches D-16 decision. |

**Installation:** No new packages needed. All dependencies are already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
docs/projects/screener/
├── index.html          # Screener SPA (vanilla JS, inline CSS, ~300-400 lines)
└── data.json           # Committed by GitHub Actions nightly

scripts/
└── fetch_sp500.py      # Nightly batch script (standalone, imports existing modules)

.github/
└── workflows/
    └── nightly-screener.yml  # GitHub Actions workflow definition
```

### Pattern 1: GitHub Actions Commit-Back Workflow

**What:** A GitHub Actions workflow uses `GITHUB_TOKEN` to commit generated files back to the repository branch that triggered it.

**When to use:** Whenever a CI job must update a static file served directly from the repo (e.g., GitHub Pages data files).

```yaml
name: Nightly S&P 500 Screener Data
on:
  schedule:
    - cron: '0 2 * * *'   # 02:00 UTC daily
  workflow_dispatch:        # manual trigger

permissions:
  contents: write           # required for git push with GITHUB_TOKEN

jobs:
  fetch-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -r requirements.txt

      - run: python scripts/fetch_sp500.py

      - name: Commit data.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/projects/screener/data.json
          git diff --staged --quiet || git commit -m "chore: nightly S&P 500 screener data update"
          git push
```

Key details:
- `git diff --staged --quiet || git commit ...` prevents empty-commit failure when data has not changed.
- `permissions: contents: write` grants write access — this is required; GitHub Actions defaults to read-only on newer repos.
- `workflow_dispatch` allows manual re-runs without waiting for the schedule.
- `GITHUB_TOKEN` is automatically provided — no manual secret setup required.

### Pattern 2: DCF Intrinsic Value Formula (Python)

**What:** The batch script must compute the intrinsic value per stock. The API returns raw inputs; the actual DCF calculation lives in the calculator's JavaScript frontend. The batch script must implement the same formula in Python.

The DCF model uses 20-year projections in three stages (years 1-5 at `growth_1_5`, years 6-10 at half that rate, years 11-20 at 4% fixed). Each year's cash flow is discounted to present value, summed, then net cash per share is added.

```python
def calculate_intrinsic_value(cash_flow_m, growth_1_5_pct, discount_rate_pct,
                               shares_millions, debt_m, cash_m):
    """
    Replicates the 20-year DCF model from the calculator frontend.
    Returns (intrinsic_value_per_share, None) or (None, reason_string).
    """
    if cash_flow_m is None or shares_millions is None or shares_millions <= 0:
        return None, "missing_inputs"

    g1 = growth_1_5_pct / 100
    g2 = g1 / 2          # years 6-10
    g3 = 0.04            # years 11-20 fixed per model
    r  = discount_rate_pct / 100

    cf = cash_flow_m
    pv_sum = 0.0

    for year in range(1, 21):
        if year <= 5:
            cf *= (1 + g1)
        elif year <= 10:
            cf *= (1 + g2)
        else:
            cf *= (1 + g3)
        pv_sum += cf / ((1 + r) ** year)

    net_cash_m = (cash_m or 0) - (debt_m or 0)
    intrinsic_value = (pv_sum + net_cash_m) / shares_millions
    return round(intrinsic_value, 2), None
```

CRITICAL: Verify this formula produces the same output as the calculator by cross-checking a known ticker (e.g., AAPL) against the live calculator before the full batch run. The exact JS formula must be read from `docs/projects/calculator/index.html` before implementing — it is the authoritative source.

### Pattern 3: Wikipedia S&P 500 Ticker Fetch and Normalization

```python
import pandas as pd

def get_sp500_tickers():
    """Returns list of Yahoo Finance-format tickers from Wikipedia."""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    df = tables[0]  # First table is the S&P 500 constituent list
    # Defensive: find the column whose name contains 'Symbol' or 'Ticker'
    ticker_col = next(
        (c for c in df.columns if 'symbol' in c.lower() or 'ticker' in c.lower()),
        None
    )
    if ticker_col is None:
        raise ValueError(f"Could not find ticker column. Columns: {df.columns.tolist()}")
    tickers = df[ticker_col].tolist()
    # Normalize dots to hyphens: BRK.B -> BRK-B
    return [str(t).replace('.', '-') for t in tickers]
```

### Pattern 4: Vanilla JS Sortable/Filterable Table

Store all stock objects in a JS array. On filter/sort events, recompute a filtered subset and re-render rows.

```javascript
let allStocks = [];        // loaded from data.json once
let sortCol = 'discount_pct';
let sortDir = -1;          // -1 = descending, 1 = ascending
let filterText = '';
let filterSector = '';

function getFiltered() {
  return allStocks.filter(function(s) {
    var q = filterText.toLowerCase();
    var matchText = !q ||
      s.ticker.toLowerCase().indexOf(q) !== -1 ||
      s.company_name.toLowerCase().indexOf(q) !== -1;
    var matchSector = !filterSector || s.sector === filterSector;
    return matchText && matchSector;
  }).sort(function(a, b) {
    var av = a[sortCol], bv = b[sortCol];
    if (av === null && bv === null) return 0;
    if (av === null) return 1;   // nulls always sort to end
    if (bv === null) return -1;
    return sortDir * (av < bv ? -1 : av > bv ? 1 : 0);
  });
}
```

**Row rendering:** Build each row as a `<tr>` DOM element using `createElement` and `textContent` (not innerHTML with untrusted data) for all user-visible text content. The `data.json` values come from a controlled source, but using `textContent` is the correct default pattern.

**Debounce search:** 150ms debounce on the search `input` event is sufficient for 500 rows and avoids re-render spam on fast typing.

### Pattern 5: postMessage Navigation (Screener to Parent to Calculator)

**In screener iframe (`docs/projects/screener/index.html`):**
```javascript
function navigateToCalculator(ticker) {
  window.parent.postMessage(
    { type: 'navigate', project: 'calculator', ticker: ticker },
    '*'
  );
}
// Attach to table row click via event delegation on tbody
```

**In parent page (`docs/index.html`) — additions needed:**

The current `navigate()` function creates iframes with `src = projects[hash]` (no query params). To pass `?ticker=AAPL`, use a `pendingTicker` variable set before the hash change:

```javascript
var pendingTicker = null;

window.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'navigate' && projects[event.data.project]) {
    pendingTicker = event.data.ticker || null;
    // Remove existing iframe so navigate() creates a fresh one with the ticker param
    var existing = projectView.querySelector('iframe');
    if (existing) existing.remove();
    location.hash = '#' + event.data.project;
  }
});
```

Then inside the existing `navigate()` function, when creating the iframe, replace:
```javascript
iframe.src = projects[hash];
```
with:
```javascript
var base = projects[hash];
iframe.src = pendingTicker ? base + '?ticker=' + encodeURIComponent(pendingTicker) : base;
pendingTicker = null;
```

**In calculator (`docs/projects/calculator/index.html`) — addition at bottom of script:**
```javascript
(function() {
  var params = new URLSearchParams(location.search);
  var t = params.get('ticker');
  if (t) {
    var input = document.getElementById('tickerInput');
    if (input) input.value = t.toUpperCase();
    // Auto-submit is optional per D-17; omit for now, user clicks Fetch Data
  }
})();
```

### Recommended data.json Format

```json
{
  "updated_at": "2026-04-05T02:00:00Z",
  "stocks": [
    {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "sector": "Technology",
      "current_price": 172.50,
      "intrinsic_value": 210.30,
      "discount_pct": 18.0,
      "method": "ocf",
      "valuation_label": "Slightly Undervalued"
    },
    {
      "ticker": "XYZ",
      "company_name": "XYZ Corp",
      "sector": "Energy",
      "current_price": 45.20,
      "intrinsic_value": null,
      "discount_pct": null,
      "method": null,
      "valuation_label": "N/A"
    }
  ]
}
```

`updated_at` at the top level enables the "last updated" display without parsing any stock row.

### Anti-Patterns to Avoid

- **Calling the Render API from GitHub Actions:** The batch script must import Python modules directly (D-01). The Render instance may be asleep (free tier) and fetching 500 tickers via HTTP API would be ~500x slower than direct module calls.
- **Paginating the table:** D-08 explicitly requires all rows on load. Pagination adds state complexity with no benefit for 500 rows.
- **Re-fetching `data.json` on every filter/sort:** Load once on page init, store in JS array, filter/sort in memory.
- **Using innerHTML with unescaped values for table cells:** Use `textContent` or `createElement` for all cell content. Company names come from a controlled JSON source, but `textContent` is the correct default.
- **Not debouncing the search input:** Add a 150ms debounce to avoid redundant re-renders on fast typing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fetching S&P 500 constituent list | Hardcoded array of 500 tickers | `pandas.read_html(wikipedia_url)` | Wikipedia auto-updates after rebalances; no maintenance needed |
| DCF intrinsic value formula | New implementation from scratch | Extract exact formula from `docs/projects/calculator/index.html` JS and translate to Python | Single source of truth prevents drift between screener and calculator |
| GitHub Actions git commit-back | Custom push script | Standard `git config / git add / git commit / git push` run step + `actions/checkout@v4` | Well-documented, works with `GITHUB_TOKEN`, no extra action needed |
| Sector dropdown options | Hardcoded sector list | Derive unique sectors from `data.json` at load time | Auto-adapts as S&P 500 sector composition changes |
| Valuation label logic duplication | Compute labels in both Python and JS | Compute in batch script only; store as `valuation_label` string in JSON | Frontend reads the pre-computed label — no duplication, no risk of drift |

**Key insight:** The batch script is the authoritative source for all computed values. The frontend is a display layer that reads pre-computed JSON.

---

## Runtime State Inventory

Greenfield phase — no rename or migration involved. No runtime state affected.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no databases or datastores involved | None |
| Live service config | None — Render API is not called by the screener at runtime | None |
| OS-registered state | None | None |
| Secrets/env vars | None — `GITHUB_TOKEN` is auto-provisioned by GitHub Actions; no manual secret setup needed | None |
| Build artifacts | None | None |

---

## Common Pitfalls

### Pitfall 1: DCF Formula Drift Between Batch Script and Calculator

**What goes wrong:** The batch script implements the DCF formula slightly differently from the calculator's JavaScript. Visitors notice the screener shows a different intrinsic value for AAPL than the calculator produces for the same ticker.

**Why it happens:** The DCF formula is currently only in the calculator's JS frontend (not in `api_server.py`). It is easy to make subtle errors when translating to Python (off-by-one year, wrong growth rate application order, missing terminal value step).

**How to avoid:** Read the calculator's JS DCF function verbatim before writing the Python version. Cross-check the Python output for AAPL against the live calculator result before running the full batch.

**Warning signs:** Screener discount % values differ from what the calculator shows for the same stock on the same day.

### Pitfall 2: GitHub Actions Push Fails Due to Token Permissions

**What goes wrong:** The workflow runs successfully and commits the file, then fails on `git push` with "remote: Permission to ... denied to github-actions[bot]".

**Why it happens:** `GITHUB_TOKEN` defaults to read-only in newer GitHub repository settings unless explicitly granted write permission.

**How to avoid:** Add `permissions: contents: write` at the job level in the workflow YAML. This grants the `GITHUB_TOKEN` write access — no PAT or additional secret required.

**Warning signs:** Workflow step fails with exit code 128 on `git push`.

### Pitfall 3: Wikipedia Table Structure Change Breaks Ticker Fetch

**What goes wrong:** `pd.read_html(url)[0]['Symbol']` raises `KeyError` because Wikipedia renamed or restructured the S&P 500 table.

**Why it happens:** Wikipedia table column names are informal and have changed historically.

**How to avoid:** Use the defensive column lookup shown in Pattern 3. Raise a descriptive error listing available columns so the failure is immediately diagnosable.

**Warning signs:** GitHub Actions run fails at the fetch step before any Yahoo Finance calls.

### Pitfall 4: yfinance Rate Limiting at Scale

**What goes wrong:** Fetching 500 tickers sequentially causes Yahoo Finance to return 429 errors or empty data for many tickers in the middle of the batch.

**Why it happens:** Yahoo Finance has undocumented rate limits. `yfinance` handles per-request retries but cannot prevent volume-based rate limiting.

**How to avoid:** Add `time.sleep(0.5)` between ticker fetches (500 x 0.5s = ~4 minutes total — well within GitHub Actions' 6-hour limit). Wrap each ticker in a try/except and store failed tickers with `intrinsic_value: null` and `valuation_label: "N/A"`.

**Warning signs:** Large proportion of stocks in `data.json` have `null` intrinsic value after the first run.

### Pitfall 5: FinViz Blocking GitHub Actions IP Range

**What goes wrong:** `finviz_fetcher.py` returns `False` (HTTP 403/429) for all tickers when run from GitHub Actions, causing all stocks to fall back to Yahoo Finance-only growth rates.

**Why it happens:** FinViz blocks data center IP ranges (GitHub Actions runs on Azure IPs) with stricter limits than residential IPs.

**How to avoid:** The batch script must treat FinViz as fully optional — exactly as `api_server.py` already does with its `try/except finviz_ok` pattern. If FinViz fails, growth rate falls back to Yahoo CF/EPS historical or 5% default. This is acceptable per D-07.

**Warning signs:** All `growth_source` values in `data.json` are `"Yahoo Finance (historical CF growth)"` or `"Default (5%)"` rather than `"FinViz (EPS next 5Y estimate)"`.

### Pitfall 6: postMessage Navigate and iframe src Timing

**What goes wrong:** The parent page receives `postMessage`, sets `location.hash`, but the new iframe is created without `?ticker=AAPL` because `navigate()` runs before `pendingTicker` is set.

**Why it happens:** `hashchange` can fire synchronously in some browsers. Execution order depends on whether the message handler completes before `hashchange` fires.

**How to avoid:** Set `pendingTicker` before setting `location.hash` (as shown in Pattern 5). Both operations are in the same synchronous call stack, so `pendingTicker` is guaranteed to be set before `navigate()` reads it.

**Warning signs:** Calculator loads but ticker input is empty after clicking a screener row.

### Pitfall 7: Empty Commit Failure in GitHub Actions

**What goes wrong:** If `data.json` content has not changed (e.g., market closed, or all fetches failed), `git commit` exits with code 1 and fails the workflow step.

**How to avoid:** Use `git diff --staged --quiet || git commit -m "..."` — only commits when staged changes exist.

---

## Code Examples

Verified patterns from existing codebase:

### Read `?ticker=` in Calculator on Load (D-17)

```javascript
// Add to the bottom of the IIFE in docs/projects/calculator/index.html
(function() {
  var params = new URLSearchParams(location.search);
  var t = params.get('ticker');
  if (t) {
    var input = document.getElementById('tickerInput');
    if (input) input.value = t.toUpperCase();
  }
})();
```

`tickerInput` is the confirmed element ID at `docs/projects/calculator/index.html:498`.

### Valuation Label Computation (Python, batch script)

```python
def compute_valuation_label(intrinsic_value, current_price):
    """D-14 thresholds. Returns (discount_pct, label) tuple."""
    if intrinsic_value is None or intrinsic_value <= 0 or current_price is None:
        return None, "N/A"
    discount_pct = round((intrinsic_value - current_price) / intrinsic_value * 100, 2)
    if discount_pct > 30:
        label = "Highly Undervalued"
    elif discount_pct > 10:
        label = "Slightly Undervalued"
    elif discount_pct >= -10:
        label = "Fairly Valued"
    elif discount_pct >= -30:
        label = "Slightly Overvalued"
    else:
        label = "Highly Overvalued"
    return discount_pct, label
```

### Badge CSS (valuation labels on dark surface)

```css
/* Legible on --surface: #161b22 */
.badge {
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}
.badge-highly-undervalued   { background: rgba(63,185,80,0.15);   color: #3fb950; border: 1px solid rgba(63,185,80,0.3);   }
.badge-slightly-undervalued { background: rgba(63,185,80,0.08);   color: #7ee787; border: 1px solid rgba(63,185,80,0.2);   }
.badge-fairly-valued        { background: rgba(139,148,158,0.15); color: #8b949e; border: 1px solid rgba(139,148,158,0.3); }
.badge-slightly-overvalued  { background: rgba(248,81,73,0.08);   color: #f0a3a0; border: 1px solid rgba(248,81,73,0.2);   }
.badge-highly-overvalued    { background: rgba(248,81,73,0.15);   color: #f85149; border: 1px solid rgba(248,81,73,0.3);   }
.badge-na                   { background: rgba(139,148,158,0.10); color: #8b949e; border: 1px solid rgba(139,148,158,0.2); }
```

### Sticky Table Header (CSS)

```css
.screener-table thead th {
  position: sticky;
  top: 0;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  z-index: 10;
  cursor: pointer;
  user-select: none;
}
.screener-table thead th:hover { color: var(--text-bright); }
.screener-table thead th[data-sort="asc"]::after  { content: ' \2191'; color: var(--accent); }
.screener-table thead th[data-sort="desc"]::after { content: ' \2193'; color: var(--accent); }
```

### Mobile Table Responsiveness

```css
.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
@media (max-width: 640px) {
  .col-sector, .col-method { display: none; }
}
```

### Last-Updated Timestamp Display

```javascript
var ts = new Date(data.updated_at);
var label = ts.toLocaleDateString('en-US', {
  month: 'short', day: 'numeric', year: 'numeric',
  hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
});
document.getElementById('last-updated').textContent = 'Data as of ' + label;
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GitHub Actions push with PAT secret | `GITHUB_TOKEN` with `permissions: contents: write` | ~2021 | No manual secret setup needed |
| `actions/checkout@v2` | `actions/checkout@v4` | 2023 | v4 uses Node 20; required on current runners |
| `actions/setup-python@v4` | `actions/setup-python@v5` | 2024 | v5 supports Python 3.13, better caching |
| `::set-output name=key::value` | `echo "key=value" >> $GITHUB_OUTPUT` | 2022 | Old set-output command is deprecated and disabled |
| `pandas.read_html` required `html5lib` | Works with `lxml` (already in requirements.txt) | pandas 2.x | No extra install needed |

**Deprecated/outdated:**
- `::set-output` GitHub Actions command: Replaced by `$GITHUB_OUTPUT` environment file. Use `echo "key=value" >> $GITHUB_OUTPUT` if any step outputs are needed.

---

## Open Questions

1. **Exact DCF formula location in calculator JS**
   - What we know: `api_server.py` returns raw inputs; the DCF calculation lives in the JS frontend.
   - What's unclear: The exact function name and precise accumulation logic (especially terminal value handling — whether it is a perpetuity growth model or just 20 years of discounted CFs).
   - Recommendation: Read `docs/projects/calculator/index.html` from line ~800 onward as the first step in implementation. This is CRITICAL before writing the Python batch formula.

2. **Will FinViz block GitHub Actions runners?**
   - What we know: FinViz is already wrapped in try/except in `api_server.py`; failure is graceful.
   - What's unclear: Whether any FinViz data will be retrievable from an Azure cloud IP.
   - Recommendation: Design the batch script to work correctly with 0% FinViz success. All growth rates fall back to Yahoo Finance historical or 5% default — acceptable per D-07.

3. **GitHub Actions scheduled workflow inactivity disable**
   - What we know: GitHub disables scheduled workflows on repos with no activity for 60 days.
   - What's unclear: Whether the portfolio repo will remain active enough to keep the schedule alive long-term.
   - Recommendation: Include `workflow_dispatch` on the workflow for manual re-trigger. Document this limitation in the workflow YAML comment. Not a blocker for initial implementation.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Batch script (local dev/test) | Yes | 3.11.9 | — |
| yfinance | Yahoo Finance data fetch | Yes (requirements.txt) | 0.2.65 | — |
| pandas | Wikipedia ticker fetch | Yes (requirements.txt) | 2.3.2 | — |
| lxml | pandas `read_html` backend | Yes (requirements.txt) | 6.0.1 | — |
| requests | FinViz fetch | Yes (requirements.txt) | 2.32.5 | — |
| beautifulsoup4 | FinViz HTML parsing | Yes (requirements.txt) | 4.13.5 | — |
| GitHub Actions runners (ubuntu-latest) | Nightly workflow | Yes | managed by GitHub | — |
| GITHUB_TOKEN | Commit-back to repo | Yes (auto-provisioned) | — | — |
| `.github/workflows/` directory | Workflow file | No (not yet created) | — | Must be created |
| `docs/projects/screener/` directory | data.json + index.html | No (not yet created) | — | Must be created |

**Missing dependencies with no fallback:**
- None that block execution. All runtime packages are in requirements.txt.

**Missing dependencies that must be created:**
- `.github/workflows/` directory — needed before workflow YAML can exist.
- `docs/projects/screener/` directory — needed before screener files and data.json can exist.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None installed — browser smoke tests and local Python invocation |
| Config file | None |
| Quick run command | `python scripts/fetch_sp500.py --limit 3` (dry-run with 3 tickers) |
| Full suite command | Manual browser walkthrough: home page -> screener card -> sort/filter -> row click -> calculator |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHOW-04 | Screener card appears on home page | smoke | Open `docs/index.html` in browser, verify card visible | No — Wave 0 |
| NAV-03 | Click screener card loads screener in-page | smoke | Click card, verify screener iframe loads | No — Wave 0 |
| SCREENER-01 | Table renders with all stocks, default sort by discount | smoke | Open screener page, verify row count and sort | No — Wave 0 |
| SCREENER-01 | Search filter narrows rows | smoke | Type "Apple" in search, verify row count decreases | No — Wave 0 |
| SCREENER-01 | Sector dropdown filters table | smoke | Select a sector, verify only that sector's rows show | No — Wave 0 |
| SCREENER-02 | Batch script produces valid data.json | unit | `python scripts/fetch_sp500.py --limit 3` exits 0, writes valid JSON | No — Wave 0 |
| SCREENER-02 | DCF formula matches calculator | manual | Fetch AAPL via calculator, compare to batch script output for AAPL | manual-only |
| SCREENER-03 | Row click sends postMessage to parent | smoke | Click a row, verify calculator opens with ticker pre-filled | No — Wave 0 |
| SCREENER-04 | GitHub Actions workflow runs without error | smoke | `workflow_dispatch` manual trigger, verify data.json commit appears | manual-only |

### Sampling Rate
- **Per task commit:** Open the affected file in browser; verify the specific change renders correctly.
- **Per wave merge:** Full browser walkthrough — home page to screener card click to screener loads to sort/filter to row click to calculator pre-filled.
- **Phase gate:** Full walkthrough green plus one successful GitHub Actions workflow run before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `docs/projects/screener/` directory — must exist before screener files
- [ ] `.github/workflows/` directory — must exist before workflow YAML
- [ ] `scripts/fetch_sp500.py` — batch script with `--limit N` flag for local testing
- [ ] `docs/projects/screener/data.json` — seed/empty file (`{"updated_at": null, "stocks": []}`) so screener index.html can load without 404 before first Actions run

---

## Sources

### Primary (HIGH confidence)

- Existing codebase: `api_server.py`, `yahoo_finance_fetcher.py`, `finviz_fetcher.py` — verified DCF logic structure, data fetching patterns, module interface
- Existing codebase: `docs/index.html` — verified card pattern at line 201, hash routing at lines 247-316, projects object at line 232
- Existing codebase: `docs/projects/calculator/index.html` — verified `tickerInput` element ID at line 498
- Existing codebase: `requirements.txt` — confirmed package versions
- GitHub Actions official documentation — workflow syntax, `GITHUB_TOKEN` permissions, commit-back pattern

### Secondary (MEDIUM confidence)

- GitHub Actions `permissions: contents: write` — widely documented pattern; required for commit-back since 2021 GitHub default permissions tightening
- `pandas.read_html` with `lxml` backend — standard pattern; `lxml` already confirmed in requirements.txt

### Tertiary (LOW confidence)

- FinViz blocking GitHub Actions IPs — based on known community-observed behavior of FinViz rate-limiting data center IPs; not formally documented by FinViz. Batch script is designed to be resilient regardless.
- GitHub disabling scheduled workflows after 60 days of inactivity — documented in GitHub docs; exact current threshold may vary.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages in requirements.txt, versions verified directly from file
- Architecture: HIGH — patterns derived directly from reading existing codebase files
- GitHub Actions workflow: HIGH — commit-back pattern is well-documented; only uncertainty is branch protection settings on the specific repo
- DCF formula: MEDIUM — structure is clear from `api_server.py`; exact implementation requires reading the calculator JS before coding
- FinViz behavior in Actions: LOW — behavior-based observation, not formally documented

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack; yfinance API changes are the main risk within this window)
