## ADDED Requirements

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
