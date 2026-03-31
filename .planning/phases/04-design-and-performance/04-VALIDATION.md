---
phase: 4
slug: design-and-performance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual browser verification + Lighthouse CLI / Chrome DevTools |
| **Config file** | none — static HTML, no test framework |
| **Quick run command** | Open `docs/index.html` via GitHub Pages URL in browser |
| **Full suite command** | Run Lighthouse audit in Chrome DevTools on deployed GitHub Pages URL |
| **Estimated runtime** | ~60 seconds manual check |

---

## Sampling Rate

- **After every task commit:** Open browser, verify the specific change visually
- **After every plan wave:** Full visual check across mobile (320px), tablet (768px), desktop (1280px) viewports using Chrome DevTools device emulation
- **Before `/gsd:verify-work`:** Lighthouse run must show LCP < 2.5s; all viewport sizes must render correctly
- **Max feedback latency:** ~60 seconds (open browser, resize viewport)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | PERF-02 | visual | Open in browser at 1400px width — verify no 900px max-width clamp | ✅ | ⬜ pending |
| 4-01-02 | 01 | 1 | PERF-02 | visual | Resize to ≤640px — verify padding 16px, name 22px, bio 15px | ✅ | ⬜ pending |
| 4-01-03 | 01 | 2 | PERF-01 | visual | Click card — verify fade transition (no instant jump) at ~200ms | ✅ | ⬜ pending |
| 4-01-04 | 01 | 2 | PERF-01 | visual | Hover over card — verify translateY(-2px) lift + border-color change | ✅ | ⬜ pending |
| 4-02-01 | 02 | 1 | PERF-01 | grep | `grep "Goh Jun Xian" docs/index.html` returns title tag match | ✅ | ⬜ pending |
| 4-02-02 | 02 | 1 | PERF-01 | grep | `grep "loading=\"lazy\"" docs/index.html` returns match | ✅ | ⬜ pending |
| 4-02-03 | 02 | 1 | PERF-03 | file | `docs/projects/calculator/thumbnail.webp` exists | ❌ W0 | ⬜ pending |
| 4-02-04 | 02 | 2 | PERF-03 | lighthouse | Lighthouse LCP < 2.5s on deployed GitHub Pages URL | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/projects/calculator/thumbnail.webp` — produced by Python Pillow conversion script in plan 04-02

*Wave 0 is a single file creation (WebP conversion) — no test framework install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-width layout at 1400px+ viewport | PERF-02 | Visual layout check — no automated pixel testing | Open site in browser, set viewport to 1400px+, verify content fills width with ~1200px card grid cap |
| Mobile layout at 320px | PERF-02 | Visual check — requires viewport emulation | Chrome DevTools → iPhone SE (375px) or manual 320px, verify hero font sizes and 16px padding |
| Fade transition timing | PERF-01 | Perceptual check — 200ms needs to feel smooth | Click card, verify fade is visible but not sluggish; check no flash-of-content on initial load |
| Card hover lift | PERF-01 | Perceptual check | Hover over calculator card, verify subtle upward shift + border highlight |
| Lighthouse LCP < 2.5s | PERF-03 | Requires deployed site + Lighthouse tool | Chrome DevTools → Lighthouse tab → Run audit on GitHub Pages URL → check LCP in Performance section |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
