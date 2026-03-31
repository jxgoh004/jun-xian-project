# Requirements: Personal Portfolio Website

**Defined:** 2026-03-18
**Core Value:** Visitors quickly understand who I am as a developer and interact with my working projects in a professional, accessible, single-page experience.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Home Page

- [x] **HOME-01**: Home page displays personal logo in top-left corner
- [x] **HOME-02**: Home page includes introduction section with bio, skills/technologies, and contact links

### Project Showcase

- [x] **SHOW-01**: Home page displays project showcase section with visual card grid
- [x] **SHOW-02**: Each project card shows title, thumbnail image, description, and category tags
- [x] **SHOW-03**: Intrinsic value calculator is integrated as the first featured project

### Navigation

- [x] **NAV-01**: Clicking a project card loads that project running in-page (no new tab/window)
- [x] **NAV-02**: Clicking the logo returns user to home page from any project view

### Design & Performance

- [ ] **PERF-01**: Site uses modern, clean aesthetic with whitespace and professional styling
- [ ] **PERF-02**: Site is fully responsive across mobile, tablet, and desktop
- [ ] **PERF-03**: Site passes Core Web Vitals (optimized images, fast loading, LCP < 2.5s)

### Deployment

- [x] **DEPLOY-01**: Site is deployable to GitHub Pages as a static site
- [x] **DEPLOY-02**: Site structure allows adding future projects via code editing

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Polish

- **POLISH-01**: Dark mode toggle with WCAG AA contrast compliance
- **POLISH-02**: Smooth animations and hover effects on cards and navigation
- **POLISH-03**: Performance badge displaying Lighthouse score

### Content

- **CONT-01**: Project case studies with problem/approach/outcome context
- **CONT-02**: Live GitHub activity integration showing recent commits

### Portfolio Expansion

- **PORT-01**: Additional projects added to showcase grid
- **PORT-02**: Downloadable resume / link to LinkedIn

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Separate tabs/windows for projects | Projects run in-page to maintain single-site experience |
| Backend CMS or admin panel | Will add projects by editing code with Claude |
| Blog or article section | Focused purely on project showcase for v1 |
| Contact form with backend | Mailto links + social links are sufficient; no server needed |
| Skill bars / progress charts | Dated pattern (pre-2020); simple tech list preferred |
| Auto-playing video backgrounds | Performance and accessibility risk |
| Authentication / user accounts | Public portfolio site, no login needed |
| Real-time analytics or tracking | Privacy-focused, keep it simple |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HOME-01 | Phase 2 | Complete |
| HOME-02 | Phase 2 | Complete |
| SHOW-01 | Phase 2 | Complete |
| SHOW-02 | Phase 2 | Complete |
| SHOW-03 | Phase 3 | Complete |
| NAV-01 | Phase 3 | Complete |
| NAV-02 | Phase 3 | Complete |
| PERF-01 | Phase 4 | Pending |
| PERF-02 | Phase 4 | Pending |
| PERF-03 | Phase 4 | Pending |
| DEPLOY-01 | Phase 1 | Complete |
| DEPLOY-02 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after roadmap creation*
