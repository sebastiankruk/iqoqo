# User Requests Navigation

## Purpose

Define the navigation components, dropdown links, pending request count badge, and profile panel help request section.

## Requirements

### Requirement: Navbar Dropdown Link to Help Requests

The system SHALL render a "My Help Requests" menu item in the authenticated user's navbar dropdown menu. This item MUST link directly to the user's help requests section on the profile page. The link SHALL be positioned between "Manage Collections" and "Admin Configuration" (or "Custodian Tools" if no admin access).

#### Scenario: Authenticated user with pending requests clicks the dropdown link

- **WHEN** an authenticated user opens the navbar dropdown menu and clicks "My Help Requests"
- **THEN** the system SHALL navigate to `/admin/settings?tab=profile#help-requests` and scroll the help requests section into view.

#### Scenario: Authenticated user with no requests clicks the dropdown link

- **WHEN** an authenticated user with zero submitted escalation requests opens the navbar dropdown menu
- **THEN** the system SHALL still render the "My Help Requests" menu item, and navigating to it SHALL show an empty state.

#### Scenario: Unauthenticated user views the navbar

- **WHEN** an unauthenticated user views the navbar
- **THEN** the system SHALL NOT render the "My Help Requests" menu item (the user icon dropdown is not shown).

### Requirement: Pending Request Count Badge on Dropdown Link

The system SHALL display a count badge next to the "My Help Requests" dropdown item when the user has one or more requests with status `pending`. The badge SHALL show the number of pending requests. The badge SHALL NOT appear when the count is zero.

#### Scenario: User has pending requests

- **WHEN** an authenticated user has 3 escalation requests with status `pending`
- **THEN** the "My Help Requests" dropdown item SHALL display a badge showing "3".

#### Scenario: User has only resolved requests

- **WHEN** an authenticated user has 2 escalation requests, both with status `accepted` or `rejected`
- **THEN** the "My Help Requests" dropdown item SHALL NOT display a badge.

#### Scenario: User has no requests at all

- **WHEN** an authenticated user has zero escalation requests
- **THEN** the "My Help Requests" dropdown item SHALL NOT display a badge.

### Requirement: Profile Panel Help Requests Section

The system SHALL render a dedicated "Help Requests" section within the user's profile panel. Each request card SHALL display the target entity (with clickable link), field name, suggested value, status, and creation date. Cards SHALL have internal padding of at least `p-4` (16px) to prevent border-to-text contact.

#### Scenario: User views profile with help requests

- **WHEN** an authenticated user views the profile page and has submitted escalation requests
- **THEN** the system SHALL render each request in a card with `p-4` padding, the target entity as a clickable link, the field name and suggested value clearly displayed, and the current status badge.

#### Scenario: User views profile with no help requests

- **WHEN** an authenticated user views the profile page and has not submitted any escalation requests
- **THEN** the system SHALL display a friendly empty state message within the "Help Requests" section.

#### Scenario: Card padding prevents text touching borders

- **WHEN** a help request card is rendered at any viewport width (320px to 2560px)
- **THEN** the text content SHALL have at least 16px (p-4) internal padding on all sides, and no text SHALL visually touch the card border.
