---
phase: 01-static-foundation
verified: 2026-03-23T00:00:00Z
status: human_needed
score: 3/3 must-haves verified
human_verification:
  - test: "Visit https://jxgoh004.github.io/jun-xian-project/ in a browser and confirm the portfolio page loads with dark theme, 'Projects' heading, and at least one project card visible."
    expected: "Portfolio landing page renders with no 404 and the Intrinsic Value Calculator card is visible and clickable."
    why_human: "HTTP 200 is confirmed programmatically from this machine, but browser-side rendering, DNS propagation, and CDN edge behaviour cannot be verified by curl."
  - test: "Click the Intrinsic Value Calculator card and confirm the calculator page loads at /projects/calculator/ with the correct dark-themed UI."
    expected: "Calculator renders with ticker input, Fetch Data button, and header status indicator."
    why_human: "Page existence is confirmed (HTTP 200 from curl) but correct visual rendering requires a browser."
  - test: "On the calculator page, observe the server-status indicator dot. Confirm it turns green within 30 seconds (allow for Render cold-start)."
    expected: "Green dot — Render API health check passes, confirming CORS allows the GitHub Pages origin."
    why_human: "CORS headers are confirmed via curl (access-control-allow-origin: https://jxgoh004.github.io), but the browser fetch from the live page under the actual GitHub Pages origin is the definitive CORS test."
  - test: "Enter 'AAPL' in the ticker field and click 'Fetch Data'. Confirm stock data loads."
    expected: "Stock data populates the results panel. No CORS error in browser console."
    why_human: "End-to-end data flow (GitHub Pages -> Render API -> yfinance -> back) requires a real browser session to verify."
  - test: "After fetching AAPL data, change the valuation method dropdown. Confirm the verify panel updates immediately without a re-fetch."
    expected: "Verify panel re-renders with the selected method's data — bug fix committed in 797213e is active."
    why_human: "Requires interactive browser testing; cannot be verified by static code inspection alone."
---

# Phase 1: Static Foundation Verification Report

**Phase Goal:** Restructure repo for GitHub Pages static site serving from docs/ directory, with calculator frontend separated from Flask backend, and GitHub Pages deployment live with Render API CORS verified.
**Verified:** 2026-03-23
**Status:** human_needed (all automated checks passed; 5 items require browser confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Visiting the GitHub Pages URL loads a page (no 404, no broken deployment) | VERIFIED | `curl https://jxgoh004.github.io/jun-xian-project/` → HTTP 200; `/projects/calculator/` → HTTP 200 |
| 2 | Repository file structure separates portfolio shell from project assets so adding a new project requires only adding files and a card entry | VERIFIED | `docs/index.html` has `.projects` CSS Grid; each project is `docs/projects/{name}/`; portfolio card links to `projects/calculator/index.html` |
| 3 | The existing Render-hosted API is reachable from the static frontend (CORS verified) | VERIFIED | Render returns `access-control-allow-origin: https://jxgoh004.github.io`; `/api/health` returns `{"status":"ok"}`; `CORS(app)` allow-all confirmed in `api_server.py` |

**Score:** 3/3 truths verified (automated evidence)

---

## Required Artifacts

### Plan 01-01

| Artifact | Provides | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Status |
|----------|----------|-----------------|----------------------|----------------|--------|
| `docs/index.html` | Portfolio shell landing page | Yes (2800 bytes) | Contains `<!DOCTYPE html>`, `.projects` grid, `href="projects/calculator/index.html"`, `<span class="tag">Python</span>` | Served at root by GitHub Pages — HTTP 200 confirmed | VERIFIED |
| `docs/projects/calculator/index.html` | Calculator frontend separated from Flask server | Yes (61048 bytes) | Contains "True Value Finder", `jun-xian-project.onrender.com`, API constant, `api/health` fetch, `api/fetch-stock` fetch | Served at `/projects/calculator/` — HTTP 200 confirmed | VERIFIED |
| `docs/projects/calculator/img/logo_2.png` | Calculator logo asset | Yes (4,928,756 bytes) | Non-zero binary PNG | Referenced in `docs/index.html` `<img src="projects/calculator/img/logo_2.png">` | VERIFIED |

### Plan 01-02

| Artifact | Provides | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Status |
|----------|----------|-----------------|----------------------|----------------|--------|
| `docs/index.html` | Portfolio landing page served by GitHub Pages | Yes | Contains `<!DOCTYPE html>` | HTTP 200 from `https://jxgoh004.github.io/jun-xian-project/` | VERIFIED |
| `docs/projects/calculator/index.html` | Calculator frontend that calls Render API | Yes | Contains `jun-xian-project.onrender.com` | HTTP 200 from `/projects/calculator/`; CORS headers confirmed from Render | VERIFIED |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docs/projects/calculator/index.html` | `https://jun-xian-project.onrender.com` | API constant at line 707–709 | WIRED | `const API = (window.location.hostname === 'localhost' ...) ? 'http://localhost:5000' : 'https://jun-xian-project.onrender.com'` |
| `docs/projects/calculator/index.html` | `/api/health` | `fetch(API + '/api/health', ...)` at line 719 | WIRED | AbortSignal.timeout(3000) present; response handling present |
| `docs/projects/calculator/index.html` | `/api/fetch-stock/` | `` fetch(`${API}/api/fetch-stock/${ticker}`) `` at line 834 | WIRED | Ticker interpolated; response handling populates results |
| Render `api_server.py` | GitHub Pages origin | `CORS(app)` (flask-cors allow-all) | WIRED | Confirmed: `access-control-allow-origin: https://jxgoh004.github.io` returned by Render |
| `docs/index.html` | `docs/projects/calculator/index.html` | `<a class="card" href="projects/calculator/index.html">` at line 78 | WIRED | Relative link present in portfolio shell |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEPLOY-01 | 01-01, 01-02 | Site is deployable to GitHub Pages as a static site | SATISFIED | `docs/` directory exists and is committed; GitHub Pages serves HTTP 200 from `https://jxgoh004.github.io/jun-xian-project/`; commits `74129b9`, `4cef77e` |
| DEPLOY-02 | 01-01 | Site structure allows adding future projects via code editing | SATISFIED | `docs/projects/{name}/` pattern established; `.projects` CSS Grid in `docs/index.html` grows automatically; extensibility documented in SUMMARY |

No orphaned requirements: REQUIREMENTS.md traceability table maps only DEPLOY-01 and DEPLOY-02 to Phase 1, and both plans claim them.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Checked files: `docs/index.html`, `docs/projects/calculator/index.html`, `.gitignore`

No TODO/FIXME, no placeholder returns, no empty handlers, no console.log-only implementations detected.

---

## Additional Finding: Local Commits Not Yet Pushed

`git status` shows the local branch is **3 commits ahead of `origin/main`**:

```
53ff3b3 docs(01-02): complete github-pages-deploy plan
797213e fix: re-render verify panel when user switches valuation method
4cef77e chore(01-02): verify GitHub Pages live and CORS confirmed
```

The GitHub Pages deployment confirmed working (HTTP 200) reflects an earlier push. The three unpushed commits include the bug fix (`797213e`) and the SUMMARY doc. The live deployment will not reflect the verify-panel fix until these are pushed. This is a **warning**, not a blocker — the fix exists locally and the deployment URL is live.

---

## Human Verification Required

### 1. Portfolio Landing Page Visual Render

**Test:** Open `https://jxgoh004.github.io/jun-xian-project/` in a browser.
**Expected:** Dark-themed page with "Projects" heading and Intrinsic Value Calculator card visible and clickable.
**Why human:** HTTP 200 confirmed programmatically but visual rendering, CSS application, and card layout require a browser.

### 2. Calculator Page Renders Correctly

**Test:** Click the calculator card. Confirm `/projects/calculator/` loads the full calculator UI (ticker input, Fetch Data button, header with status indicator).
**Expected:** Calculator page renders identically to the standalone version.
**Why human:** Page existence confirmed (HTTP 200) but correct visual rendering requires a browser.

### 3. Render API Health Check (CORS live test)

**Test:** On the calculator page, observe the server-status dot in the header. Allow up to 30 seconds for Render cold-start.
**Expected:** Dot turns green — API health check passes from the GitHub Pages origin.
**Why human:** CORS headers confirmed via server-side curl, but the browser fetch from the actual GitHub Pages domain is the true end-to-end CORS test.

### 4. Stock Data Fetch End-to-End

**Test:** Enter "AAPL" in the ticker field and click "Fetch Data".
**Expected:** Stock data populates the results panel. No CORS errors in browser console (F12).
**Why human:** Full data path (GitHub Pages → Render → yfinance → JSON response → JS render) requires a live browser session.

### 5. Verify Panel Method-Switch (Bug Fix)

**Test:** After fetching AAPL data, change the valuation method dropdown (e.g., OCF → FCF → Earnings).
**Expected:** The verify panel re-renders immediately with the selected method's figures — no re-fetch needed.
**Why human:** `onMethodChange()` is wired via `onchange` attribute at line 508 and defined at line 771, but interactive re-render correctness requires browser testing.

---

## Gaps Summary

No gaps found. All automated checks pass:

- All three artifacts exist, are substantive (non-placeholder), and are wired into the deployment
- All five key links are present and connected
- Both required requirements (DEPLOY-01, DEPLOY-02) are satisfied with evidence
- GitHub Pages URL returns HTTP 200 (portfolio and calculator sub-path)
- Render API returns `{"status":"ok"}` and sends correct CORS headers for the GitHub Pages origin
- `.gitignore` no longer contains the `img//` typo
- Commits `74129b9`, `5dfafcb`, `4cef77e`, `797213e` all exist in git log

The phase is pending only final human browser confirmation. The warning about 3 unpushed commits should be resolved by pushing before marking Phase 1 fully complete.

---

_Verified: 2026-03-23_
_Verifier: Claude (gsd-verifier)_
