---
phase: 06-website-marketing-revamp
plan: "01"
subsystem: frontend
tags: [hero, messaging, cta, marketing, css]
dependency_graph:
  requires: []
  provides: [hero-value-prop-rewrite, linkedin-cta-button]
  affects: [docs/index.html]
tech_stack:
  added: []
  patterns: [hero-credential CSS class, hero-bio/hero-bio-secondary split, hero-cta button pattern]
key_files:
  created: []
  modified:
    - docs/index.html
decisions:
  - "Replaced hero-value-prop/bullets/social-proof blocks with hero-bio + hero-bio-secondary — simpler messaging hierarchy, value-prop leads"
  - "LinkedIn CTA uses dedicated .hero-cta class with var(--accent) border rather than reusing .btn-secondary — visually distinct from secondary nav buttons"
  - "Kept GitHub and email buttons as .btn btn-secondary; LinkedIn is the sole hero-cta to draw attention to the professional profile"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-27T14:39:16Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 06 Plan 01: Hero Messaging Rewrite and LinkedIn CTA Button Summary

**One-liner:** Rewrote hero section to lead with tool-sharing value prop and added accent-bordered LinkedIn CTA button replacing inline text link.

## What Was Built

The portfolio hero section in `docs/index.html` was overhauled in two commits:

**Task 1 — Hero messaging rewrite:**
- Expanded hero title from "AI Engineer" to "AI Engineer · Graph Analytics · LLM Applications"
- Added `hero-credential` line: "AI Singapore Associate AI Engineer (2025)"
- Replaced the old `hero-value-prop` / `hero-bullets` / `social-proof` blocks with two new paragraphs:
  - `hero-bio`: "I build useful tools — things I use every day and want to share with everyone. This is where they live."
  - `hero-bio-secondary`: BSc + Neo4j + AISG background (moved to secondary position)
- Added CSS for `hero-credential` and `hero-bio-secondary` including mobile breakpoint rules

**Task 2 — LinkedIn CTA button:**
- Added `.hero-cta` CSS rule with `border: 1px solid var(--accent)`, `padding: 7px 16px`, `border-radius: 6px`, accent color text, and hover background
- Replaced LinkedIn's `btn btn-secondary` (with icon) with a clean `hero-cta` text button
- No old `.hero a` generic rules existed to remove (file was already using `.btn` system)

## Deviations from Plan

**1. [Rule 1 - Adaptation] hero-value-prop/bullets/social-proof replaced, not hero-bio**
- **Found during:** Task 1 setup
- **Issue:** Plan expected `<p class="hero-bio">` in the file but the file had been significantly updated since planning — it had `hero-value-prop`, `hero-bullets`, and `social-proof` sections instead
- **Fix:** Applied the spirit of the plan — replaced all three old sections with the new `hero-bio` + `hero-bio-secondary` structure as specified. Old CSS classes (`hero-value-prop`, `hero-bullets`, `social-proof`, `proof-item`) removed.
- **Files modified:** docs/index.html
- **Commits:** ea57ab0, 8009ed1

**2. [Rule 1 - Adaptation] LinkedIn already styled as .btn; icon SVG removed**
- **Found during:** Task 2 setup
- **Issue:** Plan expected a plain inline text link; file had LinkedIn as `.btn btn-secondary` with an SVG icon
- **Fix:** Replaced with clean `hero-cta` class as specified. Removed the SVG icon to match the plan's plain text button design. LinkedIn URL kept identical.
- **Files modified:** docs/index.html
- **Commit:** 8009ed1

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | ea57ab0 | feat(06-01): rewrite hero messaging with tool-sharing value prop and expanded title |
| 2 | 8009ed1 | feat(06-01): convert LinkedIn link to styled hero-cta button with accent border |

## Known Stubs

None — all elements render from static HTML with no placeholder data.

## Threat Flags

No new trust boundaries introduced. LinkedIn link retains existing `rel="noopener noreferrer"` and hardcoded URL per T-06-01 disposition (accept).

## Self-Check: PASSED

| Item | Status |
|------|--------|
| docs/index.html | FOUND |
| 06-01-SUMMARY.md | FOUND |
| commit ea57ab0 | FOUND |
| commit 8009ed1 | FOUND |
