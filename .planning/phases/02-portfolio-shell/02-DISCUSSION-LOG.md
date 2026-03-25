# Phase 2: Portfolio Shell - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 02-portfolio-shell
**Areas discussed:** Bio section layout (session 1: 2026-03-23), Project card thumbnails (session 2: 2026-03-25)

---

## Bio Section Layout

*(Discussed in session 1 — 2026-03-23. Restored from .continue-here.md checkpoint.)*

| Option | Description | Selected |
|--------|-------------|----------|
| Centered hero | Name, title, bio, contact links centered above project grid | ✓ |
| Left-aligned sidebar | Bio on the left, projects on the right | |
| Top banner with grid below | Full-width banner with smaller bio text | |

**User's choice:** Centered hero
**Notes:** Transition story framing — data analyst (graph analytics / Neo4j) pivoting into AI Engineering, building AI-powered tools he personally uses and wants to share. Title: "AI Engineer". No skills section — bio + LinkedIn link only.

---

## Contact Links

| Option | Description | Selected |
|--------|-------------|----------|
| LinkedIn only | Single contact link | ✓ |
| LinkedIn + GitHub | Two links | |
| LinkedIn + GitHub + Email | Three links | |

**User's choice:** LinkedIn only
**Notes:** Keep it clean and focused.

---

## Skills Display

| Option | Description | Selected |
|--------|-------------|----------|
| Not included | Bio + contact links only | ✓ |
| Tech list in hero | Simple text list of technologies below bio | |
| Skill tags | Pill-style tags for each technology | |

**User's choice:** Not included — clean, focused hero.

---

## Project Card Thumbnails

| Option | Description | Selected |
|--------|-------------|----------|
| App screenshot | Capture actual project UI, use as card image | ✓ |
| Styled placeholder | CSS gradient/icon placeholder, no image file | |
| No thumbnail | Text-only cards (title, description, tags) | |

**User's choice:** App screenshot
**Notes:** Authentic — shows what the project looks like.

---

## Thumbnail Location

| Option | Description | Selected |
|--------|-------------|----------|
| docs/projects/calculator/ | Alongside the project it belongs to (scales per-project) | ✓ |
| docs/img/ | Shared images folder at docs root | |

**User's choice:** `docs/projects/{project-name}/thumbnail.png`

---

## Thumbnail Dimensions

| Option | Description | Selected |
|--------|-------------|----------|
| 16:9, ~800×450px | Standard widescreen, matches app screenshot proportions | ✓ |
| 4:3, ~800×600px | Slightly taller | |
| You decide | Claude picks a sensible default | |

**User's choice:** 16:9, ~800×450px

---

## Bio Copy Text

| Option | Description | Selected |
|--------|-------------|----------|
| User specifies | User provides key facts, Claude writes the paragraph | |
| Claude's discretion | Claude writes based on agreed framing | ✓ |
| Ready for context | Skip, move on | |

**User's choice:** Claude's discretion
**Notes:** Write a 2–3 sentence paragraph based on the transition story framing.

---

## Claude's Discretion

- Bio copy text: write naturally from the transition story (data analyst → AI Engineering)
- CSS placeholder for thumbnail if screenshot not yet available

## Deferred Ideas

None.
