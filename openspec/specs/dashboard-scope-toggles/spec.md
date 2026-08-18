# Dashboard Scope Toggles

## Purpose

Provide responsive layout and toggle capabilities on the collector dashboard, allowing users to switch between numeric metric tiles and Insights time charts, filter data between personal collection and global library scopes, and interact with horizontally scrollable rows on mobile devices.

## Requirements

### Requirement: Mobile Tile Layout

The dashboard metric tiles, Insights charts, and Wish list section SHALL render in a horizontally scrollable layout on mobile viewports.

#### Scenario: Viewing dashboard on mobile

- **WHEN** a user loads the dashboard on a mobile viewport (e.g., width < 768px)
- **THEN** the metric tiles and Wish list section scroll horizontally, and Insights charts take full width with a hint of horizontal scrolling.

### Requirement: Tile View Toggle

The dashboard SHALL provide a UI toggle to switch between standard "Stats" (metrics like My items, Reading) and "Insights" (time charts like acquisition velocity).

#### Scenario: Toggling stats view

- **WHEN** a user clicks the toggle switch
- **THEN** the UI seamlessly transitions between displaying Stats and Insights.

### Requirement: Dynamic Scope Labels

The dashboard SHALL dynamically adjust labels based on the selected scope.

#### Scenario: Toggling global vs personal scope

- **WHEN** a user switches between personal and global scope
- **THEN** labels update appropriately (e.g., "My items" becomes "All items", "Reading" becomes "Being read").

### Requirement: Stats Scoping Toggle

The dashboard SHALL provide a toggle to calculate statistics based on either the global repository or the user's personal collection.

#### Scenario: Switching scope to personal

- **WHEN** a user sets the scope toggle to "personal"
- **THEN** the dashboard fetches and displays numeric metrics and Insight charts scoped only to items the user owns or intends to interact with (e.g., wishlist).

#### Scenario: Switching scope to global

- **WHEN** a user sets the scope toggle to "global"
- **THEN** the dashboard fetches and displays numeric metrics and Insight charts for the entire library repository.

### Requirement: Stable Test Selectors for Dashboard Tiles
The dashboard metric tiles scrolling container SHALL include a `data-testid="stats-scroll-container"` attribute to enable robust test targeting independent of CSS class names.

#### Scenario: Test suite queries scroll container

- **WHEN** a frontend test needs to verify the horizontal scrolling container exists and has the correct layout classes
- **THEN** it queries by `data-testid="stats-scroll-container"` instead of raw CSS class selectors, ensuring test stability across Tailwind version upgrades and class refactors.
