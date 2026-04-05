---
phase: 5
slug: s-p-500-stock-screener-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None installed — browser smoke tests + local Python invocation |
| **Config file** | None |
| **Quick run command** | `python scripts/fetch_sp500.py --limit 3` |
| **Full suite command** | Manual browser walkthrough: home → screener card → sort/filter → row click → calculator pre-filled |
| **Estimated runtime** | ~60 seconds (3-ticker dry-run) |

---

## Sampling Rate

- **After every task commit:** Open affected file in browser; verify the specific change renders correctly
- **After every plan wave:** Full browser walkthrough — home page → screener card click → screener loads → sort/filter → row click → calculator pre-filled
- **Before `/gsd:verify-work`:** Full walkthrough green + one successful GitHub Actions workflow run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | SCREENER-02 | unit | `python scripts/fetch_sp500.py --limit 3` exits 0, outputs valid JSON | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 0 | SCREENER-04 | manual | `.github/workflows/` directory exists | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 0 | SCREENER-02 | unit | `docs/projects/screener/data.json` contains `{"updated_at": null, "stocks": []}` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | SCREENER-02 | unit | `python scripts/fetch_sp500.py --limit 3` exits 0, `data.json` has 3 stock entries with all required fields | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 2 | SHOW-04 | smoke | `docs/index.html` contains `.card[data-project="screener"]`; open in browser, card visible | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 2 | NAV-03 | smoke | Click screener card, screener iframe loads at `projects/screener/index.html` | ❌ W0 | ⬜ pending |
| 5-04-01 | 04 | 3 | SCREENER-01 | smoke | Open screener page, table renders rows, default sort is discount % descending | ❌ W0 | ⬜ pending |
| 5-04-02 | 04 | 3 | SCREENER-01 | smoke | Type "Apple" in search, verify row count decreases | ❌ W0 | ⬜ pending |
| 5-04-03 | 04 | 3 | SCREENER-01 | smoke | Select sector from dropdown, verify only that sector's rows show | ❌ W0 | ⬜ pending |
| 5-04-04 | 04 | 3 | SCREENER-03 | smoke | Click a stock row, verify calculator opens with ticker pre-filled in input | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `docs/projects/screener/` — directory must exist before screener files
- [ ] `.github/workflows/` — directory must exist before workflow YAML
- [ ] `scripts/fetch_sp500.py` — batch script with `--limit N` flag for local testing
- [ ] `docs/projects/screener/data.json` — seed file (`{"updated_at": null, "stocks": []}`) so screener loads before first Actions run

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DCF formula matches calculator output | SCREENER-02 | Requires running both calculator and batch script for same ticker and comparing numbers | Fetch AAPL via calculator UI; run `python scripts/fetch_sp500.py --limit 1 --ticker AAPL`; compare intrinsic_value |
| GitHub Actions workflow runs end-to-end | SCREENER-04 | Requires live GitHub Actions environment and repo push | Trigger via `workflow_dispatch` in GitHub UI; verify `data.json` commit appears in repo history |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
