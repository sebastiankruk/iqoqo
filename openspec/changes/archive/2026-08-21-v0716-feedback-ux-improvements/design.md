## Context

The dashboard in `frontend/components/dashboard/stats-cards.tsx` uses a full pill-button group for `Personal | Global` scope toggle, exceeding the 4-button density heuristic. The feedback page at `frontend/app/feedback/page.tsx` renders filter controls in a sidebar that forces excessive scrolling on mobile. The backend `PATCH /api/feedback/<id>` endpoint in `app/api/feedback.py` parses payloads via raw `request.get_json()` without schema validation.

## Goals / Non-Goals

**Goals:**

- Replace pill-button scope toggle with minimalist icon-toggle (e.g., user icon vs globe icon) next to section heading
- Implement collapsible drawer/accordion for feedback page mobile filters
- Add Pydantic schema validation for `PATCH /api/feedback/<id>` endpoint
- Add Vitest component tests for new UI components
- Maintain responsive behavior across mobile and desktop viewports

**Non-Goals:**

- Redesigning the entire dashboard layout
- Adding new filter types to the feedback page
- Changing feedback data model (handled in Spec 5)

## Decisions

### Decision 1: Icon-toggle pattern for scope switch
**Choice:** Use Shadcn UI `Toggle` component with Lucide icons (`User` and `Globe`) in a compact button group.
**Rationale:** Icon toggles are standard in modern UIs, reduce visual noise, and communicate scope instantly. Shadcn components ensure consistency.
**Alternative considered:** Dropdown selector — rejected because scope is binary and dropdowns add unnecessary interaction cost.

### Decision 2: Shadcn Sheet for mobile filter drawer
**Choice:** Use Shadcn UI `Sheet` component (bottom drawer variant) for mobile filter sidebar.
**Rationale:** Bottom sheet is the mobile UX standard for filter panels. Shadcn Sheet provides built-in animation, backdrop, and accessibility.
**Alternative considered:** Accordion — rejected because it still occupies inline space and pushes content down.

### Decision 3: Marshmallow over Pydantic for feedback validation
**Choice:** Use Marshmallow schema validation (consistent with existing patterns in the codebase).
**Rationale:** The project already uses Marshmallow for other endpoints; maintaining consistency reduces cognitive load.

## Risks / Trade-offs

- **Risk:** Icon-toggle may be less discoverable for first-time users → **Mitigation:** Add tooltip on hover explaining "Personal" vs "Global" scope
- **Risk:** Shadcn Sheet import increases frontend bundle size → **Mitigation:** Sheet is already used in scanner components; no additional bundle cost
