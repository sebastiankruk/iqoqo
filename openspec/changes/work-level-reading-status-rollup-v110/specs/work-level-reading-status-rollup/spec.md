## Purpose

Compute and display a user-scoped reading/consumption status rollup at the FRBR `Work` tier by aggregating owned `Item` statuses across all `Expression`s and `Manifestation`s of a `Work`, preserving strict FRBR separation and per-user privacy.

## ADDED Requirements

### Requirement: User-Scoped Work Reading Status Rollup Without Mutating `Work`
The backend SHALL compute `work_reading_status` strictly as a read-time, user-scoped projection over the authenticated caller's owned `Item`s (including the caller's `private` / `is_hidden` items) linked to a `Work` via `Manifestation → Expression → Work`, using batched `GROUP BY` aggregate queries and storing zero personal reading state on `Work`.

#### Scenario: User has read Paperback Item A and views Hardcover Manifestation B or Work W
- **GIVEN** User U owns Item A (status `"read"`) of Manifestation A under Work W, and does not own Hardcover Manifestation B under Work W
- **WHEN** User U requests `GET /api/works/<W>` or `GET /api/manifestations/<B>`
- **THEN** the response MUST return `work_reading_status: "read"` (and for Manifestation B indicate `completed_via_other_edition: true`), while `Work` itself contains no personal reading columns.

#### Scenario: Precedence when user owns both a read copy and an unread/reading copy of the same Work
- **GIVEN** User U owns Item 1 (`status == "read"`) and Item 2 (`status == "want_to_read"` or `"reading"`) under Work W
- **WHEN** `compute_work_reading_rollup` evaluates Work W for User U
- **THEN** completed status (`"read"`) MUST take precedence over in-progress (`"reading"`) and unstarted (`"want_to_read"`).

#### Scenario: Privacy isolation for unauthenticated visitors and other users
- **GIVEN** User U owns a `"read"` Item under Work W
- **WHEN** an anonymous visitor or User V (who has no items under Work W) requests `GET /api/works/<W>` or `GET /api/manifestations/<M>`
- **THEN** `work_reading_status` MUST be `null` and User U's personal reading status MUST NOT be leaked.

### Requirement: Works Catalog Rollup Filtering and Detail Page Badges
`GET /api/works/shelf` SHALL support filtering by `work_read_status` (`completed`, `in_progress`, `unread`) for authenticated callers, and `/work/[id]` plus `/manifestation/[id]` SHALL render localized badges showing the rolled-up Work consumption status.

#### Scenario: Displaying Work-level status badge on `/work/[id]` and `/manifestation/[id]`
- **GIVEN** an authenticated user viewing `/manifestation/[B]` where `work_reading_status == "read"` and `completed_via_other_edition == true`
- **WHEN** the detail page renders
- **THEN** the UI MUST display a localized `"Read (another edition)"` badge linking or clarifying that the Work was completed in another owned copy.
