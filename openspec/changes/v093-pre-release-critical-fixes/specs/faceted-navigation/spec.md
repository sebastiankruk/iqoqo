## ADDED Requirements

### Requirement: Global Scope Preservation on Collection Facet Counts

When an authenticated user selects the `"all"` or `"global"` ("Whole Library") scope on `/collection`, the frontend SHALL pass `"global"` (rather than `"user"`) to `useFacetStats` and `GET /api/stats/facets` so sidebar facet counts reflect the entire library catalog.

#### Scenario: Authenticated user switches Collection scope to Whole Library

- **WHEN** a logged-in user switches `currentScope` on `/collection` to `"all"` or `"global"`
- **THEN** `useFacetStats` requests `GET /api/stats/facets?scope=global` (or `scope=all`) instead of coercing the scope to `"user"`
