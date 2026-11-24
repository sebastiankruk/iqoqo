## Context

See `proposal.md` for motivation. Under iqoqo's FRBR/FRBRoo ontology (`docs/ontology/iqoqo.ttl`, `openspec/specs/concert-modeling/spec.md`, `app/db/core.py:74-86, 387`):
- **Work (`F1_Work`)** represents the creative concert/musical work.
- **Expression (`F2_Expression` / `F31_Performance`)** holds two orthogonal attributes:
  - `Expression.content_type` (`"music"` vs `"movie"`, etc.) — primary medium domain.
  - `Expression.kind` (`"live_performance"` vs `NULL` studio/default) — already an indexed `VARCHAR(50)` column (`catalog.expressions.kind`).
- **Manifestation (`F3_Manifestation_Product_Type`)** holds the physical carrier (`cd`, `vinyl`, `bluray_audio`, `cd_dvd_combo`, `dvd`, `bluray`, `4k_uhd`, `vcd`, `vhs`).
- **Item (`F5_Item`)** holds ownership, visibility, shelf status, and loans.

Currently, `CatalogFilterBuilder` (`app/api/filters.py`), `DataManager.get_faceted_stats` (`app/core/data_manager.py`), `ItemSearchFilters` (`app/core/search_service.py`), `_resolve_share_filter_specs` (`app/api/public_items.py`), `SidebarFilters`, `FilterBar`, and `ShareCollectionDialog` have no `expression_kind` axis, and `FORMAT_TO_CATEGORY` maps every format to exactly one category (so `cd_dvd_combo` maps only to `"music"` and is invisible under `category=movie`).

## Goals / Non-Goals

**Goals:**
- Preserve strict FRBR four-tier purity: never add `"concert"` to `MediaCategory`, never encode concert identity as a tag or item flag, and never weaken `C141`'s guard against single-carrier `dvd`s leaking into pure `music` shares.
- Expose `expression_kind` (`live_performance` | `studio`) end-to-end across faceted navigation, catalog listing, PostgreSQL FTS + SQLite `ILIKE` search, `SharedCollection` delivery surfaces (JSON, JSON-LD, RDF/Turtle, RSS, Wishlist `UserWorkIntent`), and frontend URL/dialog state.
- Support genuine multi-carrier manifestations (`cd_dvd_combo`) across both `"music"` and `"movie"` categories via an ontology-derived `MIXED_MEDIA_FORMAT_CATEGORIES` map.
- Require zero Alembic migrations (leveraging existing indexed `catalog.expressions.kind`).

**Non-Goals:**
- Introducing new `EXPRESSION_KINDS` beyond `live_performance` (e.g., `remix`, `directors_cut`), though the SQL/API plumbing MUST stay vocabulary-driven so future kinds work automatically.
- Auto-reclassifying legacy mis-tagged concert rows (manual/custodian editing already exists via `concert-kind-ui`).

## Decisions

### 1. Orthogonal `expression_kind` Axis Rather Than a `"concert"` `MediaCategory`
- **Decision:** Keep `MediaCategory` strictly as the 7 media domains (`text`, `audiobook`, `music`, `movie`, `board_game`, `puzzle`, `lego`) and expose `expression_kind` (`live_performance` vs `studio`) as a first-class facet and filter parameter.
- **SQL Semantics:**
  - `live_performance` → `Expression.kind == "live_performance"`
  - `studio` → `Expression.kind.is_(None)`
  - Multiple values (`expression_kind=live_performance,studio`) → OR-within (`or_(Expression.kind == "live_performance", Expression.kind.is_(None))`), matching `advanced-facets-filtering`.
  - Unknown/unrecognized values → fail-closed (`sa.false()` on shares; empty result on `/api/items`) after validating against `(*EXPRESSION_KINDS, "studio")`.
- **Alternatives Considered:**
  - *Alternative A — Add `"concert"` to `MediaCategory`:* Rejected by `/ontologist-expert` because a concert is a Performance Event realization (`F31_Performance`), not a mutually exclusive top-level medium; a concert CD is still `music` and a concert Blu-ray is still `movie`.
  - *Alternative B — Filter concerts by genre/tag `"concert"`:* Explicitly prohibited by `concert-modeling` spec (`Concert is never flattened into tags`).

### 2. Multi-Carrier `MIXED_MEDIA_FORMAT_CATEGORIES` Mapping
- **Decision:** Define `MIXED_MEDIA_FORMAT_CATEGORIES: dict[str, tuple[str, ...]]` in `shared/taxonomy.yaml` → `scripts/generate_taxonomy.py` → `app/core/taxonomy.py`, starting with `"cd_dvd_combo": ("music", "movie")`.
  - Primary category in `FORMAT_TO_CATEGORY["cd_dvd_combo"]` remains `"music"` for single-value displays and backwards compatibility.
  - Helper `format_matches_categories(fmt, allowed_cats)` checks `any(c in allowed_cats for c in MIXED_MEDIA_FORMAT_CATEGORIES.get(fmt, (FORMAT_TO_CATEGORY[fmt],)))`.
  - In `_resolve_share_filter_specs()`: `excluded_formats` excludes a format `fmt` only when **none** of its categories (primary or mixed-media) is in `allowed_cats`. Thus `cd_dvd_combo` is NOT excluded when `allowed_cats == {"movie"}` or `{"music"}`, while single-carrier `dvd` IS still excluded when `allowed_cats == {"music"}`!
  - In `CatalogFilterBuilder._apply_category(category)`: match `Expression.content_type.in_(category)` OR `Manifestation` format in the set of mixed-media formats whose secondary categories intersect `category` (e.g. `cd_dvd_combo` when `"movie"` is selected).
  - In `DataManager.get_faceted_stats`: count `cd_dvd_combo` under both `"music"` and `"movie"` in `categories` counts (distinct entity IDs per bucket) while keeping `total` distinct.
- **Alternatives Considered:**
  - *Alternative A — Allow all `live_performance` DVDs into `category=music` shares:* Rejected because a pure DVD-Video disc has no audio-only CD/Vinyl carrier and directly contradicts `C141` (`shared-collection-type-integrity` Scenario: *"Music-filtered share excludes movie DVDs"*). Collectors wanting both audio and video concerts filter/share by `expression_kind=live_performance` (or `category=music,movie` + `expression_kind=live_performance`).

### 3. Shared Query Parity Across PostgreSQL FTS, SQLite `ILIKE`, Facets Cache & Wishlist
- **Decision:**
  - Add `expression_kind: tuple[str, ...] | list[str] | None = None` to `ItemSearchFilters` (`app/core/search_service.py`) and apply `e.kind` predicates inside both `_pg_item_fts` (pre-`LIMIT`) and `_ilike_item_search`.
  - Add `expression_kind` to `DataManager.get_faceted_stats` normalized cache key (`FACETS_CACHE_PREFIX`, bumping version suffix if needed or including sorted `expression_kind` tuple) and compute `expression_kinds` facet via `GROUP BY func.coalesce(Expression.kind, "studio")`.
  - Apply `expression_kind` to `UserWorkIntent` subqueries in `app/api/public_items.py` (binding to `intent.expression_id` when set, otherwise any `Expression` of `intent.work_id`).

### 4. Frontend Faceted Navigation & Share Dialog UX
- **Decision:**
  - Add `"expression_kind"` to `ActiveFilter["type"]` (`frontend/components/collection/filter-bar.tsx`) and `FacetStatsResponse` (`frontend/types/frbr.ts`).
  - Render a compact collapsible **Performance / Kind** section in `SidebarFilters` showing `Live performance (Concert)` and `Studio / Standard` with cross-filtered counts (only rendering when counts exist or filter is active, avoiding visual clutter).
  - Sync `expression_kind` to URL query params on `/collection` and serialize `filtersPayload.expression_kind` in `ShareCollectionDialog` (with smart default share title, e.g., `"Live Performances"` / `"Koncerty na żywo"` when `expression_kind === ["live_performance"]`).

## Risks / Trade-offs

- **[Facet cache key collision across requests with vs without `expression_kind`]** → Mitigated by including sorted `expression_kind` in `DataManager.get_faceted_stats` cache key normalization and testing cache isolation in `tests/test_facets_cache.py` / `tests/test_api_facets.py`.
- **[Category facet count sum exceeding total when `cd_dvd_combo` appears in both `music` and `movie`]** → Expected and standard for multi-valued facets (just like multi-tag items); `total` remains `COUNT(DISTINCT entity_id)`.
- **[`shared/taxonomy.yaml` codegen drift]** → Mitigated by updating `shared/taxonomy.yaml` and regenerating `app/core/taxonomy.py` via `scripts/generate_taxonomy.py` + asserting completeness in `tests/test_ontology.py`.
