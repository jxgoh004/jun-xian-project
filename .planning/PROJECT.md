# Personal Portfolio Website

## Current Milestone: v2.0 Inside Bar Pattern Scanner

**Goal:** Add a computer-vision-powered inside bar spring setup scanner as a new portfolio project — algorithmic detection, YOLOv8 training, backtesting, and a live-updating frontend screener.

**Target features:**
- Algorithmic pattern detection engine (Python, full inside bar spring ruleset)
- Training dataset generation (2D OHLC chart rendering + auto-annotation)
- YOLOv8 model training & ONNX export
- Backtesting engine (10-year historical — win rate, avg return, hold period)
- Nightly batch pipeline via GitHub Actions → `docs/projects/patterns/data.json`
- Frontend portfolio page (screener table + per-stock drilldown with chart, confidence, stats)

---

## What This Is

A personal portfolio website that showcases my projects and introduces who I am. The site features a clean, modern home page with a brief bio, technical skills, and contact information, along with a visual grid of project cards. Visitors can click on any project card to view and interact with that project directly within the site. The intrinsic value calculator is the first featured project, with the structure designed to easily accommodate future projects.

## Core Value

Visitors can quickly understand who I am as a developer and interact with my working projects in a professional, accessible, single-page experience.

## Requirements

### Validated

<!-- Existing intrinsic value calculator functionality -->

- ✓ User can fetch stock data by entering a ticker symbol — existing
- ✓ User can view verified financial metrics from Yahoo Finance and FinViz — existing
- ✓ User can calculate intrinsic value using DCF methodology — existing
- ✓ User can compare intrinsic value to current stock price with discount/premium percentage — existing
- ✓ User can toggle between OCF and FCF valuation methods — existing
- ✓ User can adjust growth rates and discount rates before calculating — existing
- ✓ Application displays detailed 20-year projection breakdown — existing

### Active

<!-- Portfolio website features to be built -->

- [ ] Home page displays personal logo in top-left corner
- [ ] Home page includes introduction section with bio, skills/technologies, and contact links
- [ ] Home page displays project showcase section with visual card grid
- [ ] Each project card shows: title, thumbnail image, description, and category tags
- [ ] Clicking a project card navigates to that project running in-page
- [ ] Clicking the logo returns user to home page from any project
- [ ] Intrinsic value calculator is integrated as the first featured project
- [ ] Site uses modern, clean aesthetic with whitespace and professional styling
- [ ] Site structure allows easy addition of future projects via code editing
- [ ] Site is deployable to GitHub Pages as a static site

### Active (Milestone v2.0 — Inside Bar Pattern Scanner)

- [x] **PAT-01**: Pattern detection engine identifies bullish inside bar spring setups across S&P 500 tickers using the defined 5-bar ruleset _(Validated in Phase 7: Detection Engine — DET-01..DET-04 covered by 12 unit tests + 11 live integration tests over user-approved KNOWN_SETUPS)_
- [ ] **PAT-02**: Training dataset generator renders 2D OHLC chart images and produces YOLOv8-compatible annotations
- [ ] **PAT-03**: YOLOv8 model is trained on annotated data and exported as ONNX for offline inference
- [ ] **PAT-04**: Backtesting engine computes win rate, average return, and hold period stats per detected setup over 10-year history
- [ ] **PAT-05**: Nightly GitHub Actions pipeline runs detection across S&P 500 and writes results to `docs/projects/patterns/data.json`
- [ ] **PAT-06**: Frontend screener page lists current detections in a filterable/sortable table
- [ ] **PAT-07**: Per-stock drilldown shows annotated chart, detection confidence score, and backtest stats
- [ ] **PAT-08**: Pattern scanner is added as a project card on the portfolio home page

### Out of Scope

- Separate tab/window opening for projects — projects run in-page to maintain single-site experience
- Backend CMS or admin panel — will add projects by editing code with Claude
- Blog or article section — focused purely on project showcase
- Downloadable resume/CV — keeping it simple for v1, can add later
- Authentication or user accounts — public portfolio site
- Real-time analytics or tracking — keep it simple and privacy-focused

## Context

**Existing Codebase:**
- Working intrinsic value calculator built with Flask backend (Python) and vanilla JavaScript frontend
- Current deployment on Render with Flask serving both API and static HTML
- Single-page application architecture with REST API for stock data fetching
- Logo asset ready at `./img/logo_2.png`

**Technical Environment:**
- Flask 3.1.3 backend with Python 3.x
- Vanilla JavaScript (no framework dependencies)
- Currently uses Flask to serve static HTML

**Transition Needed:**
- Moving from Flask-served single app to static portfolio site hosting multiple projects
- Need to restructure for GitHub Pages deployment (static-only, no Flask server)
- Intrinsic value calculator will need backend API hosted separately (keep Render deployment) while frontend integrates into portfolio

## Constraints

- **Hosting**: GitHub Pages (static site only) — intrinsic value calculator backend stays on Render, frontend calls Render API
- **Navigation**: Logo must be in top-left position and clicking it returns to home
- **Project Display**: Projects must run in-page, not open in new tabs or windows
- **Design**: Modern, clean aesthetic with minimalist approach and professional appearance
- **Maintenance**: New projects added via manual code editing with Claude assistance

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GitHub Pages for hosting | Free, reliable, integrates with git workflow, perfect for static portfolio | — Pending |
| Keep intrinsic value calculator API on Render | Calculator needs Python backend; GitHub Pages is static-only; split frontend/backend | — Pending |
| Vanilla JavaScript (no framework) | Existing calculator uses vanilla JS; consistency and simplicity for small site | — Pending |
| Single-page navigation | Clean UX, fast transitions, avoids full page reloads, maintains context | — Pending |
| Cards/grid layout for projects | Modern standard for portfolios, visually appealing, scales well as projects are added | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-02 — Phase 7 (Detection Engine) complete*
