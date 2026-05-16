# Phase 11: Frontend - Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 5 (2 new HTML, 1 new PNG asset, 2 modified existing files)
**Analogs found:** 5 / 5 (100% — phase is a pure recombination of existing pages)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/projects/patterns/index.html` (NEW) | page (table/screener) | fetch-then-render (client-side filter/sort) | `docs/projects/screener/index.html` (707 lines) | **exact** — clone skeleton; only column set, badge variants, filter chips, and SVG legend differ |
| `docs/projects/patterns/stock.html` (NEW) | page (drilldown) | fetch-then-render (single ticker via querystring) | `docs/projects/screener/stock.html` (1809 lines) | **exact** — clone skeleton; replace financial snapshot/spider with annotated PNG + 5-bar anatomy + resolution + 3-up stat cards |
| `docs/projects/patterns/og-image.png` (NEW) | static asset (social-card image) | static binary | `docs/projects/calculator/thumbnail.png` (referenced as `og:image` by DCF screener line 12) | role-match — same shape (≥1200×630 PNG); content sourced from one annotated chart in `docs/projects/patterns/charts/*.png` |
| `docs/index.html` (MODIFIED) | portfolio shell | hash-routed iframe loader | self (lines 357–391 card markup; lines 406–409 `projects` registry; lines 423–497 router) | **exact** — additive only, no logic changes |
| `docs/sitemap.xml` (MODIFIED) | static SEO manifest | XML | self (3 existing `<url>` entries) | **exact** — append two entries |

---

## Pattern Assignments

### `docs/projects/patterns/index.html` (page, GitHub-blue screener)

**Analog:** `docs/projects/screener/index.html` (707 lines, verified). **Mirror line-for-line; swap content only.**

**Meta + SEO stack pattern** (analog lines 6–18) — adapt strings, keep structure verbatim:
```html
<title>S&amp;P 500 Intrinsic Value Screener — DCF Analysis | Goh Jun Xian</title>
<meta name="description" content="...">
<meta property="og:type" content="website">
<meta property="og:url" content="https://jxgoh004.github.io/jun-xian-project/projects/screener/">
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:image" content="https://jxgoh004.github.io/jun-xian-project/projects/calculator/thumbnail.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="...">
<meta name="twitter:description" content="...">
<meta name="twitter:image" content="...">
<link rel="canonical" href="...">
<meta name="theme-color" content="#0d1117">
```
For patterns: substitute the title/description per UI-SPEC Copywriting Contract; flip `og:image` to `https://jxgoh004.github.io/jun-xian-project/projects/patterns/og-image.png`. **Note:** DCF reuses `calculator/thumbnail.png` as its og:image — patterns gets its own dedicated `og-image.png` per D-18.

**CSS token block pattern** (analog lines 19–31) — **copy verbatim**:
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --accent: #58a6ff;
  --text: #c9d1d9;
  --text-bright: #f0f6fc;
  --text-dim: #8b949e;
  --radius: 8px;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
}
```

**Header / back-link / subtitle pattern** (analog lines 41–71) — copy verbatim; only `<h1>` text and `#last-updated` content differ.

**Controls strip pattern** (analog lines 73–130, markup lines 350–367) — copy structure; replace moat-filter `<select>` with five status-filter `<button class="chip">` elements. Each chip carries `aria-pressed="true|false"`. Keep search input + sector select + row-count span verbatim.

**Sticky thead / sortable header pattern** (analog lines 138–174) — **copy verbatim**:
```css
.screener-table thead th {
  position: sticky;
  top: 0;
  background: var(--surface);
  border-bottom: 2px solid var(--border);
  z-index: 10;
  cursor: pointer;
  user-select: none;
  padding: 10px 12px;
  text-align: left;
  color: var(--text-dim);
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
.screener-table thead th[data-sort="asc"]::after  { content: ' \2191'; color: var(--accent); }
.screener-table thead th[data-sort="desc"]::after { content: ' \2193'; color: var(--accent); }
```

**Badge geometry pattern** (analog lines 213–256) — copy `.badge` base verbatim; **define new variants** (NOT reuse `.badge-highly-undervalued` etc.):
```css
.badge {
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  display: inline-block;
}
/* Pattern Quality tiers (D-02, D-03) — exact rgba alphas from analog */
.badge-quality-green   { background: rgba(63,185,80,0.15);   color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.badge-quality-yellow  { background: rgba(227,179,65,0.15);  color: #e3b341; border: 1px solid rgba(227,179,65,0.3); }
.badge-quality-red     { background: rgba(248,81,73,0.15);   color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
.badge-quality-na      { background: rgba(139,148,158,0.10); color: #8b949e; border: 1px solid rgba(139,148,158,0.2); }
/* Status pills (D-10) */
.badge-status-target   { background: rgba(63,185,80,0.15);   color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.badge-status-stop     { background: rgba(248,81,73,0.15);   color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
.badge-status-open     { background: rgba(88,166,255,0.15);  color: #58a6ff; border: 1px solid rgba(88,166,255,0.3); }
.badge-status-pending  { background: rgba(139,148,158,0.10); color: #8b949e; border: 1px solid rgba(139,148,158,0.2); }
```

**Loading / error state divs pattern** (analog lines 278–301, markup lines 369–376) — copy verbatim; add a new `#empty-state` div per D-16 and `#stale-banner` div per D-15.

**Accessibility utilities pattern** (analog lines 304–316) — **copy verbatim**:
```css
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

**Skip-nav link pattern** (analog line 342) — copy verbatim; change anchor target from `#table-wrap` to `#detection-table`:
```html
<a href="#detection-table" style="position:absolute;top:-100%;left:16px;z-index:10000;padding:8px 16px;background:var(--accent);color:#0d1117;font-weight:600;border-radius:8px;text-decoration:none;" onfocus="this.style.top='8px'" onblur="this.style.top='-100%'">Skip to detections</a>
```

**Mobile breakpoint pattern** (analog lines 319–338) — copy verbatim; adapt column hide classes (`.col-sector`, `.col-company` instead of `.col-method`, `.col-moat`).

**Fetch + render + sort + filter state machine** (analog lines 395–703) — clone the full JS structure; adaptations:
- Replace `stocks` array with `detections` array
- Default sort: `confirmation_date` desc (not `discount_pct`) per D-12
- Add `filterStatus` state for status chip filter (radio-style)
- Add chip-click handler (toggle `aria-pressed`, recompute `getFiltered()`)
- Row click navigates to `stock.html?ticker={TICKER}` (analog line 575–577 verbatim shape)
- Add tier function (RESEARCH Pitfall 8):
```js
function tierFor(yolo_conf) {
  if (yolo_conf === null || yolo_conf === undefined) return 'na';
  if (yolo_conf >= 0.50) return 'green';
  if (yolo_conf >= 0.25) return 'yellow';
  return 'red';
}
```
- Add stale-banner toggle (D-15): check `data.pipeline_status.completed === false` and `failed_count`
- Add empty-state toggle (D-16): `detections.length === 0` → show empty card, keep legend visible
- Status normalisation (RESEARCH Pitfall 5): `const status = (row.status || '').toLowerCase();`
- Back-link postMessage handler (analog lines 699–702) — copy verbatim:
```js
document.getElementById('back-to-portfolio').addEventListener('click', function (e) {
  e.preventDefault();
  window.parent.postMessage({ type: 'navigate', project: null }, '*');
});
```

**5-bar SVG legend block (NEW — only original visual)** — no analog. Inline `<svg viewBox="0 0 600 140">` per UI-SPEC §"5-Bar Legend SVG"; insert between `<header>` (or stale banner) and `.controls`. Below 480px viewport, hide via media query and show caption-only fallback (RESEARCH Pitfall 6).

---

### `docs/projects/patterns/stock.html` (page, analytical-dark drilldown)

**Analog:** `docs/projects/screener/stock.html` (1809 lines, verified).

**Static title pattern** (analog line 6 is `<title>Stock Overview</title>` — **DO NOT copy verbatim**; RESEARCH Pitfall 3 mandates a richer static title that survives crawler/JS-disabled environments):
```html
<title>Inside Bar Pattern Detail | Goh Jun Xian</title>
```
Then JS rewrites `document.title` post-fetch to `{TICKER} — {company_name} | Pattern Scanner` (mirrors analog line 1587).

**Google Fonts preconnect + stylesheet** (analog lines 8–10) — **copy verbatim**.

**Analytical-dark CSS token block** (analog lines 12–40) — **copy verbatim**:
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:           #080c12;
  --surface:      #0f1520;
  --surface2:     #161e2e;
  --surface3:     #1e2840;
  --border:       #1e2840;
  --border-mid:   #2a3550;
  --accent:       #58a6ff;
  --accent-dim:   #1f6feb;
  --accent-glow:  rgba(88,166,255,0.18);
  --green:        #3fb950;
  --green-bg:     rgba(63,185,80,0.08);
  --green-border: rgba(63,185,80,0.25);
  --yellow:       #e3b341;
  --yellow-bg:    rgba(227,179,65,0.08);
  --yellow-border:rgba(227,179,65,0.25);
  --red:          #f85149;
  --red-bg:       rgba(248,81,73,0.08);
  --red-border:   rgba(248,81,73,0.25);
  --text:         #a8b4c8;
  --text-dim:     #546278;
  --text-bright:  #e8edf5;
  --mono:         'DM Mono', monospace;
  --sans:         'DM Sans', sans-serif;
  --display:      'Syne', sans-serif;
  --radius:       12px;
}
```

**Dot-grid background pattern** (analog lines 44–62) — **copy verbatim**:
```css
body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
  background-image: radial-gradient(circle, #1e2840 1px, transparent 1px);
  background-size: 28px 28px;
  background-attachment: fixed;
}
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background: linear-gradient(160deg, rgba(8,12,18,0.97) 0%, rgba(8,12,18,0.93) 100%);
  pointer-events: none;
  z-index: 0;
}
body > * { position: relative; z-index: 1; }
```

**Top-nav pattern** (analog lines 67–127 CSS, lines 693–703 HTML) — **copy verbatim**; only the section text changes:
```html
<nav class="top-nav" aria-label="Page navigation">
  <div class="nav-logo">
    <div class="nav-logo-mark" aria-hidden="true">📈</div>
    Goh Jun Xian
  </div>
  <div class="nav-divider" aria-hidden="true"></div>
  <span class="nav-section">Patterns</span>
  <span class="nav-ticker-label" id="nav-ticker">—</span>
  <span class="nav-spacer"></span>
  <a href="index.html" class="btn-back">← Back to scanner</a>
</nav>
```
Native `<a href="index.html">` works in both iframed and direct-deep-link modes (RESEARCH Pitfall 4 — DO NOT use postMessage here).

**Hero band pattern** (analog lines 145–296 CSS, lines 715–736 HTML) — copy structure; **replace `.hero-right` chart-container with the status/quality/price pill stack**. Reuse glow variants (`glow-green` / `glow-blue` / `glow-yellow` / `glow-red`) driven by status (target→green, open→blue, pending→yellow, stop→red) instead of valuation label (analog lines 1592–1596).

**Chart-fallback pattern** (analog lines 285–296) — **copy verbatim** for TradingView graceful degradation.

**TradingView `initChart()` function** (analog lines 1535–1580) — **copy verbatim with ONE field flipped** per D-08:
```js
function initChart(sym) {
  var outer = document.getElementById('tv-chart');
  outer.innerHTML = '';
  var container = document.createElement('div');
  container.className = 'tradingview-widget-container';
  container.style.cssText = 'width:100%;height:100%;min-height:340px;';
  outer.appendChild(container);
  var widgetDiv = document.createElement('div');
  widgetDiv.className = 'tradingview-widget-container__widget';
  widgetDiv.style.cssText = 'width:100%;height:100%;min-height:340px;';
  container.appendChild(widgetDiv);
  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  script.async = true;
  var config = {
    autosize: true,
    symbol: sym.replace(/-/g, '.'),
    interval: 'D',                          // ← FLIP from analog's 'W' per D-08
    timezone: 'Etc/UTC',
    theme: 'dark',
    style: '1',
    locale: 'en',
    hide_top_toolbar: false,
    hide_legend: false,
    save_image: false,
    calendar: false,
    allow_symbol_change: false,
    backgroundColor: 'rgba(8,12,18,1)',
    gridColor: 'rgba(30,40,64,0.5)',
    support_host: 'https://www.tradingview.com'
  };
  script.textContent = JSON.stringify(config);
  script.onerror = function() {
    outer.innerHTML =
      '<div class="chart-fallback">' +
      '<span style="font-size:24px">📊</span>' +
      '<span>Chart unavailable offline</span>' +
      '</div>';
  };
  container.appendChild(script);
}
```

**Badge variants pattern** (analog lines 298–312) — copy `.badge` base; define pattern-specific variants (same colour vocabulary as screener `index.html` Pattern Quality + Status — keep names identical across both pattern pages for visual cohesion).

**Stat-table styling pattern** (analog lines 406–435) — adapt for the **5-bar OHLC anatomy table** (5 rows × 5 cols Date/O/H/L/C; DM Mono tabular-nums) and the **resolution card detail grid**:
```css
.stat-table { width: 100%; border-collapse: collapse; }
.stat-table tr:nth-child(even) td { background: rgba(30,40,64,0.35); }
.stat-table td {
  padding: 9px 14px;
  font-size: 13px;
  border-bottom: 1px solid rgba(30,40,64,0.5);
}
.stat-td-label { color: var(--accent); width: 58%; font-family: var(--sans); }
.stat-td-value { color: var(--text-bright); text-align: right; font-family: var(--mono); font-size: 12px; }
.stat-td-value.positive { color: var(--green); }
.stat-td-value.negative { color: var(--red); }
```

**Anatomy table block (NEW)** — reads `detection.bars[]` (5 OHLC bars) directly; left-column label per row: `Mother / Inside / Break / Confirm / Continuation` per UI-SPEC. No analog beyond the generic `.stat-table` pattern.

**Resolution card block (NEW)** — surface2 background, status-coloured outline (`1px solid var(--green|red|accent|text-dim)`), 12px radius. Headline derived from `status` + `entry_date` + `entry_price` + `exit_date` + `exit_price` + `hold_days` (NEVER read `exit_reason` — RESEARCH Pitfall 1). R-multiple format: `+0.53R` (signed, suffixed).

**3-up stat cards block (NEW)** — `display:grid; grid-template-columns: repeat(3,1fr); gap:16px;`. Each card: surface2 bg, 16–20px padding, 12px radius, label (DM Mono 11px uppercase) over value (DM Mono 28–32px / 500 / tabular-nums). Subtitle below the row shows fallback cut + N per D-13.

**Stats fallback chain (NEW JS)** — RESEARCH Pattern 4:
```js
function statsFor(detection, stats) {
  var key = detection.confirmation_type + (detection.is_spring ? '_spring' : '_extended');
  var floor = stats.n_floor || 10;
  var byTypeSpring = (stats.stats && stats.stats.by_type_x_spring) || {};
  var byType       = (stats.stats && stats.stats.by_confirmation_type) || {};
  var all          = (stats.stats && stats.stats.all) || null;
  var cells = [
    { cut: 'by_type_x_spring',    label: 'out-of-sample ' + key,                              data: byTypeSpring[key] },
    { cut: 'by_confirmation_type',label: 'out-of-sample ' + detection.confirmation_type,       data: byType[detection.confirmation_type] },
    { cut: 'all',                 label: 'out-of-sample all-type',                            data: all }
  ];
  for (var i = 0; i < cells.length; i++) {
    if (cells[i].data && cells[i].data.n_resolved >= floor) return cells[i];
  }
  return cells[cells.length - 1];  // last-resort 'all' even if n < floor
}
```

**DCF cross-link card (NEW)** — on-demand `fetch('../screener/data.json')` ONLY on drilldown (RESEARCH Pitfall 2: real size is 1.23 MB on disk / ~250 KB gzipped, NOT 800 KB). Check membership in `stocks[].ticker`; render card with `border: 1px solid var(--accent)` only on hit; silent absence otherwise.

**Annotated PNG hero (NEW)** — RESEARCH Pitfall 7 override: use `loading="eager" fetchpriority="high" decoding="async"` (NOT `loading="lazy"`) plus explicit `width`/`height` for CLS. This is the LCP candidate.

---

### `docs/projects/patterns/og-image.png` (static asset)

**Analog:** `docs/projects/calculator/thumbnail.png` (referenced by DCF screener as its `og:image` at line 12 of `docs/projects/screener/index.html`).

**Source material:** one polished, visually striking annotated chart from `docs/projects/patterns/charts/*.png` (42 candidates on disk today). Planner picks the cleanest textbook example (e.g., a green-tier setup like `APD_2026-04-20.png` since APD has the highest `yolo_conf` in the dataset).

**Spec:** ≥1200×630 PNG for LinkedIn/Twitter card rendering. Committed directly to `docs/projects/patterns/og-image.png`. No image-processing pipeline — direct export/copy of an existing chart, optionally upscaled.

---

### `docs/index.html` (MODIFIED — additive only)

**Analog:** self (existing DCF screener card at lines 357–369; existing `projects` registry at lines 406–409; existing iframe router at lines 423–497).

**Card markup pattern** (analog lines 357–369) — clone exact structure:
```html
<a href="#screener" class="card" data-project="screener"
     aria-label="Open S&P 500 Stock Screener project">
  <div class="card-thumbnail-placeholder" role="img" aria-label="S&P 500 Stock Screener preview"></div>
  <h2>S&amp;P 500 Stock Screener</h2>
  <p class="card-benefit">Find undervalued stocks before the crowd does</p>
  <p>DCF intrinsic values pre-calculated for every S&amp;P 500 company. Filter by sector, sort by discount, and jump straight to the full calculator.</p>
  <div class="tags" aria-label="Technologies used">
    <span class="tag">Python</span>
    <span class="tag">JavaScript</span>
    <span class="tag">Finance</span>
    <span class="tag">Data</span>
  </div>
</a>
```

**New card insertion** — insert **first** (top) in the `.projects` grid at line 356 (before the screener card on line 357). Card content per D-17 (UI-SPEC Copywriting Contract):
```html
<a href="#patterns" class="card" data-project="patterns"
     aria-label="Open Inside Bar Pattern Scanner project">
  <div class="card-thumbnail-placeholder" role="img" aria-label="Inside Bar Pattern Scanner preview"></div>
  <h2>Inside Bar Pattern Scanner</h2>
  <p class="card-benefit">AI-curated chart setups, updated every trading day</p>
  <p>Computer-vision-graded inside-bar-spring detections across the S&amp;P 500, with backtested outcomes per setup type.</p>
  <div class="tags" aria-label="Technologies used">
    <span class="tag">Python</span>
    <span class="tag">ONNX</span>
    <span class="tag">Computer Vision</span>
    <span class="tag">Finance</span>
  </div>
</a>
```

**Registry update** (analog lines 406–409) — current state:
```js
var projects = {
  calculator: 'projects/calculator/index.html',
  screener:   'projects/screener/index.html'
};
```
**Add one entry, preserve existing two:**
```js
var projects = {
  patterns:   'projects/patterns/index.html',
  calculator: 'projects/calculator/index.html',
  screener:   'projects/screener/index.html'
};
```

**Router logic** (analog lines 423–497) — **DO NOT MODIFY**. The existing `navigate()` function reads `projects[hash]` dynamically; adding the registry key is sufficient. The `postMessage` handler (lines 480–493) handles "back to portfolio" from any sub-page without modification.

---

### `docs/sitemap.xml` (MODIFIED — additive only)

**Analog:** self (existing 3 `<url>` entries, lines 3–17).

**Pattern** — copy the screener entry shape (`changefreq=daily, priority=0.8` since patterns data updates nightly like screener):
```xml
<url>
  <loc>https://jxgoh004.github.io/jun-xian-project/projects/patterns/</loc>
  <changefreq>daily</changefreq>
  <priority>0.8</priority>
</url>
<url>
  <loc>https://jxgoh004.github.io/jun-xian-project/projects/patterns/stock.html</loc>
  <changefreq>daily</changefreq>
  <priority>0.7</priority>
</url>
```
Insert before the closing `</urlset>` tag (line 18).

---

## Shared Patterns

### Accessibility utilities (sr-only + focus-visible)
**Source:** `docs/projects/screener/index.html` lines 304–316 (GitHub-blue) and `docs/projects/screener/stock.html` line 680 (analytical-dark).
**Apply to:** Both pattern HTML files. Copy `.sr-only` class verbatim; `:focus-visible` rule verbatim.

### Skip-nav link
**Source:** `docs/projects/screener/index.html` line 342.
**Apply to:** Both pattern HTML files. Change anchor target per page (`#detection-table` / `#detection-detail`); keep inline styles + onfocus/onblur verbatim.

### Badge geometry
**Source:** `docs/projects/screener/index.html` lines 213–220 (`.badge` base).
**Apply to:** Both pattern HTML files (Pattern Quality + Status pills + filter chips share geometry). Copy verbatim; define new colour-mapping variants per D-02/D-03/D-10.

### Loading / Error state divs
**Source:** `docs/projects/screener/index.html` lines 278–301 (CSS) + lines 369–376 (markup) + lines 623–659 (state-machine JS).
**Apply to:** Both pattern HTML files. Copy verbatim; extend with `#empty-state` (D-16) and `#stale-banner` (D-15) on the screener page.

### Single inline `<style>` + inline `<script>` convention
**Source:** All three existing project pages.
**Apply to:** Both pattern HTML files. NO external CSS files. NO bundler. NO module imports.

### postMessage back-navigation from sub-pages
**Source:** `docs/projects/screener/index.html` lines 699–702 (back-to-portfolio handler).
**Apply to:** `docs/projects/patterns/index.html` only — the screener page's `← Back to portfolio` link must postMessage `{type: 'navigate', project: null}` to the parent shell.
**Note:** `docs/projects/patterns/stock.html` does NOT use postMessage for "← Back to scanner" — it uses native `<a href="index.html">` (RESEARCH Pitfall 4 — handles both iframed and direct-deep-link modes).

### Status normalisation
**Source:** RESEARCH Pitfall 5.
**Apply to:** Every JS comparison against `row.status` on both pattern pages.
```js
const status = (row.status || '').toLowerCase();
```

### Tier function (Pattern Quality)
**Source:** RESEARCH Pitfall 8 + UI-SPEC §"Pattern Quality badge".
**Apply to:** Both pattern HTML files (screener row badge + drilldown hero pill).
```js
function tierFor(yolo_conf) {
  if (yolo_conf === null || yolo_conf === undefined) return 'na';
  if (yolo_conf >= 0.50) return 'green';
  if (yolo_conf >= 0.25) return 'yellow';
  return 'red';
}
```

### Derive exit copy from status (NOT exit_reason)
**Source:** RESEARCH Pitfall 1 (Phase 10 data.json has NO `exit_reason` field at the row level).
**Apply to:** `docs/projects/patterns/stock.html` resolution-card headline only.
```js
function exitCopy(row) {
  var s = (row.status || '').toLowerCase();
  if (s === 'target')  return 'Hit target at $' + Number(row.exit_price).toFixed(2) + ' on ' + row.exit_date;
  if (s === 'stop')    return 'Stopped out at $' + Number(row.exit_price).toFixed(2) + ' on ' + row.exit_date;
  if (s === 'open')    return 'Open trade — entered ' + row.entry_date + ', ' + row.hold_days + ' days held';
  if (s === 'pending') return 'Pending entry — confirmation just printed; entry at next open';
  return '—';
}
```

### LCP image (annotated PNG) eager-loading override
**Source:** RESEARCH Pitfall 7.
**Apply to:** `docs/projects/patterns/stock.html` annotated-PNG `<img>` only.
```html
<img src="charts/{TICKER}_{DATE}.png"
     loading="eager" fetchpriority="high" decoding="async"
     width="..." height="..."
     alt="Annotated 5-bar inside bar spring detection for {TICKER} on {confirmation_date}">
```
All OTHER images on both pages keep `loading="lazy"` per D-20.

---

## No Analog Found

| File / Component | Role | Reason | Planner Action |
|------------------|------|--------|----------------|
| 5-bar SVG legend block | inline diagram (visual component) | No existing inline SVG diagram in the codebase (only icon SVGs in nav/buttons; calculator may use Chart.js but that's a library, not inline) | Hand-roll per UI-SPEC §"5-Bar Legend SVG"; use vanilla `<svg viewBox="0 0 600 140">` with `<rect>` + `<line>` + `<text>` primitives, theme tokens for colour, `<title>` + `<desc>` for a11y. Below 480px viewport: hide SVG, show caption-only fallback. |
| Status filter chips (5-chip radio strip) | filter control | DCF screener uses `<select>` dropdowns for filters (sector, moat); no chip pattern exists yet | Hand-roll per UI-SPEC §"Status filter chips". Use real `<button>` elements (NOT `<div>`), `aria-pressed` for state, keyboard-focusable. Below 640px, collapse into a `<select>` matching DCF mobile breakpoint pattern. |
| Stale-data banner | inline notification | No banner/toast component exists in any portfolio page | Hand-roll per UI-SPEC §"Stale-data banner" — yellow palette (`#e3b341` / `rgba(227,179,65,0.15)` bg / `rgba(227,179,65,0.3)` border), 12px padding, same `--radius` as cards. Toggled by `data.pipeline_status.completed === false` on the screener page only. |
| 5-bar OHLC anatomy table | data display | Closest analog is `.stat-table` (analog lines 406–435) which is a generic 2-column key-value table; the 5×5 anatomy table is a different shape | Reuse `.stat-table` row striping + border styling; add 5 columns (Date / O / H / L / C); apply DM Mono + tabular-nums on numeric cells. Bar-name labels in left column or as `<tr>` headers. |
| Resolution card | status-coloured outlined panel | Generic `.panel` exists (analog lines 332–360) but no status-outline variant | Extend `.panel` pattern with 4 status-outline modifier classes: `.panel-target` (green outline), `.panel-stop` (red outline), `.panel-open` (blue accent outline), `.panel-pending` (text-dim outline). |
| 3-up backtest stat-card grid | metric display | DCF stock.html has spider chart + score rows + stat tables — none in a 3-up "big number" card format | Hand-roll per UI-SPEC §"Backtest stat cards". `display:grid; grid-template-columns: repeat(3, 1fr); gap:16px;`; each card surface2 bg, 12px radius, 16–20px padding; DM Mono value at 28–32px/500 over DM Mono 11px-uppercase label. |
| DCF cross-link card | navigation card | Top-of-page nav button exists but no inline cross-link card | Hand-roll: surface bg with `1px solid var(--accent)` border, 12px radius, single-line headline `View DCF analysis for {TICKER} →` as an `<a href="../screener/stock.html?ticker={TICKER}">`. Native anchor (works in both iframed and direct-deep-link modes). |

All NEW components above use **existing CSS tokens only** — no new palette variables. Geometry inherits from the established 8-point spacing scale + `--radius` token.

---

## Metadata

**Analog search scope:**
- `docs/projects/screener/index.html` (707 lines — full read for index analog)
- `docs/projects/screener/stock.html` (1809 lines — targeted reads at lines 1–130, 140–310, 680–740, 1525–1625)
- `docs/index.html` (lines 340–500 — card markup + projects registry + router)
- `docs/sitemap.xml` (full read — 18 lines)
- `docs/projects/screener/CLAUDE.md` (full read — project conventions)

**Files scanned:** 5 source files + 2 upstream context files (CONTEXT, RESEARCH) + 1 upstream UI contract (UI-SPEC).

**Pattern extraction date:** 2026-05-16.

**Critical observations:**
1. **Phase 11 is 95% verbatim reuse.** Only 7 components have no analog (legend SVG, chip strip, stale banner, anatomy table, resolution card, 3-up stat cards, DCF cross-link card) and 6 of those 7 are token-driven extensions of existing patterns (only the legend SVG is truly novel visual design).
2. **Two CSS variable token blocks are sacred** — copy verbatim from the two DCF analogs, never redefine palette values. Phase 11 explicitly forbids a third theme (D-06).
3. **The TradingView `initChart()` function changes exactly one field** (`interval: 'W'` → `'D'`). Everything else verbatim, including the `script.onerror` fallback.
4. **The portfolio shell router needs zero code changes** — only the `projects` registry object gets one new key.
5. **Three RESEARCH pitfall mitigations are non-negotiable** in any plan that touches the drilldown:
   - Pitfall 1: derive exit copy from `status` + `exit_date` + `exit_price`, NEVER read `row.exit_reason` (field doesn't exist on disk)
   - Pitfall 3: static `<title>` must be `Inside Bar Pattern Detail | Goh Jun Xian`, NOT a placeholder like analog's `Stock Overview`
   - Pitfall 7: annotated PNG uses `loading="eager"` + `fetchpriority="high"`, overriding D-20's blanket lazy-load default
