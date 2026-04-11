# Personal Portfolio Website

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

### Active (Phase 6 — Marketing Revamp)

- [ ] Hero section communicates platform purpose (useful tools for everyone) within 3 seconds — not a career bio summary
- [ ] LinkedIn CTA is a styled button, not an inline text link
- [ ] Every page has a unique `<meta name="description">` (155 chars)
- [ ] All pages have Open Graph + Twitter Card meta tags with OG image
- [ ] Heading hierarchy correct: single `<h1>` per page, `<h1>` is not "Portfolio" header label
- [ ] Page titles are keyword-rich and unique per page
- [ ] `robots.txt` and `sitemap.xml` exist in `docs/` root
- [ ] `<link rel="canonical">` on every page
- [ ] All interactive elements have visible `:focus-visible` styles
- [ ] Project cards are `<a>` elements (not `<div role="link">`) for keyboard/AT semantics
- [ ] Screener search and sector filter inputs have `<label>` elements
- [ ] Valuation badges include text content, not color only
- [ ] Screener and calculator pages have a "← Portfolio" back-link in header

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

---
*Last updated: 2026-03-17 after initialization*
