## MODIFIED Requirements

### Requirement: Facet counts reflect the FRBR level of the current view

Facet counts shown next to facet values MUST accurately reflect the number of records at the FRBR level AND ownership scope (`scope="own"` vs. `scope="friends"` vs. `scope="all"`) currently being browsed, regardless of whether the user is authenticated. Counts MUST NOT hardcode or default to personal-only Item counts when browsing the "Friends' Items" (`scope="friends"`) view.

#### Scenario: Global view shows Manifestation-scoped counts

- **WHEN** the user is in the global library view (manifestations scope)
- **THEN** Media Category counts SHALL reflect the total number of Manifestation records per category across the entire catalog, not just those owned by the user.

#### Scenario: Works/Expressions view shows Work/Expression-scoped counts

- **WHEN** the user is in the Works or Expressions view
- **THEN** Media Category counts SHALL reflect the number of Work or Expression records per category, not Item records

#### Scenario: Private view shows Item-scoped counts

- **WHEN** the user is in the private library view (items scope, `scope="own"`)
- **THEN** facet counts SHALL reflect the number of Item records the logged-in user owns per facet value

#### Scenario: Friends' Items view shows friend-scoped Item counts

- **WHEN** the user selects the "Friends' Items" scope (`scope="friends"`) in the collection view
- **THEN** `useFacetStats` (`/api/stats/facets?scope=friends`) SHALL compute facet counts across confirmed friends' visible items (`public`, `friends_only`, `shared`, `is_hidden=False`) rather than the caller's personal inventory
