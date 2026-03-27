---
phase: 02-portfolio-shell
plan: 01
subsystem: ui
tags: [html, css, portfolio, hero, cards, github-pages]

# Dependency graph
requires:
  - phase: 01-static-foundation
    provides: docs/index.html shell with header, card grid, and deployed GitHub Pages pipeline
provides:
  - Hero section with real name, AI Engineer title, bio paragraph, and LinkedIn link
  - Projects section label (left-aligned h3) replacing bare h2
  - Card thumbnail CSS (aspect-ratio 16:9, object-fit cover) ready for real screenshots
  - CSS-only card-thumbnail-placeholder div for cards without a screenshot yet
affects: [03-calculator-integration, 04-design-performance]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS cascade specificity guard: class-specific rules (.hero-bio) placed AFTER broad rules (main p) to override without !important"
    - "Thumbnail placeholder pattern: CSS gradient div swapped for real img tag when screenshot available"
    - "Section heading demoted from h2 to h3 + class to maintain single h2 per page (SEO/accessibility)"

key-files:
  created: []
  modified:
    - docs/index.html

key-decisions:
  - "Single h2 per page: hero name is the only h2; Projects label uses h3.section-label to avoid duplicate landmark"
  - "CSS placeholder div instead of broken img tag: thumbnail.png does not exist yet; swap happens when user provides screenshot"
  - "LinkedIn only in hero contact links: no email, GitHub, or Twitter per D-04 locked decision"
  - "Bio text hard-coded in plan rather than placeholder: content was finalised in CONTEXT.md"

patterns-established:
  - "Cascade guard: new class overrides must appear after broad element selectors in the same stylesheet"
  - "Thumbnail slot pattern: .card-thumbnail-placeholder div replaced by .card img when asset is ready"

requirements-completed: [HOME-01, HOME-02, SHOW-01, SHOW-02]

# Metrics
duration: multi-session (Task 1 automated, Task 2 human-verify)
completed: 2026-03-27
---

# Phase 2 Plan 1: Portfolio Shell — Hero Section and Card Thumbnails Summary

**Centered hero section with real name (Goh Jun Xian), AI Engineer title, bio, and LinkedIn link added to docs/index.html along with left-aligned Projects label and 16:9 CSS thumbnail placeholder on the calculator card**

## Performance

- **Duration:** Multi-session (automated + human-verify checkpoint)
- **Started:** 2026-03-27
- **Completed:** 2026-03-27
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments

- Hero section built and centered using existing CSS variables — name, AI Engineer title in accent blue, bio in --text color, LinkedIn link
- Projects section label converted from bare h2 to h3.section-label with text-align:left, eliminating duplicate h2 on the page
- Card thumbnail CSS rules added (.card img with aspect-ratio 16:9, .card-thumbnail-placeholder CSS gradient fallback)
- User filled in real name ("Goh Jun Xian") and real LinkedIn URL, replacing TODO placeholders

## Task Commits

Each task was committed atomically:

1. **Task 1: Add hero section, section label, and card thumbnail support to docs/index.html** - `571b596` (feat)
2. **Task 2: User provides personal details and verifies visual output** - human checkpoint (no code commit — user edited file directly before checkpoint approval)

**Plan metadata:** (docs commit — this summary)

## Files Created/Modified

- `docs/index.html` — Extended with hero section CSS rules, .section-label, .card img, .card-thumbnail-placeholder; HTML updated with `<section class="hero">`, h3.section-label, and placeholder div inside card

## Decisions Made

- Single h2 per page: hero `<h2>` is the only h2; "Projects" heading uses `<h3 class="section-label">` — avoids duplicate h2 landmark, improves SEO
- Used CSS gradient placeholder div (not a broken img tag) because thumbnail.png does not exist yet; swap to `<img>` tag is deferred to when the user provides a screenshot
- LinkedIn is the only contact link in the hero per locked decision D-04 — no email, GitHub, or Twitter added

## Deviations from Plan

None — plan executed exactly as written. The user filled in personal details (name + LinkedIn URL) directly as instructed at the Task 2 checkpoint.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. The user may optionally take a screenshot of the calculator (~800x450px), save it as `docs/projects/calculator/thumbnail.png`, and swap the placeholder div for an `<img>` tag inside the card. This is deferred and not blocking Phase 3.

## Known Stubs

- `docs/index.html` line 148: `<div class="card-thumbnail-placeholder" ...>` — CSS gradient placeholder used because `docs/projects/calculator/thumbnail.png` does not exist yet. The thumbnail slot CSS (.card img) is fully wired; the placeholder div just needs to be replaced with `<img src="projects/calculator/thumbnail.png" alt="...">` when the screenshot is available. This does not block the plan goal (card grid is visible with title, description, and tags as required by SHOW-02).

## Next Phase Readiness

- Phase 3 (Calculator Integration) can begin: home page is complete with hero, project card, and navigation structure
- CORS concern from STATE.md still applies: Render API CORS must be verified before Phase 3 end-to-end calculator test can pass
- Optional improvement available: swap thumbnail placeholder for real screenshot at any time without code changes elsewhere

---
*Phase: 02-portfolio-shell*
*Completed: 2026-03-27*
