# Phase 5: S&P 500 Stock Screener Page - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a second portfolio project: an S&P 500 stock screener that shows pre-calculated DCF intrinsic values for all ~500 S&P 500 stocks. Visitors arrive at the home page, click the screener project card, and the screener loads in-page via the existing hash routing + iframe pattern. The screener displays a sortable, searchable, sector-filterable table of S&P 500 stocks with their current price, intrinsic value, discount %, valuation method, and a valuation label. Clicking any row navigates the parent page to the intrinsic value calculator with that ticker pre-filled.

A nightly GitHub Actions workflow fetches all ~500 stocks' data and commits a static `data.json` snapshot to the repo. The screener frontend reads this static file at runtime — no Render API call at runtime.

This phase also adds the screener project card to the portfolio home page (`docs/index.html`) and wires it into the existing hash navigation.

</domain>

<decisions>
## Implementation Decisions

### Data Pipeline

- **D-01:** GitHub Actions cron job runs nightly. The job runs a Python script in-workflow that imports the existing `yahoo_finance_fetcher.py` and `finviz_fetcher.py` modules directly (not via the Render API). It reuses the same DCF calculation logic from `api_server.py`.
- **D-02:** S&P 500 constituent list is fetched dynamically from Wikipedia via `pandas.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')`. Updates automatically after quarterly rebalances. No hardcoded ticker list.
- **D-03:** Wikipedia tickers are normalized to Yahoo Finance format before fetching (e.g., `BRK.B` → `BRK-B`, `BF.B` → `BF-B`). The normalized Yahoo-format ticker is stored in `data.json` so the screener and calculator always use the same ticker format.
- **D-04:** The snapshot is stored as `docs/projects/screener/data.json` and auto-committed to the `main` branch by the GitHub Actions workflow. The screener frontend fetches this static file directly from GitHub Pages — zero latency, no backend call at runtime.
- **D-05:** Metrics stored per stock in `data.json`: `ticker`, `company_name`, `sector`, `current_price`, `intrinsic_value`, `discount_pct`, `method` (ocf/fcf), `valuation_label`. Any stock where the DCF calculation fails or returns null is stored with `null` intrinsic value and `valuation_label: "N/A"`.

### DCF Calculation

- **D-06:** Use the same auto-selection logic as `api_server.py`: OCF by default; switch to FCF if negative earnings or inflated OCF (>1.5× net income). `method` field records which was used.
- **D-07:** The intrinsic value calculation uses the same growth rate priority chain as `api_server.py`: FinViz 5Y EPS estimate → Yahoo CF historical → Yahoo EPS historical → 5% default. Same discount rate lookup table from beta.

### Screener Features

- **D-08:** Show all ~500 stocks in the table by default on load (render all rows at once — no pagination).
- **D-09:** Search: filter rows by ticker symbol or company name (case-insensitive substring match).
- **D-10:** Sector filter: dropdown populated from unique sectors in `data.json`. Selecting a sector filters the table to that sector only.
- **D-11:** Search and sector filter compose — a user can search "Apple" within "Technology".

### Display Format

- **D-12:** Sortable table. Columns: Ticker | Company | Sector | Price | Intrinsic Value | Discount % | Method | Valuation Label. Clicking a column header sorts ascending; clicking again sorts descending.
- **D-13:** Default sort: by Discount % descending (most undervalued first).
- **D-14:** Valuation label thresholds (based on discount % = (intrinsic_value - current_price) / intrinsic_value × 100):
  - **Highly Undervalued**: discount % > 30% (stock trades >30% below IV)
  - **Slightly Undervalued**: discount % 10–30%
  - **Fairly Valued**: discount % −10% to +10%
  - **Slightly Overvalued**: discount % −10% to −30% (stock trades 10–30% above IV)
  - **Highly Overvalued**: discount % < −30%
  - **N/A**: DCF calculation not applicable (negative earnings + negative FCF)
- **D-15:** Valuation label shown as a colour-coded badge in the table (green for undervalued, grey for fairly valued, red for overvalued) matching the existing dark theme palette.

### Calculator Link-Through

- **D-16:** Clicking a stock row navigates to the intrinsic value calculator with the ticker pre-filled. Implementation: the screener iframe calls `window.parent.postMessage({ type: 'navigate', project: 'calculator', ticker: 'AAPL' }, '*')`. The parent page (`docs/index.html`) listens for this message, navigates to `#calculator`, and passes the ticker to the calculator iframe via the URL: `projects/calculator/index.html?ticker=AAPL`.
- **D-17:** The calculator frontend (`docs/projects/calculator/index.html`) reads `?ticker=` from `location.search` on load and auto-fills the ticker input field (and optionally auto-submits the fetch).

### Portfolio Integration

- **D-18:** Add screener project card to `docs/index.html` projects grid. Card format: same `.card[data-project]` pattern as the calculator card. Tags: `Python`, `JavaScript`, `Finance`, `Data`.
- **D-19:** Register screener in the `projects` JS object in `docs/index.html`: `screener: 'projects/screener/index.html'`.
- **D-20:** Screener project directory: `docs/projects/screener/`. Contains `index.html` and `data.json` (the latter committed by GitHub Actions).

### Styling

- **D-21:** Screener `index.html` uses the same dark-theme CSS variables as the portfolio (`--bg: #0d1117`, `--surface: #161b22`, `--border: #30363d`, `--accent: #58a6ff`, `--text: #c9d1d9`, `--text-bright: #f0f6fc`, `--text-dim: #8b949e`). Vanilla JavaScript, no framework.

### Claude's Discretion

- Table row hover state, sticky header behaviour, mobile table responsiveness (horizontal scroll or column hiding) — standard patterns, Claude decides.
- Exact badge colour values for valuation labels (must remain legible on `--surface` background).
- GitHub Actions workflow name, trigger time (UTC), and Python version.
- Error state UI when `data.json` fails to load.
- Last-updated timestamp display (show when data was last refreshed).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Project Structure
- `docs/index.html` — Portfolio home page; contains the card grid, hash routing JS, and `projects` object. New screener card and route entry go here.
- `docs/projects/calculator/index.html` — Existing calculator project page; reference for iframe-hosted project structure and how `?ticker=` param could be received.

### Existing Backend
- `api_server.py` — DCF calculation logic, recommended_method selection, beta_to_discount_rate lookup table, growth rate priority chain. The nightly script reuses this logic.
- `yahoo_finance_fetcher.py` — Yahoo Finance data fetching module used by the nightly script.
- `finviz_fetcher.py` — FinViz data fetching module used by the nightly script.

### Project State
- `.planning/STATE.md` — Project decisions and prior phase history.
- `.planning/ROADMAP.md` — Phase 5 goal and context.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.card[data-project]` pattern in `docs/index.html:201` — add screener card using identical markup
- `projects` JS object in `docs/index.html:232` — add `screener: 'projects/screener/index.html'`
- `window.addEventListener('hashchange', navigate)` in `docs/index.html` — parent navigation already handles hash changes; screener uses `postMessage` to trigger a hash change
- `api_server.py` DCF logic (lines 55–235) — copy/adapt for the nightly batch script

### Established Patterns
- Static file hosting via GitHub Pages from `docs/` — `data.json` goes in `docs/projects/screener/`
- Iframe-per-project pattern: project loads in `<section id="project-view">` via dynamically created `<iframe>`
- Dark theme CSS variables defined in `docs/index.html` — screener `index.html` re-declares or imports the same set

### Integration Points
- `postMessage` from screener iframe → parent `docs/index.html` for calculator link-through
- `?ticker=` query param on `docs/projects/calculator/index.html` for pre-filling the calculator

</code_context>

<specifics>
## Specific Ideas

- The screener is the most compelling when sorted by Discount % descending by default — visitors immediately see the most undervalued S&P 500 stocks per DCF.
- The link-through from screener → calculator creates a workflow: "screen all 500 → find interesting stock → see the full DCF breakdown." This is the key differentiator of the screener vs. a plain price list.
- The ticker normalization (BRK.B → BRK-B) must happen in the GitHub Actions script before any Yahoo Finance fetch, not after.

</specifics>

<deferred>
## Deferred Ideas

- Additional screening metrics (P/E, market cap, dividend yield, beta, revenue growth) — data-only extension, add in a future phase
- Advanced multi-criteria filtering (e.g., "Technology sector AND discount > 20%") — add in a future phase
- Historical intrinsic value trend per stock — future phase
- Dark/light mode toggle — listed in v2 requirements (POLISH-01)

</deferred>

---

*Phase: 05-s-p-500-stock-screener-page*
*Context gathered: 2026-04-05*
