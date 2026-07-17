# facet-url-sync Specification

## Purpose
TBD - created by archiving change faceted-navigation-finalization. Update Purpose after archive.
## Requirements
### Requirement: URL encodes all active facet selections as query parameters

All active facet selections — including category, format, status, tag, collection, genre, and publisher — SHALL be serialized into URL search parameters so that any URL represents a fully reproducible, shareable filter state.

#### Scenario: Category filter persists in URL

- **WHEN** a user selects a category facet value (e.g., "music")
- **THEN** the URL SHALL update to include `?category=music` without a full-page reload

#### Scenario: Multiple same-type selections are comma-joined

- **WHEN** a user selects two genre values "sci-fi" and "fantasy"
- **THEN** the URL SHALL contain `?genres=sci-fi,fantasy`

#### Scenario: Browser Back restores filter state

- **WHEN** a user navigates away from a filtered view and presses the browser Back button
- **THEN** the filters SHALL be restored from the URL exactly as they were before navigation

#### Scenario: Shared URL restores filter state for another user

- **WHEN** a user opens a URL containing facet query parameters (e.g., `?genres=sci-fi&format=vinyl`)
- **THEN** the filter sidebar SHALL reflect those selections on initial render
- **AND** the result grid SHALL show results matching those filters

#### Scenario: Empty filter state produces clean URL

- **WHEN** no filters are active
- **THEN** no filter-related query parameters SHALL appear in the URL

