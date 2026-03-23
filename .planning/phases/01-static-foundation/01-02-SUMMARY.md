---
phase: 01-static-foundation
plan: 02
subsystem: infra
tags: [github-pages, cors, render, deployment, static-site]

# Dependency graph
requires:
  - phase: 01-static-foundation/01-01
    provides: "docs/ directory structure committed and pushed, ready for GitHub Pages to serve"
provides:
  - "GitHub Pages enabled on repository, serving docs/ from main branch"
  - "Live portfolio URL accessible from the public internet"
  - "Render API CORS verified — GitHub Pages origin accepted by backend"
  - "Calculator frontend fully operational end-to-end on the public deployment"
affects: [03-portfolio-polish, 04-ci-automation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["API_BASE_URL constant pattern — single hostname check handles local vs production transparently"]

key-files:
  created: []
  modified:
    - "docs/projects/calculator/index.html"

key-decisions:
  - "CORS(app) with allow-all origins on Render is sufficient for current scale — no origin allowlist needed at this stage"
  - "Verify panel re-renders on method switch — bug fix committed alongside deployment verification"

patterns-established:
  - "Deployment verification gate: user confirms site loads and API is reachable before marking plan complete"

requirements-completed: [DEPLOY-01]

# Metrics
duration: ~5 days (multi-session including Render cold-start iteration)
completed: 2026-03-23
---

# Phase 1 Plan 2: GitHub Pages Deployment and CORS Verification Summary

**GitHub Pages enabled on main/docs with Render API CORS confirmed live — calculator fetches stock data from the public deployment**

## Performance

- **Duration:** ~5 days (multi-session; most time was Render cold-start iteration and bug fix between sessions)
- **Started:** 2026-03-18
- **Completed:** 2026-03-23
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments
- GitHub Pages enabled on the repository, serving from `docs/` on the `main` branch
- Public portfolio URL is live and returns HTTP 200 — no 404
- Calculator page at `/projects/calculator/` loads correctly with dark theme
- Render API health check passes from the GitHub Pages origin (server status dot turns green)
- AAPL stock data fetch succeeds end-to-end — CORS fully working
- Bug fixed: verify panel now re-renders correctly when user switches valuation method

## Task Commits

Each task was committed atomically:

1. **Task 1: Enable GitHub Pages and push docs/ to remote** - `4cef77e` (chore)
2. **Task 2: Verify GitHub Pages loads and Render API CORS works** - user approved

**Bug fix (deviation):** `797213e` (fix: re-render verify panel when user switches valuation method)

## Files Created/Modified
- `docs/projects/calculator/index.html` - Verify panel re-render bug fixed (method switch now correctly re-renders output section)

## Decisions Made
- `CORS(app)` allow-all on Render is sufficient for current traffic level — no origin allowlist required at this stage
- Deployment verification required user approval as a hard gate before marking the plan complete

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Verify panel did not re-render when user switched valuation method**
- **Found during:** Task 2 (human verification of deployed site)
- **Issue:** After fetching data, switching the valuation method dropdown did not update the output panel — the panel stayed blank or showed stale content until re-fetch
- **Fix:** Added method-switch event listener to re-render the verify panel when the selected method changes, without requiring a new fetch
- **Files modified:** `docs/projects/calculator/index.html`
- **Verification:** Confirmed on live deployment — switching methods now immediately updates the output section
- **Committed in:** `797213e` (fix: re-render verify panel when user switches valuation method)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Bug fix was a UX correctness requirement for the verification step. No scope creep.

## Issues Encountered

- Render free tier cold-start added latency during initial verification — resolved by waiting 30 seconds for the instance to wake before retesting the health check. Not a CORS issue.

## User Setup Required

None - GitHub Pages was enabled via the `gh` CLI. No manual GitHub Settings navigation required.

## Next Phase Readiness
- Full deployment pipeline is live: static site on GitHub Pages, Python API on Render, CORS verified
- Phase 1 is complete — both plans executed and verified
- Phase 3 (portfolio polish) can proceed: navigation, about section, project descriptions
- Phase 4 (CI/automation) can also proceed: both the docs/ source and the Render deploy target are confirmed working
- No remaining blockers from the STATE.md CORS concern — CORS is confirmed working

---
*Phase: 01-static-foundation*
*Completed: 2026-03-23*
