## 1. Dashboard Scope Icon-Toggle

- [x] 1.1 Replace pill-button scope toggle in `frontend/components/dashboard/stats-cards.tsx` with Shadcn `Toggle` component
- [x] 1.2 Use Lucide `User` and `Globe` icons for Personal/Global scope states
- [x] 1.3 Add tooltip on hover showing "Personal" or "Global" for discoverability
- [x] 1.4 Verify button count in dashboard viewport stays ≤ 4 after change
- [x] 1.5 Create Vitest test for icon-toggle rendering and state switching

## 2. Feedback Page Mobile Filter Drawer

- [x] 2.1 Wrap feedback page filter sidebar in Shadcn `Sheet` component (bottom variant) for mobile viewports
- [x] 2.2 Add conditional rendering: `Sheet` on mobile (< 768px), inline sidebar on desktop (≥ 768px)
- [x] 2.3 Add "Filters" trigger button visible on mobile when drawer is collapsed
- [x] 2.4 Ensure filter application closes drawer and updates results in < 3 taps
- [x] 2.5 Create Vitest test for drawer open/close behavior and filter application

## 3. Feedback PATCH Schema Validation

- [x] 3.1 Create Marshmallow schema class for feedback PATCH payload in `app/api/feedback.py` or `app/schemas/`
- [x] 3.2 Define allowed fields: `status`, `feedback_type`, `description`
- [x] 3.3 Replace raw `request.get_json()` with Marshmallow schema loading
- [x] 3.4 Return 400 with field-level validation errors for invalid payloads
- [x] 3.5 Create pytest tests for valid, invalid, and empty PATCH payloads

## 4. Verification

- [x] 4.1 Run `make format-python && make format-js`
- [x] 4.2 Run `make lint-python && make lint-js` — verify no errors
- [x] 4.3 Run `make test-backend && make test-frontend` — verify all tests pass
- [x] 4.4 Manual verification: check dashboard toggle on mobile and desktop viewports
- [x] 4.5 Manual verification: check feedback filter drawer on mobile viewport
