---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Backend: API Exposes Publisher Natively

- [x] 1.1 In `_get_physical_item_detail()` (`app/api/items.py`), add `"publisher": manifestation.publisher` to `item_data`
- [x] 1.2 In `get_items()` search path (raw SQL path), add `m.publisher` to the query and `"publisher": row["publisher"]` to the response dict
- [x] 1.3 In `get_items()` ORM path, add `"publisher": manifestation.publisher if manifestation else None` to the response dict
- [x] 1.4 In `get_virtual_items()`, add `"publisher": manifestation.publisher if manifestation else None` where manifestation exists
- [x] 1.5 Verify `_get_physical_item_detail()` returns publisher via `curl /api/items/:id | jq .data.publisher`

## 2. Frontend: Genre/category display fix

- [x] 2.1 Update `ItemTabs` → `DetailsTab` (`item-tabs.tsx`) to also pass `item.work?.meta` to `ExtendedMetadata`
- [x] 2.2 Update `ExtendedMetadata` (`extended-metadata.tsx`) to accept new `workMeta` prop and merge categories from `work.meta.categories` + `work.meta.genres` + `manifestation.meta.categories`, deduplicating
- [x] 2.3 Verify genres appear on item detail pages for items with work-level `genres` or `categories`

## 3. Frontend: Publisher display fix

- [x] 3.1 Update `ItemHeader` (`item-header.tsx`) to read `item.publisher` (new top-level field from API) first, then fall back to `meta["publisher"]` + `meta["label"]` for legacy
- [x] 3.2 Verify publisher displays for book items (column-based) and music items (meta-based) on item detail page

## 4. Backend + Frontend: Collection status faceted navigation fix

- [x] 4.1 In `get_faceted_stats()` (`app/core/data_manager.py`), COALESCE NULL `Item.collection_status` to `"available"` in the GROUP BY query so items without an explicit collection_status contribute to the `"available"` facet bucket instead of being silently dropped
- [x] 4.2 In `get_faceted_stats()`, add `borrowed_count` computation: `SELECT COUNT(Item.id) WHERE lent_to_user_id = :owner_id AND Item.id IN (SELECT id FROM status_subq)`. Include `"borrowed_count"` in the returned dict.
- [x] 4.3 In `FacetStatsResponse` type (`frontend/types/frbr.ts`), add `borrowed_count?: number` field
- [x] 4.4 In `SidebarFilters` (`sidebar-filters.tsx`), remove `disabled` attribute from zero-count collection status facets (line 426, 436). Keep all options clickable regardless of count — zero-result queries are valid faceted-search behavior.
- [x] 4.5 In `SidebarFilters` (`sidebar-filters.tsx`), add "all zero" fallback: if every value in `statusCounts` for collection status keys is 0, hide the `collectionStatuses.map(...)` list and show an informational message instead of a wall of greyed-out checkboxes
- [x] 4.6 In `SidebarFilters` (`sidebar-filters.tsx`), read the "borrowed" count from `facetStatsData.borrowed_count` instead of `statusCounts["borrowed"]`; verify the count and toggle behavior work correctly

> **Note**: Item cards (`item-card.tsx`) remain unchanged. Cards continue to suppress the "available" status badge as the default. This is correct UX: filters represent the complete state space, cards highlight exceptional states only.

## 5. Database: metadata_refetch_log table

- [x] 5.1 Define `MetadataRefetchLog` model in `app/db/` (new file or in `app/db/core.py`) with columns: `id`, `entity_type`, `entity_id`, `strategy`, `checked_at`, `iqoqo_version`, `found_fields` (JSON), `error` (Text). Unique constraint on `(entity_type, entity_id, strategy)`. Place in `inventory` schema on PostgreSQL.
- [x] 5.2 Generate Alembic migration: `flask db migrate -m "add metadata_refetch_log"` and verify it produces correct DDL
- [x] 5.3 Run `flask db upgrade` on dev to create the table
- [x] 5.4 Verify table exists with `psql -c "\d inventory.metadata_refetch_log"`

## 6. Backend: refetch_metadata.py script

- [x] 6.1 Create `scripts/refetch_metadata.py` skeleton with argparse: `--gap` (format|publisher|genres|cover|all), `--content-type` (text|music|movie|board_game|puzzle), `--dry-run`, `--force`, `--limit N`
- [x] 6.2 Implement gap detection queries per entity type: `manifestation.meta->>'format'` IS NULL for format gap; `publisher` IS NULL AND `meta->>'publisher'` IS NULL for publisher gap; `work.meta->>'genres'` IS NULL/empty AND `work.meta->>'categories'` IS NULL/empty for genre gap; `cover_url` IS NULL for cover gap
- [x] 6.3 Implement refetch log check: query `metadata_refetch_log` for `(entity_type, entity_id, strategy)`, skip if current version matches and no `--force`
- [x] 6.4 Define rate-limit config dict with per-strategy delays (tmdb: 0.025s, discogs: 1.0s, bgg: 0.5s, igdb: 0.25s, musicbrainz: 1.0s, google_books: 0.0s)
- [x] 6.5 Implement throttling: `time.sleep(rate_limit[strategy] - elapsed)` between API calls; handle HTTP 429 with `Retry-After` header
- [x] 6.6 Wire up existing strategies (`app/strategies/`) and API clients (`app/utils/tmdb.py`, `app/utils/discogs.py`, `app/utils/bgg.py`, `app/utils/igdb.py`, `app/utils/musicbrainz.py`) to fetch metadata for entities with identifiers (ISBN, UPC, barcode)
- [x] 6.7 Implement metadata update: only set fields that are currently NULL/empty; use `manifestation.update_meta()` for JSON fields; use direct column assignment for `publisher`; commit per batch
- [x] 6.8 Implement log writing: upsert `MetadataRefetchLog` row after each attempt with found_fields or error
- [x] 6.9 Implement `--dry-run` output: table listing entity ID, content_type, gap, strategy, without making API calls
- [x] 6.10 Implement `--limit N` to cap total refetch attempts

## 7. Makefile integration

- [x] 7.1 Add `refetch-metadata` target to `Makefile` that runs `python scripts/refetch_metadata.py $(REFETCH_ARGS)` in the Flask app context
- [x] 7.2 Ensure `.PHONY` includes `refetch-metadata`
- [x] 7.3 Default `REFETCH_ARGS` to `--gap all` when not provided
- [x] 7.4 Verify: `make refetch-metadata --dry-run` runs without errors

## 8. Testing & verification

- [x] 8.1 Backend: add/update unit tests for `_get_physical_item_detail()` to assert `publisher` field in response
- [x] 8.2 Backend: add/update unit tests for `get_items()` both paths to assert `publisher` field
- [x] 8.3 Frontend: verify `ExtendedMetadata` renders genres from work.meta via component test or manual check
- [x] 8.4 Frontend: verify `ItemHeader` renders publisher from column-based items
- [x] 8.5 Frontend: verify `ItemCard` shows "On Shelf" badge for available items
- [x] 8.6 Run `make refetch-metadata --dry-run` against dev DB and verify gap counts match manual DB queries (~1582 format gaps, ~1662 publisher gaps)
- [x] 8.7 Run `make refetch-metadata --dry-run --gap format --content-type movie` and verify only the 1 movie with NULL format is listed
- [x] 8.8 Run `make refetch-metadata --dry-run --limit 5` and verify only 5 entities are listed
