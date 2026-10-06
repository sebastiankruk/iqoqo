## Why

Dashboard button density exceeds the 4-button heuristic threshold with the full `Personal | Global` pill-button scope toggle, creating visual clutter. The feedback page mobile filter sidebar forces excessive scrolling past filter buttons on small viewports. Additionally, the `PATCH /api/feedback/<id>` endpoint uses raw `request.get_json()` parsing without schema validation, risking malformed payloads.

## What Changes

- **Replace** the `Personal | Global` pill-button scope toggle on the dashboard with a minimalist icon-toggle next to the section heading, reducing button density below the 4-button threshold
- **Wrap** the feedback page mobile filter sidebar in a collapsible drawer/accordion component to prevent excessive scrolling past filter controls on mobile viewports
- **Standardize** `PATCH /api/feedback/<id>` endpoint to use Pydantic/Marshmallow schema validation instead of manual `request.get_json()` parsing

## Capabilities

### New Capabilities

- `feedback-schema-validation`: Pydantic/Marshmallow validation for feedback PATCH endpoint

### Modified Capabilities

- `dashboard-scope-toggles`: Replacing pill-button group with minimalist icon-toggle
- `feedback-mechanism`: Adding collapsible mobile filter drawer to feedback page

## Impact

- **Frontend Files:** `frontend/components/dashboard/stats-cards.tsx`, `frontend/app/feedback/page.tsx`
- **Backend Files:** `app/api/feedback.py`
- **Tests:** Vitest component tests for icon-toggle and drawer, pytest for Pydantic validation
- **Risk:** Medium — UI behavioral changes require visual verification
- **UX Constraints:** Dashboard toggle must stay under 4-button density; filter drawer must require < 3 taps to apply
