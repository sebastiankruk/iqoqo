## ADDED Requirements

### Requirement: Removal of Placeholder Tabs in Admin Navigation
The administration navigation in `admin-sidebar.tsx` and `app/admin/settings/page.tsx` MUST NOT render active navigation items for features that display empty "Coming soon" content. Specifically, Monetization and Security tabs MUST be removed from the default admin navigation until their underlying capabilities are implemented in future milestones (`v1++`).

#### Scenario: Admin views administration settings menu
- **GIVEN** an authenticated user with administrative permissions viewing `/admin/settings`
- **WHEN** the administrative sidebar is rendered
- **THEN** navigation links for "Monetization" and "Security" are not displayed in the sidebar
- **AND** only fully functional tabs ("Settings", "API Integrations", "Users", "Roles") are selectable

#### Scenario: Federation Tab Handling Ahead of v0.9.1
- **GIVEN** Milestone v0.9.0 does not yet ship the full server-to-server Admin Federation Suite (scheduled for v0.9.1 `C78`)
- **WHEN** an admin views the sidebar
- **THEN** the Federation link in the sidebar is either hidden or marked with an explicit disabled badge ("Coming in v0.9.1") rather than linking to an empty placeholder card
