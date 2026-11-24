# shared-collection-type-integrity Specification

## Purpose
Enforce strict FRBR media-category and physical carrier-format integrity across shared collection queries, search backends, wishlist projections, and public serialization surfaces so non-matching items cannot leak into filtered shares.

## Requirements

### Requirement: Unified Media-Category and Format Filtering Across All Share Delivery Surfaces

All shared collection delivery surfaces (`GET /api/public/share/<token>`, `GET /share/<token>`, `GET /share/<token>/jsonld/<page>`, `GET /api/public/rdf/share/<token>`, and RSS feeds) SHALL evaluate `SharedCollection.filters` through a single shared query resolution pipeline that normalizes category filters (`tags` and `category` via `FORMAT_ALIAS_TO_CATEGORY`), evaluates carrier format filters (`format` via `expand_format_filter`) across `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']`, pushes both positive format lists and `excluded_formats` into PostgreSQL full-text search (`SearchService.search_items` / `search_manifestations`) and SQLite `ILIKE` filtering (`CatalogFilterBuilder`) prior to applying SQL `LIMIT`, enforces fail-closed semantics on empty filter arrays (`tags: []`, `category: []`, `format: []`), and preserves `visibility_scope` plus `Cache-Control: private, no-store` response headers for non-public scopes and Friend Bonus views.

#### Scenario: Music-filtered share excludes movie DVDs across JSON, RDF, JSON-LD, and RSS

- **GIVEN** User A owns a public music `cd`, a public music `vinyl`, a public music `cd_dvd_combo`, and a public movie `dvd`, and creates a `SharedCollection` with `filters={"tags": ["music"]}`
- **WHEN** any caller fetches `GET /api/public/share/<token>`, `GET /api/public/share/<token>?format=jsonld`, `GET /api/public/rdf/share/<token>?format=turtle`, or `GET /api/public/share/<token>/feed.xml`
- **THEN** the response MUST include the music `cd`, `vinyl`, and `cd_dvd_combo` items and MUST exclude the movie `dvd`.

#### Scenario: Format-filtered share narrows results across relational and JSONB format columns

- **GIVEN** User A owns a music `cd` stored in `Manifestation.format`, a music `vinyl` stored only in `Manifestation.meta['format']`, and a music `cassette` stored in `Manifestation.format_type`
- **WHEN** a `SharedCollection` with `filters={"tags": ["music"], "format": ["vinyl"]}` is queried (with or without `filters["query"]` under PostgreSQL FTS or SQLite `ILIKE`)
- **THEN** only the `vinyl` item MUST be returned.

#### Scenario: FTS share query applies excluded_formats before SQL LIMIT

- **GIVEN** a `SharedCollection` with `filters={"tags": ["movie"], "query": "Live"}` where the catalog contains 500 music items matching `"Live"` and 5 movie items matching `"Live"`
- **WHEN** the share query resolves FTS matches
- **THEN** `excluded_formats` MUST be applied inside the search query prior to the `LIMIT 500` ceiling so the 5 matching movie items are not crowded out by excluded-format hits.

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

When `SharedCollection.filters["status"]` includes `"wish_list"` or intent-level statuses (`want_to_read`, `want_to_listen`, `want_to_watch`, `want_to_play`, `want_to_build`), the share query pipeline SHALL apply the same normalized category (`tags`/`category`), carrier format (`format` including `include_null_fmt` support), `excluded_formats` (`FORMAT_TO_CATEGORY` consistency guard), and `query` filters to `UserWorkIntent` entries—constraining the `Expression`/`Manifestation` correlation strictly to `UserWorkIntent.expression_id` and `UserWorkIntent.manifestation_id` when bound (falling back to any expression/manifestation of the parent `Work` only when unbound), preserving conceptual F1/F2 `UserWorkIntent` entries whose `Work`/bound `Expression` has zero `Manifestation` rows when no explicit non-null `format` filter is active (or when `include_null_fmt` is true), and SHALL serialize `content_type` and `format` on returned wishlist items across JSON and JSON-LD/RDF projections.

#### Scenario: Music wishlist share excludes movie DVD and audiobook intents

- **GIVEN** User A has non-hidden `UserWorkIntent` records for a music `Work` (`want_to_listen`, `vinyl`), a movie DVD `Work` (`want_to_watch`, `dvd`), and an audiobook `Work` (`want_to_listen`, `audiobook_cd`)
- **WHEN** a `SharedCollection` with `filters={"status": ["wish_list"], "tags": ["music"]}` is requested
- **THEN** only the music `Work` intent MUST be returned, with top-level `content_type: "music"` and `format: "vinyl"`, while the movie DVD and audiobook intents MUST be excluded.

#### Scenario: Intent bound to a specific Manifestation filters by that Manifestation's format

- **GIVEN** a `Work` with both a `cd` manifestation and a `vinyl` manifestation (or a movie `dvd` manifestation and a music `cd` manifestation), and a `UserWorkIntent` bound via `intent.manifestation_id` to the `vinyl` (or `dvd`) manifestation
- **WHEN** a `SharedCollection` with `filters={"status": ["want_to_listen"], "tags": ["music"], "format": ["cd"]}` is requested
- **THEN** that `vinyl`-bound (or `dvd`-bound) `UserWorkIntent` MUST be excluded by the SQL `sa.exists` predicate (and included only when the bound manifestation itself satisfies `tags`, `format`, `include_null_fmt`, and `excluded_formats`).

#### Scenario: Category-filtered wishlist share preserves unmanifested conceptual Work intents

- **GIVEN** User A has a non-hidden `UserWorkIntent` (`status="want_to_listen"`, `manifestation_id=None`) for a music `Work` that has an `Expression(content_type="music")` but zero `Manifestation` rows in the catalog
- **WHEN** a `SharedCollection` with `filters={"status": ["want_to_listen"], "tags": ["music"]}` (or `filters={"status": ["want_to_listen"], "tags": ["music"], "format": ["unknown_audio"]}`) is requested
- **THEN** the unmanifested music `UserWorkIntent` MUST be included in the response rather than dropped by the `excluded_formats` manifestation subquery.

### Requirement: Expression-Kind and Mixed-Media Concert Filtering in Shared Collections

All shared collection delivery surfaces (`GET /api/public/share/<token>`, `GET /share/<token>`, `GET /share/<token>/jsonld/<page>`, `GET /api/public/rdf/share/<token>`, RSS feeds, and wishlist `UserWorkIntent` projections) SHALL support `SharedCollection.filters["expression_kind"]` (`"live_performance"`, `"studio"`) alongside `tags`/`category`, `format`, `status`, and `query`. Empty `expression_kind: []` arrays MUST fail closed (returning zero items). When `filters["expression_kind"]` includes `"live_performance"` without a single-category restriction (or with `category`/`tags` spanning both `"music"` and `"movie"`), shared collections SHALL return both audio (`cd`, `vinyl`, `cd_dvd_combo`, `bluray_audio`, etc.) and video (`dvd`, `bluray`, `4k_uhd`, `vcd`, `vhs`, etc.) concert releases while excluding studio/non-concert items. Genuine multi-carrier formats (`cd_dvd_combo`) SHALL satisfy both `"music"` and `"movie"` category-filtered shares via `MIXED_MEDIA_FORMAT_CATEGORIES`, while single-carrier video formats (`dvd`, `bluray`, `vcd`, etc.) MUST remain excluded from pure `"music"`-only shares.

#### Scenario: Concert-filtered share includes both movie Blu-ray and audio CD concerts across JSON, JSON-LD, RDF, and RSS

- **GIVEN** User A owns a public live concert Blu-ray (`movie` / `live_performance` / `bluray`), a public live concert CD (`music` / `live_performance` / `cd`), a public studio CD (`music` / `NULL` / `cd`), and a public feature film DVD (`movie` / `NULL` / `dvd`), and creates a `SharedCollection` with `filters={"expression_kind": ["live_performance"]}`
- **WHEN** any caller fetches `/api/public/share/<token>`, `/share/<token>/jsonld/1`, `/api/public/rdf/share/<token>?format=turtle`, or `/api/public/share/<token>/feed.xml`
- **THEN** both the concert Blu-ray and the concert CD MUST be returned, and the studio CD and feature film DVD MUST be excluded

#### Scenario: Combined music+movie live_performance share excludes books and studio releases

- **GIVEN** User A creates a `SharedCollection` with `filters={"tags": ["music", "movie"], "expression_kind": ["live_performance"]}`
- **WHEN** shared items (including PostgreSQL FTS `query` searches and `UserWorkIntent` wishlist entries) are resolved
- **THEN** both audio and video live concerts MUST be included, while books, board games, studio albums, and non-concert movies MUST be excluded

#### Scenario: Empty expression_kind filter fails closed

- **GIVEN** a `SharedCollection` stores `filters={"expression_kind": []}`
- **WHEN** any share delivery surface evaluates the collection
- **THEN** zero items MUST be returned

#### Scenario: Pure music share still excludes single-carrier movie concert DVD while retaining cd_dvd_combo

- **GIVEN** User A owns a `cd_dvd_combo` concert (`music` / `live_performance` / `cd_dvd_combo`) and a single-carrier concert `dvd` (`movie` / `live_performance` / `dvd`), and creates a `SharedCollection` with `filters={"tags": ["music"]}`
- **WHEN** the share is evaluated
- **THEN** the `cd_dvd_combo` MUST be included and the single-carrier `dvd` MUST be excluded (whereas a share with `filters={"tags": ["movie"]}` includes both the `dvd` and the multi-carrier `cd_dvd_combo`)
