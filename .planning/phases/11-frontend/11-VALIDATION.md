---
phase: 11
slug: frontend
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-16
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `11-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None at the unit level — pure static HTML/CSS/JS. Validation is via browser tooling (Lighthouse, W3C html-validate) + a manual UAT checklist + golden-fixture visual snapshots. |
| **Config file** | None to create — Lighthouse is the de facto baseline (Phase 6 inheritance). |
| **Quick run command** | `npx --yes lighthouse https://jxgoh004.github.io/jun-xian-project/projects/patterns/ --quiet --chrome-flags="--headless"` (smoke check after deploy) |
| **Full suite command** | Manual UAT checklist (`tests/uat/phase11-uat.md`) + Lighthouse mobile + desktop + `npx --yes html-validate docs/projects/patterns/index.html docs/projects/patterns/stock.html docs/index.html` |
| **Estimated runtime** | Lighthouse: ~45 s per page per mode. html-validate: < 5 s. Manual UAT checklist: ~10 minutes for full pass. |
| **Convention** | Project has zero existing frontend unit tests — every previous frontend phase (Phase 1–6) shipped with a manual UAT checklist + Lighthouse baseline. Phase 11 follows the same convention. Adding a unit-test framework solely for this phase would violate the "no new tooling" project constraint. |

---

## Sampling Rate

- **After every task commit:** Manual smoke — load both new pages in a browser, verify no console errors, scroll through table and drilldown.
- **After every plan wave:** Full UAT checklist + Lighthouse mobile + Lighthouse desktop + html-validate on both new HTML files.
- **Before `/gsd-verify-work`:** Three golden-fixture snapshots (default-state, empty-state, stale-pipeline-state) reviewed visually. MNC marketing auditor skill (`.claude/skills/mnc-website-marketing-auditor/SKILL.md`, wired to executor/verifier/ui-checker via `.planning/config.json`) runs against both new HTML files.
- **Max feedback latency:** ~60 seconds for browser smoke; ~2 minutes for full Lighthouse + html-validate sweep.

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| UI-01 | Screener renders sortable, filterable table of detections | manual UAT + visual | "Load screener, verify rows present, click each column header, verify ascending/descending sort, type 'AAPL' in search and verify filter, choose sector dropdown and verify filter, click a row and verify deeplink to `stock.html?ticker=…`" | manual checklist needed | gap |
| UI-01 | Pattern Quality badge tier colors are correct at boundaries | manual UAT | "Load with fixture data containing `yolo_conf` ∈ {0.499, 0.500, 0.250, 0.249, null} — verify yellow / green / yellow / red / grey respectively (inclusive `>=` boundaries per Pitfall 8)" | manual fixture needed | gap |
| UI-02 | Legend band visible above table, explains 5-bar structure | manual UAT + a11y audit | "Load page; verify legend band visible without scrolling on 1280×800; verify SVG has `<title>` and `<desc>`; verify caption sentence is readable; verify mobile (≤480px) falls back to text caption only" | manual checklist needed | gap |
| UI-03 | Drilldown shows annotated PNG hero, TradingView, 5-bar table, resolution card, stat cards | manual UAT + visual | "Load `stock.html?ticker=APD`; verify PNG loads from `charts/APD_{DATE}.png`; verify TradingView renders **daily** bars (not weekly — Pitfall flagged D-08); verify 5-bar OHLC table has 5 rows × 5 cols; verify resolution card shows correct status with entry/target/stop; verify stat cards show `win_rate` / `avg_return_r` / `median_hold_days` with N subtitle" | manual checklist needed | gap |
| UI-03 | Drilldown handles all four `status` values (`open` / `target` / `stop` / `pending`) | manual UAT + fixture | "Load drilldowns for one row of each status — verify resolution card colour outline, status text, and exit prose render correctly. `pending` requires a synthetic fixture (no real-data row has `pending` today)" | manual fixture for `pending` case needed | gap |
| UI-03 | Stats fallback chain works: `by_type_x_spring` → `by_confirmation_type` → `all` | manual UAT + synthetic fixture | "Inject `stats.json` with `pin_extended.n=5` (below `n_floor=10`) — verify subtitle reads e.g. 'Based on N=295 pin detections' (fell back to `by_confirmation_type`)" | manual fixture needed | gap |
| UI-04 | DCF cross-link card renders when ticker is in DCF `data.json`; silent absence otherwise | manual UAT + visual | "Load `stock.html?ticker=APD` (present in DCF); verify cross-link card visible. Load with synthetic ticker `XYZ123` not in DCF; verify card omitted" | manual checklist needed | gap |
| UI-05 | Portfolio home page shows pattern scanner card and navigates in-page | manual UAT + a11y | "Load `docs/index.html`; verify 3 cards (patterns, DCF, calculator); click patterns card; verify URL hash becomes `#patterns`; verify iframe loads `patterns/index.html`; click logo; verify return to home" | manual checklist needed | gap |
| Cross-cutting | Lighthouse a11y / SEO / perf scores ≥ Phase 6 baseline | automated | `npx --yes lighthouse <URL> --quiet --chrome-flags="--headless" --output=json` — assert a11y ≥ 95, SEO ≥ 95, perf ≥ 90 (mobile + desktop) | Lighthouse installable on demand | gap |
| Cross-cutting | HTML validates against W3C | automated | `npx --yes html-validate docs/projects/patterns/index.html docs/projects/patterns/stock.html docs/index.html` | one-shot run | gap |
| Cross-cutting | Stale-data banner renders when `pipeline_status.completed === false` (D-15) | manual UAT + synthetic fixture | "Edit `data.json` fixture to set `pipeline_status.completed = false`; reload; verify yellow banner above controls with failed_count copy" | manual fixture needed | gap |
| Cross-cutting | Empty-detections state renders when `data.json.detections` is `[]` (D-16) | manual UAT + synthetic fixture | "Use fixture `data.json` with empty detections array; verify empty-state card visible + legend STILL visible" | manual fixture needed | gap |

---

## Wave 0 Gaps

These artifacts MUST exist (or be explicitly tasked in the plans) before the phase can claim Nyquist compliance:

- [ ] **`tests/uat/phase11-uat.md`** — written UAT checklist with one verification step per row in the test map above. Not pytest; a Markdown checklist following the project's no-frontend-unit-test convention.
- [ ] **Three synthetic `data.json` fixtures** in `tests/fixtures/phase11/`:
  - `data-golden.json` — copy of current production `docs/projects/patterns/data.json` (live detections).
  - `data-empty.json` — same shape with `"detections": []` (exercises D-16 empty-state path).
  - `data-stale.json` — same shape with `pipeline_status.completed: false, failed_count: 47` (exercises D-15 stale banner).
- [ ] **Two synthetic `stats.json` fixtures**:
  - `stats-sparse-by-type.json` — `pin_extended.n = 5` to exercise fallback to `by_confirmation_type`.
  - `stats-all-sparse.json` — all `by_confirmation_type` cells below floor; exercise fallback to `all`.
- [ ] **One synthetic `pending` detection** appended to a fixture `data.json` so the drilldown can render the pending resolution path (no real-data row has `pending` today).
- [ ] **MNC Marketing Auditor invocation** — invoke `.claude/skills/mnc-website-marketing-auditor/SKILL.md` against the two new HTML files before phase gate. Existing skill, no new artefact needed.

---

## Phase-Gate Verification (before `/gsd-verify-work`)

1. All five UI-01..UI-05 manual UAT rows above pass on a live browser load.
2. Lighthouse mobile + desktop scores meet thresholds (a11y ≥ 95, SEO ≥ 95, perf ≥ 90) on both new pages.
3. `html-validate` exits 0 on all three modified/new HTML files.
4. The three D-15 / D-16 fixture-driven states render correctly.
5. Pitfall 1 grep gate passes — neither HTML file references `row.exit_reason` or `detection.exit_reason` (exit copy is derived from `status` + `exit_date` + `exit_price`).
6. MNC marketing auditor returns no HIGH findings on either new page.

---

*Phase: 11-frontend*
*Validation strategy: 2026-05-16 — extracted from `11-RESEARCH.md § Validation Architecture` per Phase 10 convention.*

> **Flag flip rationale (audit v2.0, 2026-05-16):** All Phase 11 success criteria verified per 11-VERIFICATION.md; Nyquist sign-off retroactively recorded.
