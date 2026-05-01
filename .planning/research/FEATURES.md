# Features Research: Inside Bar Pattern Scanner

**Domain:** Technical analysis pattern scanner with CV detection and backtesting
**Researched:** 2026-05-01
**Downstream consumer:** Roadmap phase planning — table stakes vs differentiators vs anti-features for the screener page and per-stock drilldown

---

## Existing Screener Baseline (This Codebase)

The S&P 500 DCF screener already establishes the interaction model this scanner will follow:
- Static `data.json` consumed client-side — no backend call from browser
- Controls row: text search + dropdown filters + row count
- Sortable table with sticky header, clickable rows
- Drilldown page via URL param (`stock.html?ticker=X`)
- Dark theme: `#080c12` bg, `#0f1520` surface, `#58a6ff` accent, DM Mono + DM Sans + Syne
- Sticky top-nav with breadcrumb + back button
- Panel components with `panel-header` / `panel-body` pattern
- TradingView embedded chart on drilldown

The pattern scanner should follow this structure so it feels like a sister tool to the screener, not a foreign page.

---

## Table Stakes

Features a visitor to a pattern scanner page expects to see. Missing these makes the page feel incomplete or unprofessional.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Sortable table with pattern rows** | Core mechanic — every scanner (Finviz, TradingView) has a click-to-sort column header | Low | Mirror existing screener table pattern exactly |
| **Ticker + company name columns** | Identification — users need to know what stock they're looking at | Low | Reuse DCF screener `td-ticker` / `td-company` styles |
| **Detection date column** | Context — a pattern from 3 days ago is actionable; one from 6 months ago is historical | Low | Formatted as relative ("2 days ago") + tooltip with absolute date |
| **Current price column** | First question traders ask after seeing a setup | Low | Pull from `data.json` — can be same nightly batch |
| **Sector filter dropdown** | Standard screener mechanic — traders segment by sector (e.g., "only Tech") | Low | Already exists in screener; reuse |
| **Text search by ticker/company** | Fast lookup — "is AAPL in the list?" | Low | Already exists in screener; reuse |
| **Row count / results count** | Transparency — "Showing 12 of 47 results" | Low | Already exists in screener |
| **Clickable row → drilldown** | Expected navigation pattern established by DCF screener | Low | Deep-link to `pattern.html?ticker=X` |
| **Loading + error states** | Professional polish — blank screen on load or silent failure is broken-looking | Low | Already exists in screener; reuse |
| **Last updated timestamp** | Static data credibility — visitor needs to know the scan was run recently | Low | Already exists in screener |
| **Confidence score column** | Unique to CV-based detection — shows model certainty (0–1 or %) | Low | Required because YOLOv8 produces a confidence float |
| **Pattern label column** | Not all rows are the same confirmation type — Pin Bar / Mark Up / Ice-cream | Low | Short label + tooltip explaining the type |
| **Mobile column hiding** | Sector, method, confidence can hide on narrow viewports | Low | Mirror existing screener `@media (max-width: 640px)` pattern |

---

## Differentiators

Features that are not expected but significantly increase perceived value — especially relevant to the portfolio angle where the audience is evaluating Jun Xian's thinking.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **YOLOv8 confidence badge with color tier** | Makes the CV detection tangible and legible — "High / Medium / Low" with green/yellow/red tells a non-technical visitor what the model is saying | Low | Derived from confidence float; thresholds: ≥0.8 High, 0.6–0.8 Medium, <0.6 Low |
| **Annotated chart image on drilldown** | The actual bounding-box detection output — shows YOLOv8 drew a box around the pattern. This is the single most compelling visual proof of CV at work | Medium | Render and save annotated chart image in batch pipeline; display as `<img>` on drilldown |
| **Backtest stat summary on drilldown** | Win rate + avg return + median hold period per detected setup — connects detection to forward outcomes | Medium | Pre-computed in batch; 3 numbers displayed as stat cards |
| **Pattern diagram / legend** | A small inline diagram showing the 5-bar structure (mother bar, inside bar, break-below, confirmation bar) so a visitor unfamiliar with the pattern can immediately understand what they're looking at | Low | Static SVG or PNG; show once above the table or in a collapsible "How it works" section |
| **SMA context badges on drilldown** | Show which SMA the setup was detected near (20-SMA / 50-SMA), one of the defined filter conditions — demonstrates that the scanner encodes real TA domain logic, not just shape detection | Low | Computed in batch; displayed as badge on drilldown hero row |
| **Cross-link to DCF screener drilldown** | "See DCF valuation for this stock →" link on the pattern drilldown — creates a narrative bridge between the two tools (pattern entry point meets fundamental context) | Low | Already have the screener data; add one anchor link if ticker exists in `data.json` |
| **Historical detections list on drilldown** | "Previous setups detected for this ticker" — shows past instances with dates and whether they triggered (outcome badge) | Medium | Requires storing detection history per ticker in `data.json`, not just current detections |
| **Uptrend context indicator** | Show the HH/HL count and 20-SMA slope direction that qualified this stock — makes the filter conditions visible rather than invisible | Low | Pre-computed in batch; add 2 fields to `data.json` |

---

## Anti-Features

Features that would clutter, bloat, or misrepresent the project. Explicitly avoid these.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time or streaming detection** | Pattern is defined on daily bars — real-time adds backend complexity with no analytical value. The setup is either present on close or it isn't | Nightly batch is correct; show last-updated timestamp prominently |
| **Buy/sell signal labels or price targets** | This is a research/demonstration portfolio, not financial advice. Explicit signal labels create legal ambiguity and false authority | Show "setup detected" framing; let the stats speak for themselves |
| **Filtering by confidence threshold (slider)** | Adds UI complexity. At this stage the scanner has few enough results that threshold filtering isn't needed. The confidence column already lets visitors sort | Keep it: sort by confidence column instead |
| **Alert / notification system** | Requires auth, backend state, email integration — entirely out of scope for a static portfolio project | Not applicable; this is a read-only screener |
| **Editable pattern parameters (bar count, confirmation type)** | Turns a scanner into a pattern editor. The defined ruleset is the point — encoding a specific setup is a demonstration of domain knowledge | Show the ruleset description in the "How it works" section; don't parameterise it |
| **Comparing this pattern to other patterns** | Scope creep — implies building a multi-pattern framework. The milestone is one pattern done well | Document the architecture so additional patterns could be added in a future milestone |
| **Heatmap or grid view** | Adds visualization complexity without improving decision-making for this pattern type. The table is the right format for a list of current setups | Stick to the table; annotated chart image on drilldown is the visual payload |
| **P&L simulation or equity curve** | Requires trade-sizing logic and backtesting assumptions beyond win rate/return. Easily misleading without careful caveats | Show win rate + avg return as pre-computed stats; no curve |

---

## Backtest Display Patterns

What makes a backtesting results display useful vs. cluttered — informed by what the existing screener drilldown already does well with its stats grid.

### Useful patterns

**Stat cards over tables for summary stats.** Win rate, avg return, and median hold period are 3 numbers. Put them in a `stats-grid` style hero row (same pattern as the screener's `hero-iv-row`). Don't put them in a table — tables suggest more rows than you have.

**Context labels.** "Win rate: 63% (over 47 setups, 10-year backtest)" is informative. "Win rate: 63%" without the denominator is meaningless. The parenthetical matters.

**Outcome coloring.** Win rate ≥ 60% → green. 50–60% → yellow. < 50% → red. Mirrors the existing badge color system.

**Distinguishing backtest scope from current detection.** A single section header like "Historical Performance (10-year backtest)" separates it clearly from "Current Detection" stats.

**Entry/exit definition disclosure.** One line: "Entry: close of confirmation bar. Exit: 3 ATR take-profit or stop at mother-bar low." Prevents the question "how were these measured?" This builds trust.

### Cluttered patterns (avoid)

**Month-by-month or year-by-year breakdown table.** Too much data for a drilldown sidebar. Goes in a research doc, not a portfolio page.

**Equity curve chart on drilldown.** A single line chart showing hypothetical account growth encourages the reader to extrapolate. Keep stats to summary only.

**Statistical significance p-value or confidence intervals.** Correct in a research paper, confusing to a non-quant portfolio visitor. The win rate denominator (N setups) is enough context.

**Multiple backtest parameter comparisons.** Don't show "with vs. without uptrend filter" side by side — this reads as uncertainty about the model, not depth of analysis. Show the results of the best-defined configuration.

---

## Per-Stock Drilldown Patterns

What a drilldown for a pattern scanner typically shows, mapped to what makes sense for this specific setup.

### Section structure (recommended order)

**1. Hero section — detection identity**
Mirrors the existing `stock.html` hero. Contains:
- Ticker + company name + exchange tag
- Current price + detection date
- Pattern label badge (e.g., "Pin Bar Confirmation") + confidence tier badge
- SMA context badge (e.g., "Near 20-SMA")
- TradingView chart in hero-right (same pattern as DCF screener drilldown) — gives instant price context

**2. Annotated detection image**
The YOLOv8 bounding-box output image. This is the distinctive visual payload of the CV angle. Single panel, full-width or two-column with the chart. Labeled with the detection window (5-bar window dates). Caption notes algorithmic vs. CV detection where applicable.

**3. Pattern anatomy breakdown**
A small labeled breakdown of the 5-bar pattern in this specific detection: Bar 1 (mother bar) date + OHLC, Bar 2 (inside bar) date + OHLC, Break-below bar date, Confirmation bar type + date. This is the forensic view — "here is exactly what the algorithm saw." Use the `stat-table` component pattern from `stock.html`.

**4. Uptrend context**
Higher-high/higher-low count, 20-SMA slope, whether price is above 50-SMA at detection. Three fields; use `iv-item` style inline row or a single `stat-row` section.

**5. Historical performance panel**
3 stat cards: Win rate (N setups), Avg return %, Median hold (bars). Defined entry/exit method as a single italic caption below. Use green/yellow/red coloring based on win rate threshold.

**6. Historical detections (optional, if stored)**
Compact table of past detections for this ticker: date detected, confirmation type, outcome (triggered / not triggered), return if triggered. This is only worth building if the batch pipeline stores history; if it only stores current detections it can be deferred.

**7. Cross-links footer**
"Open in DCF Screener →" if ticker exists in screener data. "View full screener →" back to index. Mirrors the existing `btn-calc` CTA pattern.

### Complexity notes

- Hero + TradingView chart: Low — direct reuse of `stock.html` hero pattern
- Annotated image panel: Medium — requires batch pipeline to save annotated images and store image paths in `data.json`
- Pattern anatomy breakdown: Low — all data already in `data.json` detection record
- Uptrend context: Low — 2 fields added to `data.json`
- Historical performance: Low — 3 fields pre-computed in backtesting phase
- Historical detections table: Medium — requires per-ticker detection history array in `data.json`; deferred to later iteration

---

## Dependencies on Existing Screener Patterns

| Pattern Scanner Element | Reuse From DCF Screener |
|------------------------|------------------------|
| Dark theme CSS variables | `stock.html` `:root` block — copy verbatim |
| Sticky table header + sort indicators | `screener/index.html` table + sort logic |
| Text search + sector filter + row count | `screener/index.html` `.controls` block |
| Clickable row → URL param navigation | `screener/index.html` row click handler |
| Top nav (logo, breadcrumb, back button) | `stock.html` `.top-nav` block |
| Hero section (ticker, price, badges) | `stock.html` `.hero` + `.hero-grid` block |
| TradingView chart embed | `stock.html` `.hero-right` TradingView widget |
| Stat table component | `stock.html` `.stat-table` / `.stats-grid` |
| Panel component (header dot + title + body) | `stock.html` `.panel` / `.panel-header` |
| Badge components (color tiers) | Both files — confidence badge maps to same green/yellow/red |
| `fadeUp` animation + stagger | `stock.html` `.anim` classes |
| Loading + error states | `screener/index.html` `#loading-state` / `#error-state` |
| Last-updated timestamp | `screener/index.html` `displayUpdatedAt()` |
| Static JSON data pipeline | `data.json` → fetch on load → client-side filter/sort |
| Mobile column hiding | `screener/index.html` `@media (max-width: 640px)` |

The pattern scanner page is essentially a new `index.html` in `docs/projects/patterns/` that inherits the `stock.html` visual language but replaces valuation columns with detection columns. Minimal new CSS is needed.

---

## MVP Prioritisation

**Build in MVP (screener page):**
1. Table with: ticker, company, sector, detection date, confirmation type, confidence score badge, current price
2. Filters: sector dropdown, confidence tier dropdown (High/Med/Low), text search
3. Sort: all columns, default sort by detection date descending
4. Row click → drilldown
5. Last-updated timestamp + row count
6. Pattern legend / "How it works" callout above the table (static, inline)

**Build in MVP (drilldown page):**
1. Hero: ticker, company, price, detection date, pattern type badge, confidence badge, SMA context badge
2. TradingView chart (reuse)
3. Annotated detection image panel
4. Pattern anatomy table (5-bar breakdown)
5. Historical performance: 3 stat cards (win rate, avg return, hold period) + entry/exit caption
6. Cross-link footer to DCF screener drilldown if ticker in screener data

**Defer to later iteration:**
- Historical detections per ticker (requires storing detection history in pipeline)
- Uptrend context panel (low value for MVP; the filter ran — reader can assume it passed)
- Confidence threshold slider filter (sort by confidence column suffices)

---

## AI + CV Differentiators for Portfolio Storytelling

This project sits at the intersection of domain knowledge (the specific inside bar spring ruleset is not a generic TA pattern — it has a defined confirmation taxonomy) and computer vision (YOLOv8 applied to chart images). Both angles deserve surface area on the page.

**Make the CV angle tangible:** The annotated image is the proof. A bounding box drawn by a model that learned to find patterns from labeled chart images is visually distinct from algorithmic detection. Show the image prominently.

**Make the domain knowledge angle tangible:** The pattern legend and anatomy breakdown show that the pattern definition is deliberate. Three specific confirmation types with precise bar range thresholds are not accidental — they encode a thesis about how price action traps and flushes sellers.

**Make the AI angle tangible via the backtest:** The question "does it work?" is what separates a tool from a toy. Win rate and avg return on 10 years of data answers it. A portfolio visitor evaluating Jun Xian as a developer should see: (1) I can train a CV model, (2) I can define a rule precisely enough to backtest it, (3) the model's output has a documented historical edge. Those three facts together are the value demonstration.

---

*Confidence: HIGH on table stakes and reuse patterns (based on direct examination of existing codebase). MEDIUM on backtest display patterns (domain knowledge + general TA tool conventions). MEDIUM on differentiator prioritization (based on portfolio positioning judgment, not external sources verified).*
