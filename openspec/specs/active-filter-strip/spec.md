# active-filter-strip Specification

## Purpose

TBD - created by archiving change faceted-navigation-finalization. Update Purpose after archive.

## Requirements

### Requirement: Active filters are displayed as dismissible pills above the result grid

All active facet selections SHALL be displayed as colored dismissible pill chips in a horizontally-scrollable strip above the result grid. A single "Clear All" text button SHALL appear when two or more filters are active.

#### Scenario: Active filters render as chips above grid

- **WHEN** one or more facet filters are active
- **THEN** each active filter SHALL be rendered as a labeled pill chip above the result grid
- **AND** each chip SHALL display the filter type and value (e.g., "Genre: Sci-Fi")

#### Scenario: Clicking a chip removes that filter

- **WHEN** the user clicks the × on a filter chip in the active filter strip
- **THEN** that filter SHALL be deactivated immediately
- **AND** the result grid SHALL update to reflect the removed filter

#### Scenario: Clear All removes all filters

- **WHEN** two or more filters are active and the user clicks "Clear All"
- **THEN** all active filters SHALL be removed simultaneously
- **AND** the result grid SHALL return to the unfiltered state

#### Scenario: Strip is hidden when no filters are active

- **WHEN** no filters are active
- **THEN** the active filter strip SHALL not be rendered (or SHALL take zero visible space)

#### Scenario: Strip scrolls horizontally on overflow

- **WHEN** more active filter chips exist than can fit in one line
- **THEN** the strip SHALL scroll horizontally without wrapping to a second line
