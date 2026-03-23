# Roadmap: Personal Portfolio Website

## Overview

The project transforms an existing Flask-served intrinsic value calculator into a static portfolio site hosted on GitHub Pages. The work moves in four delivery boundaries: first standing up the static site structure and deployment pipeline, then building the portfolio home page with project cards, then wiring the calculator as the first in-page project with working navigation, and finally polishing design and performance so the site meets professional standards across all devices.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Static Foundation** - Restructure project for GitHub Pages and establish deployment pipeline (completed 2026-03-23)
- [ ] **Phase 2: Portfolio Shell** - Build home page with logo, bio, and project card grid
- [ ] **Phase 3: Calculator Integration** - Wire intrinsic value calculator as first in-page project with navigation
- [ ] **Phase 4: Design and Performance** - Polish styling, responsiveness, and Core Web Vitals

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
**Plans**: TBD

Plans:
- [ ] 02-01: Build home page HTML/CSS with logo, intro section, and project card grid

### Phase 3: Calculator Integration
**Goal**: Visitors can click the intrinsic value calculator card and use the full calculator without leaving the site, and can return home via the logo
**Depends on**: Phase 2
**Requirements**: SHOW-03, NAV-01, NAV-02
**Success Criteria** (what must be TRUE):
  1. Clicking the intrinsic value calculator card loads the calculator UI in-page (no new tab, no full page reload)
  2. The calculator fetches stock data from the Render API and displays results identically to the standalone version
  3. Clicking the logo from inside the calculator view returns the visitor to the home page
**Plans**: TBD

Plans:
- [ ] 03-01: Integrate calculator frontend into portfolio in-page navigation system
- [ ] 03-02: Verify calculator API calls work end-to-end from GitHub Pages domain

### Phase 4: Design and Performance
**Goal**: The site looks and feels professional on all screen sizes and loads fast enough to pass Core Web Vitals
**Depends on**: Phase 3
**Requirements**: PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):
  1. The site renders correctly and is usable on mobile (320px), tablet (768px), and desktop (1280px+) viewports
  2. The visual design uses consistent whitespace, typography, and color so the overall impression is clean and modern
  3. Lighthouse LCP is under 2.5s and images are optimized (compressed, correct format, lazy-loaded where appropriate)
**Plans**: TBD

Plans:
- [ ] 04-01: Implement responsive layout and mobile breakpoints
- [ ] 04-02: Apply design system (spacing, typography, color) and optimize images for Core Web Vitals

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Static Foundation | 2/2 | Complete   | 2026-03-23 |
| 2. Portfolio Shell | 0/1 | Not started | - |
| 3. Calculator Integration | 0/2 | Not started | - |
| 4. Design and Performance | 0/2 | Not started | - |
