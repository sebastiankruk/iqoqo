# Escalation Queue UI

## Purpose

Provide custodians and admins with a dedicated frontend interface to view and manage pending escalation requests directly from the admin content page.

## Requirements

### Requirement: Escalation Queue Admin UI

The system SHALL provide a frontend interface within the admin content page that allows users with `escalate:resolve` permission to view and manage pending escalation requests. The queue MUST display all pending requests with requester name, target entity, field name, suggested value, note, and creation timestamp. Custodians MUST be able to accept, reject, or mark requests as duplicate with an optional resolution note, directly from this interface.

#### Scenario: Custodian views escalation queue in admin panel

- **WHEN** an authenticated user with `escalate:resolve` permission navigates to the admin content page and selects the "Escalation Queue" tab
- **THEN** the system SHALL render a list of all pending escalation requests ordered by oldest first, showing requester display name, target entity type and ID, field name, suggested value, optional note, and creation timestamp.

#### Scenario: Custodian resolves an escalation request from the queue UI

- **WHEN** a custodian clicks "Accept", "Reject", or "Duplicate" on a pending request in the queue UI and optionally provides a resolution note
- **THEN** the system SHALL call the PATCH `/api/escalations/<id>` endpoint with the chosen status and resolution note, update the queue display to remove the resolved request, and show a success toast.

#### Scenario: Empty escalation queue

- **WHEN** a custodian views the escalation queue with no pending requests
- **THEN** the system SHALL display a friendly empty state message indicating no pending requests.

#### Scenario: Non-custodian cannot see escalation queue tab

- **WHEN** an authenticated user without `escalate:resolve` permission views the admin content page
- **THEN** the system SHALL NOT render the "Escalation Queue" navigation item in the sidebar.
