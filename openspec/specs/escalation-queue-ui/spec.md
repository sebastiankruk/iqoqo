# Escalation Queue UI

## Purpose
Specify custodian request escalation queues, permission request flows, and IDOR mitigation entity detail displays.
## Requirements
### Requirement: Escalation Queue Admin UI

The system SHALL provide a frontend interface within the admin content page, labeled "User Requests", that allows users with `escalate:resolve` permission to view and manage pending escalation requests. To prevent IDOR (Insecure Direct Object Reference) manipulation confusion, the queue MUST clearly display all pending requests with requester name, explicit target entity details (including entity UUID and title/name), a clickable target entity link, field name, suggested value, note, and creation timestamp. For pending requests, the UI SHALL present all resolution actions ("Accept" / "Accept & Delete", "Reject", "Mark as Duplicate") as direct inline buttons on the card. Overflow dropdown menus MUST NOT be used for queue actions — all actions shall be directly visible to minimize interaction cost. The system SHALL also provide an expandable "Processed Requests" section, hidden by default, that lists previously resolved requests.

#### Scenario: Custodian views escalation queue in admin panel

- **WHEN** an authenticated user with `escalate:resolve` permission navigates to the admin content page and selects the "User Requests" tab
- **THEN** the system SHALL render a list of all pending escalation requests ordered by oldest first, showing requester display name, clear target entity details (UUID and title/name) alongside a clickable link to the target manifestation or item page, field name, suggested value, optional note, and creation timestamp.

#### Scenario: Custodian clicks on target entity link in queue

- **WHEN** a custodian clicks the target entity label (e.g., "MANIFESTATION / The Great Gatsby") in the pending requests list
- **THEN** the system SHALL navigate to the manifestation or item detail page for that entity.

#### Scenario: Custodian resolves an escalation request from the queue UI

- **WHEN** a custodian clicks "Accept", "Reject", or "Mark as Duplicate" on a pending request in the queue UI and optionally provides a resolution note
- **THEN** the system SHALL call the PATCH `/api/escalations/<id>` endpoint with the chosen status and resolution note, update the queue display to remove the resolved request, and show a success toast.

#### Scenario: Empty escalation queue

- **WHEN** a custodian views the "User Requests" tab with no pending requests
- **THEN** the system SHALL display a friendly empty state message indicating no pending user requests.

#### Scenario: Custodian expands processed requests list

- **WHEN** a custodian clicks the "Processed Requests" toggle below the pending queue
- **THEN** the system SHALL fetch and display all resolved escalation requests (accepted, rejected, duplicate), ordered by most recently resolved first, each showing resolution status, resolution note, and resolver name.

#### Scenario: Non-custodian cannot see user requests tab

- **WHEN** an authenticated user without `escalate:resolve` permission views the admin content page
- **THEN** the system SHALL NOT render the "User Requests" navigation item in the sidebar.

### Requirement: Resolved Escalation Requests API Endpoint

The system SHALL support fetching resolved escalation requests via the existing queue endpoint by accepting a `status` query parameter with comma-separated status values. When `status` is not provided, the endpoint SHALL default to returning only `pending` requests (backward compatible).

#### Scenario: Fetch resolved requests

- **WHEN** a user with `escalate:resolve` permission sends a GET to `/api/escalations/queue?status=accepted,rejected,duplicate`
- **THEN** the system SHALL return a JSON array of escalation requests matching any of the specified statuses, ordered by `created_at` ascending.

#### Scenario: Backward compatible default

- **WHEN** a user with `escalate:resolve` permission sends a GET to `/api/escalations/queue` without a `status` parameter
- **THEN** the system SHALL return only `pending` requests, preserving existing behavior.

#### Scenario: Non-custodian attempts to access resolved queue

- **WHEN** an authenticated user without `escalate:resolve` permission sends a GET to `/api/escalations/queue?status=accepted`
- **THEN** the system SHALL return HTTP 403 with error `"Forbidden"`.

