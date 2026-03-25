# Phase 2: Portfolio Shell - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the portfolio home page on top of the existing `docs/index.html` skeleton. This phase delivers a centered hero section (name, title, bio, contact link) and a project card grid with thumbnail images, title, description, and tags. Navigation wiring (in-page project loading) is Phase 3 — cards can link directly to project HTML for now.

</domain>

<decisions>
## Implementation Decisions

### Hero / Bio Section
- **D-01:** Layout is a centered hero — name, "AI Engineer" title, short bio paragraph, and LinkedIn contact link, all centered horizontally above the project card grid.
- **D-02:** Narrative framing: transition story — data analyst background (graph analytics / Neo4j team) pivoting into AI Engineering, building AI-powered tools he personally uses and wants to share with others.
- **D-03:** Skills/technologies list is NOT included in the hero. Bio paragraph + LinkedIn contact link only. Clean and focused.
- **D-04:** Contact links: LinkedIn only (no email, GitHub, Twitter, or other links in the hero).

### Project Card Thumbnails
- **D-05:** Thumbnail type: app screenshot of the actual project UI. Authentic — shows what the project looks like.
- **D-06:** Image location: `docs/projects/{project-name}/thumbnail.png` — each project stores its own thumbnail alongside its own files. This is the extensibility pattern for future projects.
- **D-07:** Dimensions: 16:9 aspect ratio, ~800×450px. File name: `thumbnail.png`.

### Claude's Discretion
- **Bio copy text:** Write a short paragraph (2–3 sentences) based on D-02 framing. No need to match exact words — capture the transition story naturally.
- **Card thumbnail placeholder:** If no screenshot exists at build time, use a CSS-only placeholder (gradient or muted block) with the same 16:9 dimensions so the layout doesn't break. Replace with the real screenshot once captured.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — HOME-01, HOME-02, SHOW-01, SHOW-02 are the active requirements for this phase. Read the full entries.
- `.planning/ROADMAP.md` §Phase 2 — Success criteria (logo top-left, intro section visible, card grid visible with at least one card).

### Existing Code
- `docs/index.html` — The existing portfolio skeleton. Build Phase 2 on top of this file. It already has: GitHub-dark color scheme, logo in header top-left, card grid structure (auto-fill, minmax 280px), cards with title/description/tags, one card linking to the calculator. Do NOT rewrite from scratch — extend it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/index.html`: Full skeleton with CSS variables, card grid, and one working card entry. Extend this — don't replace it.
- `docs/projects/calculator/img/logo_2.png`: Logo already in use in the header — HOME-01 is structurally done, just needs styling refinement if needed.
- Color scheme: GitHub-dark palette already defined (`--bg: #0d1117`, `--surface: #161b22`, `--accent: #58a6ff`, etc.). Hero and thumbnail styles should use these same variables for consistency.

### Established Patterns
- Cards use `<a class="card" href="...">` with `border-color` transition on hover. Thumbnail should slot in above the text content inside this same card element.
- Tags use `<span class="tag">` inside `<div class="tags">`. Pattern already works — reuse it.

### Integration Points
- The hero section goes between `<header>` and the `.projects` grid inside `<main>`. The existing `<main>` has a `<h2>Projects</h2>` placeholder — that gets replaced with the full hero + grid.
- Phase 3 will change card `href` links to in-page JS navigation. Phase 2 can keep the direct `href` links — they'll be refactored in Phase 3.

</code_context>

<specifics>
## Specific Ideas

- The bio should read as a personal, first-person-implied paragraph, not a formal resume bio. Warm but professional tone consistent with the clean dark aesthetic.
- Thumbnail file at `docs/projects/calculator/thumbnail.png` — this file needs to be created (screenshot capture) as part of Phase 2 execution or noted as a task for the user to provide.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-portfolio-shell*
*Context gathered: 2026-03-25*
