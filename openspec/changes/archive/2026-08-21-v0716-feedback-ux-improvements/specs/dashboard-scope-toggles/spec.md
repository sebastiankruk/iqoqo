## ADDED Requirements

### Requirement: Dashboard scope toggle uses minimalist icon-toggle
The dashboard scope toggle SHALL use a compact icon-toggle pattern (e.g., User icon for Personal, Globe icon for Global) instead of a full pill-button group, reducing button density below the 4-button threshold per viewport.

#### Scenario: User switches from Global to Personal scope

- **WHEN** a user clicks/taps the scope icon-toggle from Globe to User icon
- **THEN** the dashboard metrics SHALL update to show personal collection statistics
- **AND** the toggle SHALL visually indicate the active scope

#### Scenario: Dashboard renders with default scope

- **WHEN** the dashboard page loads
- **THEN** the scope toggle SHALL render as a compact icon-toggle next to the section heading
- **AND** the total button count in the viewport SHALL NOT exceed 4 visible buttons

#### Scenario: Icon-toggle tooltip for discoverability

- **WHEN** a user hovers over the scope icon-toggle on desktop
- **THEN** a tooltip SHALL display "Personal" or "Global" depending on current state
