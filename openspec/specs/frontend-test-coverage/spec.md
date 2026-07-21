# frontend-test-coverage

## Purpose

TBD

## Requirements

### Requirement: Facet ARIA live region is tested at the component level

The system SHALL have Vitest component tests that verify the facet filter area includes an ARIA live region element and that announcement text updates when filters are toggled or cleared.

#### Scenario: ARIA live element is present

- **WHEN** the facet filter component is rendered
- **THEN** an element with `aria-live="polite"` SHALL be present in the DOM

#### Scenario: Announcement text on filter toggle

- **WHEN** a user toggles a filter on
- **THEN** the aria-live element SHALL contain announcement text describing the applied filter

#### Scenario: Announcement text on filter clear

- **WHEN** a user clears all filters
- **THEN** the aria-live element SHALL contain announcement text indicating filters were cleared

#### Scenario: SR-only visual hiding class

- **WHEN** the aria-live element is rendered
- **THEN** the element SHALL have a CSS class that visually hides it while keeping it accessible to screen readers (sr-only or equivalent)

### Requirement: Facet URL sync is tested at the component level

The system SHALL have Vitest component tests that verify facet URL parameter serialization, deserialization, and that the URL updates correctly when filters are selected or deselected.

#### Scenario: URL parameter serialization on filter selection

- **WHEN** a user selects a facet filter
- **THEN** the URL query parameters SHALL be updated to include the selected filter

#### Scenario: URL parameter deserialization on page load

- **WHEN** the page loads with facet query parameters in the URL
- **THEN** the facet filter UI SHALL reflect the pre-selected filters from the URL

#### Scenario: Multiple filter serialization

- **WHEN** the user selects multiple filters from different facet groups
- **THEN** all selected filters SHALL appear as comma-separated values in the URL

#### Scenario: URL parameter removal on filter clear

- **WHEN** the user clears all filters
- **THEN** all facet-related query parameters SHALL be removed from the URL

### Requirement: Active filter strip rendering is tested

The system SHALL have Vitest component tests that verify the active filter strip displays currently applied filters and allows removal of individual filters.

#### Scenario: Active filters displayed as removable chips

- **WHEN** filters are applied to a collection view
- **THEN** each active filter SHALL be displayed as a chip or badge in the active filter strip

#### Scenario: Individual filter removal

- **WHEN** a user clicks the remove button on an active filter chip
- **THEN** that specific filter SHALL be removed from the active filters
- **THEN** the remaining filters SHALL still be displayed

#### Scenario: Filter strip hidden when no filters active

- **WHEN** no filters are applied
- **THEN** the active filter strip SHALL NOT be rendered

### Requirement: Mobile facet drawer is tested

The system SHALL have Vitest component tests that verify the mobile facet drawer renders and behaves correctly at mobile viewport sizes.

#### Scenario: Drawer renders at mobile viewport

- **WHEN** the viewport width is below the mobile breakpoint (typically 768px)
- **THEN** the facet UI SHALL render as a drawer or slide-in panel

#### Scenario: Drawer toggle opens and closes

- **WHEN** the user taps the facet toggle button on mobile
- **THEN** the facet drawer SHALL open, displaying filter options
- **WHEN** the user taps close or the backdrop
- **THEN** the facet drawer SHALL close

#### Scenario: Drawer is not rendered at desktop viewport

- **WHEN** the viewport width is above the mobile breakpoint
- **THEN** the facet UI SHALL render inline rather than as a drawer

### Requirement: Wishlist tagging is tested at the component level

The system SHALL have Vitest component tests that verify wishlist items display their tags and that tag state is reflected correctly.

#### Scenario: Tags displayed on wishlist items

- **WHEN** a wishlist item has associated tags
- **THEN** those tags SHALL be visible in the item card or detail view

#### Scenario: Tag persistence after state change

- **WHEN** a wishlist item's state changes
- **THEN** the item's tags SHALL remain unchanged

#### Scenario: Owner-only tag controls hidden for non-owners

- **WHEN** a non-owner views a wishlist item
- **THEN** tag editing controls SHALL NOT be rendered

### Requirement: Loan button visibility is tested at the component level

The system SHALL have Vitest component tests that verify the "Request Loan" button visibility rules based on item borrowability and user authentication state.

#### Scenario: Loan button visible for borrowable items

- **WHEN** an authenticated user views a physical item marked as borrowable
- **THEN** a "Request Loan" or equivalent button SHALL be visible

#### Scenario: Loan button hidden for non-borrowable items

- **WHEN** a user views a physical item not marked as borrowable
- **THEN** a "Request Loan" button SHALL NOT be visible

#### Scenario: Loan button hidden for unauthenticated users

- **WHEN** an unauthenticated user views a borrowable physical item
- **THEN** a "Request Loan" button SHALL NOT be visible

#### Scenario: Loan button hidden for wishlist-only items

- **WHEN** a user views a wishlist item that has no physical copy
- **THEN** a "Request Loan" button SHALL NOT be visible

### Requirement: Shared collection UI for unauthenticated users is tested

The system SHALL have Vitest component tests that verify the shared collection view renders correctly for unauthenticated users, hiding auth-gated controls.

#### Scenario: Unauth shared collection renders browseable view

- **WHEN** an unauthenticated user navigates to a shared collection URL
- **THEN** the collection items SHALL be visible and browseable

#### Scenario: Auth-gated controls hidden for unauth users

- **WHEN** an unauthenticated user views a shared collection
- **THEN** edit, delete, and management controls SHALL NOT be rendered
