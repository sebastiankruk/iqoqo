## ADDED Requirements

### Requirement: Backend tests enforce write:metadata on FRBR edit endpoints
The backend test suite SHALL include tests verifying that FRBR edit endpoints (`update_work`, `update_expression`, `update_manifestation`, `update_item`, `upload_manifestation_image`, `add_work_part`, `remove_work_part`) accept requests from users with `write:metadata` permission (non-admin) and reject requests from users with only `read:metadata` permission.

#### Scenario: Non-admin with write:metadata can update a work
- **WHEN** a user with `write:metadata` (but not admin) sends PATCH to `/api/v1/admin/frbr/work/<id>`
- **THEN** the response SHALL return 200 and the work SHALL be updated

#### Scenario: User with only read:metadata cannot update a work
- **WHEN** a user with `read:metadata` (but not `write:metadata`) sends PATCH to `/api/v1/admin/frbr/work/<id>`
- **THEN** the response SHALL return 403 with `missing_permission: write:metadata`

#### Scenario: Non-admin with write:metadata can update a manifestation
- **WHEN** a user with `write:metadata` (but not admin) sends PATCH to `/api/v1/admin/frbr/manifestation/<id>`
- **THEN** the response SHALL return 200

#### Scenario: Non-admin with write:metadata can upload a manifestation image
- **WHEN** a user with `write:metadata` sends POST to `/api/v1/manifestations/<id>/images`
- **THEN** the response SHALL return 200

#### Scenario: Non-admin with write:metadata can add a work part
- **WHEN** a user with `write:metadata` sends POST to `/api/v1/admin/works/<id>/parts`
- **THEN** the response SHALL return 200

### Requirement: Backend tests enforce read:metadata on FRBR tree and search endpoints
The backend test suite SHALL verify that the FRBR tree endpoint (`/frbr/tree/manifestation/<id>`) accepts requests from non-admin users with `read:metadata` permission.

#### Scenario: Custodian with read:metadata can access FRBR tree
- **WHEN** a non-admin user with `read:metadata` calls `GET /api/v1/admin/frbr/tree/manifestation/<id>`
- **THEN** the response SHALL return 200 with the FRBR tree data

#### Scenario: User without read:metadata cannot access FRBR tree
- **WHEN** a user without `read:metadata` calls `GET /api/v1/admin/frbr/tree/manifestation/<id>`
- **THEN** the response SHALL return 403

### Requirement: Alembic migration test verifies escalation permission assignment
A test SHALL verify that the migration `52dbd8310811_assign_escalation_permissions_to_roles.py` correctly assigns `escalate:request` to the `user` role and `escalate:resolve` to `custodian`, `contributor`, and `admin` roles during upgrade, and removes them during downgrade.

#### Scenario: Migration upgrade assigns escalation permissions
- **WHEN** the migration is upgraded
- **THEN** the `user` role SHALL have `escalate:request` permission and the `custodian` role SHALL have `escalate:resolve` permission

#### Scenario: Migration downgrade removes escalation permissions
- **WHEN** the migration is downgraded
- **THEN** the `user` role SHALL no longer have `escalate:request` and the `custodian` role SHALL no longer have `escalate:resolve`

### Requirement: Frontend logout route has unit test coverage
The Next.js logout route handler at `/api/auth/logout/route.ts` SHALL have a unit test verifying it deletes the session cookie and returns a success response.

#### Scenario: Logout deletes session cookie
- **WHEN** the logout route handler is invoked
- **THEN** the response SHALL delete the session cookie and return a JSON success body

### Requirement: Require_permission decorator unit tests
The `@require_permission` decorator SHALL have a focused unit test verifying it handles invalid permission types, returns 401 for unauthenticated requests, and returns 403 for missing permissions.

#### Scenario: Decorator returns 401 when user is missing
- **WHEN** the decorator wraps a route and no auth token is provided
- **THEN** the decorator SHALL return 401 before the route handler executes

#### Scenario: Decorator accepts valid permission names
- **WHEN** the decorator is applied with a valid `PermissionName` enum value
- **THEN** the decorator SHALL not raise an error during registration
