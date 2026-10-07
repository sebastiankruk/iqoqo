## Context

See `proposal.md` for motivation. Currently, collection browsing isolates the user from conceptual Work and Expression entities.

## Goals / Non-Goals

**Goals:**
- Provide direct navigation to parent Work and Expression from collection cards and detail headers.
- Strictly adhere to valid HTML by avoiding nested `<a>` anchor tags inside cards.
- Maintain fast card clicking for primary item/manifestation inspection.

**Non-Goals:**
- Modifying backend SQL queries or introducing new API endpoints.
- Redesigning collection layout or grid systems.

## Decisions

- **Decision 1: Click delegation / Action pill overlay.**
  - *Rationale:* Rather than nesting an `<a>` inside another `<a>`, secondary pills for Work and Expression stop event propagation (`e.preventDefault()`, `e.stopPropagation()`) and navigate via Next.js `router.push()`, or use an interactive card footer rendered outside the primary card link.
  - *Alternatives considered:* Converting whole card to `<div>` with `onClick` (worse for SEO and right-click "Open in new tab").
- **Decision 2: Subtle badge styling with clear tooltips.**
  - *Rationale:* Display small muted badges (e.g. `Work: The Hobbit`, `Exp: Polish (Text)`) with hover tooltips so cards do not become visually cluttered.

## Risks / Trade-offs

- **[Risk]** Accidental navigation when tapping near card edges on mobile.
  - *Mitigation:* Ensure adequate touch target padding (minimum 36px) and distinct visual boundaries for secondary tier buttons.
