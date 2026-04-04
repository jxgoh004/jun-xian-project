# Phase 5: S&P 500 Stock Screener Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Session date:** 2026-04-05
**Areas discussed:** Data source, Screener features, Display format, Calculator link-through

---

## Area 1: Data source

**Q: Where does the screener get its data?**
Options: Extend Render API (Recommended) / Free public API / Static dataset
Selected: **Extend Render API**

**Q: Should the S&P 500 stock list be fetched dynamically or hardcoded?**
Options: Hardcoded list / Fetch dynamically
Selected: **Fetch dynamically** — user doesn't want to manually check quarterly rebalances
User note: "I want to make it dynamic so that I don't have to check every quarter if a stock has been replaced. But I'm not sure about the need to add a network call. Can this be done simply by taking from either Yahoo Finance or FinViz instead?"
Clarification provided: Wikipedia via `pd.read_html` — single request, no API key, same ticker format as Yahoo Finance.

**Q: For the dynamic constituent list, which source?**
Options: Wikipedia via pandas (Recommended) / FinViz screener endpoint
Selected: **Wikipedia via pandas**

**Q: How should the screener handle the 30–60s bulk fetch?**
Options: Load on demand with caching / Pre-built nightly snapshot / Paginated
Selected: **Pre-built nightly snapshot**

**Q: What metrics should be fetched per stock?**
Options: Price + market cap / P/E + sector / Revenue + earnings growth / Dividend yield + beta
Selected: **Just price for now** (user freetext)

**Q: Where does the nightly snapshot job run?**
Options: GitHub Actions cron (Recommended) / Render cron
Selected: **GitHub Actions cron**

**Q: Where is the snapshot JSON stored?**
Options: Committed to repo (Recommended) / Served from Render
Selected: **Committed to repo** → `docs/projects/screener/data.json`

**User concern:** "Since stock tickers are taken from different sources, will they definitely work with the calculator?"
Clarification: Wikipedia uses standard NYSE/NASDAQ symbols matching Yahoo Finance. One known exception (BRK.B → BRK-B) handled by ticker normalization in the nightly script.

---

## Area 2: Screener features

**Q: What's the primary way visitors use the screener?**
Options: Search by ticker/name / Filter by sector / Sort by price
Selected: **Both search (1) and sector filter (2)**
(Implies data.json must include sector, not just price.)

**Q: Should all stocks show by default or start empty?**
Options: Show all stocks, filterable (Recommended) / Start empty, search-driven
Selected: **Show all stocks, filterable**

---

## Area 3: Display format

**Q: How are stocks displayed?**
Options: Sortable table (Recommended) / Card grid
Selected: **Sortable table**

**Q: How many rows visible at once?**
Options: Paginated / Infinite scroll / All at once
Selected: **All at once**

---

## Area 4: Calculator link-through

**User message (key pivot):** "I think you are misunderstanding something. I want the page to already populate the intrinsic values of all the stocks fetched. However, users can still click into the stock row to navigate to the calculator with the ticker pre-filled so that they can see the values used to calculate the intrinsic value."
Result: The nightly snapshot must include full DCF intrinsic value calculation per stock, not just prices. Columns expanded accordingly.

**Q: What columns does the screener table show?**
Options: Ticker, Company, Price, IV, Discount% / ...with Sector
Selected: **Ticker, Company, Sector, Price, IV, Discount%, Method, Valuation Label** (user freetext)

**Q: Which DCF method for bulk calculation?**
Options: Same auto-selection / OCF only / Both columns
Selected: **Same auto-selection as calculator**

**Q: Valuation label thresholds?**
Options: Standard margin of safety / Aggressive / Custom
Selected: **Standard margin of safety**
Thresholds: Highly Undervalued >30%, Slightly Undervalued 10–30%, Fairly Valued ±10%, Slightly Overvalued −10 to −30%, Highly Overvalued < −30%.

**Q: Can users navigate to calculator from a stock row?**
Selected: **Yes — click row to open in calculator**

**Q: How does link-through navigate?**
Options: Hash navigation on parent page (Recommended) / New tab
Selected: **Hash navigation on parent page**
Implementation: screener iframe → `postMessage` → parent switches to calculator iframe with `?ticker=`.

---

*Discussion completed: 2026-04-05*
