# advanced-facets-filtering Specification

## Purpose

Define how faceted list filtering behaves: comma-separated parameter parsing, the OR-within / AND-across-facets combination rule, LIKE-term escaping, the ownership-scoped status filter, and the cache keys for facet and taxonomy responses.

## Requirements

### Requirement: Comma-separated facet parameters are parsed as lists

Faceted list endpoints MUST accept repeated values in one parameter as a
comma-separated list, and MUST treat an absent or empty parameter as "no filter"
rather than as a filter that matches nothing.

#### Scenario: A user filters a list by two tags in one parameter

- **WHEN** a request supplies `tags=fantasy,sci-fi` to an item list endpoint
- **THEN** both values are applied as filters on that facet
- **AND** the values are combined with OR within the facet, so an Item matching
  either tag is returned

#### Scenario: A user filters by two different facets at once

- **WHEN** a request supplies both a tag value and a status value
- **THEN** the facets are combined with AND
- **AND** only Items satisfying both are returned

#### Scenario: A filter value matches nothing

- **WHEN** a request supplies a facet value for which no record matches
- **THEN** the endpoint returns 200 with an empty result set
- **AND** it does not return an error, because an empty facet is a valid query

### Requirement: Facet filters are escaped before being placed in LIKE predicates

Filter terms MUST be escaped before interpolation into `ILIKE` patterns so that
user input containing wildcard or escape characters is matched literally.

#### Scenario: A user searches for a term containing a percent sign

- **WHEN** a filter term contains `%` or `_`
- **THEN** it is escaped before interpolation
- **AND** it matches only records containing that literal text

#### Scenario: A user submits a genre filter

- **WHEN** a genre filter list is applied to a query
- **THEN** each term is escaped and combined into a single case-insensitive
  predicate
- **AND** the terms are combined with OR

### Requirement: Status filters respect ownership and borrowing state

The status filter MUST support the values that only make sense for the requesting
user, and MUST scope them to what that user is permitted to see -- in particular a
borrowed-only filter MUST be restricted to items the caller is borrowing.

#### Scenario: A user filters to items they are currently borrowing

- **WHEN** the status filter is asked for borrowed items
- **THEN** the query is additionally constrained to loans held by the caller
- **AND** another user's borrowed items are never returned

### Requirement: Facet and taxonomy responses are cached with normalized keys

Faceted statistics and taxonomy payloads MUST be cached, and the cache key MUST
be normalized so that equivalent filter orderings share one cache entry.

#### Scenario: Two requests differ only in the order of their filters

- **WHEN** a client requests the same facets with the filter values in a
  different order
- **THEN** both requests hit the same cache entry
- **AND** the second is served from cache rather than recomputed

#### Scenario: Facet counts are invalidated on refresh

- **WHEN** the taxonomy refresh task runs
- **THEN** the cached facet and taxonomy payloads are invalidated
- **AND** the next request recomputes them from the database
