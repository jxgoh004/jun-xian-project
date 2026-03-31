# Phase 4: Design and Performance - Research

**Researched:** 2026-03-31
**Domain:** CSS responsive design, Core Web Vitals, image optimization, CSS transitions
**Confidence:** HIGH

## Summary

Phase 4 polishes an existing 237-line single-file portfolio (`docs/index.html`) with inline CSS and vanilla JS. All work is CSS and markup changes — no new libraries, no build step. The three locked concerns are: (1) responsive breakpoints at ≤640px, (2) a fade transition replacing the current `display:none` toggle in the `navigate()` function, and (3) image optimization for the thumbnail (currently a 73.9 KB PNG at 1854×771px).

The fade transition is the only moderately complex change: it requires replacing the instant `style.display` toggle with a CSS opacity + `pointer-events` pattern timed with `setTimeout` so the outgoing section finishes fading before the incoming section appears. This is a well-understood vanilla JS pattern with no library dependency. The image optimization requires a Python Pillow install (pip3 is available; cwebp and sharp are not present). A `<picture>` element with WebP and PNG fallback is the correct HTML pattern.

Core Web Vitals for a GitHub Pages static site of this scale are straightforward: the page is tiny (one HTML file, one image), loads no external scripts, and uses no render-blocking resources. With the thumbnail optimized and lazy-loaded, LCP will be dominated by the hero text which renders instantly. The main risk for LCP is the thumbnail image being above the fold — but the card grid is below the hero, so `loading="lazy"` is safe here.

**Primary recommendation:** Implement all CSS changes (layout, breakpoints, transitions, hover) directly in the `<style>` block. Use `pip3 install Pillow` and a Python one-liner to produce WebP. Use a `<picture>` element for the thumbnail so the original PNG remains as a fallback.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Remove the `max-width: 900px` constraint on `<main>`. The layout fills the full viewport width with generous side padding.
**D-02:** The card grid is capped at approximately 1200px centered (not fully edge-to-edge). Cards stay readable at ultra-wide viewports (1400px+) — consistent with how GitHub's feed layout works.
**D-03:** The hero section stays center-aligned on all viewport widths.
**D-04:** Primary mobile breakpoint: ≤640px. At this width: main padding reduces to 16px (from 24px), hero name font shrinks to 22px (from 28px), bio text shrinks to 15px (from 16px).
**D-05:** Header stays as-is on mobile — logo + "Portfolio" title side by side. No changes to header layout at any breakpoint.
**D-06:** Project iframe on mobile: leave `calc(100vh - 63px)` unchanged. No mobile warning banner.
**D-07:** Card grid already adapts via `auto-fill, minmax(280px, 1fr)` — no card-specific breakpoint changes needed.
**D-08:** Fade transition between home and project view: home view fades out (~200ms CSS opacity transition), project view fades in. No slide or instant switch.
**D-09:** Back navigation (logo click or browser back from project view) also uses fade: project view fades out, home view fades in.
**D-10:** Card hover enhancement: add `transform: translateY(-2px)` on hover, combined with the existing `border-color` transition. Subtle lift effect.
**D-11:** Rewrite the bio paragraph for clarity. Target 2–3 clean sentences covering: data analyst background (graph analytics, Neo4j) → AI Engineering pivot, AISG Associate AI Engineer program, now building AI-powered tools to share. Fix existing typos and run-on sentences. Maintain warm but professional tone.
**D-12:** Update `<title>` tag from "Portfolio" to "Goh Jun Xian — Portfolio" so the name appears in the browser tab.
**D-13:** Desktop spacing (60px top margin on main, 48px hero margin-bottom, 20px card gap) is kept as-is. Only mobile spacing is adjusted (D-04).
**D-14:** Apply `loading="lazy"` to the thumbnail `<img>` tag. Compress and/or convert to WebP if the current PNG is large. This directly affects LCP for PERF-03.

### Claude's Discretion

- Exact card grid max-width cap value (approximately 1200px — fine-tune for visual balance)
- Fade transition easing curve and exact timing (200ms suggested)
- Whether a tablet breakpoint (≤900px) is needed between mobile and desktop
- Section-label and tag font sizing on mobile if adjustment looks needed
- Image compression tool/approach for thumbnail optimization
- Whether to add `will-change: opacity` hint for fade transitions

### Deferred Ideas (OUT OF SCOPE)

- Custom domain DNS setup (Cloudflare CNAME → GitHub Pages) — post-Phase 4
- Additional project cards beyond the calculator — future milestone
- Dark mode toggle — v2 requirement (POLISH-01)
- Smooth animations beyond the view fade (e.g., card entrance animations) — post-v1

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERF-01 | Site uses modern, clean aesthetic with whitespace and professional styling | D-01 through D-13: full-width layout, fade transitions, hover polish, bio rewrite, title tag update |
| PERF-02 | Site is fully responsive across mobile, tablet, and desktop | D-04 mobile breakpoint (≤640px), card grid already uses auto-fill minmax — one media query block covers the requirement |
| PERF-03 | Site passes Core Web Vitals (optimized images, fast loading, LCP < 2.5s) | D-14: lazy loading + WebP conversion; single-file site architecture means sub-2.5s LCP is achievable with optimized image |

</phase_requirements>

---

## Standard Stack

### Core

| Library / Approach | Version | Purpose | Why Standard |
|--------------------|---------|---------|--------------|
| Inline CSS in `<style>` | N/A | All styling — consistent with existing file structure | Project constraint: no separate stylesheet; all CSS in `<head>` |
| CSS `@media` queries | N/A | Responsive breakpoints | Browser-native; no library needed for two breakpoints |
| CSS `opacity` + `transition` | N/A | Fade between views | Browser-native; no GSAP/Animate.css needed for 200ms fade |
| Python Pillow | 12.1.1 (latest) | Convert PNG to WebP | Available via pip3 on this machine; one-liner conversion; no cwebp or sharp present |
| `<picture>` element | N/A | WebP with PNG fallback | Browser-native; provides graceful degradation without JS |

### Supporting

| Approach | Purpose | When to Use |
|----------|---------|-------------|
| `loading="lazy"` on `<img>` | Defer off-screen image load | Cards are below the hero fold — safe to lazy load |
| `width` + `height` on `<img>` | Prevent Cumulative Layout Shift (CLS) | Always set when dimensions are known to reserve space |
| `pointer-events: none` on hidden view | Prevent click-through during fade | Required during opacity transition — element is visually hidden but still in DOM |
| `will-change: opacity` | GPU compositing hint for fade | Add only if transition looks janky; avoid over-using (memory cost) |

### No Additional Packages Needed

This phase is pure HTML/CSS/JS editing. No npm install, no pip install beyond Pillow for image conversion.

**Pillow installation:**
```bash
pip3 install Pillow
```

**Version verification:** `pip3 show Pillow` confirms 12.1.1 is current (dry-run confirmed 2026-03-31).

---

## Architecture Patterns

### CSS Structure (within existing `<style>` block)

The existing style block has these logical sections. New rules slot into the same block:

```
<style>
  /* 1. Reset + box-sizing */
  /* 2. :root variables */
  /* 3. body */
  /* 4. header */
  /* 5. main ← remove max-width:900px here */
  /* 6. hero, hero-bio, hero-title, hero links */
  /* 7. section-label */
  /* 8. .projects grid */
  /* 9. .card, .card:hover ← extend transition here */
  /* 10. .card img, .card-thumbnail-placeholder */
  /* 11. #project-view ← no changes */
  /* 12. ← NEW: .view (shared fade class) */
  /* 13. ← NEW: @media (max-width: 640px) block */
</style>
```

### Pattern 1: Full-Width Layout with Capped Grid

**What:** Remove `max-width: 900px` from `main`. Give `main` full width with side padding. Apply `max-width` only to the `.projects` grid.
**When to use:** When the main element should breathe at all widths but card content stays readable.

```css
/* Remove this from main: */
/* max-width: 900px; */

main {
  margin: 60px auto;
  padding: 0 24px;
  /* full viewport width by default */
}

.projects-wrapper {  /* or apply directly to .projects */
  max-width: 1200px;
  margin: 0 auto;
}
```

Note: The hero `.hero` already has `text-align: center` — it will remain centered naturally in a full-width main.

### Pattern 2: CSS Opacity Fade Transition (Vanilla JS)

**What:** Replace `display:none/block` toggles with CSS opacity transition. Hidden elements use `opacity: 0; pointer-events: none` and are switched to `opacity: 1; pointer-events: auto` to show.

**The key insight:** You cannot transition `display`. The workaround is to keep both sections in the normal flow but control visibility via `opacity` + `pointer-events`, then use `setTimeout` to sequence out → in.

```css
.view {
  transition: opacity 0.2s ease;
}
.view.hidden {
  opacity: 0;
  pointer-events: none;
}
/* No display:none — element stays in DOM flow */
```

```javascript
function fadeOut(el, callback) {
  el.classList.add('hidden');
  setTimeout(callback, 200); // match CSS transition duration
}

function fadeIn(el) {
  el.classList.remove('hidden');
}

function navigate() {
  const hash = location.hash.slice(1) || 'home';

  if (projects[hash]) {
    fadeOut(homeView, function() {
      homeView.style.display = 'none'; // remove from flow after fade
      projectView.style.display = 'block';
      // Create iframe if needed
      if (!projectView.querySelector('iframe')) {
        const iframe = document.createElement('iframe');
        iframe.src = projects[hash];
        iframe.title = hash.charAt(0).toUpperCase() + hash.slice(1);
        projectView.appendChild(iframe);
      }
      requestAnimationFrame(function() { fadeIn(projectView); });
    });
  } else {
    fadeOut(projectView, function() {
      projectView.style.display = 'none';
      const iframe = projectView.querySelector('iframe');
      if (iframe) iframe.remove();
      homeView.style.display = '';
      requestAnimationFrame(function() { fadeIn(homeView); });
    });
  }
}
```

**Initialization concern:** On first page load, both views must be in their correct initial opacity state without a visible flash. Set initial states synchronously before any `navigate()` call.

**Alternative (simpler, no setTimeout):** Use CSS `visibility: hidden` instead of `display:none` — allows transitions but keeps layout space occupied. Given the `#project-view` is `max-width: none; margin: 0; padding: 0`, retaining it in the flow while invisible would cause an extra gap. The `display:none` + `setTimeout` pattern is preferred here.

### Pattern 3: Mobile Breakpoint

**What:** Single `@media (max-width: 640px)` block at the end of the `<style>` block. Only override what changes per D-04.

```css
@media (max-width: 640px) {
  main {
    padding: 0 16px;
  }
  .hero h2 {
    font-size: 22px;
  }
  .hero-bio {
    font-size: 15px;
  }
}
```

No changes to `.card`, `.tags`, `.tag`, `header`, or `#project-view` at this breakpoint per locked decisions.

### Pattern 4: Card Hover with Transform

**What:** Extend existing `.card` transition to include `transform`, then add `translateY(-2px)` on hover.

```css
/* BEFORE */
.card {
  transition: border-color 0.2s;
}
.card:hover { border-color: var(--accent); }

/* AFTER */
.card {
  transition: border-color 0.2s, transform 0.2s;
}
.card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}
```

### Pattern 5: WebP Image with PNG Fallback

**What:** Replace `<img>` with `<picture>` containing a WebP `<source>` and PNG fallback `<img>`. Add `loading="lazy"` and explicit `width`/`height` to prevent CLS.

```html
<picture>
  <source srcset="projects/calculator/thumbnail.webp" type="image/webp">
  <img
    src="projects/calculator/thumbnail.png"
    alt="Intrinsic Value Calculator screenshot"
    loading="lazy"
    width="1854"
    height="771">
</picture>
```

**WebP conversion command (Pillow):**
```python
from PIL import Image
img = Image.open('docs/projects/calculator/thumbnail.png')
img.save('docs/projects/calculator/thumbnail.webp', 'WEBP', quality=80, method=6)
```

Or as a one-liner:
```bash
python3 -c "from PIL import Image; Image.open('docs/projects/calculator/thumbnail.png').save('docs/projects/calculator/thumbnail.webp', 'WEBP', quality=80)"
```

### Anti-Patterns to Avoid

- **Transitioning `display`:** `display` cannot be transitioned in CSS. Always pair `opacity` with `pointer-events` to fake visibility toggling.
- **`will-change` on everything:** `will-change: opacity` promotes elements to their own compositing layer and consumes GPU memory. Only add it if the fade actually looks choppy on testing.
- **`loading="lazy"` on above-the-fold images:** The hero area does not contain images — only cards which are below the hero. All card images are safe to lazy load. If a future above-the-fold image is added, omit `loading="lazy"` on it.
- **Hardcoded colors:** All new CSS must use existing CSS variables (`--bg`, `--surface`, `--border`, `--accent`, `--text`, `--text-bright`, `--text-dim`, `--radius`). No `#58a6ff` literals.
- **Removing `#project-view`'s `max-width: none; margin: 0; padding: 0`:** These overrides prevent the full-width layout changes on `main` from affecting the iframe container. They must remain.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image format conversion | Custom base64 manipulation | `pip3 install Pillow` + one-liner | Pillow handles ICC profiles, alpha channels, compression optimization — custom code misses edge cases |
| Fade transition sequencing | Complex animation library | CSS `opacity` + `setTimeout(200)` | 200ms linear fade needs 4 lines of JS, not a library |
| Responsive grid | Custom JS layout engine | `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` already in place | Grid already adapts — only breakpoint overrides needed |
| WebP browser detection | JS `canPlayType` or feature detection | `<picture>` element with `<source type="image/webp">` | Browser handles fallback natively; WebP is supported in all modern browsers (95%+ global) |

---

## Common Pitfalls

### Pitfall 1: Fade Flash on Initial Page Load

**What goes wrong:** On first `navigate()` call, `homeView` starts in an unknown opacity state. If JS applies `.hidden` class before the CSS transition is registered, the element flashes before fading in.
**Why it happens:** The `navigate()` function runs on `DOMContentLoaded`. If it immediately toggles opacity, there is no "starting" animation frame for the browser.
**How to avoid:** On initial load, skip the fade entirely — use `display:none` directly for the inactive view, and set the active view to full opacity without transition. Only apply the fade class system after the first render. One approach: add a `.no-transition` utility class that sets `transition: none` and apply it during initialization, then remove it after the first paint.
**Warning signs:** On hard refresh, one of the views briefly flickers before settling.

### Pitfall 2: pointer-events Leaking Through Opacity-0 Elements

**What goes wrong:** A view at `opacity: 0` is still in the DOM and can intercept clicks if `pointer-events` is not set to `none`. Links or buttons in the hidden view receive hover states and clicks even though the user cannot see them.
**Why it happens:** `opacity: 0` is a visual change only — the element's click area remains.
**How to avoid:** Always pair `opacity: 0` with `pointer-events: none`. When restoring visibility, restore `pointer-events: auto` (or remove the class) before or simultaneously with the opacity change.
**Warning signs:** Clicking "through" the visible view unexpectedly triggers something on the hidden view.

### Pitfall 3: max-width on main Breaks project-view

**What goes wrong:** Removing `max-width: 900px` from `main` and adding side padding globally causes the full-height iframe in `#project-view` to have unexpected horizontal padding.
**Why it happens:** `#project-view` resets its own `max-width: none; margin: 0; padding: 0` — but if the planner modifies `main` padding, those resets may be insufficient.
**How to avoid:** Verify that `#project-view` still has its own `padding: 0` override after main's padding changes. The iframe must be truly edge-to-edge.
**Warning signs:** The calculator iframe appears with horizontal white/dark bars on the sides at full screen.

### Pitfall 4: Layout Shift from Missing Image Dimensions

**What goes wrong:** The card thumbnail causes visible content jumping (CLS) as it loads, because the browser doesn't know the image's aspect ratio until it downloads the file.
**Why it happens:** No explicit `width`/`height` attributes on the `<img>` — browser allocates no space until the image arrives.
**How to avoid:** Add `width="1854" height="771"` (or scaled-down equivalents like `width="928" height="386"`) to the `<img>` inside the `<picture>` element. The browser uses these to compute the aspect ratio before download. The CSS `aspect-ratio: 16 / 9` on `.card img` already handles this but explicit attributes are belt-and-suspenders.
**Warning signs:** Lighthouse CLS score above 0.1; content jumps visibly when scrolling down to the card.

### Pitfall 5: Bio Text Regression — stale TODO comment

**What goes wrong:** `docs/index.html` line 160 has a stale `<!-- TODO: Replace YOUR-HANDLE -->` comment. The Phase 3 verification noted this as a non-blocking anti-pattern. The bio rewrite (D-11) should also remove this stale comment.
**Why it happens:** Carried forward from Phase 2. Phase 3 verification flagged it as "Info" severity but did not fix it.
**How to avoid:** When rewriting the bio paragraph, remove the TODO comment at the same time.
**Warning signs:** Still present after bio rewrite.

---

## Code Examples

### Full-Width Main with Capped Card Grid

```css
/* Source: D-01, D-02 from CONTEXT.md */
main {
  /* REMOVED: max-width: 900px; */
  margin: 60px auto;
  padding: 0 24px;
  text-align: center;
}

.projects-section {
  max-width: 1200px;
  margin: 0 auto;
  text-align: left;
}
```

Note: The `.projects` grid div is already `text-align: left` via `.card`. The `.section-label` h3 is also `text-align: left`. These can be wrapped in a `max-width: 1200px` container div or that constraint can be applied directly to `.projects` and `.section-label` via a shared wrapper.

### Mobile Media Query Block

```css
/* Source: D-04 from CONTEXT.md */
@media (max-width: 640px) {
  main {
    padding: 0 16px;
  }
  .hero h2 {
    font-size: 22px;
  }
  .hero-bio {
    font-size: 15px;
  }
}
```

### Card Hover with Lift

```css
/* Source: D-10 from CONTEXT.md */
.card {
  /* ... existing properties ... */
  transition: border-color 0.2s, transform 0.2s;
}
.card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}
```

### WebP Picture Element

```html
<!-- Source: D-14 from CONTEXT.md; MDN picture element pattern -->
<picture>
  <source srcset="projects/calculator/thumbnail.webp" type="image/webp">
  <img
    src="projects/calculator/thumbnail.png"
    alt="Intrinsic Value Calculator screenshot"
    loading="lazy"
    width="1854"
    height="771">
</picture>
```

### Fade Transition CSS

```css
/* Source: D-08, D-09 from CONTEXT.md */
.view {
  transition: opacity 0.2s ease;
}
.view.hidden {
  opacity: 0;
  pointer-events: none;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PNG for web thumbnails | WebP (with PNG fallback via `<picture>`) | WebP baseline since ~2020, `<picture>` widely supported since ~2019 | ~50-70% smaller file for same visual quality |
| `display:none` toggle | CSS `opacity` + `pointer-events` transition | Standard since CSS3 transitions | Smooth fade without JS animation libraries |
| Fixed-width containers | CSS Grid `auto-fill, minmax()` | Grid baseline since ~2017 | Automatically responsive without breakpoints per column |
| Explicit `loading="eager"` (default) | `loading="lazy"` for below-fold images | HTML spec baseline 2019, all major browsers by 2020 | Zero-cost deferred loading, no JS required |

**Not deprecated in this project:**
- `font-family: -apple-system, BlinkMacSystemFont, "Segoe UI"` system font stack — still appropriate for GitHub-aesthetic portfolio, no web font load penalty.
- CSS variables (`:root` custom properties) — fully supported, correct approach.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npx commands | ✓ | 22.17.1 | — |
| Python 3 | Pillow image conversion | ✓ | 3.11.9 | — |
| pip3 | Pillow install | ✓ | included with Python 3.11.9 | — |
| Pillow | WebP conversion | ✗ (installable) | 12.1.1 available | Install via `pip3 install Pillow` — confirmed by dry-run |
| cwebp | WebP conversion | ✗ | — | Use Pillow instead |
| sharp (Node.js) | WebP conversion | ✗ | — | Use Pillow instead |
| Browser DevTools | Lighthouse audit | ✓ (human step) | — | — |

**Missing dependencies with no fallback:** None — Pillow is installable.

**Missing dependencies with fallback:** cwebp and sharp are not present, but Pillow provides equivalent WebP output and is readily installable.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None — no automated test framework exists or is appropriate for this single HTML file |
| Config file | None |
| Quick run command | Manual browser inspection (DevTools) |
| Full suite command | Lighthouse CLI or manual Lighthouse in Chrome DevTools |

This project has no test framework and none is appropriate to add for a 237-line static HTML file. Verification for this phase is visual inspection + Lighthouse audit — these are manual-only tests.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | Modern aesthetic: consistent whitespace, typography, color | Visual inspection | N/A — manual-only (subjective visual quality) | ✗ Wave 0 N/A |
| PERF-01 | Fade transition works between home/project views | Manual browser | N/A — requires browser | ✗ Wave 0 N/A |
| PERF-01 | Card hover shows translateY(-2px) lift | Manual browser | N/A — requires browser | ✗ Wave 0 N/A |
| PERF-01 | Title tag reads "Goh Jun Xian — Portfolio" | Static file grep | `grep -c "Goh Jun Xian — Portfolio" docs/index.html` | ✗ Wave 0 — add as grep check |
| PERF-01 | Bio rewritten (no "dwell", clean sentences) | Static file grep | `grep -c "dwell" docs/index.html` (expect 0) | ✗ Wave 0 — add as grep check |
| PERF-02 | Responsive at 320px: padding 16px, name 22px, bio 15px | CSS rule grep | `grep -c "max-width: 640px" docs/index.html` | ✗ Wave 0 — add as grep check |
| PERF-02 | Full-width main (no max-width: 900px) | Static file grep | `grep -c "max-width: 900px" docs/index.html` (expect 0) | ✗ Wave 0 — add as grep check |
| PERF-03 | thumbnail has loading="lazy" | Static file grep | `grep -c 'loading="lazy"' docs/index.html` | ✗ Wave 0 — add as grep check |
| PERF-03 | WebP file exists | File existence check | `ls docs/projects/calculator/thumbnail.webp` | ✗ Wave 0 — add as existence check |
| PERF-03 | LCP < 2.5s | Lighthouse audit | Manual — open Chrome DevTools Lighthouse | ✗ Wave 0 N/A |

### Sampling Rate

- **Per task commit:** Run static grep checks (title tag, lazy loading, no max-width:900px, no "dwell") — takes < 5 seconds
- **Per wave merge:** Same grep checks + verify thumbnail.webp file exists
- **Phase gate:** Lighthouse Performance score ≥90 (mobile) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] No test files to create — this project uses grep/file-check verification only
- [ ] Lighthouse audit: manual step in Chrome DevTools — cannot be automated without installing lighthouse CLI (`npm install -g lighthouse`)

*(No new test infrastructure needed. Verification is static grep checks + manual browser Lighthouse.)*

---

## Open Questions

1. **Tablet breakpoint (≤900px) — discretionary**
   - What we know: D-07 says the card grid already adapts via `auto-fill, minmax(280px, 1fr)`. D-05 says header is unchanged. The only mobile adjustments are padding and font sizes.
   - What's unclear: Whether the layout looks awkward at 700–900px viewport width with the full-width main but no padding reduction.
   - Recommendation: Test visually at 768px in DevTools. If the padding at 24px looks fine and the two-column grid fills reasonably, no tablet breakpoint is needed. Only add `@media (max-width: 900px)` if visual inspection reveals an obvious problem.

2. **Card grid max-width — fine-tune**
   - What we know: D-02 says "approximately 1200px". The `.section-label` h3 must align with the grid left edge.
   - What's unclear: Whether to use a wrapper `<div>` around both `.section-label` and `.projects`, or apply `max-width: 1200px; margin: 0 auto` to each independently.
   - Recommendation: Wrap both in a `<div class="projects-section">` with `max-width: 1200px; margin: 0 auto; text-align: left`. This is cleaner than duplicating the constraint on each element.

3. **Fade transition on initial page load**
   - What we know: Currently `navigate()` runs immediately on `DOMContentLoaded` and sets `display:none` on inactive views.
   - What's unclear: Whether replacing `display:none` with the fade system will cause a flash-of-content before the hidden view becomes opacity:0.
   - Recommendation: On initial load, set hidden views to `display:none` directly (same as current behavior). Only apply the CSS fade transition class system when navigating after load. Use a boolean flag `let initialized = false` and skip the fade on the first `navigate()` call.

---

## Sources

### Primary (HIGH confidence)

- MDN Web Docs — `<picture>` element, `loading="lazy"`, CSS `pointer-events`, CSS `transition` — verified behavior matches spec
- Existing `docs/index.html` — direct code inspection, lines 1–237 — all current CSS and JS state documented from source
- `.planning/phases/04-design-and-performance/04-CONTEXT.md` — all locked decisions copied verbatim

### Secondary (MEDIUM confidence)

- `.planning/research/PITFALLS.md` — Phase-level pitfall research from 2026-03-17; image optimization targets (<200KB thumbnails) cross-referenced against current file size (73.9 KB — already under limit)
- Python Pillow 12.1.1 — pip dry-run confirmed installable on this machine (2026-03-31)

### Tertiary (LOW confidence)

- WebP browser support "95%+ global" — widely cited figure; exact number varies by source but WebP is universally considered baseline support since 2023

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; existing inline CSS + Python Pillow for image conversion, all verified present/installable
- Architecture: HIGH — all patterns verified against existing code in `docs/index.html`; CSS transition and `<picture>` patterns are MDN-documented
- Pitfalls: HIGH — derived from direct code inspection of the 237-line file and well-known CSS transition gotchas

**Research date:** 2026-03-31
**Valid until:** 2026-05-01 (stable domain — CSS, HTML, Web APIs change slowly)
