# e2e-test-coverage

## Purpose

TBD

## Requirements

### Requirement: Cross-FRBR filtering at Works and Expressions level is tested via E2E

The system SHALL have Playwright E2E tests that verify cross-FRBR filtering works correctly at the Works and Expressions browsing levels, with filters applied across FRBR layers.

#### Scenario: Works-level filtering with item status filter

- **WHEN** a user browses Works and applies an item status filter (e.g., "Available")
- **THEN** only Works whose associated items have the "Available" status SHALL be displayed

#### Scenario: Works-level filtering with item tag filter

- **WHEN** a user browses Works and applies an item tag filter
- **THEN** only Works whose associated items have that tag SHALL be displayed

#### Scenario: Expressions-level filtering with item format filter

- **WHEN** a user browses Expressions and applies a physical format filter
- **THEN** only Expressions whose associated items match the format SHALL be displayed

#### Scenario: Combined cross-FRBR filters at Works level

- **WHEN** a user applies both an item status filter and an item format filter while browsing Works
- **THEN** only Works whose items satisfy BOTH conditions SHALL be displayed

### Requirement: Facet URL sync full round-trip is tested via E2E

The system SHALL have Playwright E2E tests that verify the full URL sync cycle: URL updates on filter selection, browser back button restores previous filter state, and sharing a faceted URL restores filters.

#### Scenario: URL updates on filter selection

- **WHEN** a user selects a facet filter in the browser
- **THEN** the browser URL SHALL update to include the filter parameter

#### Scenario: Browser back restores previous filter state

- **WHEN** a user applies a filter, then applies a second filter, then presses browser back
- **THEN** the facet UI and results SHALL revert to the state with only the first filter applied

#### Scenario: Shared URL loads with filters applied

- **WHEN** a user navigates to a URL with facet query parameters
- **THEN** the page SHALL load with the specified filters pre-applied and results filtered accordingly

### Requirement: Mobile facet drawer behavior is tested via E2E

The system SHALL have Playwright E2E tests that verify the mobile facet drawer opens, allows filter selection, and closes correctly on mobile viewport.

#### Scenario: Facet drawer opens on mobile

- **WHEN** the browser viewport is set to a mobile width (e.g., 375px) and the user taps the "Filters" button
- **THEN** a drawer panel SHALL slide in from the side containing filter options

#### Scenario: Filter selection inside mobile drawer

- **WHEN** the mobile facet drawer is open and the user selects a filter
- **THEN** the filter selection SHALL be applied and reflected in the results

#### Scenario: Mobile drawer closes on backdrop tap

- **WHEN** the mobile facet drawer is open and the user taps the backdrop area
- **THEN** the drawer SHALL close

### Requirement: ARIA live region announcements are tested via E2E

The system SHALL have Playwright E2E tests that verify the ARIA live region announces filter changes to screen readers.

#### Scenario: ARIA announcement on filter application

- **WHEN** a user applies a facet filter
- **THEN** the `aria-live="polite"` element SHALL contain text describing the applied filter

#### Scenario: ARIA announcement on filter removal

- **WHEN** a user removes an active filter
- **THEN** the `aria-live="polite"` element SHALL contain text describing the removal

#### Scenario: ARIA announcement on clear all

- **WHEN** a user clears all filters
- **THEN** the `aria-live="polite"` element SHALL announce that all filters have been cleared

### Requirement: Entity audit log UI visibility is tested via E2E

The system SHALL have Playwright E2E tests that verify the entity audit log is accessible and displays correctly in the admin interface.

#### Scenario: Audit log is accessible from admin panel

- **WHEN** an authenticated admin user navigates to the entity management section
- **THEN** an audit log view SHALL be accessible showing entity change history

#### Scenario: Audit log shows merge event

- **WHEN** a merge operation has been performed on two entities
- **THEN** the audit log SHALL display the merge event with source and target entity information

### Requirement: Item custody loan button visibility is tested via E2E

The system SHALL have Playwright E2E tests that verify the "Request Loan" button appears only when appropriate.

#### Scenario: No loan button for unauthenticated users

- **WHEN** an unauthenticated user views a physical item detail page
- **THEN** no "Request Loan" button SHALL be visible

#### Scenario: Loan button visible for authenticated user on borrowable item

- **WHEN** an authenticated user views a borrowable physical item
- **THEN** a "Request Loan" button SHALL be visible

#### Scenario: No loan button for wishlist-only items

- **WHEN** an authenticated user views a wishlist item that has no physical copy
- **THEN** no "Request Loan" button SHALL be visible

### Requirement: Unauthenticated shared collection navigation is tested via E2E

The system SHALL have Playwright E2E tests that verify unauthenticated users can browse shared collections but cannot perform auth-gated actions.

#### Scenario: Unauth user can browse shared collection

- **WHEN** an unauthenticated user navigates to a shared collection URL
- **THEN** the collection items SHALL be displayed and browsable

#### Scenario: Unauth user sees login prompt for protected actions

- **WHEN** an unauthenticated user attempts to perform an action requiring authentication on a shared collection
- **THEN** the system SHALL redirect to login or display an authentication prompt

### Requirement: Metadata refetch dry-run verification is tested via E2E

The system SHALL have Playwright E2E tests that verify the metadata refetch dry-run feature reports changes without modifying data.

#### Scenario: Dry-run reports metadata gaps

- **WHEN** the metadata refetch is triggered in dry-run mode for an item with missing metadata
- **THEN** the system SHALL report what metadata would be fetched without actually updating the database

#### Scenario: Dry-run makes no database changes

- **WHEN** the metadata refetch dry-run completes
- **THEN** no metadata values in the database SHALL have changed

### Requirement: Facet search-within functionality is tested via E2E

The system SHALL have Playwright E2E tests that verify the search-within-facets functionality filters facet options based on user input.

#### Scenario: Search-within narrows facet options

- **WHEN** a user types a search term into the facet search-within input
- **THEN** only facet options matching the search term SHALL be displayed

#### Scenario: Search-within clear restores all options

- **WHEN** a user clears the facet search-within input after narrowing
- **THEN** all facet options SHALL be displayed again

#### Scenario: Search-within works with selected filters

- **WHEN** a user has active filters and uses search-within
- **THEN** the search SHALL narrow the available options while keeping selected filters applied
