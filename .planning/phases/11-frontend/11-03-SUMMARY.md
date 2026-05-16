---
phase: 11-frontend
plan: 03
subsystem: ui
tags: [frontend, portfolio-shell, sitemap, og-image, seo, marketing]

# Dependency graph
requires:
  - phase: 11-frontend (Plan 11-01)
    provides: "docs/projects/patterns/index.html — the screener page that the new home-page card links to via #patterns"
  - phase: 11-frontend (Plan 11-02)
    provides: "docs/projects/patterns/stock.html — drilldown page whose og:image / twitter:image meta tags now resolve to the exported og-image.png"
provides:
  - "docs/index.html third project card (Inside Bar Pattern Scanner, inserted FIRST per D-17) + patterns registry entry — completes UI-05"
  - "docs/projects/patterns/og-image.png (1200×630, 112 KB) — social-card image referenced by both pattern pages' og:image and twitter:image"
  - "docs/sitemap.xml entries for /projects/patterns/ (0.8) and /projects/patterns/stock.html (0.7) — both indexable by search crawlers"
affects: [marketing surface for LinkedIn/Twitter previews, SEO discovery of the new pattern pages]

# Tech tracking
tech-stack:
  added: []  # zero new dependencies — registry edit, PNG export, sitemap append
  patterns:
    - "Card-first registry ordering (suggested order per D-17: patterns → screener → calculator) — newest project surfaces first to recruiters"
    - "Letterboxed og-image generation: source annotated chart resized to fit 1200×630 with #080c12 brand-background fill (preserves aspect ratio, no crop)"
    - "Sitemap-as-append: new <url> entries inserted before </urlset>, retaining existing 3 entries unchanged"

key-files:
  created:
    - "docs/projects/patterns/og-image.png (1200×630 PNG, 112 KB, sourced from charts/APD_2026-04-20.png with yolo_conf=0.5516)"
  modified:
    - "docs/index.html (+16 / -2 — Pattern Scanner card inserted before screener card; patterns registry entry as FIRST key per D-17)"
    - "docs/sitemap.xml (+10 / -0 — two new <url> entries appended before </urlset>)"

key-decisions:
  - "Inserted Pattern Scanner card FIRST in the .projects grid (order: patterns → screener → calculator) per D-17 — newest project surfaces first to recruiters scanning the page"
  - "Registered patterns as the FIRST key in the projects registry to mirror the grid order; existing hash router (navigate()) reads dynamically and required no logic changes"
  - "og-image source = charts/APD_2026-04-20.png (yolo_conf=0.5516, first green-tier detection in data.json document order) — visually striking, brand-aligned"
  - "Letterboxed render on #080c12 brand background to preserve aspect ratio (no crop) and match the analytical-dark theme used by both pattern pages"
  - "robots.txt confirmed already permissive (User-agent * Allow / with no Disallow rules) — no edit needed"

patterns-established:
  - "Home-page registry pattern: adding a new project requires only one card markup block + one registry line; the existing on-demand-iframe navigate() picks it up automatically"
  - "og-image generation pattern: PIL Image.thumbnail(LANCZOS) into a brand-coloured 1200×630 canvas — usable for future projects that need a social card"

requirements-completed: [UI-05]

# Metrics
duration: ~20min (implementation) + human verification walkthrough
completed: 2026-05-16
---

# Phase 11 Plan 03: Portfolio Shell Wiring Summary

**Pattern Scanner card wired into the portfolio home page (inserted first, ahead of the DCF screener and calculator per D-17), patterns registry entry added, og-image exported, and sitemap extended with two new URLs — UI-05 satisfied and the v2.0 milestone deliverable is now discoverable from the landing page.**

## Performance

- **Duration:** ~20 min implementation + visual checkpoint
- **Started:** 2026-05-16
- **Completed:** 2026-05-16
- **Tasks:** 3 / 3 (Tasks 1 and 2 automated; Task 3 human-verify checkpoint)
- **Files modified:** 2 modified + 1 created (binary)

## Accomplishments

- New `<a href="#patterns" class="card" data-project="patterns">` block in `docs/index.html` (+16 / -2): thumbnail placeholder, h2 "Inside Bar Pattern Scanner", blue-accent benefit line "AI-curated chart setups, updated every trading day", description "Computer-vision-graded inside-bar-spring detections across the S&P 500, with backtested outcomes per setup type.", four tags (Python · ONNX · Computer Vision · Finance), `aria-label="Open Inside Bar Pattern Scanner project"` for accessibility (D-19).
- `projects` registry now has `patterns: 'projects/patterns/index.html'` as the FIRST entry (D-17 order: patterns → screener → calculator). Existing hash-router `navigate()` and `postMessage` handler untouched — registry is the only wiring point.
- `docs/projects/patterns/og-image.png` exported (1200×630 PNG, 112 KB): sourced from `docs/projects/patterns/charts/APD_2026-04-20.png` (APD, yolo_conf=0.5516 — the first green-tier detection in `data.json` document order), letterboxed onto a `#080c12` analytical-dark background to preserve aspect ratio without cropping the algorithmic bbox.
- `docs/sitemap.xml` extended (+10 / -0) with two new `<url>` entries: `https://jxgoh004.github.io/jun-xian-project/projects/patterns/` (changefreq=daily, priority=0.8) and `.../projects/patterns/stock.html` (changefreq=daily, priority=0.7). File remains valid XML; total URL count now 5.
- `docs/robots.txt` verified permissive: contains `User-agent: *` followed by `Allow: /` with no `Disallow` rules — `/projects/patterns/` is crawlable by all bots, no change needed.

## Task Commits

Each task was committed atomically (no AI co-author trailer, per the user's `git-attribution-guard` rule in MEMORY):

1. **Task 1: Add Pattern Scanner card + registry entry to docs/index.html** — `93c4af4` (feat)
2. **Task 2: Export og-image.png + append sitemap URLs + verify robots.txt** — `419927e` (feat)
3. **Task 3: Human-verify end-to-end home → screener → drilldown navigation** — APPROVED via 20-point browser walkthrough (no commit; checkpoint gate)

**Plan metadata:** see the follow-on `docs(11-03): complete portfolio shell wiring plan + phase SUMMARY` commit for SUMMARY persistence.

## Files Created/Modified

- **MODIFIED** `docs/index.html` (+16 / -2) — Pattern Scanner card inserted as the first child of `<div class="projects">` (before the existing screener card); `patterns: 'projects/patterns/index.html'` added as the first key in the `var projects = { ... }` object. Card structure mirrors the existing screener card recipe (same `.card` CSS classes, thumbnail placeholder, h2 / benefit / description / tags layout). Router function `navigate()` and the cross-window `postMessage` handler are unchanged.
- **CREATED** `docs/projects/patterns/og-image.png` (1200×630, 112 KB) — letterboxed render of `charts/APD_2026-04-20.png` on a `#080c12` background, generated via PIL (`Image.thumbnail(LANCZOS)` into a 1180×610 inner bound with the canvas filled to 1200×630). Referenced by both pattern pages' `og:image` and `twitter:image` meta tags (Plan 11-01 head and Plan 11-02 head).
- **MODIFIED** `docs/sitemap.xml` (+10 / -0) — two `<url>` blocks appended immediately before the closing `</urlset>` tag, matching the existing entry shape (`<loc>` + `<changefreq>` + `<priority>`). Validated as well-formed XML (round-trips through `[xml]` in PowerShell when run locally).

## Decisions Made

- **Card order = patterns → screener → calculator (D-17 suggested order honoured).** Pattern Scanner is the newest project; placing it first front-loads the recent work for recruiters who scan top-to-bottom. DCF screener moves to position 2; calculator (oldest) drops to position 3.
- **Registry order matches card order.** `patterns: ...` is the first key in `var projects = { ... }`. The router doesn't depend on key order (it does a hash lookup), but matching the grid order makes the diff easier to read and the source-order intent obvious to future maintainers.
- **og-image source = APD_2026-04-20.png.** Selection rule: first detection in `data.json` document order with `yolo_conf >= 0.50` (the green-tier cutoff per D-02). APD scored 0.5516 — clean inside-bar-spring textbook example, visually balanced, status=Open at time of export.
- **Letterbox, no crop.** The annotated bbox + the 5-bar window are the meaning of the image; cropping to a 1.91:1 frame would risk truncating either the algorithmic bbox or the surrounding context. Letterboxing onto `#080c12` (the analytical-dark drilldown background) keeps brand cohesion and shows the whole artefact.
- **robots.txt unchanged.** The file already has `Allow: /` and no `Disallow` rules — `/projects/patterns/` is fully crawlable. Adding a redundant `Allow: /projects/patterns/` would be noise, not signal.

## Human Verification Checkpoint

**Result:** APPROVED. The user walked through the 20-point browser check (`python -m http.server 8000 --directory docs`) covering visual rendering on the home page, click-through to the patterns scanner, status-chip filtering, column sort, drilldown rendering (annotated PNG hero, TradingView daily candles, 5-bar anatomy, resolution card, stat cards), back-navigation, SEO source-view, sitemap visibility, og-image direct fetch, console error scan, and mobile responsive behaviour.

Four items the user initially flagged turned out to be check-interpretation misunderstandings, NOT code defects — capturing them here for future-self context:

| Initial flag | Actual state | Resolution |
|---|---|---|
| "og:image not present" | The `og:image` meta IS present and resolves to a full absolute URL containing `/projects/patterns/og-image.png` (the relative path is normalised to absolute via the canonical base) | Confirmed via view-source on patterns/index.html |
| "Page title says 'Inside Bar Pattern Detail \| Goh Jun Xian' not 'TICKER — Company \| Pattern Scanner'" | The static `<title>` is intentionally `Inside Bar Pattern Detail \| Goh Jun Xian` for crawlability with no-JS (Plan 11-02 Pitfall 3); JS rewrites `document.title` to the TICKER-flavoured form AFTER data loads. UX is intentional | Confirmed: static title is in source; JS rewrite is the post-fetch enhancement |
| "Sitemap page shows 'no XSL stylesheet' error in browser" | This is the default browser rendering hint for raw XML, not an error. Search engines parse the XML directly — they do NOT need an XSL transform | Cosmetic browser message only; sitemap is valid and crawlable |
| "Console shows 'asynchronous response… message channel closed' + Network 304s" | The message-channel warning is from a browser extension (not the page); 304 Not Modified responses are cache HITS (success, not failure) | Both are normal browser behaviour, not page bugs |

No code changes were required from any of the four items. UI-05 is complete.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1 / 2 / 3 / 4 deviations encountered during Tasks 1 or 2. Task 3 (the human checkpoint) clarified four check-interpretation questions without uncovering any code defect.

## Issues Encountered

None. The plan's pre-frozen interfaces (the exact card markup from UI-SPEC, the verbatim registry diff, the two sitemap URL templates, the og-image source-selection rule) made implementation mechanical.

## User Setup Required

None — pure static-site change. No environment variables, no external services, no deployment configuration to touch. GitHub Pages will pick up the changes on the next push to `main`.

## Next Phase Readiness

Phase 11 is complete (3 / 3 plans). Milestone v2.0 (Inside Bar Pattern Scanner) is fully delivered end-to-end:

- Detection engine (Phase 7)
- Training pipeline + ONNX export (Phase 8)
- Backtesting engine (Phase 9)
- Nightly batch pipeline (Phase 10)
- Frontend screener + drilldown + portfolio card (Phase 11)

See `.planning/phases/11-frontend/11-SUMMARY.md` for the phase-level consolidation, file inventory, decision honour-roll, and deferred follow-ups carried into a future iteration.

## Verification Status

| Check | Result |
|-------|--------|
| `docs/index.html` contains `data-project="patterns"`, `href="#patterns"`, `patterns:   'projects/patterns/index.html'` | PASS (commit 93c4af4) |
| Card source order in HTML: patterns BEFORE screener BEFORE calculator | PASS |
| `docs/sitemap.xml` contains `/projects/patterns/` and `/projects/patterns/stock.html` | PASS (commit 419927e) |
| `docs/sitemap.xml` parses as valid XML | PASS |
| `docs/projects/patterns/og-image.png` exists, ≥10 KB (actual 112 KB), 1200×630 | PASS |
| `docs/robots.txt` does not block `/projects/patterns/` | PASS (no change required) |
| Human end-to-end browser walkthrough (20 checks) | PASS (APPROVED) |
| No AI co-author trailer on either commit | PASS (both authored as `Goh Jun Xian <zenn.goh.is@hotmail.com>`) |

## Self-Check: PASSED

- FOUND: `docs/index.html` modified by `93c4af4` (+16 / -2).
- FOUND: `docs/projects/patterns/og-image.png` (112 464 bytes) introduced by `419927e`.
- FOUND: `docs/sitemap.xml` modified by `419927e` (+10 / -0).
- FOUND commit `93c4af4` in `git log` — VERIFIED.
- FOUND commit `419927e` in `git log` — VERIFIED.

---
*Phase: 11-frontend*
*Plan: 03*
*Completed: 2026-05-16*
