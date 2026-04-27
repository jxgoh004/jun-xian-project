# Roadmap: Personal Portfolio Website

## Overview

The project transforms an existing Flask-served intrinsic value calculator into a static portfolio site hosted on GitHub Pages. The work moves in four delivery boundaries: first standing up the static site structure and deployment pipeline, then building the portfolio home page with project cards, then wiring the calculator as the first in-page project with working navigation, and finally polishing design and performance so the site meets professional standards across all devices.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Static Foundation** - Restructure project for GitHub Pages and establish deployment pipeline (completed 2026-03-23)
- [x] **Phase 2: Portfolio Shell** - Build home page with logo, bio, and project card grid (completed 2026-03-27)
- [x] **Phase 3: Calculator Integration** - Wire intrinsic value calculator as first in-page project with navigation (completed 2026-03-31)
- [x] **Phase 4: Design and Performance** - Polish styling, responsiveness, and Core Web Vitals (completed 2026-04-04)

## Phase Details

### Phase 1: Static Foundation
**Goal**: A deployable static site structure exists on GitHub Pages and the project is organized for future expansion
**Depends on**: Nothing (first phase)
**Requirements**: DEPLOY-01, DEPLOY-02
**Success Criteria** (what must be TRUE):
  1. Visiting the GitHub Pages URL loads a page (no 404, no broken deployment)
  2. The repository file structure separates the portfolio shell from project assets so adding a new project requires only adding files and a card entry
  3. The existing Render-hosted API is reachable from the static frontend (CORS verified)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Restructure repo into docs/ directory with portfolio shell and calculator project subfolder
- [ ] 01-02-PLAN.md — Enable GitHub Pages deployment and verify Render API CORS

### Phase 2: Portfolio Shell
**Goal**: Visitors can land on the home page, read who you are, and see the project grid
**Depends on**: Phase 1
**Requirements**: HOME-01, HOME-02, SHOW-01, SHOW-02
**Success Criteria** (what must be TRUE):
  1. The personal logo appears in the top-left corner of the home page
  2. The introduction section is visible with bio text, a list of technologies, and at least one contact link
  3. The project showcase grid is visible with at least one card displaying a title, thumbnail image, description, and category tags
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Add hero section with bio and LinkedIn link, section label, and card thumbnail support

### Phase 3: Calculator Integration
**Goal**: Visitors can click the intrinsic value calculator card and use the full calculator without leaving the site, and can return home via the logo
**Depends on**: Phase 2
**Requirements**: SHOW-03, NAV-01, NAV-02
**Success Criteria** (what must be TRUE):
  1. Clicking the intrinsic value calculator card loads the calculator UI in-page (no new tab, no full page reload)
  2. The calculator fetches stock data from the Render API and displays results identically to the standalone version
  3. Clicking the logo from inside the calculator view returns the visitor to the home page
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Implement hash routing, iframe calculator embed, and logo home link
- [x] 03-02-PLAN.md — Deploy and verify CORS on live GitHub Pages site

### Phase 4: Design and Performance
**Goal**: The site looks and feels professional on all screen sizes and loads fast enough to pass Core Web Vitals
**Depends on**: Phase 3
**Requirements**: PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):
  1. The site renders correctly and is usable on mobile (320px), tablet (768px), and desktop (1280px+) viewports
  2. The visual design uses consistent whitespace, typography, and color so the overall impression is clean and modern
  3. Lighthouse LCP is under 2.5s and images are optimized (compressed, correct format, lazy-loaded where appropriate)
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Responsive layout (full-width main, 1200px card grid cap), mobile breakpoint at 640px, fade view transition, card hover lift
- [x] 04-02-PLAN.md — Title tag and bio rewrite, WebP thumbnail conversion with picture element, lazy loading, Lighthouse LCP verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Static Foundation | 2/2 | Complete   | 2026-03-23 |
| 2. Portfolio Shell | 1/1 | Complete   | 2026-03-27 |
| 3. Calculator Integration | 2/2 | Complete   | 2026-03-31 |
| 4. Design and Performance | 2/2 | Complete   | 2026-04-04 |
| 5. S&P 500 Stock Screener | 2/2 | Complete   | 2026-04-05 |
| 6. Website Marketing Revamp | 0/3 | Not started | — |

### Phase 5: S&P 500 Stock Screener Page

**Goal:** Deliver a second portfolio project: an S&P 500 stock screener with pre-calculated DCF values, sortable/filterable table, and calculator link-through
**Depends on:** Phase 4
**Plans:** 2/2 plans complete (completed 2026-04-05)

Plans:
- [x] 05-01-PLAN.md — S&P 500 batch DCF pipeline (scripts/fetch_sp500.py + nightly GitHub Actions workflow)
- [x] 05-02-PLAN.md — Screener frontend (docs/projects/screener/index.html)

### Phase 6: Website Marketing Revamp

**Goal:** Elevate the portfolio to MNC production standards — fix SEO gaps, rewrite hero messaging to reflect the platform's true purpose (sharing useful tools with everyone), add proper CTAs, fix accessibility, and wire up Open Graph for professional sharing previews
**Depends on:** Phase 5
**Success Criteria** (what must be TRUE):
  1. Sharing the portfolio URL on LinkedIn/Slack shows a rich preview with title, description, and OG image
  2. The hero section communicates the platform's purpose (useful tools for everyone) within 3 seconds, not a career summary
  3. There is a visible, styled CTA in the hero (LinkedIn button at minimum)
  4. All interactive elements are keyboard-navigable with visible focus styles
  5. Every page has a unique `<meta name="description">` and correct heading hierarchy (single `<h1>` per page)
  6. `robots.txt` and `sitemap.xml` exist in the docs/ root
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Hero rewrite + CTA buttons (messaging, LinkedIn button, value prop)
- [x] 06-02-PLAN.md — SEO: meta descriptions, OG tags, heading hierarchy, page titles, robots.txt, sitemap.xml, canonical tags
- [x] 06-03-PLAN.md — Accessibility + UX: focus styles, card `<a>` elements, form labels, badge text, screener back-link
