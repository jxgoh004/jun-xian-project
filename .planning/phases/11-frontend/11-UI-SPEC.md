---
phase: 11
slug: frontend
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-16
---

# Phase 11 — UI Design Contract

> Visual and interaction contract for the Inside Bar Pattern Scanner frontend.
> Three deliverables: `docs/projects/patterns/index.html` (GitHub-blue screener),
> `docs/projects/patterns/stock.html` (analytical-dark drilldown), and a new
> project card on `docs/index.html`. All visual tokens inherit verbatim from
> existing DCF screener analogs — Phase 11 introduces zero new palettes.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (vanilla HTML/CSS/JS — project mandates no frameworks per `CLAUDE.md`) |
| Preset | not applicable |
| Component library | none — recombination of existing in-repo components |
| Icon library | inline SVG (per-instance), matching existing portfolio convention |
| Font (screener `index.html`) | System stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif` |
| Font (drilldown `stock.html`) | Google Fonts: **Syne** (display 400/600/700/800) + **DM Sans** (body 300/400/500) + **DM Mono** (numbers 400/500) — preconnect already established in analog |

**Inheritance rule:** Pattern-specific styling EXTENDS the existing token set, never replaces it. CSS variable blocks copied verbatim from the two DCF analogs.

---

## Token Block A — GitHub-Blue (`patterns/index.html`)

Verbatim from `docs/projects/screener/index.html` `:root` (lines 22–31). Do not redefine.

```css
:root {
  --bg:          #0d1117;   /* page background */
  --surface:     #161b22;   /* card / thead / input surface */
  --border:      #30363d;   /* dividers */
  --accent:      #58a6ff;   /* links, sort arrows, ticker text, focus ring */
  --text:        #c9d1d9;   /* body text */
  --text-bright: #f0f6fc;   /* headlines, primary cell content */
  --text-dim:    #8b949e;   /* subtitles, NA badges, dim cells */
  --radius:      8px;       /* corners on inputs, cards, table cells */
}
```

Body font: system sans stack at 14–15px / 1.6 line-height.

---

## Token Block B — Analytical-Dark (`patterns/stock.html`)

Verbatim from `docs/projects/screener/stock.html` `:root` (lines 14–40). Do not redefine.

```css
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
  --green:        #3fb950;  --green-bg:     rgba(63,185,80,0.08);  --green-border:  rgba(63,185,80,0.25);
  --yellow:       #e3b341;  --yellow-bg:    rgba(227,179,65,0.08); --yellow-border: rgba(227,179,65,0.25);
  --red:          #f85149;  --red-bg:       rgba(248,81,73,0.08);  --red-border:    rgba(248,81,73,0.25);
  --text:         #a8b4c8;
  --text-dim:     #546278;
  --text-bright:  #e8edf5;
  --mono:         'DM Mono', monospace;
  --sans:         'DM Sans', sans-serif;
  --display:      'Syne', sans-serif;
  --radius:       12px;
}
```

Dot-grid background (verbatim from analog): `radial-gradient(circle, #1e2840 1px, transparent 1px); 28px 28px; fixed;` plus a `body::before` overlay gradient `linear-gradient(160deg, rgba(8,12,18,0.97) 0%, rgba(8,12,18,0.93) 100%)`.

---

## Spacing Scale

8-point base, multiples of 4. Inherited from existing analogs.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Inline tag/badge gaps |
| sm | 8px | Compact element spacing (`back-link` margin, button inner gap) |
| md | 12px | Default control padding (`8px 12px` inputs/selects); table cell padding (`10px 12px`) |
| lg | 16px | Controls strip vertical padding; card inner gap |
| xl | 24px | Section padding (`header`, `.table-scroll`); page horizontal gutter |
| 2xl | 28px | Drilldown nav horizontal padding; dot-grid period |
| 3xl | 48px | Empty / error / loading state vertical padding |

Exceptions:
- Badges + pills use **2px × 10px** padding (existing `.badge` pattern, lines 213–220 of DCF index) — fixed geometry, not from the scale.
- Card thumbnail aspect / sticky-nav height (52px) inherited verbatim from analogs.

---

## Typography

### Screener `index.html` (GitHub-blue)

| Role | Size | Weight | Line Height | Family |
|------|------|--------|-------------|--------|
| H1 (page title) | 22px | 700 | 1.2 | system sans |
| Subtitle / "Last updated" | 13px | 400 | 1.4 | system sans |
| Body / table cell | 14px | 400 | 1.6 | system sans |
| Ticker cell | 13px | 600 | 1.4 | system sans |
| Table header (`thead th`) | 12px | 600 | 1.4 | system sans, uppercase, letter-spacing 0.5px |
| Badge / chip | 12px | 500–600 | 1.4 | system sans |
| Legend caption | 13–14px | 400 | 1.5 | system sans |

Tabular numerals on all numeric columns: `font-variant-numeric: tabular-nums;` (existing `.td-number`).

### Drilldown `stock.html` (analytical-dark)

| Role | Size | Weight | Line Height | Family |
|------|------|--------|-------------|--------|
| Hero ticker badge | 24–28px | 800 | 1.1 | Syne (display) |
| Company name | 18–20px | 600 | 1.3 | Syne |
| Section heading | 14–15px | 600 | 1.4 | Syne, uppercase, letter-spacing 0.5px |
| Body | 14px | 400 | 1.6 | DM Sans |
| Stat-card value | 28–32px | 500 | 1.2 | DM Mono (tabular) |
| Stat-card label | 11–12px | 500 | 1.4 | DM Mono, uppercase, letter-spacing 0.4px |
| 5-bar anatomy OHLC | 13px | 400–500 | 1.4 | DM Mono, tabular-nums |
| Nav logo | 13px | 800 | 1.0 | Syne, letter-spacing 0.5px |
| Nav section / breadcrumb | 12px | 500 | 1.0 | DM Mono, letter-spacing 0.3px |

Single `<h1>` per page (REQ PERF/marketing inheritance from Phase 6).

---

## Color

### Screener (GitHub-blue) — 60/30/10 split

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0d1117` (`--bg`) | Page background, body, table tbody rows |
| Secondary (30%) | `#161b22` (`--surface`) | Sticky thead, search input, sector select, status chips (inactive), empty/error cards |
| Border / scaffold | `#30363d` (`--border`) | Table row dividers, input borders, card outlines |
| Accent (10%) | `#58a6ff` (`--accent`) | Ticker cell text, active sort arrow, focus ring (3px `rgba(88,166,255,0.4)` shadow), row-hover tint `rgba(88,166,255,0.04)`, active filter chip, link colour |
| Text-bright | `#f0f6fc` | H1, company name cell, primary numbers |
| Text-dim | `#8b949e` | Subtitle, `td-dim`, table header label, row count |

**Accent reserved for:** ticker cells, active sort indicator, active status filter chip, focus rings, hyperlinks, row-hover background tint. NEVER applied to badges, status pills, the legend SVG, or non-link prose.

### Drilldown (analytical-dark) — layered surfaces

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#080c12` (`--bg`) | Page background under dot-grid |
| Layer 1 (20%) | `#0f1520` (`--surface`) | Top nav (with `rgba(8,12,18,0.92)` + `backdrop-filter: blur(12px)`), hero band, primary cards |
| Layer 2 (10%) | `#161e2e` (`--surface2`) | Nested cards (resolution card, stat cards), anatomy table row backgrounds |
| Layer 3 (5%) | `#1e2840` (`--surface3`) | Hover lifts, sticky-thead surface on inner tables, dot-grid dot colour |
| Accent (5%) | `#58a6ff` (`--accent`) | Hyperlinks, breadcrumb separator highlight, "Open" status pill, focus ring, DCF cross-link card border |

**Accent reserved for:** nav-logo gradient (`linear-gradient(135deg, var(--accent-dim), var(--accent))`), nav-ticker-label pill (`var(--accent-glow)` bg), focus rings, hyperlinks, the **Open** status pill colour, and the DCF cross-link card outline. NEVER applied to Pattern Quality tiers (those use green/yellow/red), to anatomy-table numbers, or to "Back to scanner" button styling.

### Semantic colour vocabulary (shared by both pages)

| Semantic | Hex | Background (alpha) | Border (alpha) | Used for |
|----------|-----|--------------------|-----------------|----------|
| Green ("clean" / target / win) | `#3fb950` | `rgba(63,185,80,0.15)` | `rgba(63,185,80,0.3)` | Pattern Quality green badge, Status=target pill, win-rate positive framing |
| Yellow ("standard" / stale-data warning) | `#e3b341` | `rgba(227,179,65,0.15)` | `rgba(227,179,65,0.3)` | Pattern Quality yellow badge, **stale data banner** (D-15) |
| Red ("loose" / stop) | `#f85149` | `rgba(248,81,73,0.15)` | `rgba(248,81,73,0.3)` | Pattern Quality red badge, Status=stop pill |
| Blue ("open" / accent) | `#58a6ff` | `rgba(88,166,255,0.15)` | `rgba(88,166,255,0.3)` | Status=open pill (active live trade) |
| Grey ("na" / pending) | `#8b949e` (screener) / `#546278` (drilldown text-dim) | `rgba(139,148,158,0.10)` | `rgba(139,148,158,0.2)` | Pattern Quality NA (yolo_conf null), Status=pending pill |

Destructive: not applicable (no destructive actions in this phase — all interactions are read-only).

---

## Badge Component Contracts

### Geometry (shared by Pattern Quality + Status)

```css
.badge {
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  display: inline-block;
}
```

Verbatim from `docs/projects/screener/index.html` lines 213–220. Only colour mapping differs between Pattern Quality and Status.

### Pattern Quality badge (column "Pattern Quality")

Computed once per row via:
```js
function tierFor(yolo_conf) {
  if (yolo_conf === null || yolo_conf === undefined) return 'na';
  if (yolo_conf >= 0.50) return 'green';
  if (yolo_conf >= 0.25) return 'yellow';
  return 'red';
}
```
(Inclusive `>=` boundaries per RESEARCH Pitfall 8.)

| Tier | Label text inside pill | Colour | Bg | Border |
|------|------------------------|--------|----|----|
| green | `Clean 0.55` (label + 2-decimal score) | `#3fb950` | `rgba(63,185,80,0.15)` | `rgba(63,185,80,0.3)` |
| yellow | `Standard 0.34` | `#e3b341` | `rgba(227,179,65,0.15)` | `rgba(227,179,65,0.3)` |
| red | `Loose 0.18` | `#f85149` | `rgba(248,81,73,0.15)` | `rgba(248,81,73,0.3)` |
| na | `—` (em-dash) | `#8b949e` | `rgba(139,148,158,0.10)` | `rgba(139,148,158,0.2)` |

Text inside pill is REQUIRED — never colour-only meaning (D-19).

### Status pill (column "Status" on screener; hero band on drilldown)

Computed from the lowercased status string (RESEARCH Pitfall 5):
```js
const status = (row.status || '').toLowerCase();
```

| Status | Label inside pill | Colour | Bg | Border |
|--------|-------------------|--------|----|----|
| target | `Target` | `#3fb950` | `rgba(63,185,80,0.15)` | `rgba(63,185,80,0.3)` |
| stop | `Stop` | `#f85149` | `rgba(248,81,73,0.15)` | `rgba(248,81,73,0.3)` |
| open | `Open` | `#58a6ff` | `rgba(88,166,255,0.15)` | `rgba(88,166,255,0.3)` |
| pending | `Pending` | `#8b949e` / `#546278` (drilldown) | `rgba(139,148,158,0.10)` | `rgba(139,148,158,0.2)` |

Same 12px-radius / 2×10px-padding / 12px-font geometry as Pattern Quality. Text always paired with colour.

### Status filter chips (controls strip)

Same geometry as the Status pill, but slightly larger touch target. Five chips total, single-active radio behaviour. Inactive chips: surface background + border colour; active chip: accent border + accent-tinted background. Counts in parens computed dynamically from loaded `data.json`.

```
[All (44)] [Open (10)] [Target (4)] [Stop (29)] [Pending (1)]
```

Each chip carries `aria-pressed="true|false"` and is a real `<button>` (keyboard-focusable).

---

## Layout Contracts

### Screener page (`patterns/index.html`)

Vertical stack, top to bottom:

1. **Skip-nav link** (off-screen until focus) — `<a href="#detection-table">Skip to detections</a>`
2. **Header** (`header` element, padding `24px 24px 0`, centred)
   - `<a class="back-link">← Back to portfolio</a>` (accent colour, 13px)
   - `<h1>Inside Bar Pattern Scanner</h1>` (22px / 700 / `--text-bright`)
   - `<p class="subtitle">` — either `Last updated: {as_of_date}` (normal) OR the stale-data banner (D-15, see below)
3. **Stale-data banner** (D-15, conditional) — yellow band, full-width, above controls, between header and legend. Text: `Data may be stale — last nightly pipeline run reported {failed_count} ticker failures.` Yellow palette = `#e3b341` colour, `rgba(227,179,65,0.15)` bg, `rgba(227,179,65,0.3)` border, 12px padding, same `--radius` as cards. Hidden when `pipeline_status.completed === true`.
4. **5-bar legend band** (D-04, see "5-Bar Legend SVG" section below) — always visible at ≥480px; collapses to caption-only below 480px.
5. **Controls strip** (`.controls`, `display:flex; gap:12px; padding:16px 24px; flex-wrap:wrap`)
   - Left: `<label class="sr-only">Search ticker or company</label><input type="text" placeholder="Search ticker or company">` (flex:1, min-width 200px)
   - Middle: `<label class="sr-only">Filter by sector</label><select>` (min-width 160px)
   - Right: status filter chips row — `[All] [Open] [Target] [Stop] [Pending]` (own flex-wrap line on narrower viewports). On viewport <640px, status chips collapse into a `<select>` with the same five options.
   - Far right: `<span id="row-count">N detections</span>` (text-dim, 13px, nowrap)
6. **Table scroll wrapper** (`.table-scroll`, `overflow-x:auto; padding:0 24px 24px`)
7. **`<table class="screener-table">`** — sticky thead, 8 columns:
   | # | Column | data-col | Default sort | Mobile hide order |
   |---|--------|----------|--------------|--------------------|
   | 1 | Ticker | `ticker` | n/a | always show |
   | 2 | Company | `company_name` | n/a | hide first at <640px |
   | 3 | Sector | `sector` | n/a | hide first at <640px (with Company) |
   | 4 | Date | `confirmation_date` | **desc (default)** | always show |
   | 5 | Type | `confirmation_type` | n/a | always show |
   | 6 | Pattern Quality | `yolo_conf` | n/a | always show |
   | 7 | Price | `current_price` | n/a | always show |
   | 8 | Status | `status` | n/a | always show |
   Each `th` carries `aria-sort="none|ascending|descending"` for screen readers; visual indicator via existing `th[data-sort="asc"]::after { content: ' \2191' }` + `desc::after { content: ' \2193' }` (DCF index lines 166–174).
8. **Loading / Error / Empty states** — three hidden divs (`display:none` initial), one shown by the fetch state machine.
   - `#loading-state`: centred, 48px vertical padding, text `Loading detections...`
   - `#error-state`: centred, text `Couldn't load detections. Try refreshing.` plus a dim `.error-detail` line with the error message
   - `#empty-state` (D-16): centred card, text `No active inside-bar-spring setups in the last 20 trading days.` Legend band remains visible above.

Row interaction: clicking any `<tr>` navigates to `stock.html?ticker={TICKER}` (use `cursor:pointer` + row-hover tint `rgba(88,166,255,0.04)`; entire row is clickable via JS listener on `tbody`).

**Mobile breakpoint (≤640px):**
- Hide `.col-sector` and `.col-company` (`display:none`)
- Collapse status chips into a `<select>` (same 5 options)
- Header padding tightens to `16px 16px 0`
- Table-scroll padding tightens to `0 16px 16px`

---

### Drilldown page (`patterns/stock.html`)

Vertical stack:

1. **Top nav** (sticky, 52px height) — verbatim from `screener/stock.html` lines 67–125:
   - `nav-logo-mark` (26×26 gradient square, "JX" or initial) + `nav-logo` "Goh Jun Xian"
   - `nav-divider`
   - `nav-section` "Patterns"
   - `›` separator
   - `nav-ticker-label` (e.g. `AAPL`, in accent-glow pill)
   - `nav-spacer`
   - `<a href="index.html" class="btn-back">← Back to scanner</a>` (native anchor — handles both iframed and direct-deep-link modes per RESEARCH Pitfall 4)
2. **Hero band** (`section.hero`, full-width, padded 28px 28px 24px)
   - **Left column:** large ticker (Syne 28px/800), company name (Syne 18px/600), `Sector › Industry` breadcrumb (DM Mono 12px / text-dim)
   - **Right column:** vertical stack of pills — Status pill (coloured per status), Pattern Quality pill (coloured per tier), current price (`$xxx.xx`, DM Mono 20px/500, tabular-nums)
   - Optional 3-pill filters strip (Claude's Discretion — recommended): `Trend ✓` `Above 50-SMA ✓` `Cluster ✓` — small pills (10px font, neutral grey-on-surface2) below the hero, demonstrating all three trend filters passed for this detection
3. **Annotated PNG hero** (`<figure>`, centred, max-width 640px)
   - `<img src="charts/{TICKER}_{DATE}.png" loading="eager" fetchpriority="high" decoding="async" width="..." height="..." alt="Annotated 5-bar inside bar spring detection for {TICKER} on {confirmation_date}">`
   - **Override D-20's blanket `loading="lazy"` for this one image** — it's the LCP candidate (RESEARCH Pitfall 7)
   - Explicit `width` + `height` attributes from the on-disk PNG dimensions for CLS prevention
   - Caption below (DM Mono 11px / text-dim): `Algorithmic 5-bar bbox · {confirmation_date} · Pin/Mark-Up/Ice-cream`
4. **TradingView embed** (full-width, height ~340–420px)
   - `initChart(ticker)` function copied verbatim from `screener/stock.html` lines 1535–1580
   - Config: `interval: 'D'` (flip from analog's `'W'`), `theme: 'dark'`, `style: '1'` (candles)
   - Script: `loading` is async by default; load only after first paint
   - `script.onerror` fallback: render `.chart-fallback` div with text `Live chart unavailable offline.` (existing pattern verbatim)
5. **5-bar OHLC anatomy table** (`<section class="anatomy">`, surface2 background, 12px radius)
   - Section heading "Pattern Anatomy" (Syne 14px/600 uppercase, letter-spacing 0.5px)
   - Table: 5 rows × 5 columns (Date / Open / High / Low / Close) reading from `detection.bars[]`
   - Numbers: DM Mono, tabular-nums, 13px / 400–500
   - Each row labelled in left margin or first column: Mother / Inside / Break / Confirm / Continuation (5th bar = continuation context)
6. **Resolution card** (`<section class="resolution">`, surface2 bg, status-coloured outline)
   - Outline colour driven by `status`: green for target, red for stop, blue for open, grey for pending — using the same colour vocabulary as the Status pill
   - Headline (Syne 16px/600): nice-language exit copy, derived from `status` + `entry_date` + `entry_price` + `exit_date` + `exit_price` + `hold_days` (NEVER read `exit_reason` — RESEARCH Pitfall 1):
     - target → `Hit target at $${exit_price.toFixed(2)} on ${exit_date}`
     - stop → `Stopped out at $${exit_price.toFixed(2)} on ${exit_date}`
     - open → `Open trade — entered ${entry_date}, ${hold_days} days held`
     - pending → `Pending entry — confirmation just printed; entry at next open`
   - Detail grid (2-col): Entry date / Entry price / Stop price / Target price / Exit date / Exit price / Hold days / R-multiple
   - R-multiple format: **`+0.53R`** (signed, suffixed, 2 decimals)
7. **Backtest stat cards** (3-up grid, gap 16px)
   - Three cards, each surface2 bg, 16–20px padding, 12px radius
   - Each card: `label` (DM Mono 11px uppercase) over `value` (DM Mono 28–32px / 500, tabular-nums)
   - Three metrics:
     1. **Win rate** — `{win_rate*100:.1f}%` with subtitle `Based on N={n_resolved} {cut_label} detections`
     2. **Avg return** — `{avg_return_r:+.2f}R` with same subtitle
     3. **Median hold** — `{median_hold_days} days` with same subtitle
   - `{cut_label}` derived from fallback chain (D-13):
     - `by_type_x_spring` → e.g. `out-of-sample ice_cream_spring`
     - `by_confirmation_type` → e.g. `out-of-sample ice_cream`
     - `all` → `out-of-sample all-type`
   - Subtitle text: DM Mono 11px / text-dim, single line under the three cards
   - If individual metric's `n < n_floor` (10), display `—` for that metric (still render the card)
8. **DCF cross-link card** (defensive, conditional — UI-04)
   - Rendered only if the ticker exists in `docs/projects/screener/data.json` `stocks[].ticker` (fetched on drilldown only, not on screener index — accurate size **1.23 MB**, NOT 800 KB per RESEARCH Pitfall 2)
   - Silent absence: if the ticker is not in DCF data, do NOT render any placeholder
   - Visual: card with accent border (`1px solid var(--accent)`), surface bg, headline `View DCF analysis for {TICKER} →`, optional small chart-line glyph icon
   - Link: `<a href="../screener/stock.html?ticker={TICKER}">` (anchor, real navigation, no postMessage needed — works in both iframed and direct-deep-link modes)

---

### Home-page card (`docs/index.html`)

Single new `<a class="card">` block, inserted **first** in the `.projects` grid (patterns → DCF screener → calculator). Mirrors DCF card structure (lines 357–369).

```html
<a href="#patterns" class="card" data-project="patterns"
   aria-label="Open Inside Bar Pattern Scanner project">
  <div class="card-thumbnail-placeholder" role="img"
       aria-label="Inside Bar Pattern Scanner preview"></div>
  <h2>Inside Bar Pattern Scanner</h2>
  <p class="card-benefit">AI-curated chart setups, updated every trading day</p>
  <p>Computer-vision-graded inside-bar-spring detections across the S&amp;P 500,
     with backtested outcomes per setup type.</p>
  <div class="tags" aria-label="Technologies used">
    <span class="tag">Python</span>
    <span class="tag">ONNX</span>
    <span class="tag">Computer Vision</span>
    <span class="tag">Finance</span>
  </div>
</a>
```

Registry update at `docs/index.html` line 406–409:
```js
var projects = {
  patterns:   'projects/patterns/index.html',
  screener:   'projects/screener/index.html',
  calculator: 'projects/calculator/index.html'
};
```

Card order: patterns first (newest), then screener, then calculator (oldest). Thumbnail uses the existing `card-thumbnail-placeholder` gradient at launch (TODO comment for future real PNG export — deferred per CONTEXT).

---

## 5-Bar Legend SVG (D-04, the only original visual)

Inline SVG, no external dependency, vector-only. Sits between the header (or stale banner) and the controls strip.

### Geometry

- `<svg viewBox="0 0 600 140" role="img" aria-labelledby="legend-title legend-desc" style="width:100%; max-width:600px; height:auto;">`
- 5 candle figures, evenly spaced along x-axis (centres at x = 60, 180, 300, 420, 540)
- Each candle: a thin `<line>` for the wick (high-to-low) + a `<rect>` for the body (open-to-close)
- Bar 1 (Mother): wider body, bullish (green-tinted body)
- Bar 2 (Inside): narrower body fully inside Bar 1's range
- Bar 3 (Break): body dips below the mother-low reference line (the "spring")
- Bar 4 (Confirm): bullish reversal — Pin / Mark Up / Ice-cream shape — body closes back above the mother-low
- Bar 5 (Continuation): bullish continuation bar, body above bar 4
- **Dashed horizontal reference line** spanning the diagram at the mother-bar low: `<line stroke="#8b949e" stroke-dasharray="4,3" stroke-width="1">` — labelled `mother low` at the right edge in 10px text-dim
- Labels under each candle (`<text>` 11px / 500 / text-bright, centred): `Mother` / `Inside` / `Break` / `Confirm` / `Continuation`

### Colour application (uses GitHub-blue tokens only)

- Bullish body fill: `rgba(63,185,80,0.5)` (green at 50% alpha)
- Bearish body fill: `rgba(248,81,73,0.5)` (red at 50% alpha — for Bar 3 Break only)
- Body outline: `var(--border)` 1px
- Wick stroke: `var(--text-dim)` 1px
- Labels: `var(--text-bright)` for bar names; `var(--text-dim)` for `mother low` annotation

### Accessibility

- `<title id="legend-title">Inside bar spring — 5-bar pattern diagram</title>`
- `<desc id="legend-desc">A bullish reversal pattern: a wide mother bar, a narrow inside bar within its range, a brief break below the mother low, a reversal confirmation bar (pin, mark-up, or ice-cream), and a continuation bar.</desc>`

### Caption (below SVG)

One sentence, 13–14px / text-bright, centred under the SVG:
> Inside bar spring — a brief break-below after a tight pullback, recovered by the next bar.

### Mobile fallback (≤480px — Pitfall 6 mitigation)

Below 480px viewport, hide the SVG with `display:none` via media query. The caption above remains visible (text-only fallback). The legend band height collapses to ~40px so the table stays above the fold.

---

## Copywriting Contract

### Screener (`patterns/index.html`)

| Element | Copy |
|---------|------|
| `<title>` | `Inside Bar Pattern Scanner — AI-graded chart setups | Goh Jun Xian` |
| `<meta name="description">` | `Daily-updated inside-bar-spring detections across the S&P 500, computer-vision-graded for pattern quality, with backtested outcomes per setup type.` |
| H1 | `Inside Bar Pattern Scanner` |
| Subtitle (normal) | `Last updated: {as_of_date}` |
| Stale-data banner (D-15) | `Data may be stale — last nightly pipeline run reported {failed_count} ticker failures.` |
| Search placeholder | `Search ticker or company` |
| Sector select default option | `All sectors` |
| Filter chips | `All ({n})` `Open ({n})` `Target ({n})` `Stop ({n})` `Pending ({n})` |
| Row-count label | `{n} detections` |
| Loading state | `Loading detections...` |
| Error state | `Couldn't load detections. Try refreshing.` |
| Empty state (D-16) | `No active inside-bar-spring setups in the last 20 trading days.` |
| Back-link | `← Back to portfolio` |
| Skip-nav | `Skip to detections` |
| Legend caption | `Inside bar spring — a brief break-below after a tight pullback, recovered by the next bar.` |
| Column tooltip "Pattern Quality" | `YOLOv8 visual quality grade. Higher = closer to textbook structure. Does NOT predict trade success.` |

### Drilldown (`patterns/stock.html`)

| Element | Copy |
|---------|------|
| `<title>` (static — Pitfall 3 mitigation) | `Inside Bar Pattern Detail | Goh Jun Xian` |
| `document.title` (post-fetch rewrite) | `{TICKER} — {company_name} | Pattern Scanner` |
| `<meta name="description">` (static) | `Per-stock inside-bar-spring drilldown: annotated 5-bar chart, live price chart, OHLC anatomy, and backtested win-rate context.` |
| Nav breadcrumb | `Patterns › {TICKER}` |
| Back button | `← Back to scanner` |
| Hero status copy (drives outline + headline of resolution card) | target → `Hit target at $X.XX on YYYY-MM-DD` · stop → `Stopped out at $X.XX on YYYY-MM-DD` · open → `Open trade — entered YYYY-MM-DD, N days held` · pending → `Pending entry — confirmation just printed; entry at next open` |
| Anatomy section heading | `Pattern Anatomy` |
| Stat card labels | `Win Rate` · `Avg Return` · `Median Hold` |
| Stat-card subtitle | `Based on N={n_resolved} {cut_label} detections` (cut_label per D-13 fallback) |
| Stat below-floor placeholder | `—` |
| DCF cross-link card | `View DCF analysis for {TICKER} →` |
| TradingView fallback | `Live chart unavailable offline.` |
| Skip-nav | `Skip to detection detail` |

**Destructive confirmations:** none — Phase 11 is entirely read-only (no destructive actions in scope).

---

## SEO / OG Meta Stack (D-18)

Both pages MUST emit the full stack — mirror `docs/projects/screener/index.html` lines 6–18.

| Meta | Screener value | Drilldown value (static) |
|------|----------------|---------------------------|
| `<title>` | `Inside Bar Pattern Scanner — AI-graded chart setups | Goh Jun Xian` | `Inside Bar Pattern Detail | Goh Jun Xian` |
| `<meta name="description">` | (see Copywriting) | (see Copywriting) |
| `<meta property="og:type">` | `website` | `article` |
| `<meta property="og:url">` | `https://jxgoh004.github.io/jun-xian-project/projects/patterns/` | `https://jxgoh004.github.io/jun-xian-project/projects/patterns/stock.html` |
| `<meta property="og:title">` | same as `<title>` | same as `<title>` |
| `<meta property="og:description">` | same as `<meta name="description">` | same as `<meta name="description">` |
| `<meta property="og:image">` | `https://jxgoh004.github.io/jun-xian-project/projects/patterns/og-image.png` | same |
| `<meta name="twitter:card">` | `summary_large_image` | `summary_large_image` |
| `<meta name="twitter:title">` | same as `<title>` | same as `<title>` |
| `<meta name="twitter:description">` | same as `<meta name="description">` | same as `<meta name="description">` |
| `<meta name="twitter:image">` | same as `og:image` | same |
| `<link rel="canonical">` | same as `og:url` | same |
| `<meta name="theme-color">` | `#0d1117` (GitHub-blue) | `#080c12` (analytical-dark) |

**`og-image.png`:** new file at `docs/projects/patterns/og-image.png` — a polished, high-resolution export of one annotated chart PNG (planner picks the most visually striking detection from `charts/`). Recommended ≥1200×630 for LinkedIn/Twitter rendering.

**Sitemap:** add two `<url>` entries to `docs/sitemap.xml`:
- `https://jxgoh004.github.io/jun-xian-project/projects/patterns/`
- `https://jxgoh004.github.io/jun-xian-project/projects/patterns/stock.html`

**robots.txt:** verify (do not modify if already `Allow: /`).

---

## Accessibility Contract (D-19)

Mandatory, both pages:

| Requirement | Implementation |
|-------------|----------------|
| Skip-nav link | First focusable element. Off-screen by default (`position:absolute; top:-100%;`), visible on focus (`onfocus="this.style.top='8px'"`). Skips to `#detection-table` (screener) or `#detection-detail` (drilldown). |
| Focus ring | Inherit `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` from analog. Plus `box-shadow: 0 0 0 3px rgba(88,166,255,0.4)` on inputs/selects (screener) or `0 0 0 3px var(--accent-glow)` (drilldown). |
| sr-only labels | All inputs and selects carry a visually-hidden `<label class="sr-only">` (existing `.sr-only` utility, lines 304–312 of DCF index). |
| Badge / pill text | Every badge contains text (`Clean`, `Standard`, `Loose`, `—`, `Target`, `Stop`, `Open`, `Pending`) paired with colour. NO colour-only meaning. |
| Sortable table | `<th>` carries `aria-sort="none|ascending|descending"`. Click + Enter/Space both trigger sort. |
| Single `<h1>` per page | Screener: `Inside Bar Pattern Scanner`. Drilldown: `{TICKER} — {company_name}` (set by JS post-fetch); fallback static `<h1>` is `Inside Bar Pattern Detail`. |
| Semantic landmarks | `<header>` `<main>` `<section>` used, not generic divs. |
| Navigable cards (home) | `<a class="card">`, NOT `<div onclick>` — keyboard / screen-reader friendly. |
| Image alt text | Annotated PNG: `Annotated 5-bar inside bar spring detection for {TICKER} on {confirmation_date}`. Card thumbnail placeholder: `role="img" aria-label="Inside Bar Pattern Scanner preview"`. SVG legend: `<title>` + `<desc>` per spec. |
| Status / Pattern Quality contrast | Hex colours `#3fb950` / `#e3b341` / `#f85149` / `#58a6ff` on `rgba(*,0.15)` backgrounds against `#0d1117` / `#080c12` — measured against existing DCF pages; passes WCAG AA at the 12px-bold-on-tinted-bg ratio. |

---

## Performance Contract (D-20, with RESEARCH overrides)

| Asset | Loading strategy | Notes |
|-------|------------------|-------|
| `data.json` (screener) | `fetch('./data.json')` on `DOMContentLoaded`, single round-trip | ~30 KB (44 detections × ~700 bytes); gzipped over the wire |
| `data.json` (DCF screener — for cross-link check) | `fetch('../screener/data.json')` on **drilldown only**, NOT on screener index | **1.23 MB on disk** (NOT 800 KB per Pitfall 2); ~250 KB gzipped; browser HTTP cache covers repeat loads |
| `stats.json` | `fetch('./stats.json')` on drilldown DOMContentLoaded | small (<10 KB) |
| Annotated PNG (drilldown hero) | `loading="eager" fetchpriority="high" decoding="async"` + explicit `width`/`height` | LCP candidate — override D-20 default lazy for THIS image only (Pitfall 7) |
| TradingView script | `<script async>` per existing pattern; injected after first paint | `onerror` fallback renders `chart-fallback` div |
| Google Fonts (drilldown) | `<link rel="preconnect">` to `fonts.googleapis.com` and `fonts.gstatic.com`, then `<link rel="stylesheet">` | already established in analog |
| CSS | Single inline `<style>` block per HTML file — NO external CSS files | project convention (zero-build) |
| JS | Inline `<script>` blocks at end of `<body>` — NO bundler | project convention |
| Card thumbnail (home) | `card-thumbnail-placeholder` CSS gradient (no image at launch) | TODO for future real PNG; matches existing DCF card pattern |
| `og-image.png` | Static commit; ≥1200×630 | Loaded only by social-media crawlers |

**Lighthouse target:** LCP < 2.5s on both pages (REQ PERF-03 inheritance from Phase 6). Drilldown LCP = annotated PNG; screener LCP = the H1 / page header.

---

## Loading / Error / Empty / Stale State Machine

Both pages follow the DCF screener pattern (lines 369–376, 623–659):

```html
<div id="loading-state">Loading...</div>
<div id="error-state" style="display:none">
  <p>Couldn't load detections. Try refreshing.</p>
  <p class="error-detail"></p>
</div>
<div id="empty-state" style="display:none">
  <p>No active inside-bar-spring setups in the last 20 trading days.</p>
</div>
<div id="stale-banner" style="display:none">...yellow banner copy...</div>
<table class="screener-table" id="detection-table" style="display:none">...</table>
```

State transitions driven by the single `fetch().then().catch()`:
- on `fetch` start → show `#loading-state`, hide others
- on success + `data.json.pipeline_status.completed === false` → show `#stale-banner` (yellow), continue rendering table
- on success + `detections.length === 0` → hide table, show `#empty-state`, keep legend visible
- on success + `detections.length > 0` → hide loading/empty, show table
- on failure (`catch`) → hide loading, show `#error-state` with `err.message`

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| none | n/a — vanilla HTML/CSS/JS only | not applicable |
| Google Fonts | Syne, DM Sans, DM Mono (drilldown only) | pre-existing in `screener/stock.html` — no new dependency |
| TradingView Advanced Chart Widget | drilldown live-chart embed | pre-existing in `screener/stock.html` — same script URL, no new vendor |

No shadcn, no third-party UI registries, no new vendors. Phase 11 is verbatim reuse of in-repo CSS/HTML patterns plus one inline SVG. Registry safety gate: **N/A — no new external code surfaces introduced.**

---

## Out of Scope (do not contract)

- Any change to Phase 10 data contracts (`data.json`, `stats.json`, chart PNG schema).
- A third visual palette / theme tokens — explicitly forbidden by D-06.
- Confidence threshold slider, historical detection accumulation, additional confirmation bar types (PAT2-*).
- Editable pattern parameters in the UI.
- ONNX-aware re-scoring of Phase 9 backtest cache (Phase 11.x follow-up).
- YOLO bbox overlay on the annotated PNG.
- Symmetric cross-link FROM DCF drilldown back TO pattern drilldown.
- Real card thumbnail PNG for the home-page card (deferred; ship with placeholder).
- Trend-filter checklist or confirmation-type strip inside the legend band.

---

## Pre-Populated Sources

| Source | Decisions Used |
|--------|----------------|
| `.planning/REQUIREMENTS.md` | UI-01 through UI-05 (5 requirements anchor the entire spec) |
| `.planning/phases/11-frontend/11-CONTEXT.md` | D-01 through D-20 (20 locked decisions inherited verbatim) |
| `.planning/phases/11-frontend/11-RESEARCH.md` | 8 pitfalls + token-block locations + size measurements (8 corrections / overrides) |
| `docs/projects/screener/index.html` | GitHub-blue token block + badge geometry + table/sticky-thead/sortable-header/sr-only/skip-nav patterns (~16 verbatim components) |
| `docs/projects/screener/stock.html` | Analytical-dark token block + top-nav + TradingView `initChart` + chart-fallback + Google Fonts preconnect (~12 verbatim components) |
| `docs/index.html` | Home-page card markup pattern + `projects` registry + hash router (3 verbatim patterns) |
| `docs/projects/screener/CLAUDE.md` | Static-page architectural constraint reinforcement |
| User input (this session) | None required — every contract field was pre-populated from upstream artifacts. All Claude's-Discretion items resolved per RESEARCH recommendations. |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

*Phase: 11-frontend · UI-SPEC drafted 2026-05-16*
