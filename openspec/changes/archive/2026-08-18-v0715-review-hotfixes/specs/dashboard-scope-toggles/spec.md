## ADDED Requirements

### Requirement: Stable Test Selectors for Dashboard Tiles

The dashboard metric tiles scrolling container SHALL include a `data-testid="stats-scroll-container"` attribute to enable robust test targeting independent of CSS class names.

#### Scenario: Test suite queries scroll container

- **WHEN** a frontend test needs to verify the horizontal scrolling container exists and has the correct layout classes
- **THEN** it queries by `data-testid="stats-scroll-container"` instead of raw CSS class selectors, ensuring test stability across Tailwind version upgrades and class refactors.
