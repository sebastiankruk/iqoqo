## MODIFIED Requirements

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
