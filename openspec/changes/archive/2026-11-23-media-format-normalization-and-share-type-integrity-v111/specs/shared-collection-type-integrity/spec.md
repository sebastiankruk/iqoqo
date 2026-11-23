## Purpose

Enforce strict FRBR media-category and physical carrier-format integrity across shared collection queries, search backends, wishlist projections, and public serialization surfaces so non-matching items cannot leak into filtered shares.

## ADDED Requirements

### Requirement: Unified Media-Category and Format Filtering Across All Share Delivery Surfaces

All shared collection delivery surfaces (`GET /api/public/share/<token>`, `GET /share/<token>`, `GET /share/<token>/jsonld/<page>`, `GET /api/public/rdf/share/<token>`, and RSS feeds) SHALL evaluate `SharedCollection.filters` through a single shared query resolution pipeline that normalizes category filters (`tags` and `category` via `FORMAT_ALIAS_TO_CATEGORY`), evaluates carrier format filters (`format` via `expand_format_filter`) across `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']`, enforces fail-closed semantics on empty filter arrays (`tags: []`, `category: []`, `format: []`), maintains parity across PostgreSQL full-text search (`SearchService.search_items`) and SQLite `ILIKE` filtering (`CatalogFilterBuilder`), and preserves `visibility_scope` plus `Cache-Control: private, no-store` response headers for non-public scopes and Friend Bonus views.

#### Scenario: Music-filtered share excludes movie DVDs across JSON, RDF, JSON-LD, and RSS

- **GIVEN** User A owns a public music `cd`, a public music `vinyl`, a public music `cd_dvd_combo`, and a public movie `dvd`, and creates a `SharedCollection` with `filters={"tags": ["music"]}`
- **WHEN** any caller fetches `GET /api/public/share/<token>`, `GET /api/public/share/<token>?format=jsonld`, `GET /api/public/rdf/share/<token>?format=turtle`, or `GET /api/public/share/<token>/feed.xml`
- **THEN** the response MUST include the music `cd`, `vinyl`, and `cd_dvd_combo` items and MUST exclude the movie `dvd`.

#### Scenario: Format-filtered share narrows results across relational and JSONB format columns

- **GIVEN** User A owns a music `cd` stored in `Manifestation.format`, a music `vinyl` stored only in `Manifestation.meta['format']`, and a music `cassette` stored in `Manifestation.format_type`
- **WHEN** a `SharedCollection` with `filters={"tags": ["music"], "format": ["vinyl"]}` is queried (with or without `filters["query"]` under PostgreSQL FTS or SQLite `ILIKE`)
- **THEN** only the `vinyl` item MUST be returned.

#### Scenario: Category filter accepts category aliases and `category` key

- **GIVEN** User A creates a `SharedCollection` with `filters={"category": ["audio"]}` or `filters={"tags": "sound"}`
- **WHEN** shared items are resolved
- **THEN** the filter SHALL normalize `"audio"` and `"sound"` to `"music"` via `FORMAT_ALIAS_TO_CATEGORY` and return matching music items while excluding non-music items.

#### Scenario: Empty filter array fails closed instead of exposing the entire library

- **GIVEN** a `SharedCollection` stores `filters={"tags": []}` or `filters={"format": []}`
- **WHEN** any share delivery surface evaluates the collection
- **THEN** zero items MUST be returned (it MUST NOT drop the predicate and return the owner's unfiltered catalog).

#### Scenario: Non-public `visibility_scope` and Friend Bonus headers remain enforced alongside type filters

- **GIVEN** User A creates a `SharedCollection` with `filters={"tags": ["music"], "visibility_scope": "friends_and_public"}` covering a `friends_only` music `vinyl` and a `friends_only` movie `dvd`
- **WHEN** a token holder requests `GET /api/public/share/<token>`
- **THEN** the `friends_only` music `vinyl` MUST be returned, the `friends_only` movie `dvd` MUST be excluded, and the response MUST carry `Cache-Control: private, no-store`.

### Requirement: FRBR Cross-Tier Carrier Consistency Guard in Shared Collections

When a `SharedCollection` filters by a `MediaCategory` (such as `"music"`), the query pipeline SHALL enforce FRBR consistency between `Expression.content_type` and the resolved `Manifestation` carrier format (`Manifestation.format`, `Manifestation.format_type`, `Manifestation.meta['format']`) using `FORMAT_TO_CATEGORY`, excluding any item whose non-null canonical carrier format maps to a different `MediaCategory` even when `Expression.content_type` has drifted.

#### Scenario: Mis-classified Expression with movie DVD carrier is excluded from a music share

- **GIVEN** an owned `Item` whose `Expression.content_type` is `"music"` but whose `Manifestation.format` (or `Manifestation.format_type` or `Manifestation.meta['format']`) is `"dvd"` (`FORMAT_TO_CATEGORY["dvd"] == "movie"`)
- **WHEN** a `SharedCollection` filtered to `tags: ["music"]` is queried across JSON, JSON-LD, RDF, or RSS
- **THEN** the mis-classified `dvd` item MUST be excluded.

#### Scenario: Valid music carriers including cd_dvd_combo, bluray_audio, and unknown_audio are retained

- **GIVEN** owned `Item`s under `Expression.content_type == "music"` with formats `"cd_dvd_combo"`, `"bluray_audio"`, and `"unknown_audio"`
- **WHEN** a `SharedCollection` filtered to `tags: ["music"]` is queried
- **THEN** all three items MUST be included because `FORMAT_TO_CATEGORY` maps each of those formats to `"music"`.

### Requirement: UserWorkIntent Wishlist Media-Type and Format Filtering Parity

When `SharedCollection.filters["status"]` includes `"wish_list"` or intent-level statuses (`want_to_read`, `want_to_listen`, `want_to_watch`, `want_to_play`, `want_to_build`), the share query pipeline SHALL apply the same normalized category (`tags`/`category`), carrier format (`format`), `FORMAT_TO_CATEGORY` consistency guard, and `query` filters to `UserWorkIntent` entries—resolving target realization metadata via `intent.expression` and `intent.manifestation` when bound (falling back to the parent `Work`'s expressions/manifestations when unbound)—and SHALL serialize `content_type` and `format` on returned wishlist items across JSON and JSON-LD/RDF projections.

#### Scenario: Music wishlist share excludes movie DVD and audiobook intents

- **GIVEN** User A has non-hidden `UserWorkIntent` records for a music `Work` (`want_to_listen`, `vinyl`), a movie DVD `Work` (`want_to_watch`, `dvd`), and an audiobook `Work` (`want_to_listen`, `audiobook_cd`)
- **WHEN** a `SharedCollection` with `filters={"status": ["wish_list"], "tags": ["music"]}` is requested
- **THEN** only the music `Work` intent MUST be returned, with top-level `content_type: "music"` and `format: "vinyl"`, while the movie DVD and audiobook intents MUST be excluded.

#### Scenario: Intent bound to a specific Manifestation filters by that Manifestation's format

- **GIVEN** a `Work` with both a `cd` manifestation and a `vinyl` manifestation, and a `UserWorkIntent` bound via `intent.manifestation_id` to the `vinyl` manifestation
- **WHEN** a `SharedCollection` with `filters={"status": ["want_to_listen"], "tags": ["music"], "format": ["cd"]}` is requested
- **THEN** that `vinyl`-bound `UserWorkIntent` MUST be excluded (and included only when `"vinyl"` matches `format`).
