# Phase 4: Design and Performance - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Polish the existing portfolio site for professional quality: make it fully responsive across all screen sizes, apply design refinements (transitions, hover polish, bio copy, title), and ensure it passes Core Web Vitals (LCP < 2.5s). The color scheme, card grid structure, and overall dark aesthetic are fixed from prior phases — this phase polishes and extends what's there, not replaces it.

</domain>

<decisions>
## Implementation Decisions

### Full-width layout
- **D-01:** Remove the `max-width: 900px` constraint on `<main>`. The layout fills the full viewport width with generous side padding.
- **D-02:** The card grid is capped at approximately 1200px centered (not fully edge-to-edge). Cards stay readable at ultra-wide viewports (1400px+) — consistent with how GitHub's feed layout works.
- **D-03:** The hero section stays center-aligned on all viewport widths.

### Responsive breakpoints
- **D-04:** Primary mobile breakpoint: ≤640px. At this width: main padding reduces to 16px (from 24px), hero name font shrinks to 22px (from 28px), bio text shrinks to 15px (from 16px).
- **D-05:** Header stays as-is on mobile — logo + "Portfolio" title side by side. No changes to header layout at any breakpoint.
- **D-06:** Project iframe on mobile: leave `calc(100vh - 63px)` unchanged. No mobile warning banner. The calculator is desktop-first — users can scroll within the iframe.
- **D-07:** Card grid already adapts via `auto-fill, minmax(280px, 1fr)` — no card-specific breakpoint changes needed.

### View transitions
- **D-08:** Fade transition between home and project view: home view fades out (~200ms CSS opacity transition), project view fades in. No slide or instant switch.
- **D-09:** Back navigation (logo click or browser back from project view) also uses fade: project view fades out, home view fades in.
- **D-10:** Card hover enhancement: add `transform: translateY(-2px)` on hover, combined with the existing `border-color` transition. Subtle lift effect.

### Typography and copy
- **D-11:** Rewrite the bio paragraph for clarity. Target 2–3 clean sentences covering: data analyst background (graph analytics, Neo4j) → AI Engineering pivot, AISG Associate AI Engineer program, now building AI-powered tools to share. Fix existing typos and run-on sentences. Maintain warm but professional tone.
- **D-12:** Update `<title>` tag from "Portfolio" to "Goh Jun Xian — Portfolio" so the name appears in the browser tab.
- **D-13:** Desktop spacing (60px top margin on main, 48px hero margin-bottom, 20px card gap) is kept as-is. Only mobile spacing is adjusted (D-04).

### Image optimization
- **D-14:** Apply `loading="lazy"` to the thumbnail `<img>` tag (already exists at `docs/projects/calculator/thumbnail.png`). Compress and/or convert to WebP if the current PNG is large. This directly affects LCP for PERF-03.

### Claude's Discretion
- Exact card grid max-width cap value (approximately 1200px — fine-tune for visual balance)
- Fade transition easing curve and exact timing (200ms suggested)
- Whether a tablet breakpoint (≤900px) is needed between mobile and desktop
- Section-label and tag font sizing on mobile if adjustment looks needed
- Image compression tool/approach for thumbnail optimization
- Whether to add `will-change: opacity` hint for fade transitions

</decisions>

<specifics>
## Specific Ideas

- "I want the whole screen to be utilised at full screen" — remove the 900px cap so the layout breathes on wide monitors.
- Desktop spacing already feels right — no need to touch it. Mobile just needs proportional shrinking.
- The fade should feel like a smooth, professional handoff — not a dramatic animation. 200ms is a starting point.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — PERF-01, PERF-02, PERF-03 are the three requirements this phase closes. Read the full entries.
- `.planning/ROADMAP.md` §Phase 4 — Success criteria (responsive at 320/768/1280px, consistent design, Lighthouse LCP < 2.5s).

### Existing code (read before planning)
- `docs/index.html` — The single file containing all HTML, CSS, and JS. All changes in this phase happen here. Current state: inline `<style>`, no media queries, `max-width: 900px` on main, fade transition not yet implemented.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- CSS variables already defined: `--bg`, `--surface`, `--border`, `--accent`, `--text`, `--text-bright`, `--text-dim`, `--radius`. All new styles must use these variables — no hardcoded color values.
- `.card` transition already uses `transition: border-color 0.2s` — extend this to include `transform` for D-10.
- `#home-view` and `#project-view` sections already exist with `display:none` toggle — the fade transition wraps this show/hide logic with CSS opacity.

### Established Patterns
- Vanilla JavaScript only — no build step, no framework. All JS lives in the `<script>` block at the bottom of `docs/index.html`.
- `navigate()` function in the script block handles all routing — the fade logic goes here.
- All CSS is inline in `<style>` in `<head>` — add media queries to this same block.

### Integration Points
- `navigate()` function: replace `style.display = 'none'/'block'` with a CSS class-based fade (e.g., add/remove `.fading` class and use `opacity` + `pointer-events` transitions).
- `<main>` element: remove `max-width: 900px; margin: 60px auto` — replace with full-width layout (full width with padding, card grid capped separately).
- `<img src="projects/calculator/thumbnail.png">` on line 165: add `loading="lazy"`.

</code_context>

<deferred>
## Deferred Ideas

- Custom domain DNS setup (Cloudflare CNAME → GitHub Pages) — post-Phase 4, no code changes required (carried from Phase 3)
- Additional project cards beyond the calculator — future milestone
- Dark mode toggle — v2 requirement (POLISH-01)
- Smooth animations beyond the view fade (e.g., card entrance animations) — post-v1

</deferred>

---

*Phase: 04-design-and-performance*
*Context gathered: 2026-03-31*
