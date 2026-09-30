## Why

The dashboard currently suffers from mobile viewport stacking issues for top tiles and lacks granularity in metric scoping. Users need responsive horizontal scrolling and the ability to toggle stats between the entire repository and their personal collection.

## What Changes

- Implement horizontal flex-wrap with overflow scrolling (`overflow-x-auto flex-nowrap`) for metric tiles and the wish list section on mobile viewports.
- Build a UI view switch allowing users to toggle between "Stats" (standard metrics) and "Insights" (collector time charts like acquisition velocity).
- Do not present FRBR stats; use custom metrics like "My items" and "Reading" in the Stats view.
- Update global view labels dynamically based on scope (e.g., "My items" becomes "All items", "Reading" becomes "Being read", "On wish list" becomes "On wish lists").
- Ensure one Insight chart takes the full width on small screens with a hint of horizontal scrolling.
- Implement an ontologically distinct scoping toggle (`scope: 'global' | 'personal'`) to isolate global repository counts from the authenticated user's personal inventory and virtual wishlist items.

## Capabilities

### New Capabilities

- `dashboard-scope-toggles`: UI switches for toggling stats/insights views and isolating global vs personal data scopes, along with dynamic labels and corresponding responsive layout fixes for mobile.

### Modified Capabilities

## Impact

- **Frontend**: `frontend/components/dashboard/stats-cards.tsx`, `frontend/components/dashboard/navbar.tsx`.
- **Backend**: `app/api/profile.py` for strictly isolating global repository counts (`Item`, `Manifestation`) from personal inventory (`UserWorkIntent`).
- **Testing**: Playwright mobile viewport emulation tests in `frontend/__tests__/e2e/ux_audit.spec.ts`.
