---
phase: 04-design-and-performance
plan: "04-02"
subsystem: frontend
tags: [html, webp, performance, seo, lighthouse, core-web-vitals, pillow]
dependency_graph:
  requires:
    - phase: 04-01
      provides: full-width-layout, mobile-breakpoint, fade-navigation, card-hover
  provides:
    - updated-page-title
    - rewritten-bio-paragraph
    - webp-thumbnail-with-picture-element
  affects: [docs/index.html, docs/projects/calculator/thumbnail.webp]
tech_stack:
  added: [Pillow (image conversion, one-time use)]
  patterns: [picture element with WebP source and PNG fallback, loading=lazy with explicit width/height for CLS prevention]
key_files:
  created:
    - docs/projects/calculator/thumbnail.webp
  modified:
    - docs/index.html
key_decisions:
  - "Used em dash character directly in title tag rather than &mdash; HTML entity (plan specified this)"
  - "WebP quality=80 balances file size reduction with visual fidelity"
  - "Explicit width=1854 height=771 on img tag prevents CLS by reserving correct aspect ratio before image loads"
patterns-established:
  - "picture element pattern: <source type=image/webp> + <img> PNG fallback for progressive enhancement"
  - "Always add loading=lazy and explicit dimensions to card thumbnail images"
requirements-completed: [PERF-01, PERF-03]
duration: "2m"
completed: "2026-04-04"
---

# Phase 4 Plan 02: Typography polish, image optimization, Core Web Vitals verification — Summary

**Page title updated to 'Goh Jun Xian — Portfolio', bio rewritten with Neo4j/AISG/AI-tools narrative, and calculator thumbnail converted to WebP with picture element and lazy loading.**

## Performance

- **Duration:** ~3h 30min (including Lighthouse checkpoint pause for human verification)
- **Started:** 2026-04-04T05:46:25Z
- **Completed:** 2026-04-04T15:19:07Z
- **Tasks:** 3 of 3 (all complete)
- **Files modified:** 2

## Accomplishments

- Page title changed from "Portfolio" to "Goh Jun Xian — Portfolio" for browser tab and SEO
- Bio paragraph rewritten: removed "dwell" typo and "Bachelor of Sciences" opener; now cleanly describes Neo4j background, AISG Associate AI Engineer program, and AI-powered tools focus
- Stale TODO comment about LinkedIn username removed
- Calculator thumbnail converted to WebP at quality=80 using Pillow
- img tag replaced with picture element: WebP source + PNG fallback, loading=lazy, width=1854 height=771 for zero CLS

## Task Commits

Each task was committed atomically:

1. **Task 4-02-01: Update page title and rewrite bio paragraph** - `e33edb0` (feat)
2. **Task 4-02-02: Convert thumbnail to WebP and replace with picture element** - `2759803` (feat)
3. **Task 4-02-03: Lighthouse Core Web Vitals verification** - Human-verified checkpoint (approved — LCP < 2.5s confirmed on live GitHub Pages URL; bc33f80 fix also confirmed visible)

## Files Created/Modified

- `docs/index.html` - Updated title tag, rewritten bio, removed TODO comment, picture element with lazy loading
- `docs/projects/calculator/thumbnail.webp` - New WebP conversion of thumbnail.png at quality=80

## Decisions Made

- Used em dash (—) character directly in title tag per plan specification, not `&mdash;` entity
- WebP quality=80 chosen per plan for good file-size-to-quality tradeoff
- Explicit img dimensions (1854x771) match actual PNG dimensions from research file — prevents CLS

## Deviations from Plan

### Unplanned: Merge of 04-01 feature branch before applying 04-02 changes

- **Found during:** Pre-execution setup
- **Issue:** The 04-01 feature commits (full-width layout, mobile breakpoint, fade transitions) were on branch `worktree-agent-ab3a9165` and had not been merged to main. The docs/index.html on main still had the old 04-01 state.
- **Fix:** Merged `worktree-agent-ab3a9165` into main before applying 04-02 changes. Merge commit `35414a4` incorporates all 04-01 feature work.
- **Impact:** No scope creep — this was a necessary prerequisite step, not new work.

## Issues Encountered

- Main branch was missing the 04-01 feature commits (they were on a worktree branch). Resolved by merging the worktree branch before proceeding. No conflicts.

## Known Stubs

None — all changes are fully wired and functional.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 4 (Design and Performance) is fully complete — all 2 plans executed, all requirements met (PERF-01, PERF-02 via 04-01, PERF-03)
- Lighthouse Core Web Vitals verified on live GitHub Pages: LCP under 2.5s (human-approved)
- The portfolio is production-ready: responsive layout, mobile breakpoints, fade transitions, card hover, professional title/bio, and optimized WebP thumbnail are all live
- No remaining phases planned — project milestone v1.0 is complete

---
*Phase: 04-design-and-performance*
*Completed: 2026-04-04*
