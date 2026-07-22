# facet-a11y-live-region Specification

## Purpose

TBD - created by archiving change faceted-navigation-finalization. Update Purpose after archive.

## Requirements

### Requirement: Filter state changes are announced to screen readers

The collection page SHALL maintain an invisible ARIA live region that announces the result count and active filter state to screen reader users when any filter is toggled.

#### Scenario: Filter toggle triggers live announcement

- **WHEN** a user toggles a facet filter (adds or removes)
- **THEN** the `aria-live="polite"` region SHALL update its text content to announce the number of results
- **AND** the announcement SHALL be in the format: "Filtered to [Filter Label]. [N] results found."

#### Scenario: Clear All triggers live announcement

- **WHEN** the user clears all filters
- **THEN** the live region SHALL announce: "All filters cleared. [N] results found."

#### Scenario: Live region is visually hidden

- **WHEN** the live region is present in the DOM
- **THEN** it SHALL be visually hidden using a screen-reader-only CSS class (e.g., `sr-only`)
- **AND** it SHALL NOT affect the visible layout

#### Scenario: Announcement timing uses polite mode

- **WHEN** a filter is toggled
- **THEN** the live region SHALL use `aria-live="polite"` so announcements do not interrupt currently-reading content
