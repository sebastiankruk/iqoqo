## MODIFIED Requirements

### Requirement: Requests Accordion Panel on Manifestation and Item Pages

The system SHALL render a collapsible "Requests" section on manifestation detail and item detail pages. This section SHALL use the same accordion pattern as existing "Admin Actions" and "FRBR Actions" panels. The entity action sections SHALL render all admin actions (Refetch Cover, Regenerate Cover, Edit Cover Art, Remove from library / Delete manifestation) as direct inline `<Button>` elements. Overflow `<DropdownMenu>` components MUST NOT be used for admin actions \u2014 hiding actions behind a `[...]` control was rejected as a confusing UX pattern. The section SHALL contain the "Ask custodians for help" submission trigger and the list of the current user's escalation requests for that target entity. If the user has 0 pending requests for this entity, the "Ask custodians for help" trigger SHALL NOT be hidden inside an accordion, but instead rendered directly as an outline button in the action layout.

#### Scenario: Non-custodian user expands the Requests accordion with existing requests

- **WHEN** an authenticated user without `write:metadata` permission clicks the "Requests" accordion header on a manifestation detail page and they have active requests
- **THEN** the system SHALL expand the panel to reveal the "Ask custodians for help" button and a list of the user's previously submitted escalation requests for this target.

#### Scenario: Non-custodian user has no existing requests for this target

- **WHEN** an authenticated user without `write:metadata` permission views a manifestation they have never submitted a request for
- **THEN** the system SHALL show only the "Ask custodians for help" button directly as an outline button and SHALL NOT render the empty Requests accordion.

#### Scenario: Custodian views the manifestation page

- **WHEN** an authenticated user with `write:metadata` permission views a manifestation detail page
- **THEN** the system SHALL NOT render the "Requests" accordion (since the custodian sees "Edit FRBR" instead and has no need for help requests).

#### Scenario: Unauthenticated user views the manifestation page

- **WHEN** an unauthenticated user views a manifestation detail page
- **THEN** the system SHALL NOT render the "Requests" accordion.
