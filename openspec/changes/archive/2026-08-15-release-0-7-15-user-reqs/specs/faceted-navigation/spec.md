## MODIFIED Requirements

### Requirement: Ownership Filtering

The faceted navigation SHALL allow users to filter manifestations by their ownership status via a dedicated "Ownership" facet category containing options for "Owned" and "Not Owned".

#### Scenario: Finding missing manifestations

- **WHEN** a user applies the "Not Owned" option in the Ownership facet alongside other facets
- **THEN** the system returns only manifestations that match the other facets and are absent from the user's personal inventory.

#### Scenario: Default unselected state

- **WHEN** a user does not select any option in the Ownership facet (or deselects all options)
- **THEN** the system displays all matching entities (both owned and unowned) without an artificial empty state.

#### Scenario: Ownership facet visibility

- **WHEN** a user navigates to the Items view
- **THEN** the Ownership facet is hidden or removed, as ownership filtering only applies to higher-level entities (Manifestations, Expressions, Works) whose ownership is inferred from personal Item holdings.
