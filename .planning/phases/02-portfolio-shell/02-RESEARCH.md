# Phase 2: Portfolio Shell - Research

**Researched:** 2026-03-25
**Domain:** Vanilla HTML/CSS — static portfolio page extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Layout is a centered hero — name, "AI Engineer" title, short bio paragraph, and LinkedIn contact link, all centered horizontally above the project card grid.
- **D-02:** Narrative framing: transition story — data analyst background (graph analytics / Neo4j team) pivoting into AI Engineering, building AI-powered tools he personally uses and wants to share with others.
- **D-03:** Skills/technologies list is NOT included in the hero. Bio paragraph + LinkedIn contact link only. Clean and focused.
- **D-04:** Contact links: LinkedIn only (no email, GitHub, Twitter, or other links in the hero).
- **D-05:** Thumbnail type: app screenshot of the actual project UI. Authentic — shows what the project looks like.
- **D-06:** Image location: `docs/projects/{project-name}/thumbnail.png` — each project stores its own thumbnail alongside its own files. This is the extensibility pattern for future projects.
- **D-07:** Dimensions: 16:9 aspect ratio, ~800×450px. File name: `thumbnail.png`.

### Claude's Discretion
- **Bio copy text:** Write a short paragraph (2–3 sentences) based on D-02 framing. No need to match exact words — capture the transition story naturally.
- **Card thumbnail placeholder:** If no screenshot exists at build time, use a CSS-only placeholder (gradient or muted block) with the same 16:9 dimensions so the layout doesn't break. Replace with the real screenshot once captured.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HOME-01 | Home page displays personal logo in top-left corner | Logo (`docs/projects/calculator/img/logo_2.png`) is already in the header `<img>` tag. Structure is complete; styling may need minor refinement. |
| HOME-02 | Home page includes introduction section with bio, skills/technologies, and contact links | CONTEXT.md D-03 overrides the "skills/technologies" part — bio + LinkedIn link only. Hero section implementation defined in UI-SPEC.md. |
| SHOW-01 | Home page displays project showcase section with visual card grid | `.projects` grid already exists with `auto-fill, minmax(280px, 1fr)`. Needs thumbnail CSS added; grid itself needs no structural change. |
| SHOW-02 | Each project card shows title, thumbnail image, description, and category tags | Existing card has h3/p/tags. Thumbnail `<img>` must be added as first child. CSS for 16:9 sizing and placeholder div required. |
</phase_requirements>

---

## Summary

Phase 2 is a purely static HTML/CSS extension of an existing file (`docs/index.html`). No new libraries, no build tools, no JavaScript changes. The existing skeleton already delivers the card grid, color system, and logo placement — Phase 2 adds a hero section and thumbnail support to each card.

The UI contract is fully specified in `02-UI-SPEC.md`. Every pixel decision has been made: element hierarchy, exact CSS property values, spacing tokens, copy text, color roles, and accessibility requirements. Research confirms that all patterns used are well-established vanilla CSS with no footguns at this scope.

The only open execution question is the calculator thumbnail (`docs/projects/calculator/thumbnail.png`) — the file does not exist yet. The plan must include a CSS placeholder path and a clear task for the user to supply the screenshot.

**Primary recommendation:** Extend `docs/index.html` in-place following the UI-SPEC exactly. Do not rewrite, do not introduce new files, do not add any JavaScript or external dependencies.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla HTML5 | — | Page structure | Project decision: no framework |
| Vanilla CSS3 | — | Styling (variables, grid, flexbox) | Project decision: no framework |
| Vanilla JS | — | None needed in this phase | Deferred to Phase 3 |

### Supporting

None. This phase has no external dependencies.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla HTML/CSS | Tailwind, Bootstrap | Locked out by project decision — vanilla only |
| CSS `aspect-ratio` | Padding-hack (56.25%) | `aspect-ratio: 16/9` is correct modern approach; padding hack is unnecessary on all supported browsers (Chrome 88+, Firefox 89+, Safari 15+) |
| CSS Grid auto-fill | Flexbox | Grid is already used and correct for this layout |

**Installation:** None required.

---

## Architecture Patterns

### File Structure (no change)

```
docs/
├── index.html                          # The only file modified in this phase
├── projects/
│   └── calculator/
│       ├── index.html                  # Unchanged
│       ├── img/
│       │   └── logo_2.png             # Logo already in use
│       └── thumbnail.png              # NEW — user must provide screenshot
```

No new files are created by the implementer except `thumbnail.png` (user task).

### Pattern 1: Hero Section Insertion Point

The hero `<section class="hero">` goes inside `<main>`, before the `<h3 class="section-label">Projects</h3>` heading. The existing `<h2>Projects</h2>` placeholder is replaced by the new structure:

```html
<!-- Source: docs/index.html existing structure + 02-UI-SPEC.md Component Inventory -->
<main>
  <section class="hero">
    <h2>Your Name</h2>
    <p class="hero-title">AI Engineer</p>
    <p class="hero-bio">I spent years doing graph analytics and working closely with the Neo4j team as a data analyst. Now I'm building AI-powered tools — things I actually use and want to share. This is where they live.</p>
    <a href="https://linkedin.com/in/YOUR-HANDLE">LinkedIn</a>
  </section>
  <h3 class="section-label">Projects</h3>
  <div class="projects">
    ...
  </div>
</main>
```

### Pattern 2: Thumbnail as First Child Inside `.card`

```html
<!-- Source: 02-UI-SPEC.md Component Inventory — Project Card section -->
<a class="card" href="projects/calculator/index.html">
  <img src="projects/calculator/thumbnail.png" alt="Intrinsic Value Calculator screenshot" width="100%">
  <!-- fallback when thumbnail.png absent: -->
  <!-- <div class="card-thumbnail-placeholder" aria-label="Intrinsic Value Calculator thumbnail — screenshot coming soon"></div> -->
  <h3>Intrinsic Value Calculator</h3>
  <p>...</p>
  <div class="tags">...</div>
</a>
```

Use the real `<img>` tag when the file exists. Use the placeholder `<div>` when it does not.

### Pattern 3: CSS for Hero and Thumbnail

All new CSS goes inside the existing `<style>` block in `docs/index.html`. No separate stylesheet needed at this scale.

```css
/* Source: 02-UI-SPEC.md — Component Inventory, Spacing Scale, Typography, Color */

/* Hero section */
.hero {
  text-align: center;
  margin-bottom: 48px;
}
.hero h2 {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-bright);
  line-height: 1.2;
  margin-bottom: 8px;
}
.hero-title {
  font-size: 16px;
  font-weight: 400;
  color: var(--accent);
  margin-bottom: 16px;
}
.hero-bio {
  font-size: 16px;
  font-weight: 400;
  color: var(--text);
  line-height: 1.6;
  max-width: 560px;
  margin: 0 auto 16px;
}
.hero a {
  font-size: 16px;
  color: var(--accent);
  text-decoration: none;
}
.hero a:hover { text-decoration: underline; }

/* Section label (replaces h2 Projects) */
.section-label {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-bright);
  text-align: left;
  margin-bottom: 16px;
}

/* Card thumbnail */
.card img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 16px;
  display: block;
}

/* Card thumbnail placeholder */
.card-thumbnail-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: linear-gradient(135deg, #1c2128, #30363d);
  border-radius: 4px;
  margin-bottom: 16px;
}
```

### Pattern 4: Existing `main` CSS Override

The current `main` rule has `text-align: center` which would left-align break the `.section-label`. The section label needs `text-align: left`. This is handled by the `.section-label` rule overriding `text-align` directly — no change to `main` needed.

Also: the existing `main p { color: var(--text-dim); margin-bottom: 40px; }` rule is too broad — it will style `.hero-bio` incorrectly (wrong color, wrong margin). The `.hero-bio` class rule must be more specific or the `main p` rule must be scoped down. **This is a specificity pitfall — see Common Pitfalls.**

### Anti-Patterns to Avoid

- **Rewriting `docs/index.html` from scratch:** The file is the working production skeleton. Rewrite risk is high; always extend in place.
- **Adding a separate CSS file:** Unnecessary indirection at this file count. Keep styles in the `<style>` block.
- **Using padding-bottom hack for 16:9:** `aspect-ratio: 16/9` is the correct modern approach and is universally supported in the target browser range.
- **Hardcoding pixel colors instead of CSS variables:** All colors must use existing `--bg`, `--surface`, `--accent`, etc. variables.
- **Adding JavaScript for the placeholder:** Pure CSS handles the placeholder; JS is not needed and is out of scope.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 16:9 aspect ratio | Custom JS resize listener | `aspect-ratio: 16/9` CSS property | Native CSS, zero JS, supported everywhere |
| CSS variables for theming | Repeated hex values | Existing `:root` variables | Already defined; consistency guaranteed |
| Responsive grid | Custom flexbox breakpoints | Existing `auto-fill, minmax(280px, 1fr)` | Already implemented and working |

**Key insight:** Nearly everything is already built. This phase is surgical additions to one file, not construction.

---

## Runtime State Inventory

Step 2.5: SKIPPED — This is a greenfield content-addition phase, not a rename/refactor/migration. No runtime state is involved.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Browser (any modern) | Manual testing | ✓ | — | — |
| `docs/index.html` | Base file to extend | ✓ | — (Phase 1 output) | — |
| `docs/projects/calculator/img/logo_2.png` | HOME-01 logo | ✓ | — | — |
| `docs/projects/calculator/thumbnail.png` | SHOW-02 thumbnail | ✗ | — | CSS gradient placeholder (`card-thumbnail-placeholder`) |

**Missing dependencies with no fallback:** None — execution is not blocked.

**Missing dependencies with fallback:**
- `docs/projects/calculator/thumbnail.png` — not present. Use CSS placeholder div. User must supply the actual screenshot (app capture from the live calculator page) to replace it.

---

## Common Pitfalls

### Pitfall 1: `main p` Rule Conflicts With Hero Bio

**What goes wrong:** The existing CSS rule `main p { color: var(--text-dim); margin-bottom: 40px; }` is a broad selector. When `.hero-bio` is added inside `<main>`, it inherits `--text-dim` (wrong — should be `--text`) and `margin-bottom: 40px` (wrong — should be `16px`).

**Why it happens:** The skeleton's `main p` rule was written for a single paragraph ("Click a card to try the project.") and wasn't designed to coexist with hero content.

**How to avoid:** Add `.hero-bio` specific rules AFTER the `main p` rule so specificity resolves correctly. Alternatively, scope the original rule down to `.projects-intro` or a specific class. The `.hero-bio` class rule with explicit `color` and `margin-bottom` will override the broad rule when placed lower in the cascade.

**Warning signs:** Hero bio text appears in `--text-dim` grey instead of `--text` white-grey, or has excessive bottom margin.

### Pitfall 2: `<h2>` Conflict — Display vs Section Heading

**What goes wrong:** The existing file uses `<h2>Projects</h2>` as its heading. The hero name must also be an `<h2>` (per UI-SPEC accessibility requirement: "Hero `<h2>` must be the first and only h2 on the page"). If both survive, there are two h2s.

**Why it happens:** The skeleton's `<h2>Projects</h2>` is a placeholder that must be replaced, not supplemented.

**How to avoid:** Delete the `<h2>Projects</h2>` line entirely and replace it with `<h3 class="section-label">Projects</h3>`. The hero `<h2>` becomes the sole h2. Verify with browser DevTools Accessibility panel or a quick DOM inspection.

**Warning signs:** Two `<h2>` elements in the rendered page; fails accessibility document outline check.

### Pitfall 3: `main` Text-Align Center Breaks Section Label

**What goes wrong:** `main { text-align: center; }` is set globally. The `.section-label` heading for "Projects" must be left-aligned, but inherits center-align from `<main>`.

**Why it happens:** The existing `main` rule is appropriate for the old simple layout, but the new layout has mixed-alignment zones (hero: center, section label: left, card grid: left-aligned cells).

**How to avoid:** The `.section-label` rule explicitly sets `text-align: left` — this override is included in the CSS pattern above. Do not remove `text-align: center` from `main` (it controls hero alignment).

**Warning signs:** "Projects" section label appears centered over the card grid instead of left-aligned.

### Pitfall 4: Thumbnail Image Stretching on Non-16:9 Screenshots

**What goes wrong:** If the captured screenshot is not exactly 16:9, the thumbnail image distorts to fill the container.

**Why it happens:** Without `object-fit`, `<img width="100%">` stretches to fill.

**How to avoid:** Add `object-fit: cover` to `.card img` — this crops rather than stretches, maintaining the container's 16:9 shape regardless of source image proportions.

**Warning signs:** Screenshots appear squished or stretched horizontally/vertically in cards.

### Pitfall 5: Hero Link Missing LinkedIn Handle Placeholder

**What goes wrong:** `href="https://linkedin.com/in/YOUR-HANDLE"` is committed verbatim. Clicking the link goes to a 404.

**Why it happens:** The actual LinkedIn handle is not specified in CONTEXT.md or UI-SPEC.md.

**How to avoid:** The plan must include a task to insert the real LinkedIn URL. Use a clear placeholder comment in the code (e.g., `<!-- TODO: replace YOUR-HANDLE with actual LinkedIn username -->`). Flag this as a user-action item.

**Warning signs:** LinkedIn link navigates to a LinkedIn 404 page.

---

## Code Examples

Verified patterns from official sources (MDN / WHATWG):

### CSS `aspect-ratio` for 16:9 containers

```css
/* Source: MDN Web Docs — aspect-ratio property */
/* Universally supported: Chrome 88+, Firefox 89+, Safari 15+, Edge 88+ */
.card img,
.card-thumbnail-placeholder {
  aspect-ratio: 16 / 9;
  width: 100%;
}
/* object-fit: cover prevents stretch on non-16:9 source images */
.card img { object-fit: cover; }
```

### CSS Grid with auto-fill (existing pattern, already verified)

```css
/* Source: docs/index.html — already working in production */
.projects {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
```

### CSS Custom Property usage (existing pattern)

```css
/* Source: docs/index.html :root block */
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --accent: #58a6ff;
  --text: #c9d1d9;
  --text-bright: #f0f6fc;
  --text-dim: #8b949e;
  --radius: 8px;
}
/* Usage: var(--accent), var(--text-bright), etc. — never raw hex values */
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Padding-bottom hack for aspect ratio (e.g., `padding-bottom: 56.25%`) | `aspect-ratio: 16/9` CSS property | ~2021 (broad browser support) | Simpler, semantic, no positioning hacks needed |
| Separate CSS file for multi-component pages | Inline `<style>` for small single-file sites | N/A (context-dependent) | At one-file scope, inline is lower indirection |

**Deprecated/outdated:**
- Padding-bottom aspect-ratio hack: Superseded by `aspect-ratio`. Do not use.

---

## Open Questions

1. **LinkedIn URL handle**
   - What we know: LinkedIn link is required (D-04), text label is "LinkedIn" (UI-SPEC copywriting contract)
   - What's unclear: The actual LinkedIn profile URL/handle is not in any planning document
   - Recommendation: Plan must include a task explicitly asking the user to supply their LinkedIn handle before the hero section task is marked done. Use a visible TODO comment in the HTML as a placeholder.

2. **Hero name copy**
   - What we know: UI-SPEC specifies "(user's actual name — to be filled by executor, not hardcoded here)"
   - What's unclear: The actual name is not in planning documents (intentionally omitted for privacy)
   - Recommendation: Same as above — plan must include a user-action task. Use placeholder text `Your Name` in the HTML with a TODO comment.

3. **Calculator thumbnail screenshot**
   - What we know: File must be at `docs/projects/calculator/thumbnail.png`, 800×450px, 16:9
   - What's unclear: Must be captured by the user from the live calculator UI
   - Recommendation: Plan delivers the CSS placeholder so the layout is stable. Include a clearly labeled user-action task: "Take a screenshot of the calculator running at the correct dimensions and save it as `docs/projects/calculator/thumbnail.png`."

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None — vanilla static HTML; no automated test framework configured |
| Config file | None |
| Quick run command | Open `docs/index.html` in browser and visually inspect |
| Full suite command | Open in browser + check DevTools accessibility panel for h2 count and contrast |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HOME-01 | Logo `<img>` renders in header top-left | Manual visual | `n/a — open docs/index.html in browser` | ✅ |
| HOME-02 | Hero section visible: name, title, bio, LinkedIn link | Manual visual | `n/a — open docs/index.html in browser` | ✅ |
| SHOW-01 | Project grid visible with at least one card | Manual visual | `n/a — open docs/index.html in browser` | ✅ |
| SHOW-02 | Card shows title, thumbnail (or placeholder), description, tags | Manual visual | `n/a — open docs/index.html in browser` | ✅ |

**Note:** This phase has no dynamic behavior or JavaScript — all verification is static HTML/CSS visual inspection. No automated test infrastructure is applicable or necessary. The verification agent (`/gsd:verify-work`) should use browser-based spot checks against each success criterion.

### Sampling Rate

- **Per task commit:** Load `docs/index.html` in browser, verify the specific element added
- **Per wave merge:** Full visual pass — all four requirements checked simultaneously
- **Phase gate:** All four requirements visually confirmed before `/gsd:verify-work`

### Wave 0 Gaps

None — no test files needed. Visual inspection is the only validation method for static HTML.

---

## Sources

### Primary (HIGH confidence)

- `docs/index.html` — Existing code inspected directly; all CSS variables, structure, and patterns confirmed
- `.planning/phases/02-portfolio-shell/02-CONTEXT.md` — Locked decisions D-01 through D-07
- `.planning/phases/02-portfolio-shell/02-UI-SPEC.md` — Complete visual and interaction contract
- `.planning/REQUIREMENTS.md` — HOME-01, HOME-02, SHOW-01, SHOW-02 requirements text
- MDN Web Docs — `aspect-ratio` CSS property, `object-fit`, CSS custom properties (HIGH — official specification reference)

### Secondary (MEDIUM confidence)

- Browser support data for `aspect-ratio: 16/9` — supported in Chrome 88+ (Jan 2021), Firefox 89+ (Jun 2021), Safari 15+ (Sep 2021). Essentially universal for any modern browser.

### Tertiary (LOW confidence)

None — no unverified WebSearch-only findings in this research.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — project constraint is vanilla HTML/CSS, no ambiguity
- Architecture: HIGH — existing file structure inspected directly; UI-SPEC defines all insertion points
- Pitfalls: HIGH — all identified from direct code inspection of the existing file
- Open questions: HIGH — accurately identified; scope of unknowns is narrow and well-defined

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (stable domain — vanilla HTML/CSS does not change)
