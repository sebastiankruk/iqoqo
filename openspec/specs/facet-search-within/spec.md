# facet-search-within Specification

## Purpose
TBD - created by archiving change faceted-navigation-finalization. Update Purpose after archive.
## Requirements
### Requirement: Facet groups with more than 10 options expose an inline search input

When a facet group contains more than 10 option values, the `SearchableFacet` component SHALL render a borderless inline search input at the top of the option list to allow the user to filter the visible options by keyword.

#### Scenario: Search input appears for large facet groups

- **WHEN** a facet group has more than 10 distinct values (e.g., Publishers with 50 entries)
- **THEN** an inline search text input SHALL appear at the top of the facet group list

#### Scenario: Typing filters the visible options

- **WHEN** the user types a keyword into the facet search input
- **THEN** only options whose labels contain the keyword (case-insensitive) SHALL be shown
- **AND** already-selected values SHALL remain visible regardless of the search term

#### Scenario: Empty search result shows no-match message

- **WHEN** the user types a keyword that matches no facet values
- **THEN** the facet group SHALL display a "No matches" placeholder instead of an empty list

#### Scenario: Search input does not appear for small facet groups

- **WHEN** a facet group has 10 or fewer options
- **THEN** no search input SHALL be rendered in that facet group

