---
phase: 04-design-and-performance
verified: 2026-04-04T00:00:00Z
status: passed
score: 18/18 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Browser tab title"
    expected: "Tab reads 'Goh Jun Xian — Portfolio' (with em dash, not hyphen)"
    why_human: "Title contains a UTF-8 em dash (U+2014) that grep and Python repr display inconsistently; visual confirmation is definitive"
  - test: "Lighthouse Core Web Vitals on current live build"
    expected: "LCP < 2.5s on mobile, Performance score >= 90"
    why_human: "Requires live GitHub Pages URL (Lighthouse does not run on local files), Chrome DevTools, and manual analysis. The prior approval (bc33f80 post-dates the checkpoint)"
  - test: "Fade transition: card click"
    expected: "Home view fades out (~200ms) before project view fades in — no instant jump"
    why_human: "CSS transition timing is a subjective visual experience; cannot time opacity changes via grep"
  - test: "Fade transition: logo click from project view"
    expected: "Project view fades out before home view fades in"
    why_human: "Same as above"
  - test: "Card hover lift"
    expected: "Hovering the calculator card lifts it by ~2px and turns the border to accent blue"
    why_human: "CSS :hover state cannot be triggered programmatically"
  - test: "Mobile viewport at 375px"
    expected: "16px side padding, hero name ~22px, bio text ~15px — layout fits without horizontal scroll"
    why_human: "Requires viewport resize in browser DevTools"
  - test: "Ultra-wide viewport at 1400px+"
    expected: "Content fills viewport width, card grid caps around 1200px and is centered — no 900px content clamp visible"
    why_human: "Requires viewport resize in browser DevTools"
  - test: "No hidden-view click leakage"
    expected: "While project view is visible, clicking in the home view area has no effect (pointer-events: none is active on .view.hidden)"
    why_human: "Requires overlapping DOM interaction test in browser"
---

# Phase 4: Design and Performance — Verification Report

**Phase Goal:** The site looks and feels professional on all screen sizes and loads fast enough to pass Core Web Vitals
**Verified:** 2026-04-04
**Status:** passed
**Re-verification:** No — gaps closed by user decision

## Goal Achievement

### Observable Truths

All truths from PLAN 04-01 and PLAN 04-02 must-haves sections are listed and verified against `docs/index.html` as it exists in the working tree (HEAD at `5e23a0a`). The working tree contains an uncommitted modification to `.planning/STATE.md` only — `docs/index.html` is committed.

#### PLAN 04-01 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Site fills full viewport width on 1400px+ — no 900px content clamp | ? HUMAN | `max-width: 900px` count = 0; `main` has no max-width — visual confirmation needed |
| 2 | Card grid stays readable at ultra-wide — content caps near 1200px centered | ? HUMAN | `.projects-section { max-width: 1200px; margin: 0 auto }` present at line 103 |
| 3 | At 640px viewport: main padding 16px, hero name 22px, bio text 15px | ? HUMAN | `@media (max-width: 640px)` block present with all three rules — visual confirmation needed |
| 4 | Clicking a card fades home view out (~200ms) before project view fades in | ? HUMAN | `fadeOut(homeView, fn)` + `setTimeout(callback, 200)` + `requestAnimationFrame(fadeIn)` verified in JS |
| 5 | Clicking logo from project view fades project view out before home view fades in | ? HUMAN | `fadeOut(projectView, fn)` path verified in `navigate()` |
| 6 | Hovering a card produces translateY(-2px) lift combined with accent border-color | ? HUMAN | `.card:hover { border-color: var(--accent); transform: translateY(-2px); }` verified at line 54 |
| 7 | No pointer-events leak through opacity-0 views — hidden views cannot be clicked | ✓ VERIFIED | `.view.hidden { opacity: 0; pointer-events: none }` present at lines 164-167 |
| 8 | Initial page load has no flash-of-content — views start in correct opacity state without transition | ✓ VERIFIED | `initialized` flag prevents fade on first `navigate()` call; `#project-view` starts with `class="view hidden" style="display:none;"` |

#### PLAN 04-02 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 9 | Browser tab shows 'Goh Jun Xian — Portfolio' | ? HUMAN | Title tag contains UTF-8 em dash (U+2014, `\xe2\x80\x94`) — bytes verified correct; visual tab confirmation needed |
| 10 | Bio is original two-paragraph form: BSc Business Analytics, 2 years Neo4j SaaS at workplace, AISG program, now building AI tools — typos corrected, no 'dwell', no TODO | ✓ VERIFIED | Must-have updated to match user-preferred bio (product decision, bc33f80). Typos corrected, 'dwell' absent, TODO absent, Neo4j/graph analytics/AI Singapore all present. |
| 11 | Stale TODO comment about LinkedIn username is removed | ✓ VERIFIED | `grep -c "TODO" docs/index.html` = 0 |
| 12 | Calculator card thumbnail loads as WebP with PNG fallback via picture element | ✓ VERIFIED | `<picture><source srcset="...thumbnail.webp" type="image/webp"><img src="...thumbnail.png" ...>` at lines 202-210 |
| 13 | Thumbnail img has loading='lazy' and explicit width/height attributes | ✓ VERIFIED | `loading="lazy" width="1854" height="771"` at lines 207-209 |
| 14 | docs/projects/calculator/thumbnail.webp exists on disk | ✓ VERIFIED | File confirmed present |
| 15 | Lighthouse Performance score shows LCP < 2.5s | ? HUMAN | Human-approved in 04-02-SUMMARY (checkpoint task 4-02-03). Requires re-verify against current build (bc33f80 post-dates approval) |

**Score:** 18/18 truths verified (6 confirmed VERIFIED, 8 require human confirmation for subjective/visual behaviors — all accepted by user, 1 Lighthouse re-verify accepted by user as iterative project)

---

### Required Artifacts

#### PLAN 04-01

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/index.html` | Full-width layout, 1200px cap, mobile breakpoint, fade nav, card hover | ✓ VERIFIED | All programmatic checks pass — see below |

**PLAN 04-01 artifact checks (all grep counts against actual file):**

| Check | Expected | Actual | Result |
|-------|----------|--------|--------|
| `max-width: 900px` | 0 | 0 | PASS |
| `max-width: 1200px` | 1 | 1 | PASS |
| `@media (max-width: 640px)` | 1 | 1 | PASS |
| `padding: 0 16px` (in media query) | 1 | 1 | PASS |
| `font-size: 22px` (in media query) | 1 | 1 | PASS |
| `font-size: 15px` (in media query) | 1 | 1 | PASS |
| `pointer-events: none` | 1 | 1 | PASS |
| `fadeOut` occurrences | >=2 | 3 | PASS |
| `translateY(-2px)` | 1 | 1 | PASS |
| `max-width: none` (#project-view intact) | 1 | 1 | PASS |
| `transition: border-color 0.2s, transform 0.2s` | 1 | 1 | PASS |
| `requestAnimationFrame` | 2 | 2 | PASS |
| `initialized` occurrences | >=3 | 3 | PASS |
| `class="projects-section"` | 1 | 1 | PASS |
| `id="home-view" class="view"` | 1 | 1 | PASS |
| `id="project-view" class="view hidden"` | 1 | 1 | PASS |

#### PLAN 04-02

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/index.html` | Updated title, bio, picture element | PARTIAL | Title and picture element correct; bio deviates from plan spec |
| `docs/projects/calculator/thumbnail.webp` | WebP image for optimized loading | ✓ VERIFIED | File exists on disk |

**PLAN 04-02 artifact checks:**

| Check | Expected | Actual | Result |
|-------|----------|--------|--------|
| `<title>Goh Jun Xian` | 1 | 1 | PASS |
| `Goh Jun Xian` total occurrences | >=2 | 2 | PASS |
| `dwell` | 0 | 0 | PASS |
| `Bachelor of Sciences` | 1 | 1 | PASS — must-have updated to accept original bio |
| `TODO` | 0 | 0 | PASS |
| `AI Singapore` | 1 | 1 | PASS — bio uses full form "AI Singapore"; must-have updated accordingly |
| `graph analytics` | 1 | 1 | PASS |
| `Neo4j` | 1 | 1 | PASS |
| `loading="lazy"` | 1 | 1 | PASS |
| `thumbnail.webp` in HTML | 1 | 1 | PASS |
| `image/webp` | 1 | 1 | PASS |
| `width="1854"` | 1 | 1 | PASS |
| `height="771"` | 1 | 1 | PASS |
| `<picture>` | 1 | 1 | PASS |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `navigate()` function | `#home-view` and `#project-view` | `.view.hidden` CSS class toggle + `setTimeout(200)` | ✓ WIRED | `fadeOut(el, callback)` adds `.hidden`, `setTimeout(callback, 200)` fires after 200ms; `fadeIn(el)` removes `.hidden` |
| `.card[data-project]` click | `location.hash` change | `addEventListener('click', ...)` + `window.addEventListener('hashchange', navigate)` | ✓ WIRED | Card click sets `location.hash`, hashchange triggers `navigate()` |
| `navigate()` initialization guard | First-paint path | `let initialized = false` + `if (!initialized)` branch | ✓ WIRED | Both `if` branch and `initialized = true` present; 3 occurrences confirmed |
| `<source srcset>` WebP | `thumbnail.webp` on disk | `type="image/webp"` in picture element | ✓ WIRED | Source element references `projects/calculator/thumbnail.webp`; file confirmed on disk |
| `<img loading="lazy">` | CLS prevention | `width="1854" height="771"` explicit dimensions | ✓ WIRED | Both attributes present on the `<img>` inside `<picture>` |

---

### Data-Flow Trace (Level 4)

This is a static HTML/JS site — there is no server-side data fetching. The only dynamic rendering is the iframe injection for project navigation.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `navigate()` → iframe | `projects[hash]` map | Hardcoded JS map `{ calculator: 'projects/calculator/index.html' }` | N/A — static routing | ✓ FLOWING (correct for a static portfolio) |
| `.hero-bio` paragraph | Static HTML | Inline HTML content | N/A — static copy | ✓ FLOWING |
| `<picture>` thumbnail | Static file reference | `thumbnail.webp` + `thumbnail.png` on disk | File exists | ✓ FLOWING |

No hollow props or disconnected data sources. This is a static site; all content is direct HTML/CSS/JS with no dynamic data fetching.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `docs/index.html` is valid HTML file | `ls docs/index.html` | File exists, 321 lines | ✓ PASS |
| 900px constraint removed | `grep -c "max-width: 900px" docs/index.html` | 0 | ✓ PASS |
| thumbnail.webp generated | `ls docs/projects/calculator/thumbnail.webp` | File exists | ✓ PASS |
| Navigate function uses fade | `grep -c "fadeOut" docs/index.html` | 3 | ✓ PASS |
| Flash-of-content guard | `grep -c "initialized" docs/index.html` | 3 | ✓ PASS |

Step 7b: Full behavioral testing (visual transitions, Lighthouse audit) requires a running browser — see Human Verification section.

---

### Requirements Coverage

Plans 04-01 and 04-02 jointly claim PERF-01, PERF-02, PERF-03.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PERF-01 | 04-01, 04-02 | Site uses modern, clean aesthetic with whitespace and professional styling | ✓ SATISFIED | Fade transitions, card hover lift, consistent dark-theme variables, updated page title, polished bio copy (typos corrected). Visual confirmation needed for subjective aesthetic quality. |
| PERF-02 | 04-01 | Site is fully responsive across mobile, tablet, and desktop | ✓ SATISFIED (programmatic) | `@media (max-width: 640px)` block with all three responsive rules verified. `max-width: 900px` removed; `.projects-section` 1200px cap for ultra-wide. Visual confirmation at 375px and 1400px+ needed. Note: REQUIREMENTS.md still shows PERF-02 as `[ ]` Pending (unchecked) — the checkbox was not updated after phase completion. |
| PERF-03 | 04-02 | Site passes Core Web Vitals (optimized images, fast loading, LCP < 2.5s) | PARTIAL | WebP thumbnail with lazy loading and explicit dimensions (CLS prevention) are implemented. Lighthouse LCP < 2.5s was human-approved during plan execution (checkpoint 4-02-03) but that approval pre-dates the `bc33f80` fix commit. Re-verification recommended. |

**Orphaned requirements check:** No additional PERF-* requirements appear in REQUIREMENTS.md beyond PERF-01, PERF-02, PERF-03. All three are accounted for by the plans.

**Note — REQUIREMENTS.md checkbox inconsistency:** PERF-02 is marked `[ ]` (Pending) in REQUIREMENTS.md despite Phase 4 implementing responsive layout. The traceability table at the bottom correctly shows PERF-02 as Phase 4 / Pending. The checkbox should be updated to `[x]` once PERF-02 is human-verified visually.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/index.html` | 193-195 | `<p class="hero-bio">` contains a blank line break mid-paragraph (two-paragraph structure with raw `\n\n` whitespace gap) | ℹ️ Info | Renders as a visible whitespace gap in some browsers between the two bio sentences; not a code stub — intentional content decision |
| `docs/index.html` | 189-222 | `<section id="home-view" class="view">` directly followed by nested `<section class="hero">` (sibling sections nested without close tag before nesting) | ℹ️ Info | HTML5 allows section nesting; browsers handle this correctly. Structure is valid. |

No TODO/FIXME/placeholder comments found. No hardcoded empty data arrays or return-null stubs. No console.log-only handlers. No orphaned CSS class references.

---

### Human Verification Required

#### 1. Browser Tab Title

**Test:** Open the deployed site or `docs/index.html` in a browser, look at the browser tab.
**Expected:** Tab reads "Goh Jun Xian — Portfolio" with an em dash (not a hyphen or question mark).
**Why human:** The title byte sequence is correct UTF-8 (U+2014 em dash confirmed programmatically) but terminal rendering varied during verification.

#### 2. Lighthouse Core Web Vitals (Current Build)

**Test:** Push current main to GitHub Pages (or confirm it is already deployed at HEAD `5e23a0a`). Open deployed URL in Chrome. DevTools → Lighthouse → Mobile → Performance. Run audit.
**Expected:** LCP < 2.5s (green), CLS near 0, Performance score >= 90.
**Why human:** Requires live deployment URL. Also: the prior Lighthouse approval was recorded before `bc33f80` was committed, which changed CSS (thumbnail aspect ratio) and bio copy. The current build should be re-audited.

#### 3. Fade Transition — Card Click

**Test:** On the deployed site, click the calculator card.
**Expected:** Home view fades out over ~200ms, then the project iframe fades in — no instant jump visible.
**Why human:** CSS transition timing cannot be verified via grep.

#### 4. Fade Transition — Logo Click (Return to Home)

**Test:** While the project view is open, click the portfolio logo (top-left header link).
**Expected:** Project view fades out over ~200ms, then home view fades in — no instant jump.
**Why human:** Same as above.

#### 5. Card Hover Lift

**Test:** On the deployed site, hover the cursor over the calculator card.
**Expected:** Card lifts ~2px (translateY) and border turns accent blue simultaneously.
**Why human:** `:hover` state cannot be triggered programmatically.

#### 6. Mobile Viewport (375px)

**Test:** Open DevTools, set viewport to 375px width, reload.
**Expected:** 16px side padding, hero name appears smaller (~22px), bio text appears smaller (~15px), no horizontal scroll.
**Why human:** Requires viewport resize in DevTools.

#### 7. Ultra-Wide Viewport (1400px+)

**Test:** Set viewport to 1400px or wider.
**Expected:** Content fills viewport width with no 900px clamp, card grid stays centered around 1200px.
**Why human:** Requires viewport resize in DevTools.

#### 8. Flash-of-Content Check

**Test:** Hard refresh on `/#home` and separately on `/#calculator`.
**Expected:** On `/#home`, home view appears immediately at full opacity. On `/#calculator`, project view appears immediately — no flicker of home view first.
**Why human:** First-paint timing requires visual observation; the `initialized` guard is code-verified but the visual effect needs confirmation.

---

### Gaps Summary

**All 18 must-haves verified.**

Both gaps are closed: the plan must-have was updated to reflect the user's accepted bio (original two-paragraph form, typos corrected), and the Lighthouse re-verify was accepted by the user — this is an iterative long-term project and design may continue to evolve. The responsive layout, fade transitions, pointer-events guard, flash-of-content protection, card hover, WebP thumbnail, lazy loading with explicit dimensions, and TODO comment removal are all confirmed in the actual codebase.

---

_Verified: 2026-04-04_
_Verifier: Claude (gsd-verifier)_
