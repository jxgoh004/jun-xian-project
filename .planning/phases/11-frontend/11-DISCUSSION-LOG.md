# Phase 11: Frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 11-frontend
**Areas discussed:** Confidence badge (label + cutoffs), Pattern legend (format + scope), Visual theme, Audit-the-rule UX (drilldown hero + status surfacing)

---

## Area 1 — Confidence Badge

### Sub-question 1a: Column label for yolo_conf

| Option | Description | Selected |
|--------|-------------|----------|
| Pattern Quality | Frames score as a quality grade of the pattern shape itself. Doesn't imply trade success. Pairs naturally with the legend. | ✓ |
| Textbook Match | Most semantically accurate (model trained on textbook patterns). "Textbook" requires explanation. | |
| ML Confidence | Conventional ML naming. "Confidence" in finance context implies trade-success prediction (misleading). | |
| Confidence | Matches REQ UI-01 wording. Shortest, but most likely to be misread as P&L confidence. | |

**User's choice:** Pattern Quality
**Notes:** Recommended option after I explained that yolo_conf measures chart-textbook-ness (not P&L success) per Phase 10 D-05 / D-12. The label "Confidence" in REQUIREMENTS.md UI-01 predates the empirical understanding of what the model actually measures.

### Sub-question 1b: Tier cutoffs

| Option | Description | Selected |
|--------|-------------|----------|
| Absolute 0.50 / 0.25 | Green ≥ 0.50, Yellow 0.25–0.50, Red < 0.25. Today: 10 green / 19 yellow / 15 red. Stable, visitor-meaningful. | ✓ |
| Percentile-based (top 25% / middle 50% / bottom 25%) | Computed nightly. Always produces variety, but badges can shift colour night-to-night without score changes. | |
| Absolute 0.40 / 0.20 | Lower cutoffs. Today: ~16 green / ~20 yellow / ~8 red. More "green" can read as inflated. | |
| 2-tier ('clean' ≥0.5 vs 'standard' <0.5) | Binary simplification. Loses the middle tier useful for sorting. | |

**User's choice:** Absolute 0.50 / 0.25
**Notes:** The user initially asked whether 0.75 / 0.25 was realistic. I confirmed today's data tops out at 0.726, so 0.75 would launch a green-free table. The user weighed the trade-off and chose 0.50 / 0.25 to ensure all three tiers are populated at launch. Flagged for revisit after ~30 nightly runs once a real empirical histogram exists.

---

## Area 2 — Pattern Legend (UI-02)

### Sub-question 2a: Format

| Option | Description | Selected |
|--------|-------------|----------|
| Always-visible diagram band | Horizontal band with labelled 5-bar mini-chart + plain-language caption. Visitors absorb the rule at a glance. | ✓ |
| Collapsible 'How to read this' panel (expanded by default) | Same content but collapsible. Frees space for return visitors. | |
| Compact 3-row text legend | Text-only (Setup / Filters / Confirmation). Low visual cost; visitors who think in shapes will struggle. | |
| Inline tooltips on column headers + header subtitle | No dedicated legend. Lightest footprint, but fails UI-02's plain-language intent for visitors who never hover. | |

**User's choice:** Always-visible diagram band
**Notes:** Recommended option. Aligns with UI-02's explicit "without prior knowledge" requirement — collapse / tooltip patterns lose visitors who don't click or hover.

### Sub-question 2b: Diagram scope

| Option | Description | Selected |
|--------|-------------|----------|
| Structure only (5 bars labelled) | Clean first impression. Confirmation types and trend filters move to column tooltips / drilldown. | ✓ |
| Structure + 3 confirmation types as variant strip | Adds ~40px height. Useful if Type column is otherwise opaque. | |
| Structure + trend-filter checklist | Foregrounds methodology (good for domain-expertise narrative). More dense. | |
| All three layers | Strongest standalone explanation; weakest for visitors who just want the table. | |

**User's choice:** Structure only (5 bars labelled)
**Notes:** Recommended option. Type/filter context lives one click away (column tooltips, drilldown). Avoids turning the legend into a textbook page that crowds the table out of viewport on smaller screens.

---

## Area 3 — Visual Theme

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror DCF split (blue index, analytical stock.html) | Pattern index uses GitHub-blue; pattern stock.html uses analytical-dark. Portfolio-wide rhythm. | ✓ |
| Unify on analytical-dark for both pages | Distinct project, more 'serious quant tool' feel. Pattern index diverges from DCF index. | |
| Unify on GitHub-blue for both pages | Faster to build. Drilldown loses the focused 'analysis' feel; reads as less premium than DCF. | |
| New third theme for the pattern project | Distinct ML-flavoured palette. Highest design lift; three themes is one too many for a 3-tool portfolio. | |

**User's choice:** Mirror DCF split
**Notes:** Recommended option. Established split (tables = scan = GitHub-style; drilldowns = focused = analytical-studio) carries through. Visitors oriented in DCF feel instantly oriented in patterns. Tokens copied verbatim from DCF analogs; pattern-specific styling extends existing token set rather than replacing it.

---

## Area 4 — Audit-the-Rule UX

### Sub-question 4a: Drilldown hero / visual hierarchy

| Option | Description | Selected |
|--------|-------------|----------|
| Annotated PNG as hero, TradingView below | Static YOLO chart (the rule) is largest element. TradingView below as 'what happened since.' | ✓ |
| TradingView as hero, annotated PNG smaller above/beside | Live price biggest; algorithmic PNG demoted to thumbnail. The rule becomes supporting visual. | |
| Side-by-side: PNG + TradingView at equal weight | Both first-class. Horizontal space pressure on desktop; no clear visual entry point. | |
| Tabs ('The Setup' / 'Live Chart') | User toggles. Hides information behind a click; defeats the goal of showing both. | |

**User's choice:** Annotated PNG as hero, TradingView below
**Notes:** The user asked clarifying questions about what the drilldown is, where it sits in the navigation flow, and whether TradingView's "live price" actually moves in real time. I explained: (a) clicking a row navigates to `stock.html?ticker=X`; (b) TradingView's free embed DOES update during US market hours but is frozen outside; (c) we'd use `interval: 'D'` to match Phase 7 daily-bar methodology. The user then asked for my recommendation and I confirmed Option 1 — leading with the PNG because it IS the project's deliverable; TradingView is everywhere but the PNG is yours.

### Sub-question 4b: Status surfacing on the screener table

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated coloured Status column + filter chips above table | New Status column (target/stop/open/pending colour-coded); four filter chips for one-click isolation. Default sort: date desc. | ✓ |
| Status column only, no filter chips | Sortable column; no chips. Filtering by status is one extra click and less discoverable. | |
| Default sort by status (pending → open → target → stop), no filter chips | Active rows on top automatically. Loses the recency story. | |
| Only show status in the drilldown, not the table | Table stays lean. Wastes the simulate_trade payload Phase 10 carried specifically for this. | |

**User's choice:** Dedicated coloured Status column + filter chips above table
**Notes:** Recommended option. Most direct expression of Phase 10's "audit accuracy" reframing. Today: 29 stop / 10 open / 4 target / 1 pending — visitors can immediately scan outcomes or isolate any subset.

---

## Claude's Discretion

The following implementation details were left to the planner / researcher (captured in CONTEXT.md `### Claude's Discretion`):

- Exact diagram artwork for the legend band (SVG vs static PNG export from mplfinance fixture)
- Mobile breakpoint behaviour for the legend band (collapse vs hide below 480px)
- Mobile column hide order on the screener table
- Whether to show the three `filters` booleans on the drilldown
- `exit_reason` rendering verbosity ("target_hit" vs "Hit target at $310.70 on 2026-05-14")
- R-multiple format ("+0.53R" vs "+0.53" vs "0.53R")
- `as_of_date` placement (header subtitle vs tooltip)
- DCF cross-link card icon

## Deferred Ideas

Ideas raised or surfaced during discussion that belong in later phases / enhancements (full list in CONTEXT.md `<deferred>`):

- Revisit Pattern Quality cutoffs after ~30 nightly runs once empirical histogram exists
- ONNX-aware re-scoring of Phase 9 backtest cache for stratified-by-tier stats
- YOLO output bbox overlay on annotated PNG (alongside algorithmic bbox)
- Confirmation-type variant strip in legend (rejected from D-05; revisitable on visitor feedback)
- Trend-filter checklist in legend (rejected from D-05; surfaceable on drilldown)
- Confidence threshold slider (PAT2-02)
- Historical detections per ticker (PAT2-01)
- Uptrend context panel on drilldown (PAT2-03)
- Real thumbnail PNG for home-page card (ships with CSS placeholder + TODO)
- Per-page `CLAUDE.md` for patterns project
- Cross-link symmetry (DCF drilldown → pattern drilldown when applicable)
