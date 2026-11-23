# shared-collection-visibility-scope Specification

## Purpose
Allow collectors to configure each `SharedCollection` link's `visibility_scope` (`public_only`, `friends_and_public`, or `all`) using a Token Scope + Friend Bonus access model across web views, JSON APIs, AI JSON-LD/Turtle exports, and RSS feeds.

## Requirements

### Requirement: Configurable Share Collection Visibility Scope
`POST /api/sharing/` SHALL accept an optional `visibility_scope` (inside `filters.visibility_scope` or top-level request field) validated against `{"public_only", "friends_and_public", "all"}`, defaulting to `"public_only"` when omitted, and rejecting unknown values with HTTP `400`.

#### Scenario: Creating a share link without specifying `visibility_scope` defaults safely to `public_only`

- **GIVEN** an authenticated collector submitting `POST /api/sharing/` with `{"name": "My Sci-Fi"}`
- **WHEN** `visibility_scope` is omitted
- **THEN** the created `SharedCollection` MUST store `filters["visibility_scope"] == "public_only"` and serialize it in `to_dict()`.

#### Scenario: Creating a share link with an invalid `visibility_scope` is rejected

- **GIVEN** an authenticated collector submitting `POST /api/sharing/` with `visibility_scope: "everything_secret"`
- **WHEN** the backend validates the payload
- **THEN** the backend MUST reject the request with HTTP `400`.

### Requirement: Token Scope + Friend Bonus Resolution Across All Share Outputs
All shared collection delivery surfaces (`GET /api/public/share/<token>`, `GET /share/<token>`, `GET /share/<token>/jsonld/<page>`, `GET /api/public/rdf/share/<token>`, and RSS feeds) SHALL resolve visible items using the Token Scope + Friend Bonus model and set `Cache-Control: private, no-store` whenever authenticated friend bonus or non-public scopes (`friends_and_public`, `all`) are served.

#### Scenario: `public_only` share excludes non-public items for anonymous visitors and grants Friend Bonus to authenticated friends

- **GIVEN** User A creates a `SharedCollection` with `visibility_scope="public_only"` over items including `public`, `friends_only`, and `private` copies
- **WHEN** an anonymous visitor or non-friend requests the share link (web, JSON, JSON-LD, or RSS)
- **THEN** only `public` items MUST be returned.
- **WHEN** an accepted friend User B (or User A) requests the share link with valid authentication credentials
- **THEN** both `public` and `friends_only` items MUST be returned (with `private` still excluded), and `Cache-Control` MUST NOT allow shared public caching.

#### Scenario: `friends_and_public` share reveals `friends_only` items to token holders while hiding `private`

- **GIVEN** User A creates a `SharedCollection` with `visibility_scope="friends_and_public"`
- **WHEN** any caller (authenticated or anonymous, including AI fetchers) requests the share link with the valid 256-bit `share_token`
- **THEN** matching `public` and `friends_only` items MUST be included, and `private` items MUST remain excluded.

#### Scenario: `all` share reveals all matching owner items (`public`, `friends_only`, `private`) to token holders

- **GIVEN** User A creates a `SharedCollection` with `visibility_scope="all"`
- **WHEN** any caller requests the share link with the valid 256-bit `share_token`
- **THEN** matching `public`, `friends_only`, and `private` items owned by User A MUST be included across JSON, SSR HTML, JSON-LD/Turtle, and RSS outputs.

### Requirement: Share Creation UI Visibility Scope Selector and Privacy Warning
`ShareCollectionDialog` SHALL let the collector select between `Public only (Recommended)`, `Friends & Public`, and `All items (including Private/Hidden)` via localized controls and SHALL display a clear privacy warning whenever `friends_and_public` or `all` is selected.

#### Scenario: Collector selects `All items` in `ShareCollectionDialog`

- **GIVEN** an authenticated collector opening `ShareCollectionDialog`
- **WHEN** the collector chooses `"All items (including Private/Hidden)"`
- **THEN** the dialog MUST display a warning explaining that anyone holding the generated link (including AI assistants) can read private items, and MUST transmit `visibility_scope: "all"` in `POST /api/sharing/`.

### Requirement: Share Collection Filter Schema Normalization and Persistence

`POST /api/sharing/` (`SharedCollectionCreateSchema`) SHALL accept, validate, and canonicalize media-category filters (`tags` and `category` aliases normalized via `FORMAT_ALIAS_TO_CATEGORY`) and carrier-format filters (`format` / `formats` validated/normalized against `MediaFormat` constants and `FormatNormalizer`) inside `SharedCollection.filters`, rejecting invalid non-empty filter types or unrecognized format values with HTTP `400` and preserving fail-closed empty arrays when explicitly supplied.

#### Scenario: Creating a music and vinyl filtered share persists normalized category and format filters

- **GIVEN** an authenticated collector submitting `POST /api/sharing/` with `{"name": "My Vinyl", "filters": {"tags": ["audio"], "format": ["vinyl"]}}`
- **WHEN** `SharedCollectionCreateSchema` validates the request
- **THEN** the persisted `SharedCollection.filters` MUST store canonicalized `tags: ["music"]` and `format: ["vinyl"]` alongside `visibility_scope`.

#### Scenario: Creating a share link with an invalid carrier format filter is rejected

- **GIVEN** an authenticated collector submitting `POST /api/sharing/` with `{"name": "Bad Share", "filters": {"format": ["nonexistent_carrier"]}}`
- **WHEN** `SharedCollectionCreateSchema` validates the request
- **THEN** the backend MUST reject the request with HTTP `400`.

### Requirement: Share Creation UI Filter Capture for Category and Format

`ShareCollectionDialog` SHALL capture active `"format"` filters alongside `"category"` and `"status"` filters from the collection view, transmit them as `filters.format` in `POST /api/sharing/`, and include active format filters in the localized default share name (`en.json` and `pl.json` using sentence case for Polish).

#### Scenario: Collector creates a share link from a category and format filtered collection

- **GIVEN** an authenticated collector viewing `/collection` with active filters `[{ type: "category", value: "music" }, { type: "format", value: "vinyl" }]`
- **WHEN** the collector opens `ShareCollectionDialog` and submits the share form
- **THEN** the dialog MUST pre-populate a default share name reflecting the active filters and MUST transmit `filters: { visibility_scope: "public_only", tags: ["music"], format: ["vinyl"] }` in `POST /api/sharing/`.
