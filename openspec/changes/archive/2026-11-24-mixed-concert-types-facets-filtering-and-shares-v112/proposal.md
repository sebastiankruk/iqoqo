## Why

Collectors frequently own concert releases that span multiple media domains—video concerts on `dvd`/`bluray`/`4k_uhd`/`vcd`/`vhs` (`Expression.content_type = "movie"`, `Expression.kind = "live_performance"`), audio concert albums on `cd`/`vinyl`/`sacd`/`cassette`/`bluray_audio` (`Expression.content_type = "music"`, `Expression.kind = "live_performance"`), and multi-carrier `cd_dvd_combo` sets containing both audio and video discs. Although `concert-modeling` already stores `Expression.kind = "live_performance"` on an indexed column (`catalog.expressions.kind`), faceted navigation (`GET /api/stats/facets`, `SidebarFilters`, `FilterBar`), catalog filtering (`CatalogFilterBuilder`, `GET /api/items`, `SearchService`), and shared collections (`ShareCollectionDialog`, `SharedCollection.filters`, `/api/public/share/<token>`, RDF/JSON-LD/RSS) do not expose `expression_kind` filtering or mixed-carrier (`cd_dvd_combo`) cross-category matching. As a result, collectors cannot browse, filter, or share their concert collections spanning movies + audio without losing half their concerts or polluting pure `music` shares.

## What Changes

- **FRBR-Pure Orthogonal Axes (No `"concert"` Category or Tag Pollution):**
  - Strictly preserve `MediaCategory` (`text`, `audiobook`, `music`, `movie`, `board_game`, `puzzle`, `lego`) and `concert-modeling` rules: concerts remain typed at the FRBR **Expression** tier via `Expression.kind = "live_performance"` (with `NULL` / `"studio"` representing standard realizations), while physical carriers remain on **Manifestation** (`Manifestation.format` / `format_type`).
  - Introduce an explicit `MIXED_MEDIA_FORMAT_CATEGORIES` mapping in `app/core/taxonomy.py` (generated/sourced from `shared/taxonomy.yaml`) for genuine multi-carrier physical manifestations (`cd_dvd_combo -> ("music", "movie")`), while keeping single-carrier formats (`dvd`, `bluray`, `cd`, `vinyl`, `bluray_audio`) single-category so `C141`'s music-share DVD exclusion remains strictly intact.
- **Backend Faceted Navigation & Filtering (`expression_kind` + Mixed-Carrier Support):**
  - Extend `CatalogFilterBuilder` (`app/api/filters.py`) with `_apply_expression_kind(expression_kind: list[str] | None)` supporting `live_performance` (`Expression.kind == "live_performance"`) and `studio` (`Expression.kind.is_(None)`), and extend `_apply_category()` so multi-carrier formats (`cd_dvd_combo`) match when filtering by any of their constituent categories (`music` or `movie`) without leaking single-carrier video discs into `music`.
  - Extend `GET /api/stats/facets` (`app/api/system.py` & `DataManager.get_faceted_stats` in `app/core/data_manager.py`) to accept `expression_kind` (CSV, OR-within / AND-across facets, normalized in `FACETS_CACHE_PREFIX` keys) and return cross-filtered `expression_kinds` counts (`live_performance`, `studio`) alongside `categories` and `formats` (crediting multi-carrier `cd_dvd_combo` in both `music` and `movie` category facets when applicable).
  - Wire `expression_kind` through `GET /api/items` (`app/api/items.py`), `GET /api/manifestations` (`app/api/manifestations.py`), `SearchService.search_items()` / `ItemSearchFilters` (`app/core/search_service.py` — both PostgreSQL FTS and SQLite `ILIKE` paths prior to SQL `LIMIT`), and OpenAPI 3.1 docs (`app/api/docs.py`).
- **Shared Collections & Public Delivery Surfaces (`expression_kind` + Multi-Category Concert Shares):**
  - Extend `_resolve_share_filter_specs()`, `_apply_share_item_filters()`, and wishlist `UserWorkIntent` filtering (`app/api/public_items.py`, `app/api/sharing.py`, `app/api/public_rdf.py`, `app/api/schemas.py`) to accept and persist `filters["expression_kind"]` (e.g., `["live_performance"]`, with fail-closed behavior on `expression_kind: []`) across JSON, JSON-LD, RDF/Turtle, and RSS feeds.
  - Ensure `SharedCollection` with `expression_kind: ["live_performance"]` (alone or combined with `category: ["music", "movie"]`) includes both audio and video concerts while excluding studio releases, and allow `cd_dvd_combo` in `movie`-filtered shares via `MIXED_MEDIA_FORMAT_CATEGORIES` while preserving `C141`'s exclusion of single-carrier movie `dvd`s from `music` shares.
- **Frontend Faceted Navigation, URL Sync & Share Dialog:**
  - Add a **Performance / Realization** (`expression_kind`: `Live performance (Concert)` / `Studio`) facet section to `SidebarFilters`, chip label support in `FilterBar`, URL query sync (`expression_kind=...`) on `/collection`, and `filtersPayload.expression_kind` serialization + smart default share naming in `ShareCollectionDialog`, localized in `en.json` and sentence-case `pl.json`.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `concert-modeling`: Expand `Facets distinguish live performances from studio releases` to specify the `expression_kind` facet/filter contract (`live_performance` vs `studio`) across `/api/stats/facets`, `CatalogFilterBuilder`, `/api/items`, `SearchService`, frontend `SidebarFilters`/`FilterBar`, and mixed-carrier (`cd_dvd_combo`) cross-category classification without violating FRBR tier boundaries.
- `shared-collection-type-integrity`: Add support for `expression_kind` filtering, multi-category concert shares (`music` + `movie`), and `cd_dvd_combo` mixed-carrier inclusion across JSON, JSON-LD, RDF/Turtle, RSS, and Wishlist `UserWorkIntent` share queries while preserving strict single-carrier `FORMAT_TO_CATEGORY` guards.

## Impact

- **Backend Taxonomy, Filters, Facets & Search:** `shared/taxonomy.yaml`, `scripts/generate_taxonomy.py`, `app/core/taxonomy.py`, `app/api/filters.py`, `app/core/data_manager.py`, `app/api/system.py`, `app/api/items.py`, `app/api/manifestations.py`, `app/core/search_service.py`, `app/api/public_items.py`, `app/api/sharing.py`, `app/api/schemas.py`, `app/api/docs.py`.
- **Frontend UI & Localization:** `frontend/types/frbr.ts`, `frontend/app/collection/page.tsx`, `frontend/components/collection/sidebar-filters.tsx`, `frontend/components/collection/filter-bar.tsx`, `frontend/components/collection/share-collection-dialog.tsx`, `frontend/lib/api/hooks/catalog.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests:** Backend `pytest` (`tests/test_api_facets.py`, `tests/test_api_public_extended.py`, `tests/test_search.py`, `tests/test_expression_kind.py`, `tests/test_ontology.py`, `tests/test_openapi_contract_completeness.py`); frontend `Vitest` (`sidebar-filters.test.tsx`, `active-filter-strip.test.tsx`, `share-collection-dialog.test.tsx`); Playwright E2E concert facet/share flow.
- **Database Schema Impact:** Zero Alembic migrations required (`catalog.expressions.kind` is already an indexed `VARCHAR(50)` column in `app/db/core.py:387`).
