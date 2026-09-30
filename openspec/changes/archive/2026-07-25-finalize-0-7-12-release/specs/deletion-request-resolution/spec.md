## MODIFIED Requirements

### Requirement: Permission-Gated Deletion Acceptance

When resolving a deletion-type escalation request with status `accepted`, the resolve endpoint SHALL verify that the current user holds the appropriate entity-specific DELETE permission. The endpoint SHALL deny the resolution if the user lacks the required permission. Furthermore, the endpoint SHALL wrap the operation in an explicit atomic transaction using `with_for_update()` and `synchronize_session=False` to prevent race conditions. The system SHALL prevent the deletion of a Manifestation if there are dependent Items attached to it.

#### Scenario: Admin with delete:manifestation accepts a deletion request targeting a manifestation with no items

- **WHEN** a user with both `escalate:resolve` and `delete:manifestation` permissions sends a PATCH to `/api/escalations/<id>` with `status: "accepted"` on a `request_type="deletion"` request that targets a manifestation with zero dependent items
- **THEN** the system SHALL accept the resolution, SHALL delete the target manifestation entity from the database using an atomic transaction, and SHALL return HTTP 200 with the updated escalation data. The cascade-delete on the target FK SHALL also remove the escalation record.

#### Scenario: Admin attempts to delete a manifestation with dependent items

- **WHEN** a user with both `escalate:resolve` and `delete:manifestation` permissions attempts to accept a deletion request targeting a manifestation that has dependent items
- **THEN** the system SHALL reject the deletion, rollback the transaction, and return an HTTP 409 Conflict with a message indicating dependent items exist.

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

### Requirement: Resolve Endpoint Handles Entity Deletion Failure

The resolve endpoint SHALL handle cases where entity deletion fails (e.g., the target entity no longer exists, database integrity constraint violations occur, or other transactional errors happen) and SHALL NOT leave the escalation request in an inconsistent state. The resolution SHALL be executed inside an atomic transaction block that is rolled back on any SQLAlchemy error.

#### Scenario: Deletion request accepted but target entity already deleted

- **WHEN** a user with appropriate DELETE permissions sends a PATCH to `/api/escalations/<id>` with `status: "accepted"` on a deletion-type request, but the target entity has already been removed from the database (e.g., by another admin)
- **THEN** the system SHALL return HTTP 404 with an error indicating that the target entity no longer exists, and SHALL NOT update the escalation status. The escalation SHALL remain `pending`.

#### Scenario: Deletion request hits an integrity error

- **WHEN** the deletion process hits an unforeseen PostgreSQL IntegrityError
- **THEN** the transaction block SHALL issue a rollback to restore the system state and return an HTTP 500 Internal Server Error.
