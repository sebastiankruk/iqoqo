# deletion-request-resolution Specification

## Purpose

TBD - created by archiving change add-deletion-request-support. Update Purpose after archive.

## Requirements

### Requirement: Deletion Request Visibility in Admin Queue

The escalation queue admin UI SHALL display a request type badge on each escalation card, distinguishing between "Correction" and "Deletion" requests. The badge SHALL be visually distinct from the status badge and SHALL be rendered using an i18n key.

#### Scenario: Custodian views admin queue with mixed request types

- **WHEN** a custodian with `escalate:resolve` permission views the "User Requests" tab in the admin content page
- **THEN** each pending request card SHALL display a request type badge showing either "Correction" (e.g., in a neutral/badge style) or "Deletion" (e.g., in a warning/destructive style). Deletion-type requests with status `pending` SHALL have the "Accept" button label changed to "Accept & Delete".

#### Scenario: Custodian views processed (resolved) requests with request types

- **WHEN** a custodian expands the "Processed Requests" section in the admin queue
- **THEN** each resolved request card SHALL display a request type badge alongside the status badge.

### Requirement: Permission-Gated Deletion Acceptance

When resolving a deletion-type escalation request with status `accepted`, the resolve endpoint SHALL verify that the current user holds the appropriate entity-specific DELETE permission. The endpoint SHALL deny the resolution if the user lacks the required permission.

#### Scenario: Admin with delete:manifestation accepts a deletion request targeting a manifestation

- **WHEN** a user with both `escalate:resolve` and `delete:manifestation` permissions sends a PATCH to `/api/escalations/<id>` with `status: "accepted"` on a `request_type="deletion"` request that targets a manifestation
- **THEN** the system SHALL accept the resolution, SHALL delete the target manifestation entity from the database, and SHALL return HTTP 200 with the updated escalation data. The cascade-delete on the target FK SHALL also remove the escalation record.

#### Scenario: Custodian without delete:manifestation attempts to accept a deletion request

- **WHEN** a user with `escalate:resolve` but WITHOUT `delete:manifestation` permission sends a PATCH to `/api/escalations/<id>` with `status: "accepted"` on a `request_type="deletion"` request that targets a manifestation
- **THEN** the system SHALL return HTTP 403 with an error message indicating that `delete:manifestation` permission is required to execute deletion requests.

#### Scenario: Admin with delete:item accepts a deletion request targeting an item

- **WHEN** a user with both `escalate:resolve` and `delete:item` permissions sends a PATCH to `/api/escalations/<id>` with `status: "accepted"` on a `request_type="deletion"` request that targets an item
- **THEN** the system SHALL accept the resolution, SHALL delete the target item entity from the database using the existing `delete_item` handler, and SHALL return HTTP 200.

#### Scenario: Custodian rejects a deletion request

- **WHEN** a user with `escalate:resolve` but WITHOUT `delete:manifestation` permission sends a PATCH to `/api/escalations/<id>` with `status: "rejected"` on a `request_type="deletion"` request
- **THEN** the system SHALL update the request status to `rejected`, SHALL NOT perform any entity deletion, and SHALL return HTTP 200. The custodian SHALL NOT be required to hold DELETE permissions for rejecting or marking as duplicate.

#### Scenario: Custodian marks a deletion request as duplicate

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<id>` with `status: "duplicate"` on a `request_type="deletion"` request
- **THEN** the system SHALL update the request status to `duplicate`, SHALL NOT perform any deletion permission check, and SHALL return HTTP 200.

### Requirement: Frontend Admin Queue Conditional Accept Button

The admin queue ResolveActions component SHALL conditionally render the "Accept" button for deletion-type requests. For correction-type requests, the button SHALL remain labeled "Accept". For deletion-type requests, the button SHALL be labeled "Accept & Delete". The button for deletion-type requests SHALL only be enabled (clickable) if the current user's permissions include the appropriate entity-specific DELETE permission.

#### Scenario: Admin with delete permission views a deletion-type pending request

- **WHEN** an admin with `delete:manifestation` permission views a pending deletion-type request in the admin queue
- **THEN** the resolve buttons SHALL include an "Accept & Delete" button (instead of "Accept"). The button SHALL be enabled and SHALL use a destructive/emphasis style to indicate the destructive action.

#### Scenario: Custodian without delete permission views a deletion-type pending request

- **WHEN** a custodian with `escalate:resolve` but without `delete:manifestation` or `delete:item` permission views a pending deletion-type request in the admin queue
- **THEN** the "Accept & Delete" button SHALL be rendered but in a disabled state with a tooltip explaining that `delete:manifestation` or `delete:item` permission is required. The "Reject" and "Mark as Duplicate" buttons SHALL remain enabled.

#### Scenario: Admin accepts and deletes via the queue

- **WHEN** an admin with the appropriate DELETE permission confirms an "Accept & Delete" action on a deletion-type request
- **THEN** the system SHALL send the PATCH request with `status: "accepted"`, the entity SHALL be deleted, and a success toast SHALL display "Deletion request accepted — entity has been removed".

### Requirement: Deletion Request Display in User View

The "My Help Requests" component SHALL display a request type badge on each request card, distinguishing between "Correction" and "Deletion" types. The badge SHALL be displayed alongside the status badge.

#### Scenario: User views their help requests including a deletion request

- **WHEN** an authenticated user views their help requests on the profile page
- **THEN** each request card SHALL display a request type badge. Deletion-type requests SHALL show a distinct badge (e.g., "Deletion" in warning/destructive style). Correction-type requests may omit the badge or show a neutral "Correction" badge.

#### Scenario: Deletion request shows appropriate details

- **WHEN** a user views a deletion-type request card in their help requests list
- **THEN** the card SHALL display the deletion reason (from the `note` field) prominently, and SHALL NOT display field_name/suggested_value arrows (since these are empty for deletion requests).

### Requirement: Resolve Endpoint Handles Entity Deletion Failure

The resolve endpoint SHALL handle cases where entity deletion fails (e.g., the target entity no longer exists, or a database error occurs) and SHALL NOT leave the escalation request in an inconsistent state.

#### Scenario: Deletion request accepted but target entity already deleted

- **WHEN** a user with appropriate DELETE permissions sends a PATCH to `/api/escalations/<id>` with `status: "accepted"` on a deletion-type request, but the target entity has already been removed from the database (e.g., by another admin)
- **THEN** the system SHALL return HTTP 404 with an error indicating that the target entity no longer exists, and SHALL NOT update the escalation status. The escalation SHALL remain `pending`.
