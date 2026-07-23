# custodian-escalation Specification

## Purpose
TBD - created by archiving change custodian-escalation-hooks. Update Purpose after archive.
## Requirements
### Requirement: Escalation Request Submission

The system SHALL allow any authenticated user with the `escalate:request` permission to submit an escalation request targeting a specific FRBR entity (Work, Expression, Manifestation, or Item). The request MUST capture the target entity level, target entity ID, the field name the user believes is incorrect, an optional current value, a required suggested value, and an optional free-text justification note. The `escalate:request` permission MUST be assigned to the default `user` role during database initialization.

#### Scenario: Authenticated user submits a valid escalation request

- **WHEN** an authenticated user with `escalate:request` permission submits a POST to `/api/escalations/<level>/<target_id>` with `field_name`, `suggested_value`, and optional `current_value` and `note`
- **THEN** the system SHALL create an `EscalationRequest` record with status `pending`, return HTTP 201 with the created request data, and associate it with the requesting user.

#### Scenario: Default role includes escalation permission

- **WHEN** a new user registers with the system
- **THEN** the user SHALL automatically have the `escalate:request` permission via the default `user` role, enabling them to submit escalation requests without manual permission grants.

#### Scenario: Unauthenticated user attempts to submit an escalation

- **WHEN** an unauthenticated user submits a POST to `/api/escalations/<level>/<target_id>`
- **THEN** the system SHALL return HTTP 401 with error `"Token missing"`.

#### Scenario: User submits escalation for non-existent target

- **WHEN** an authenticated user submits an escalation targeting a FRBR entity ID that does not exist in the database
- **THEN** the system SHALL return HTTP 404 with error `"<Level> not found"`.

#### Scenario: User submits escalation with missing required field

- **WHEN** an authenticated user submits an escalation request without `field_name` or `suggested_value`
- **THEN** the system SHALL return HTTP 400 with a descriptive error message.

#### Scenario: User submits escalation with oversized text

- **WHEN** an authenticated user submits an escalation where `suggested_value` or `note` exceeds `MAX_SOCIAL_TEXT_LENGTH` (2048 characters)
- **THEN** the system SHALL return HTTP 400 with error indicating the maximum length constraint.

### Requirement: Escalation Request Listing

The system SHALL expose endpoints for listing escalation requests. Authenticated users SHALL be able to list their own pending requests. Users with `escalate:resolve` permission SHALL be able to list all pending escalation requests across all users (the custodian queue).

#### Scenario: User lists their own escalation requests

- **WHEN** an authenticated user sends a GET to `/api/escalations/mine`
- **THEN** the system SHALL return a JSON array of all escalation requests submitted by that user, ordered by `created_at` descending.

#### Scenario: Custodian lists all pending escalation requests

- **WHEN** a user with `escalate:resolve` permission sends a GET to `/api/escalations/queue`
- **THEN** the system SHALL return a JSON array of all escalation requests with status `pending`, ordered by `created_at` ascending (oldest first), including the requesting user's display name.

#### Scenario: Non-custodian user attempts to access the queue

- **WHEN** an authenticated user without `escalate:resolve` permission sends a GET to `/api/escalations/queue`
- **THEN** the system SHALL return HTTP 403 with error `"Forbidden"`.

### Requirement: Escalation Request Resolution

The system SHALL allow users with `escalate:resolve` permission to resolve pending escalation requests by changing their status to `accepted`, `rejected`, or `duplicate`. A resolution note MAY be provided. The `escalate:resolve` permission MUST be assigned to the `custodian` and `admin` roles during database initialization.

#### Scenario: Custodian accepts an escalation request

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "accepted"` and optional `resolution_note`
- **THEN** the system SHALL update the request status to `accepted`, record the `resolved_by` user ID, set `resolved_at` timestamp, store the `resolution_note`, and return the updated request.

#### Scenario: Custodian and admin roles include resolve permission

- **WHEN** a user is assigned the `custodian` or `admin` role
- **THEN** the user SHALL automatically have the `escalate:resolve` permission via their role, enabling them to view and resolve escalation requests.

#### Scenario: Custodian rejects an escalation request

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "rejected"` and a `resolution_note` explaining why
- **THEN** the system SHALL update the request status to `rejected` and store the resolution metadata.

#### Scenario: Custodian marks an escalation as duplicate

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "duplicate"`
- **THEN** the system SHALL update the request status to `duplicate`.

#### Scenario: Non-custodian attempts to resolve an escalation

- **WHEN** an authenticated user without `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>`
- **THEN** the system SHALL return HTTP 403 with error `"Forbidden"`.

### Requirement: Escalation Data Model

The system SHALL persist escalation requests in an `escalation_requests` database table with polymorphic FRBR-level foreign keys (same pattern as `SocialFeedback`), a status lifecycle column, and referential integrity via cascading deletes when the target entity is removed.

#### Scenario: Target FRBR entity is deleted while escalation is pending

- **WHEN** a Manifestation with a pending escalation request is deleted
- **THEN** the system SHALL cascade-delete the associated escalation request.

#### Scenario: Database enforces exactly one FRBR target

- **WHEN** an escalation request is created
- **THEN** the database SHALL enforce that exactly one of `work_id`, `expression_id`, `manifestation_id`, or `item_id` is non-NULL.

### Requirement: Escalation UI Trigger Visibility

The system SHALL render a contextual "Ask Custodians for Help" escalation trigger on item detail and manifestation detail pages. This trigger MUST only be visible to authenticated users who do NOT have `write:metadata` permission. Users who already have custodian/admin metadata write access SHALL NOT see the escalation trigger. The "Edit FRBR" button SHALL only be rendered for users with `write:metadata` permission, NOT for users with only `read:metadata` permission. If the user has an existing escalation for the current entity, the trigger MUST instead display the status and resolution note of that escalation.

#### Scenario: Non-custodian user views an item detail page with their own active escalation

- **WHEN** an authenticated user without `write:metadata` permission views an item detail page for which they have previously submitted an escalation request
- **THEN** the system SHALL render the escalation's current status (`pending`, `accepted`, `rejected`) and any `resolution_note` within the escalation trigger UI, replacing the default "Ask Custodians for Help" button.

#### Scenario: Non-custodian user views an item detail page

- **WHEN** an authenticated user without `write:metadata` permission views an item detail page
- **THEN** the system SHALL render an "Ask Custodians for Help" trigger button within the item actions panel AND SHALL NOT render the "Edit FRBR" button.

#### Scenario: Custodian views an item detail page

- **WHEN** an authenticated user with `write:metadata` permission views an item detail page
- **THEN** the system SHALL render the "Edit FRBR" button AND SHALL NOT render the escalation trigger.

#### Scenario: Regular user does not see "Edit FRBR" button

- **WHEN** an authenticated user with `read:metadata` but without `write:metadata` permission views an item detail page
- **THEN** the system SHALL NOT render the "Edit FRBR" button, since the user cannot use the FRBR metadata editor.

#### Scenario: Unauthenticated user views an item detail page

- **WHEN** an unauthenticated user views an item detail page
- **THEN** the system SHALL NOT render the escalation trigger.

### Requirement: FRBR Entity Search Access Control

The system SHALL allow any user with `read:metadata` permission to search for FRBR entities via the search endpoint. Access MUST NOT be restricted to the `admin` role exclusively — custodians with appropriate permissions SHALL have equal access.

#### Scenario: Custodian searches for FRBR entities

- **WHEN** a user with the `custodian` role and `read:metadata` permission sends a GET to `/v1/admin/frbr/search?q=<query>`
- **THEN** the system SHALL return matching FRBR entities, NOT return HTTP 403 "Admin privileges required".

#### Scenario: User without read:metadata attempts FRBR search

- **WHEN** an authenticated user without `read:metadata` permission sends a GET to `/v1/admin/frbr/search`
- **THEN** the system SHALL return HTTP 403 with the `missing_permission` field indicating `read:metadata`.

### Requirement: Escalation Input Sanitization

The system SHALL apply defense-in-depth sanitization to all user-supplied text fields in escalation requests (field_name, suggested_value, current_value, note, resolution_note). HTML-like markup MUST be stripped at ingress.

#### Scenario: User submits escalation with embedded HTML

- **WHEN** an authenticated user submits an escalation with `suggested_value` containing `<script>alert('xss')</script>Correct Title`
- **THEN** the system SHALL strip the HTML tags, storing only `alert('xss')Correct Title`.
