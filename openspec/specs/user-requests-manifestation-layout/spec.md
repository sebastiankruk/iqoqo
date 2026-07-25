# User Requests Manifestation Layout

## Purpose

Define the layout, multi-request handling, and accordion panel behavior for user help requests on manifestation and item detail pages.

## Requirements

### Requirement: Requests Accordion Panel on Manifestation and Item Pages

The system SHALL render a collapsible "Requests" section on manifestation detail and item detail pages. This section SHALL use the same accordion pattern as existing "Admin Actions" and "FRBR Actions" panels (Shadcn UI collapsible with `ChevronUp`/`ChevronDown` toggle). The entity action sections SHALL render all admin actions (Refetch Cover, Regenerate Cover, Edit Cover Art, Remove from library / Delete manifestation) as direct inline `<Button>` elements. Overflow `<DropdownMenu>` components MUST NOT be used for admin actions — hiding actions behind a `[...]` control was rejected as a confusing UX pattern. The section SHALL contain the "Ask custodians for help" submission trigger and the list of the current user's escalation requests for that target entity.

#### Scenario: Non-custodian user opens the Requests accordion

- **WHEN** an authenticated user without `write:metadata` permission clicks the "Requests" accordion header on a manifestation detail page
- **THEN** the system SHALL expand the panel to reveal the "Ask custodians for help" button and a list of the user's previously submitted escalation requests for this target.

#### Scenario: Non-custodian user has no existing requests for this target

- **WHEN** an authenticated user without `write:metadata` permission expands the "Requests" accordion on a manifestation they have never submitted a request for
- **THEN** the system SHALL show only the "Ask custodians for help" button and no request cards.

#### Scenario: Custodian views the manifestation page

- **WHEN** an authenticated user with `write:metadata` permission views a manifestation detail page
- **THEN** the system SHALL NOT render the "Requests" accordion (since the custodian sees "Edit FRBR" instead and has no need for help requests).

#### Scenario: Unauthenticated user views the manifestation page

- **WHEN** an unauthenticated user views a manifestation detail page
- **THEN** the system SHALL NOT render the "Requests" accordion.

### Requirement: Unresolved Requests Displayed Outside Accordion

The system SHALL display any unresolved (status `pending`) escalation request for the current user and target entity OUTSIDE the "Requests" accordion panel, directly below the section header. This ensures immediate visibility without requiring the user to expand the accordion. Resolved requests SHALL only be visible inside the expanded accordion.

#### Scenario: User has a pending request on the current manifestation

- **WHEN** an authenticated user without `write:metadata` permission views a manifestation for which they have a pending escalation request
- **THEN** the system SHALL render a compact status card showing the request status, field name, and suggested value OUTSIDE the collapsed "Requests" accordion, and the accordion SHALL be closed by default.

#### Scenario: User has only resolved requests on the current manifestation

- **WHEN** an authenticated user without `write:metadata` permission views a manifestation for which all their escalation requests are resolved
- **THEN** the system SHALL NOT render any request cards outside the accordion, and the accordion SHALL be closed by default.

### Requirement: Multiple Requests Per Target Entity

The system SHALL allow a user to submit more than one help request targeting the same FRBR entity. The escalation trigger component SHALL accept and display all escalation requests for the current user+target combination, not just the first match. Submitting an additional request SHALL NOT be blocked by the existence of prior requests for the same target.

#### Scenario: User submits a second request on the same manifestation

- **WHEN** an authenticated user has an existing (resolved or pending) escalation request on a manifestation and clicks "Ask custodians for help" again
- **THEN** the system SHALL open the request dialog and allow submission of a new independent request for a different field or suggested value.

#### Scenario: User views target with multiple requests

- **WHEN** an authenticated user has 3 escalation requests for the same manifestation and opens the "Requests" accordion
- **THEN** the system SHALL display all 3 request cards, with the most recent at the top, and the "Ask custodians for help" button available below them.

#### Scenario: Maximum visible request cards

- **WHEN** an authenticated user has more than 5 escalation requests for a single target entity
- **THEN** the system SHALL display the 5 most recent requests and show a "View all N requests" link to expand the full list.
