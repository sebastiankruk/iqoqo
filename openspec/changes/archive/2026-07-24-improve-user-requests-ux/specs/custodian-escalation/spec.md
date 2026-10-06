## MODIFIED Requirements

### Requirement: Escalation UI Trigger Visibility

The system SHALL render a contextual escalation trigger on item detail and manifestation detail pages within a collapsible "Requests" accordion panel. This trigger MUST only be visible to authenticated users who do NOT have `write:metadata` permission. Users who already have custodian/admin metadata write access SHALL NOT see the escalation trigger. The "Edit FRBR" button SHALL only be rendered for users with `write:metadata` permission, NOT for users with only `read:metadata` permission. If the user has any existing escalation for the current entity with status `pending`, the trigger MUST display that pending request status outside the collapsed accordion for immediate visibility. If the user has existing escalations with resolved status (`accepted`, `rejected`, `duplicate`), these SHALL be visible inside the expanded accordion. The system SHALL allow the user to submit additional escalation requests for the same target entity regardless of existing requests.

#### Scenario: Non-custodian user views an item detail page with their own pending escalation

- **WHEN** an authenticated user without `write:metadata` permission views an item detail page for which they have a pending escalation request
- **THEN** the system SHALL render a compact status card above the collapsed "Requests" accordion showing the escalation's status as `pending`, the field name, suggested value, and creation date. The "Ask Custodians for Help" button SHALL be hidden until the accordion is expanded.

#### Scenario: Non-custodian user views an item detail page with resolved escalations only

- **WHEN** an authenticated user without `write:metadata` permission views an item detail page for which they have only resolved escalation requests (no pending)
- **THEN** the system SHALL render the "Requests" accordion closed, and expanding it SHALL reveal the resolved request cards plus the "Ask Custodians for Help" button.

#### Scenario: Non-custodian user views an item detail page with no prior requests

- **WHEN** an authenticated user without `write:metadata` permission views an item detail page for which they have never submitted an escalation request
- **THEN** the system SHALL render the "Requests" accordion, and expanding it SHALL reveal the "Ask Custodians for Help" trigger button. The "Edit FRBR" button SHALL NOT be rendered.

#### Scenario: Non-custodian user submits a second request on the same entity

- **WHEN** an authenticated user without `write:metadata` permission has an existing escalation request on a manifestation and clicks "Ask Custodians for Help" from within the expanded accordion
- **THEN** the system SHALL open the submission dialog allowing a new independent request for a different field or suggested value, and SHALL NOT block the submission due to the existing request.

#### Scenario: Custodian views an item detail page

- **WHEN** an authenticated user with `write:metadata` permission views an item detail page
- **THEN** the system SHALL render the "Edit FRBR" button AND SHALL NOT render the "Requests" accordion or escalation trigger.

#### Scenario: Regular user does not see "Edit FRBR" button

- **WHEN** an authenticated user with `read:metadata` but without `write:metadata` permission views an item detail page
- **THEN** the system SHALL NOT render the "Edit FRBR" button, since the user cannot use the FRBR metadata editor.

#### Scenario: Unauthenticated user views an item detail page

- **WHEN** an unauthenticated user views an item detail page
- **THEN** the system SHALL NOT render the "Requests" accordion or escalation trigger.

### Requirement: Escalation Request Listing

The system SHALL expose endpoints for listing escalation requests. Authenticated users SHALL be able to list all their own requests (both pending and resolved). Users with `escalate:resolve` permission SHALL be able to list all pending escalation requests across all users (the custodian queue) and, optionally, filter by status to view resolved requests.

#### Scenario: User lists their own escalation requests

- **WHEN** an authenticated user sends a GET to `/api/escalations/mine`
- **THEN** the system SHALL return a JSON array of ALL escalation requests submitted by that user (regardless of status), ordered by `created_at` descending.

#### Scenario: Custodian lists all pending escalation requests

- **WHEN** a user with `escalate:resolve` permission sends a GET to `/api/escalations/queue`
- **THEN** the system SHALL return a JSON array of all escalation requests with status `pending`, ordered by `created_at` ascending (oldest first), including the requesting user's display name.

#### Scenario: Custodian lists resolved escalation requests

- **WHEN** a user with `escalate:resolve` permission sends a GET to `/api/escalations/queue?status=accepted,rejected,duplicate`
- **THEN** the system SHALL return a JSON array of escalation requests matching the specified status values, ordered by `created_at` ascending.

#### Scenario: Non-custodian user attempts to access the queue

- **WHEN** an authenticated user without `escalate:resolve` permission sends a GET to `/api/escalations/queue`
- **THEN** the system SHALL return HTTP 403 with error `"Forbidden"`.
