# search-special-character-handling Specification

## Purpose
TBD - created by archiving change release-0-7-13. Update Purpose after archive.
## Requirements
### Requirement: Apostrophe variants are canonicalized at indexing time

The system SHALL canonicalize typographic apostrophe variants (e.g. `’`, `‘`, `ʼ`) to the ASCII single quote (`'`) when building full-text search vectors and facet keys, so stored representations of titles are uniform regardless of the source punctuation style.

#### Scenario: Typographic apostrophe indexed as ASCII

- **WHEN** a title containing a typographic apostrophe (e.g. `Ocean’s Eleven` with U+2019) is indexed for full-text search or faceting
- **THEN** the indexed representation SHALL contain the ASCII form `Ocean's Eleven`

### Requirement: Apostrophe-bearing titles round-trip through full-text search

The system SHALL return matching results when a user searches for a title containing a single quote, and SHALL NOT raise a query error or return an empty result set caused by quote mishandling in `websearch_to_tsquery` input preparation.

#### Scenario: Search for title with apostrophe succeeds

- **WHEN** a user searches for `Ocean's Eleven` and a cataloged title contains `Ocean's Eleven` (stored with ASCII or typographic apostrophe)
- **THEN** the search SHALL return that title in the result set

#### Scenario: Apostrophe input never breaks the tsquery parse

- **WHEN** a user submits a search string containing single quotes, double quotes, or apostrophe variants in any position
- **THEN** the system SHALL sanitize the input before building the `tsquery` and SHALL respond with a well-formed result set rather than an HTTP 5xx or a silently empty response caused by a parse error

### Requirement: Faceted filtering escapes pattern metacharacters

Facet value comparisons using `LIKE`/`ILIKE` patterns in `app/api/filters.py` SHALL bind values as parameters with explicit escaping of `%`, `_`, and `\` metacharacters, so apostrophe- or metacharacter-bearing values match literally.

#### Scenario: Facet filter on apostrophe-bearing value matches literally

- **WHEN** a user applies a facet filter whose value contains a single quote (e.g. a publisher or genre named `L'Armée`)
- **THEN** the filter SHALL match exactly the rows carrying that literal value and SHALL NOT error or over-match via pattern interpretation

#### Scenario: LIKE metacharacters in facet values match literally

- **WHEN** a facet value contains `%`, `_`, or `\`
- **THEN** the comparison SHALL treat those characters literally rather than as wildcards

### Requirement: Regression coverage pins apostrophe round-trips

The change SHALL ship pytest and, where facet UI state is involved, Playwright/Vitest regression tests covering search and faceted filtering of titles containing single quotes.

#### Scenario: Regression suite guards the fix

- **WHEN** the test suite runs
- **THEN** at least one backend test SHALL assert an apostrophe-bearing title is found via search and at least one SHALL assert an apostrophe-bearing facet value filters correctly
