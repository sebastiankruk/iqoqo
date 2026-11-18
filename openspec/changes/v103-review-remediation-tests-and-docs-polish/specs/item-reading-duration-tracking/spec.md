## MODIFIED Requirements

### Requirement: FRBR Item-Scoped Reading Session Logging & Elapsed Duration
The system SHALL store reading sessions (`duration_minutes`, optional `pages_read`, `note`, `logged_at`) and compute start-to-finish elapsed days (from `ReadingTransition` timestamps) strictly on the `Item` (`F5_Item`) level via `POST /api/items/<int:item_id>/reading-sessions` and `GET /api/items/<int:item_id>`, enforcing item ownership (`Item.owner_id == g.user_id`), item write permission (`PermissionName.WRITE_ITEM`), and the Federation Hub physical item write guard (`FEDERATION_HEAD_MODE`), while redacting private `reading_sessions` notes from `GET /api/items/<int:item_id>` when the caller is neither the owner nor an administrator.

#### Scenario: Owner logs a reading session on an active book

- **GIVEN** an authenticated user who owns `Item` `#10` with status `currently_reading` and has `PermissionName.WRITE_ITEM`
- **WHEN** the user sends `POST /api/items/10/reading-sessions` with `{"duration_minutes": 45, "pages_read": 30}`
- **THEN** the backend validates `1 <= duration_minutes <= 1440`, appends the session to the item's reading log, updates `total_reading_minutes`, and returns HTTP `201` with the updated `reading_duration_summary`.

#### Scenario: Non-owner attempts to log reading time on another user's item

- **GIVEN** an authenticated user who does not own `Item` `#10`
- **WHEN** the user sends `POST /api/items/10/reading-sessions`
- **THEN** the backend rejects the request with HTTP `403` or `404` (preventing IDOR).

#### Scenario: Read-only PAT or Federation Hub instance cannot log reading sessions and non-owners cannot view session notes

- **GIVEN** a read-only Personal Access Token (`iqo_*` without `PermissionName.WRITE_ITEM`) or an instance with `FEDERATION_HEAD_MODE` enabled
- **WHEN** `POST /api/items/10/reading-sessions` is called
- **THEN** the backend rejects the request with HTTP `403`; and **WHEN** a non-owner requests `GET /api/items/10` on a public item
- **THEN** `data.meta` MUST NOT include `reading_sessions` while `data.reading_duration_summary` remains visible.
