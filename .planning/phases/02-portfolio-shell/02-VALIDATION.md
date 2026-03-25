---
phase: 2
slug: portfolio-shell
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — visual/structural HTML inspection only |
| **Config file** | none |
| **Quick run command** | `open docs/index.html` (browser visual check) |
| **Full suite command** | `open docs/index.html` (browser visual check) |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Open `docs/index.html` in browser and verify visual output
- **After every plan wave:** Full visual inspection per acceptance criteria
- **Before `/gsd:verify-work`:** All manual checks in table below must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | HOME-01 | manual | `grep -c "logo" docs/index.html` | ✅ | ⬜ pending |
| 2-01-02 | 01 | 1 | HOME-02 | manual | `grep -c "hero-bio" docs/index.html` | ✅ | ⬜ pending |
| 2-01-03 | 01 | 1 | SHOW-01 | manual | `grep -c "project-card" docs/index.html` | ✅ | ⬜ pending |
| 2-01-04 | 01 | 1 | SHOW-02 | manual | `grep -c "category-tag" docs/index.html` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — this is a static HTML/CSS phase with no test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Logo appears top-left | HOME-01 | Visual layout, no automated pixel test | Open docs/index.html — confirm logo in top-left nav |
| Bio text and tech list visible | HOME-02 | Visual content check | Open docs/index.html — confirm hero section with bio and tech list |
| Project card grid renders | SHOW-01 | Visual layout | Open docs/index.html — confirm at least one card with title, thumbnail, description |
| Category tags visible on card | SHOW-02 | Visual content | Open docs/index.html — confirm category tags on project card |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
