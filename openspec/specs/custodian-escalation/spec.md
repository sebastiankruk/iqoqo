# custodian-escalation Specification

## Purpose

TBD - created by archiving change custodian-escalation-hooks. Update Purpose after archive.

## Requirements

### Requirement: Escalation Request Submission

The system SHALL allow any authenticated user with the `escalate:request` permission to submit an escalation request targeting a specific FRBR entity (Work, Expression, Manifestation, or Item). The request MUST capture the target entity level, target entity ID, and the `request_type` discriminator (`"correction"` or `"deletion"`). For correction-type requests, the system SHALL require a `field_name` and `suggested_value`. For deletion-type requests, the system SHALL require a `note` (reason for deletion) and SHALL accept empty or absent `field_name` and `suggested_value`. The `escalate:request` permission MUST be assigned to the default `user` role during database initialization.

#### Scenario: Authenticated user submits a valid escalation request

- **WHEN** an authenticated user with `escalate:request` permission submits a POST to `/api/escalations/<level>/<target_id>` with `field_name`, `suggested_value`, and optional `current_value` and `note`
- **THEN** the system SHALL create an `EscalationRequest` record with status `pending`, return HTTP 201 with the created request data, and associate it with the requesting user.

#### Scenario: Authenticated user submits a valid correction escalation request

- **WHEN** an authenticated user with `escalate:request` permission submits a POST to `/api/escalations/<level>/<target_id>` with `request_type: "correction"` (or omitted), `field_name`, `suggested_value`, and optional `current_value` and `note`
- **THEN** the system SHALL create an `EscalationRequest` record with `request_type="correction"` and status `pending`, return HTTP 201 with the created request data including `request_type`, and associate it with the requesting user.

#### Scenario: Authenticated user submits a valid deletion escalation request

- **WHEN** an authenticated user with `escalate:request` permission submits a POST to `/api/escalations/<level>/<target_id>` with `request_type: "deletion"`, `note: "Created by mistake - invalid barcode scanned"`, and empty `field_name` and `suggested_value`
- **THEN** the system SHALL create an `EscalationRequest` record with `request_type="deletion"`, status `pending`, the provided note, and return HTTP 201.

#### Scenario: User submits deletion request without a reason note

- **WHEN** an authenticated user submits a POST with `request_type: "deletion"` and `note` is empty or missing
- **THEN** the system SHALL return HTTP 400 with error `"Note is required for deletion requests"`.

#### Scenario: User submits with invalid request_type

- **WHEN** an authenticated user submits a POST with `request_type: "invalid_value"`
- **THEN** the system SHALL return HTTP 400 with error indicating `request_type` must be `"correction"` or `"deletion"`.

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

#### Scenario: User submits correction with missing required field

- **WHEN** an authenticated user submits a correction-type escalation request without `field_name` or `suggested_value`
- **THEN** the system SHALL return HTTP 400 with a descriptive error message.

#### Scenario: User submits escalation with oversized text

- **WHEN** an authenticated user submits an escalation where `suggested_value` or `note` exceeds `MAX_SOCIAL_TEXT_LENGTH` (2048 characters)
- **THEN** the system SHALL return HTTP 400 with error indicating the maximum length constraint.

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

### Requirement: Escalation Request Resolution

The system SHALL allow users with `escalate:resolve` permission to resolve pending escalation requests by changing their status to `accepted`, `rejected`, or `duplicate`. A resolution note MAY be provided. When resolving a deletion-type request with status `accepted`, the system SHALL additionally verify that the resolver holds the entity-specific DELETE permission (`delete:manifestation` for manifestations, `delete:item` for items) and SHALL execute entity deletion upon acceptance. The `escalate:resolve` permission MUST be assigned to the `custodian` and `admin` roles during database initialization.

#### Scenario: Custodian accepts an escalation request

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "accepted"` and optional `resolution_note`
- **THEN** the system SHALL update the request status to `accepted`, record the `resolved_by` user ID, set `resolved_at` timestamp, store the `resolution_note`, and return the updated request.

#### Scenario: Admin accepts a deletion escalation request

- **WHEN** a user with both `escalate:resolve` and `delete:manifestation` permissions sends a PATCH to `/api/escalations/<escalation_id>` with `status: "accepted"` on a deletion-type request targeting a manifestation
- **THEN** the system SHALL execute the manifestation deletion, set target FK to NULL, and return HTTP 200 with resolved escalation status.

#### Scenario: Custodian without delete permission attempts to accept a deletion request

- **WHEN** a user with `escalate:resolve` but WITHOUT `delete:manifestation` or `delete:item` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "accepted"` on a deletion-type request
- **THEN** the system SHALL return HTTP 403 with error indicating the required DELETE permission.

#### Scenario: Custodian accepts a correction escalation request

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "accepted"` on a correction-type request
- **THEN** the system SHALL update the request status to `accepted`, record the `resolved_by` user ID, set `resolved_at` timestamp, store the `resolution_note`, and return the updated request. NO entity deletion SHALL occur. No DELETE permission check SHALL be required.

#### Scenario: Custodian and admin roles include resolve permission

- **WHEN** a user is assigned the `custodian` or `admin` role
- **THEN** the user SHALL automatically have the `escalate:resolve` permission via their role, enabling them to view and resolve escalation requests.

#### Scenario: Custodian rejects an escalation request

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "rejected"` and a `resolution_note` explaining why
- **THEN** the system SHALL update the request status to `rejected` and store the resolution metadata. Rejection SHALL work identically for both correction and deletion request types.

#### Scenario: Custodian marks an escalation as duplicate

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "duplicate"`
- **THEN** the system SHALL update the request status to `duplicate` without requiring DELETE permissions.

#### Scenario: Non-custodian attempts to resolve an escalation

- **WHEN** an authenticated user without `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>`
- **THEN** the system SHALL return HTTP 403 with error `"Forbidden"`.

### Requirement: Escalation Data Model

The system SHALL persist escalation requests in an `escalation_requests` database table with polymorphic FRBR-level foreign keys (same pattern as `SocialFeedback`), a status lifecycle column, a `request_type` discriminator column defaulting to `"correction"`, and referential integrity setting target foreign keys to NULL when the target entity is removed while preserving request history.

#### Scenario: Target FRBR entity is deleted while escalation is pending

- **WHEN** a Manifestation with an escalation request is deleted
- **THEN** the system SHALL set `manifestation_id` to NULL, preserve the escalation record, and track `target_type`.

#### Scenario: Database enforces exactly one FRBR target

- **WHEN** an escalation request is created
- **THEN** the database SHALL enforce that exactly one of `work_id`, `expression_id`, `manifestation_id`, or `item_id` is non-NULL.

#### Scenario: Database enforces at most one FRBR target

- **WHEN** an escalation request is created or updated
- **THEN** the database SHALL enforce that at most one of `work_id`, `expression_id`, `manifestation_id`, or `item_id` is non-NULL.

#### Scenario: Existing escalation rows receive default request_type

- **WHEN** the `request_type` column migration is applied to a database with existing escalation requests
- **THEN** all existing rows SHALL have `request_type` set to `"correction"` (the column default), preserving backward compatibility.

#### Scenario: EscalationRequest serialization includes request_type

- **WHEN** an escalation request is serialized to JSON via `to_dict()`
- **THEN** the output dictionary SHALL include `request_type` with the value `"correction"` or `"deletion"`.

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
