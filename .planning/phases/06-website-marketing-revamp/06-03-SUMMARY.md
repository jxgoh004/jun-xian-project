---
plan: 06-03
phase: 06-website-marketing-revamp
status: complete
completed: 2026-04-28
commits:
  - 6395ed4
  - 0727d62
  - 68b6c85
key-files:
  modified:
    - docs/index.html
    - docs/projects/screener/index.html
    - docs/projects/calculator/index.html
---

## Summary

Fixed all accessibility gaps across the three portfolio pages: keyboard focus rings, semantic card anchors, screen-reader labels, and back-navigation links.

## What Was Built

**Task 1 — docs/index.html:**
- Added global `:focus-visible` CSS rule (blue box-shadow ring on all interactive elements)
- Converted both project cards from `<div class="card" role="link" tabindex="0">` to `<a href="#calculator">` / `<a href="#screener">` semantic anchor elements
- Removed manual `card.addEventListener('click')` and `card.addEventListener('keydown')` handlers — native anchor behaviour handles both click and Enter key
- Added `display: block; cursor: pointer` to `.card` CSS rule to preserve block layout

**Task 2 — docs/projects/screener/index.html:**
- Added global `:focus-visible` ring CSS block
- Added `.sr-only` utility class
- Added `<label for="search" class="sr-only">Search ticker or company</label>` before search input
- Added `<label for="sector-filter" class="sr-only">Filter by sector</label>` before sector select
- Added `aria-label="Valuation: {label}"` to valuation badge table cells in `renderTable()`
- Added `← Portfolio` back-link in header with `postMessage({ type: 'navigate', project: null })` handler

**Task 3 — docs/projects/calculator/index.html:**
- Added global `:focus-visible` ring CSS block
- Added `input:focus-visible, select:focus-visible` override for inputs
- Added `←` back-link arrow as first child of `<header>` with `postMessage({ type: 'navigate', project: null })` handler

## Deviations

None — executed exactly as planned.

## Self-Check: PASSED

- [x] focus-visible CSS present in all 3 files
- [x] Cards are `<a>` elements — role="link" and manual event listeners removed
- [x] sr-only labels associated to search and sector-filter inputs
- [x] aria-label on valuation badge cells
- [x] Back-link present in screener header (postMessage navigate null)
- [x] Back-link present in calculator header (postMessage navigate null)
