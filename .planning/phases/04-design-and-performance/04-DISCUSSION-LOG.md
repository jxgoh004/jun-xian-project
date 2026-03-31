# Phase 4: Design and Performance — Discussion Log

**Date:** 2026-03-31
**Phase:** 04-design-and-performance

This file is a human-readable audit trail of the /gsd:discuss-phase session. It is NOT consumed by downstream agents.

---

## Areas Selected

User selected: Mobile layout, View transitions, Typography & spacing

---

## Area 1: Mobile Layout

**Q: What should happen to the header at mobile (≤640px)?**
Selected: Keep as-is — logo + "Portfolio" title side by side, already compact enough.

**Q: Hero section on mobile — how should font sizes and spacing shrink?**
Selected: Scale down proportionally — name 22px, bio 15px, main padding 16px.

**Q: Project iframe on mobile — acceptable or add mobile warning?**
Selected: Leave iframe as-is — calculator is desktop-first, users scroll within iframe.

---

## Area 2: View Transitions

**Q: How should the transition feel when clicking a project card?**
Selected: Fade — home fades out, project fades in, ~200ms CSS opacity transition.

**Q: Should card hover be enhanced beyond border-color?**
Selected: Add subtle lift — `transform: translateY(-2px)` on hover combined with existing border-color.

---

## Area 3: Typography & Spacing

**Q: Bio paragraph update?**
Selected: Rewrite for clarity — 2-3 sentences, data analyst → AI Engineer transition, Neo4j background, AISG program, building AI tools.

**Q: Page title tag?**
Selected: Use full name — "Goh Jun Xian — Portfolio".

**Q: Overall spacing feel?**
User clarified: wants the whole screen to be utilised at full width. Remove the 900px max-width constraint on main. Card grid capped at ~1200px centered. Desktop spacing values (60px top margin, 48px hero margin-bottom, 20px gap) stay unchanged — only mobile spacing adjusted.

**Q: Hero alignment at full width?**
Selected: Stay centered on all viewport widths.

---

*Discussion log: 2026-03-31*
