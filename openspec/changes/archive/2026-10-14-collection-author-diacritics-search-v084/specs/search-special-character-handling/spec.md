## ADDED Requirements

### Requirement: Diacritic-insensitive query matching (unaccent)

The system SHALL match search queries regardless of whether diacritical marks are included in the query string or in stored database entities. Search queries submitted without diacritics (e.g. `milosc`, `Garcia`) SHALL match catalog records containing accented characters (e.g. `miłość`, `García`), and queries submitted with diacritics SHALL match records stored in plain Latin characters as well as accented records.

#### Scenario: Unaccented query matches accented entity

- **WHEN** a user searches for `milosc` or `Garcia`
- **THEN** the search results SHALL include items containing `miłość` or `García` in titles, authors, or metadata

#### Scenario: Accented query matches unaccented entity

- **WHEN** a user searches for `García` or `miłość`
- **THEN** the search results SHALL match entities stored with plain Latin equivalents as well as exact accented strings

### Requirement: Contributor and author name search in collection queries

The system SHALL match query terms against Work and Expression contributors (`Agent`, `WorkContribution`, `ExpressionContribution`) and Manifestation author metadata in collection and item search operations (`SearchService.search_items`), in addition to Work titles and ISBNs.

#### Scenario: Search by author name returns creator items

- **WHEN** a user searches for `Gabriel García Márquez`
- **THEN** the search results SHALL return items where Gabriel García Márquez is recorded as author or contributor

#### Scenario: Author query with special characters executes cleanly

- **WHEN** a user searches for an author name containing spaces, hyphens, periods, or non-ASCII letters
- **THEN** the query SHALL execute without `tsquery` parsing failure, 500 error, or unhandled database exception
