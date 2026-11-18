## Purpose

Allow users to log reading sessions and track total reading time and start-to-finish elapsed days on their owned physical `Item` records (`F5_Item`), while projecting anonymized average reading duration onto `Manifestation` detail views.

## ADDED Requirements

### Requirement: FRBR Item-Scoped Reading Session Logging & Elapsed Duration
The system SHALL store reading sessions (`duration_minutes`, optional `pages_read`, `note`, `logged_at`) and compute start-to-finish elapsed days (from `ReadingTransition` timestamps) strictly on the `Item` (`F5_Item`) level via `POST /api/items/<int:item_id>/reading-sessions` and `GET /api/items/<int:item_id>`, enforcing item ownership (`Item.owner_id == g.user_id`).

#### Scenario: Owner logs a reading session on an active book
- **GIVEN** an authenticated user who owns `Item` `#10` with status `currently_reading`
- **WHEN** the user sends `POST /api/items/10/reading-sessions` with `{"duration_minutes": 45, "pages_read": 30}`
- **THEN** the backend validates `1 <= duration_minutes <= 1440`, appends the session to the item's reading log, updates `total_reading_minutes`, and returns HTTP `201` with the updated `reading_duration_summary`.

#### Scenario: Non-owner attempts to log reading time on another user's item
- **GIVEN** an authenticated user who does not own `Item` `#10`
- **WHEN** the user sends `POST /api/items/10/reading-sessions`
- **THEN** the backend rejects the request with HTTP `403` or `404` (preventing IDOR).

### Requirement: Item Reading Duration UI & Anonymized Manifestation Read-Time Stat
The `/item/[id]` sidebar SHALL render a reading duration card for the item owner with quick-log presets (`+15m`, `+30m`, `+1h`, custom) and total time read, and `GET /api/manifestations/<id>` SHALL include an anonymized `average_reading_minutes` stat across public/consented items when at least one completed reading log exists.

#### Scenario: Collector views reading duration summary on `/item/[id]`
- **GIVEN** an item owner viewing `/item/10` with 3 logged sessions totaling `120` minutes and transition dates 5 days apart
- **WHEN** the item page loads
- **THEN** `ReadingDurationCard` displays `"2h 0m read across 3 sessions (5 days)"` and provides a single primary `"Log Reading Time"` trigger.
