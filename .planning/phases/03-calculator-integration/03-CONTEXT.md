# Phase 3: Calculator Integration - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the intrinsic value calculator as the first in-page project. Clicking its card on the home page loads the calculator without a page reload or new tab. Clicking the logo from inside the calculator returns the visitor to the home page. Visual polish and responsive design are Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Embed mechanism
- **D-01:** Load the calculator via `<iframe src="projects/calculator/index.html">` — no changes to the calculator's own HTML, CSS, or JS
- **D-02:** The home view and project view are separate DOM sections; JS shows/hides them when navigating
- **D-03:** The iframe is created/inserted when navigating to a project, not pre-rendered on page load

### URL and routing
- **D-04:** Hash routing — URL updates to `#calculator` when inside the project, `#home` (or no hash) on the home page
- **D-05:** Browser back button must work — navigating back from `#calculator` returns to `#home`
- **D-06:** Direct links must work — visiting `portfolio-url/#calculator` opens the calculator directly, not the home page

### Logo / back navigation
- **D-07:** Logo in the header is always a clickable home link (navigates to `#home`). No-op behavior on the home page is acceptable.
- **Claude's Discretion:** Whether to show a visible "← Back" breadcrumb or rely solely on the logo and browser back button

### CORS verification
- **D-08:** Phase 3 must include an explicit verification step: open the deployed GitHub Pages site, load the calculator via the in-page iframe, attempt a real stock fetch, and confirm no CORS errors in devtools
- **D-09:** If CORS is blocked, fix is a one-line Flask-CORS config update on Render (`origins="*"` or explicit GitHub Pages domain). User has Render deploy access and redeploys manually.
- **D-10:** The calculator's `API` constant already handles prod vs local (`hostname === 'localhost'`). No changes needed to the API URL logic.

### Custom domain (future — no impact on Phase 3)
- **D-11:** A Cloudflare-managed custom domain will be pointed to GitHub Pages after the site is built. This requires only a CNAME file in `docs/` and a DNS record — no code changes. Phase 3 should be built and verified against the existing `github.io` URL; domain switching requires zero rework.

</decisions>

<specifics>
## Specific Ideas

- User intends to purchase a custom domain via Cloudflare and point it to GitHub Pages after the portfolio is complete. This is a post-build DNS task, not a development concern for this phase.
- Manual Render redeployment is the deployment method for the Flask API — no CI/CD pipeline.

</specifics>

<canonical_refs>
## Canonical References

No external specs or ADRs. Requirements are fully captured in the decisions above and the files below.

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — NAV-01, NAV-02, SHOW-03 are the three requirements this phase closes
- `.planning/ROADMAP.md` §Phase 3 — Success criteria and plan breakdown

### Existing code (read before planning)
- `docs/index.html` — Current home page; cards use `<a href="...">` hard navigation that must be converted to JS hash routing
- `docs/projects/calculator/index.html` — Full standalone calculator page; stays untouched per D-01. Note API constant at bottom of file (line ~707).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets
- `.card` elements in `docs/index.html` — currently `<a href="...">`, will become JS-triggered navigation hooks
- `projects/calculator/img/logo_2.png` — already used as the header logo `<img>`; needs to become a clickable `<a>` wrapping the img

### Established patterns
- Vanilla JavaScript only — no framework, no build step
- Dark theme CSS variables (`--bg`, `--surface`, `--border`, `--accent`) already defined in `docs/index.html`
- Calculator API constant: `hostname === 'localhost'` check already handles prod vs local correctly — no changes needed

### Integration points
- `docs/index.html` header `<img>` → wrap in `<a>` pointing to `#home`
- `.card` click handlers → replace `href` with JS navigation to `#calculator`
- New JS block needed in `docs/index.html`: hash routing listener (`hashchange`), show/hide logic, iframe insert/remove

</code_context>

<deferred>
## Deferred Ideas

- Animated transitions between home and project views — Phase 4 (design and performance)
- Custom domain DNS setup (Cloudflare CNAME → GitHub Pages) — post-Phase 4, no code changes required
- Additional projects beyond the calculator — future milestone (DEPLOY-02 pattern: add `docs/projects/{name}/` + card entry)

</deferred>

---

*Phase: 03-calculator-integration*
*Context gathered: 2026-03-31*
