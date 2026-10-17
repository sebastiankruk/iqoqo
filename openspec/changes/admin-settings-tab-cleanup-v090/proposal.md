## Why

The administrative sidebar (`frontend/components/admin/admin-sidebar.tsx`) and settings page (`frontend/app/admin/settings/page.tsx`) currently contain links to tabs that are placeholders or stubbed with "Coming soon":
1. **Federation**: The sidebar link renders a static "Coming soon" card in `page.tsx` because active federation management is scheduled for `v0.9.1` (`admin-federation-dashboard-v091` / `/admin/federation`).
2. **Monetization**: Displays a static "Coming soon" placeholder card.
3. **Security**: Displays a static "Coming soon" placeholder card.

Exposing dead links or placeholder tabs displaying "Coming soon" violates the iqoqo standard: *"Every interactive UI control (buttons, menus, actions) MUST be wired to an active handler or, if deferred to a future milestone, explicitly disabled with an explanatory badge or tooltip (e.g., 'Coming in v0.8.0'). Dead, unwired, or silently failing UI controls are prohibited."* Removing the stubbed tabs or cleanly decorating them with release milestones cleans up the administration experience ahead of v0.9.0 release.

## What Changes

- Clean up `frontend/components/admin/admin-sidebar.tsx` and `frontend/app/admin/settings/page.tsx` by removing the empty placeholder tabs (Monetization, Security) and redirecting or properly gating the Federation link until `v0.9.1` (`/admin/federation`).
- Update `frontend/components/admin/instance-settings.tsx` to ensure settings categories correspond strictly to active, functional configuration categories (`external_apis`, `internal`).
- Update frontend admin sidebar unit tests to assert only active administrative sections are rendered.

## Capabilities

### New Capabilities
- `admin-settings-tab-cleanup`: Streamlined administration navigation without empty or placeholder tabs.

## Impact

- Affects `frontend/components/admin/admin-sidebar.tsx`, `frontend/app/admin/settings/page.tsx`, and `frontend/components/admin/instance-settings.tsx`.
- Removes non-functional UI clutter from the admin interface.
- Zero backend or database changes.
