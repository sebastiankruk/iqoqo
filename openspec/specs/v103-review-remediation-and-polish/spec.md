# v103-review-remediation-and-polish Specification

## Purpose
Resolve all Moderate (`M-01`–`M-03`) and Low (`L-01`–`L-07`) findings from the `v1.0.3` Principal + Gemini Argon release audit (`C125`), hardening reading session permissions and note privacy, wishlist reactivation and search escaping, shared collection FTS/wishlist pagination, OpenAPI 3.1 contract parity, wishlist UI localization, concise release documentation, and full regression test coverage.

## Requirements

### Requirement: Reading Session Write Permission Enforcement, Federation Hub Guard, and Public Note Privacy (`M-01`, `M-02`)

The system SHALL enforce item write permissions (`PermissionName.WRITE_ITEM`) and the Federation Hub physical item write guard (`FEDERATION_HEAD_MODE`) on `POST /api/items/<int:item_id>/reading-sessions`, and `GET /api/items/<int:item_id>` SHALL omit or redact `reading_sessions` from `data.meta` whenever the caller is neither the item owner nor an administrator.

#### Scenario: Read-only Personal Access Token is denied reading session logging (`M-01`)

- **GIVEN** an authenticated user authenticating with a Personal Access Token (`iqo_*`) scoped only to `["read:catalog", "read:items"]` (without `write:items` / `PermissionName.WRITE_ITEM`)
- **WHEN** the client sends `POST /api/items/<item_id>/reading-sessions` with `{"duration_minutes": 30}`
- **THEN** the backend MUST reject the request with HTTP `403` and MUST NOT modify `Item.meta`.

#### Scenario: Federation Hub instance blocks reading session writes (`M-01`)

- **GIVEN** an instance with `FEDERATION_HEAD_MODE` enabled
- **WHEN** an authenticated owner sends `POST /api/items/<item_id>/reading-sessions`
- **THEN** the backend MUST reject the request with HTTP `403` via the Federation Hub item write guard.

#### Scenario: Non-owner viewing a public item cannot read private session notes (`M-02`)

- **GIVEN** a public `Item` (`visibility == "public"`, `is_hidden == False`) whose owner logged reading sessions containing personal `note` entries
- **WHEN** an unauthenticated visitor or a different non-admin user requests `GET /api/items/<item_id>`
- **THEN** `data.reading_duration_summary` (`total_minutes`, `sessions_count`, `elapsed_days`) MUST be returned, AND `data.meta` MUST NOT expose `reading_sessions` (or any session `note` text).

### Requirement: Wishlist Reactivation, Edition Upgrade, Backslash-Safe Search, and Localization (`M-03`, `L-01`, `L-05`, `L-07`)

Re-wishlisting a work that has an existing `UserWorkIntent` row (including one with `status == "fulfilled"`) SHALL reactivate the intent to an active wishlist progress status (`want_to_*`) and update `expression_id` and `manifestation_id` when a specific manifestation is targeted. `GET /api/wishlist` SHALL safely escape backslashes in `q` search queries, use SQLAlchemy 2.0 `select()` queries, and `/wishlist` plus `AddToCollectionDropdown` SHALL render localized labels via `next-intl`.

#### Scenario: Re-wishlisting a previously fulfilled work reactivates the intent and upgrades edition binding (`M-03`)

- **GIVEN** a user has an existing `UserWorkIntent` row for work `W` with `status == "fulfilled"`, `expression_id == None`, and `manifestation_id == None`
- **WHEN** the user adds manifestation `M` (belonging to expression `E` and work `W`) with `collection_status="wish_list"`
- **THEN** the existing `UserWorkIntent` MUST be updated in-place to `status == "want_to_read"` (or the category's default `want_to_*` status), `expression_id == E.id`, and `manifestation_id == M.id`, and MUST appear in `GET /api/wishlist` and `GET /api/manifestations/<M>`.

#### Scenario: Wishlist search query ending with a backslash does not fail or mis-escape (`L-01`)

- **GIVEN** an authenticated user with wishlist items
- **WHEN** the user requests `GET /api/wishlist?q=Dune\`
- **THEN** the backend MUST escape `\` prior to `%` and `_` via `escape_ilike_term()` and return HTTP `200` without raising a database `ESCAPE` error.

#### Scenario: Wishlist category filter options and dropdown actions are localized (`L-05`)

- **GIVEN** the `/wishlist` page and `AddToCollectionDropdown` rendered under EN or PL locales
- **WHEN** the category `<select>` options and wishlist dropdown actions are inspected
- **THEN** all labels MUST resolve through `next-intl` translation keys in `en.json` and `pl.json` with zero hardcoded English strings.

### Requirement: Shared Collection Search Offset Parity, LEGO Wishlist Slicing, OpenAPI 3.1 Contract, and Release Docs (`L-02`, `L-03`, `L-04`, `L-06`)

Shared collection endpoints SHALL preserve SQL pagination offsets when filtering by full-text search on PostgreSQL and when slicing shared `UserWorkIntent` rows (including `"want_to_build"`), `/api/docs/openapi.json` SHALL document all `v1.0.3` parameters and request bodies, and `docs/CHANGELOG.md` plus `.context/notes/*` SHALL concisely reflect all completed `v1.0.3` changes (`C115`–`C125`).

#### Scenario: Shared collection with saved search query paginates page 2+ on PostgreSQL (`L-02`)

- **GIVEN** a shared collection with a saved `query` filter and more than 1 page of matching public items on PostgreSQL
- **WHEN** page 2 (`offset > 0`) is fetched via `fetch_shared_collection_by_token` or `GET /api/public/share/<token>?page=2&per_page=1`
- **THEN** the backend MUST pass the requested offset/limit window to the search query and return the page 2 items rather than an empty list.

#### Scenario: Shared wishlist collection includes LEGO `want_to_build` intents and slices by page (`L-04`)

- **GIVEN** a shared wishlist collection containing `UserWorkIntent` entries (including `status == "want_to_build"`)
- **WHEN** `GET /api/public/share/<token>?page=1&per_page=2` is requested
- **THEN** `"want_to_build"` intents MUST be included and the returned `items` list MUST respect the requested `page` and `per_page` slice bounds.

#### Scenario: OpenAPI 3.1 contract documents reading sessions and shared collection pagination (`L-03`)

- **GIVEN** `GET /api/docs/openapi.json`
- **WHEN** `/api/items/{item_id}/reading-sessions`, `/api/public/share/{token}`, and `components.schemas.Expression` are inspected
- **THEN** `POST /api/items/{item_id}/reading-sessions` MUST declare its `requestBody` (`duration_minutes`, `pages_read`, `note`) and `201` response, `GET /api/public/share/{token}` MUST declare `page` and `per_page` query parameters, and `Expression.content_type` enum MUST include `"cartographic_map"`.

#### Scenario: Concise v1.0.3 changelog and roadmap synchronization (`L-06`)

- **GIVEN** `docs/CHANGELOG.md`, `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, and `.context/notes/plan/1.0.x-release-plan.md`
- **WHEN** the `v1.0.3` release documentation is inspected
- **THEN** `docs/CHANGELOG.md` MUST contain a concise `## [1.0.3] - 2026-11-18` section covering `C115`–`C125`, all `#v103` checkboxes in roadmap and development notes MUST be checked (`[x]`), and `markdownlint-cli2` MUST pass with zero errors.
