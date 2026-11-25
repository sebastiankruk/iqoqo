# concert-modeling Specification

## Purpose
Define performance event expressions and concert audio/video recording metadata modeling.

## Requirements

### Requirement: Expression kind settable through UI and escalation

A concert Expression's `kind` (e.g. `live_performance`) SHALL be settable and correctable through the FRBR editor UI by admins, and requestable through the escalation system by non-admin users. The concert identification SHALL NOT depend solely on ingestion-time auto-detection — manual correction SHALL be available through the same operational paths used for other expression metadata.

#### Scenario: Admin corrects misclassified expression kind via UI

- **WHEN** an admin discovers an Expression that should be a concert (or should no longer be a concert)
- **THEN** the admin SHALL be able to open the FRBR editor, change the `kind` dropdown, and save — without needing to delete and re-ingest the record

#### Scenario: Non-admin requests kind correction via escalation

- **WHEN** a non-admin user discovers an Expression with an incorrect `kind` value
- **THEN** the user SHALL be able to submit a correction request through the escalation system, and a Custodian SHALL be able to approve and apply the change

### Requirement: Concerts are modeled as Performance Event Expressions

A concert release SHALL be modeled as an `Expression` of a musical or audiovisual `Work` with a performance-kind marker (e.g. `expression.kind = 'live_performance'`), linked to Performance Event contribution data (performers, and where available venue/date), and realized in a `Manifestation` carrying the physical carrier format (CD, DVD, or BluRay). Concert identity SHALL NOT be encoded as a genre tag, a format value, or an item-level flag.

#### Scenario: Concert BluRay is a performance expression with a video manifestation

- **WHEN** a live concert recording is cataloged on BluRay
- **THEN** the graph SHALL contain a Work linked to an Expression marked as a live performance, linked to a Manifestation categorized `movie` (or `music` for audio-only carriers) with format `bluray`

#### Scenario: Concert is never flattened into tags

- **WHEN** any concert release is ingested or edited
- **THEN** no genre/tag field and no physical `Item` attribute SHALL be used as the sole indicator that the release is a concert

### Requirement: Facets distinguish live performances from studio releases

Faceted navigation and search filters SHALL distinguish live performance Expressions (`Expression.kind = "live_performance"`) from studio/default releases (`Expression.kind IS NULL`), deriving the distinction strictly from the Expression-level performance marker (`catalog.expressions.kind`) rather than genre tags, format overrides, or item flags. Facet endpoints (`GET /api/stats/facets`), catalog listing endpoints (`GET /api/items`, `GET /api/manifestations`), and search backends (`SearchService` PostgreSQL FTS and SQLite `ILIKE`) SHALL accept a comma-separated `expression_kind` filter parameter (`live_performance`, `studio`) combined with OR within the facet and AND across facets, SHALL expose cross-filtered `expression_kinds` counts in facet payloads (keyed into normalized facet cache keys), and SHALL support mixed-media concert workflows spanning both `music` and `movie` categories—including recognizing genuine multi-carrier manifestations (`cd_dvd_combo`) under both `music` and `movie` category filters while continuing to restrict single-carrier video formats (`dvd`, `bluray`, `4k_uhd`, `vcd`, `vhs`) to `movie` and single-carrier audio formats (`cd`, `vinyl`, `sacd`, `cassette`, `bluray_audio`) to `music`.

#### Scenario: Facet separates studio album from live concert recording

- **WHEN** a catalog contains both a studio album Expression (`kind = NULL`) and a live performance Expression (`kind = "live_performance"`) of the same musical Work
- **THEN** `GET /api/stats/facets` returns distinct `expression_kinds` counts for `studio` and `live_performance`
- **AND** filtering with `expression_kind=live_performance` returns only the live concert recording while `expression_kind=studio` returns only the studio album

#### Scenario: Filtering by live_performance spans both movie and audio concerts

- **WHEN** a library contains a live concert Blu-ray (`content_type = "movie"`, `kind = "live_performance"`, `format = "bluray"`), a live concert CD (`content_type = "music"`, `kind = "live_performance"`, `format = "cd"`), a studio album CD (`content_type = "music"`, `kind = NULL`), and a feature film Blu-ray (`content_type = "movie"`, `kind = NULL`)
- **THEN** querying `/api/items?expression_kind=live_performance` (or `/api/items?category=music,movie&expression_kind=live_performance`) returns both the concert Blu-ray and the concert CD while excluding the studio album and feature film
- **AND** cross-filtered `categories` counts reflect both `movie` and `music` concerts

#### Scenario: Multi-carrier cd_dvd_combo matches both music and movie category filters without leaking plain DVDs into music

- **WHEN** a library contains a `cd_dvd_combo` concert release (`content_type = "music"`, `kind = "live_performance"`, `format = "cd_dvd_combo"`) and a movie `dvd` (`content_type = "movie"`, `kind = NULL`, `format = "dvd"`)
- **THEN** filtering by `category=music` includes the `cd_dvd_combo` and excludes the movie `dvd`
- **AND** filtering by `category=movie` includes both the movie `dvd` and the multi-carrier `cd_dvd_combo`

### Requirement: Performance metadata is exposed on entity payloads

API payloads for Expressions and Manifestations representing concerts SHALL include the performance contribution data (performers, and venue/date when present) sourced from the Performance Event contribution entities.

#### Scenario: Concert manifestation payload includes performers

- **WHEN** a client fetches the detail payload of a concert manifestation
- **THEN** the response SHALL include the performance contributors recorded for its Expression

### Requirement: End-to-End Mixed-Media Manifestation FTS, Work Facet Deduplication, and Offline Concert Filtering Parity

Mixed-media carriers (`MIXED_MEDIA_FORMAT_CATEGORIES`, e.g., `cd_dvd_combo -> ("music", "movie")`) and `expression_kind` (`live_performance` / `studio`) filtering SHALL behave identically across PostgreSQL manifestation full-text search, `Work`-scoped facet aggregation, and Capacitor/offline client-side collection filtering:

1. **PostgreSQL Manifestation FTS Mixed-Media Category Matching (`app/core/search_service.py`):** `_pg_manifestation_fts()` MUST expand single-category filters using the same `MIXED_MEDIA_FORMAT_CATEGORIES` (`LOWER(TRIM(COALESCE(m.format, ''))) IN (...)`) `OR` predicate used by `_pg_item_fts()` and SQLite search so querying manifestations with `q=...&category=movie` matches `cd_dvd_combo` concert editions whose primary `Expression.content_type` is `"music"`.
2. **Multi-Expression Work Facet Deduplication (`app/core/data_manager.py`):** When `DataManager.get_faceted_stats(..., target_entity="works")` merges secondary mixed-media categories (`MIXED_MEDIA_FORMAT_CATEGORIES`), it MUST exclude `Work.id` values already counted under that category in the primary `Expression.content_type` aggregate so a `Work` possessing both a `"movie"` Expression and a `"music"` `cd_dvd_combo` Manifestation is counted at most once under `"movie"`.
3. **Capacitor Offline Collection Filtering Parity (`frontend/app/collection/page.tsx`):** When `/collection` evaluates `filteredItems` in `effectiveOffline` mode, it MUST filter cached items by `expressionKindFilters` (treating `null`/missing `expression_kind` as `"studio"`) and MUST match `cd_dvd_combo` items under both `"music"` and `"movie"` `categoryFilters`.

#### Scenario: PostgreSQL manifestation FTS matches cd_dvd_combo under movie category filter

- **GIVEN** a `Manifestation` with `format = "cd_dvd_combo"` linked to an `Expression` with `content_type = "music"` and `kind = "live_performance"`
- **WHEN** `SearchService.search_manifestations(query=..., category="movie")` executes on PostgreSQL (and SQLite)
- **THEN** the `cd_dvd_combo` manifestation is included in the returned results alongside `content_type = "movie"` manifestations

#### Scenario: Work-scoped category facets do not double-count multi-expression Works with cd_dvd_combo

- **GIVEN** a single `Work` that has both an Expression with `content_type = "movie"` (`format = "bluray"`) and an Expression with `content_type = "music"` (`format = "cd_dvd_combo"`)
- **WHEN** `GET /api/stats/facets?entity=works` computes `categories` counts
- **THEN** that `Work` contributes `1` to `categories["movie"]` and `1` to `categories["music"]` (never `2` to `categories["movie"]`)

#### Scenario: Offline collection mode filters cached items by expression_kind and cd_dvd_combo

- **GIVEN** `/collection` operating in `effectiveOffline` mode with cached items containing a studio CD (`expression_kind: null`, `format: "cd"`, `category: "music"`), a live concert Blu-ray (`expression_kind: "live_performance"`, `format: "bluray"`, `category: "movie"`), and a live `cd_dvd_combo` (`expression_kind: "live_performance"`, `format: "cd_dvd_combo"`, `category: "music"`)
- **WHEN** the user activates `expression_kind=live_performance` and `category=movie`
- **THEN** both the live concert Blu-ray and the live `cd_dvd_combo` remain visible while the studio CD is excluded
