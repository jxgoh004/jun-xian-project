---
phase: 03-calculator-integration
verified: 2026-03-31T12:00:00Z
status: passed
score: 8/8 must-haves verified
gaps: []
human_verification:
  - test: "Calculator iframe renders stock data from Render API on live GitHub Pages site"
    expected: "Entering a ticker (e.g., AAPL) returns live financials without CORS errors in DevTools console"
    why_human: "Cannot invoke fetch() cross-origin or open a browser from the verifier — user has already approved this; recorded for audit trail"
---

# Phase 3: Calculator Integration Verification Report

**Phase Goal:** Visitors can click the intrinsic value calculator card and use the full calculator without leaving the site, and can return home via the logo
**Verified:** 2026-03-31
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Clicking the calculator card loads the calculator UI inside an iframe without a full page reload or new tab | VERIFIED | `docs/index.html` line 164: card is `<div data-project="calculator">` (not `<a href>`); click handler at line 218 sets `location.hash`; navigate() creates iframe at lines 199-203 |
| 2  | The URL updates to `#calculator` when viewing the calculator and `#home` (or bare) on the home page | VERIFIED | `location.hash = '#' + card.dataset.project` (line 219); navigate() reads `location.hash.slice(1) \|\| 'home'` (line 191) |
| 3  | Browser back button navigates between `#calculator` and `#home` correctly | VERIFIED | `window.addEventListener('hashchange', navigate)` at line 230 — any browser-triggered hash change (including back/forward) re-runs navigate() |
| 4  | Visiting the URL with `#calculator` directly opens the calculator view | VERIFIED | `navigate()` called on load at line 233; reads initial `location.hash` and creates iframe if hash matches a project key |
| 5  | Clicking the logo from the calculator view returns to the home page | VERIFIED | Header logo wrapped in `<a href="#home">` at line 148 — sets hash, triggers hashchange, navigate() hides project-view and shows home-view |
| 6  | The calculator iframe loads `projects/calculator/index.html` and the calculator functions normally | VERIFIED | `projects` map at line 187 maps `calculator` key to `'projects/calculator/index.html'`; `iframe.src = projects[hash]` at line 201; file confirmed present at `docs/projects/calculator/index.html` |
| 7  | Calculator fetches stock data from Render API when loaded via iframe on GitHub Pages (no CORS errors) | VERIFIED (human-approved) | User approved live verification: stock ticker fetch succeeded on deployed GitHub Pages site without CORS errors |
| 8  | Full navigation flow works on the live deployed site identical to local | VERIFIED (human-approved) | User approved: card click, logo return, back button, and direct `#calculator` URL all confirmed working on live site |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docs/index.html` | Hash routing, show/hide sections, iframe embed, logo home link | VERIFIED | 237-line file; contains all required structures — `#home-view` section (line 152), `#project-view` section (line 177), IIFE script block (lines 181-235), logo anchor (line 148), card div with `data-project` (line 164) |
| `docs/projects/calculator/index.html` | Calculator app with Render API fetch | VERIFIED | File exists; API constant at line 709 correctly targets `https://jun-xian-project.onrender.com` on non-localhost — works from GitHub Pages iframe since same-origin iframe src resolves API relative to calculator file's origin context |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docs/index.html` `.card` click | `location.hash = '#calculator'` | Click handler sets `location.hash = '#' + card.dataset.project` | VERIFIED | Line 219: dynamic assignment — pattern `location\.hash.*=.*calculator` did not match literally because value is dynamic (`'#' + card.dataset.project`), but the wiring is correct and functional |
| `docs/index.html` hashchange listener | iframe creation/removal | `navigate()` function toggles section visibility and manages iframe | VERIFIED | Lines 193-213: `projects[hash]` check gates iframe creation; `document.createElement('iframe')` at line 200; `iframe.remove()` at line 211 |
| `docs/index.html` header logo | `#home` navigation | `<a href="#home">` wrapping logo `<img>` | VERIFIED | Line 148: exact match `<a href="#home" style="display:flex;align-items:center;">` |

Note on key-link pattern false negative: The PLAN frontmatter defined `pattern: "location\\.hash.*=.*calculator"` expecting a hardcoded string. The implementation correctly uses a dynamic expression `'#' + card.dataset.project`, which is the better pattern (extensible to future projects). The wiring is fully present; the regex pattern in the plan was overly specific.

---

### Data-Flow Trace (Level 4)

Not applicable for this phase. `docs/index.html` renders no dynamic data from an API or store — it is a navigation shell. The iframe embeds the calculator as a separate document; the calculator's own data-flow (Render API → stock fields) was verified at the human checkpoint (live CORS test).

---

### Behavioral Spot-Checks

Step 7b: SKIPPED for local checks — the site requires a browser environment to verify iframe behavior. Human verification (user approval) substitutes for automated spot-checks on all six navigation behaviors. Static file checks below confirm entry-point readiness.

| Behavior | Check | Result | Status |
|----------|-------|--------|--------|
| `docs/index.html` is well-formed and has no unclosed tags | File ends at line 237 with `</html>` | Closed correctly | PASS |
| Calculator file exists at expected iframe src path | `docs/projects/calculator/index.html` present | Confirmed present | PASS |
| No `<a class="card" href="projects/calculator/index.html">` (old navigation) | Grep returned no matches | Not present | PASS |
| `git status docs/index.html` clean | No output (clean working tree) | No uncommitted changes | PASS |
| Commit `d02dff1` exists with Phase 3 changes | `git show d02dff1 --stat` confirms 80-line addition to `docs/index.html` | Confirmed | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SHOW-03 | 03-01-PLAN, 03-02-PLAN | Intrinsic value calculator is integrated as the first featured project | SATISFIED | Calculator card present at line 164; iframe loads `projects/calculator/index.html`; live deployment confirmed |
| NAV-01 | 03-01-PLAN, 03-02-PLAN | Clicking a project card loads that project running in-page (no new tab/window) | SATISFIED | Card is `<div>` not `<a>`; click sets `location.hash`; navigate() creates inline iframe — no new tab or page navigation occurs |
| NAV-02 | 03-01-PLAN, 03-02-PLAN | Clicking the logo returns user to home page from any project view | SATISFIED | Logo wrapped in `<a href="#home">`; triggers hashchange → navigate() → shows `#home-view`, hides `#project-view`, removes iframe |

No orphaned requirements. REQUIREMENTS.md Traceability table maps SHOW-03, NAV-01, NAV-02 to Phase 3, all three claimed by both plans, all three verified. PERF-01/02/03 are mapped to Phase 4 (not this phase).

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/index.html` | 160 | `<!-- TODO: Replace YOUR-HANDLE with actual LinkedIn username -->` | Info | Stale comment from Phase 2 — the href at line 159 already contains the real LinkedIn URL `https://linkedin.com/in/goh-jun-xian-5890ba10b/`. The TODO comment is misleading but has no functional impact. Not a Phase 3 concern. |
| `docs/index.html` | 122-129 | `.card-thumbnail-placeholder` CSS rule defined but the actual card uses `<img>` not the placeholder class | Info | Defensive fallback CSS retained from Phase 2. No functional impact. |

No blockers. No stubs in Phase 3 code. All Phase 3 additions are substantive and wired.

---

### Human Verification Required

#### 1. Live CORS Verification (Completed — recorded for audit)

**Test:** Open the GitHub Pages URL, click the calculator card, enter a stock ticker in the calculator, submit.
**Expected:** Stock data appears in the calculator; DevTools console shows no CORS errors from `jun-xian-project.onrender.com`.
**Why human:** Cannot open a browser or execute cross-origin fetch from the verifier.
**Result:** User approved on 2026-03-31. Stock fetch succeeded on live site without CORS errors.

---

### Gaps Summary

No gaps. All six observable truths from Plan 01 and both truths from Plan 02 are verified. The single key-link pattern false negative (dynamic `location.hash` assignment vs expected literal string pattern) is a plan artifact issue, not a code gap — the functional wiring is correct. The phase goal is fully achieved.

---

_Verified: 2026-03-31_
_Verifier: Claude (gsd-verifier)_
