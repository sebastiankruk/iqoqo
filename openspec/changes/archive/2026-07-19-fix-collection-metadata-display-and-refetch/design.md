---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

A DB audit of the dev instance surfaced four metadata display issues (detailed in proposal.md). The codebase has no shared serialization layer — each API endpoint constructs dicts inline, and the frontend reads from ad-hoc property paths. The FRBR hierarchy (Work → Expression → Manifestation → Item) means metadata lives at different levels, but the frontend `ExtendedMetadata` component currently only receives `Manifestation.meta`, missing Work-level data entirely.

## Goals / Non-Goals

**Goals:**

- Genres displayed on item detail pages draw from both `work.meta` and `manifestation.meta`, prioritized correctly
- Publishers from the `Manifestation.publisher` column appear on item detail pages and item headers
- All collection statuses (including `"available"`) listed in "collection status" faceted navigation, while listing cards continue silently suppress `"available"` status
- A `make refetch-metadata` pipeline exists that can batch-enrich entities with missing metadata, with version tracking to avoid redundant refetches
- API throttling is respected per external service

**Non-Goals:**

- Refactoring the entire item serialization layer (beyond adding the publisher field)
- Real-time metadata fetching (the refetch pipeline is batch, not automatic on scan)
- Fixing the format/publisher data for existing items (the pipeline enables it, but doesn't auto-run)
- Changing how items without ISBN/barcode are looked up

## Decisions

### D1: Genre/category data source fix

**Decision:** Pass `item.work.meta` to `ExtendedMetadata` alongside `manifestation.meta`. Merge categories from both sources: `work.meta.categories` ∪ `work.meta.genres` ∪ `manifestation.meta.categories`. De-duplicate.

**Rationale:** Categories live on Work (the intellectual creation) while manifestation-level categories come from external APIs (e.g., TMDB sometimes writes genre to manifestation meta). Both are valid. The taxonomy `genres` key is used by the filter pipeline; `categories` is used by the seed data and some external sources. Unifying both maximizes coverage.

**Alternatives considered:**

- Migrate all categories to a single key at a single FRBR level — rejected for this fix scope (data migration risk, potential data loss). Can revisit in a follow-up.
- Pass only `work.meta` — would lose the 16 manifestation-level categories that currently display.

### D2: Publisher display fix

**Decision:** In `_get_physical_item_detail()` and both `get_items()` serialization paths, add `"publisher": manifestation.publisher` as a top-level field in the item response. On the frontend, `ItemHeader` reads `item.publisher` first, then falls back to `item.manifestation_meta?.publisher` (legacy path for music items where Discogs stores publisher in meta).

**Rationale:** This is the minimal change. The `Item` type already has `publisher?: string` at the top level (frbr.ts:145) — it just isn't populated by the API. Making the API fill it from the dedicated column fixes the gap without changing the frontend data model.

**Alternatives considered:**

- Copy `publisher` into `manifestation.meta` during serialization — rejected because it mutates data on read, which could cause confusing write-backs.
- Migrate existing `meta.publisher` values to the column — rejected because the column and meta serve different purposes (column: publisher/ISBN-level; meta: Discogs label field).

### D3: Collection status in faceted navigation fix

**Decision:** Fix the faceted navigation sidebar so that collection status values display with correct counts and remain interactive. Item cards continue to suppress `"available"` as the default status (no change to card rendering — cards highlight exceptional states; filters need the complete state space).

**Backend fixes** (`app/core/data_manager.py:get_faceted_stats()`):

1. **COALESCE NULL `collection_status` to `"available"`** in the GROUP BY query (line ~611). Items without an explicit `collection_status` currently produce NULL rows that are silently discarded by the `if cs in db_statuses` guard — their counts are lost entirely. After the fix, NULL items contribute to the `"available"` bucket.
2. **Add `borrowed_count` field** to the facet stats response dict. The virtual "borrowed" status is not in `ITEM_STATUSES` (which only contains real DB values), so `status_counts["borrowed"]` is always 0. Compute `borrowed_count` separately as `COUNT(Item.id) WHERE lent_to_user_id = :owner_id AND Item.id IN status_subq`.

**Frontend fixes** (`frontend/components/collection/sidebar-filters.tsx`):

1. **Remove `disabled` from zero-count facets** (lines 426, 436). Keep all facet options clickable regardless of count — selecting a zero-count filter and getting zero results is valid faceted-search behavior.
2. **"All zero" fallback**: If every collection status key in `statusCounts` is 0, hide the faceted list and show an informational message: "Collection status data is not available." This prevents a wall of greyed-out, unclickable checkboxes.
3. **Read `borrowed` from `facetStatsData.borrowed_count`** instead of `statusCounts["borrowed"]`, matching the new API field.

**Frontend types** (`frontend/types/frbr.ts`): Add `borrowed_count?: number` to `FacetStatsResponse`.

**Rationale:** Two independent backend bugs caused the "collection status always empty" symptom: (a) NULL `collection_status` items were dropped entirely from counts, and (b) the virtual "borrowed" status was never counted because it's not in `ITEM_STATUSES`. The frontend's `disabled` attribute on zero-count facets then made the entire section appear broken — seven greyed-out, unclickable rows.

**Alternatives considered:**

- **Backfill NULL collection_status to "available" via migration** — rejected because it doesn't fix the "borrowed" counting bug and introduces data migration risk. COALESCE in the query is zero-risk and fixes both issues correctly for all present and future items.
- **Remove "borrowed" from collection status list entirely** — rejected because users need to discover items they're borrowing. Moving it to a separate toggle (future UX improvement) keeps the feature while fixing the count.
- **Always show collection_status badge on cards** — rejected per user clarification. Cards should continue suppressing the default "available" status. Filters and cards serve different UX purposes: filters represent the complete state space, cards highlight exceptions.

### D4: Metadata refetch pipeline

**Decision:** A Python script `scripts/refetch_metadata.py` that:

1. Queries for entities with specific metadata gaps (no format, no publisher, no genres, no cover_url)
2. For each entity, checks `metadata_refetch_log` to see if we've already checked recently
3. Calls the appropriate external API strategy (via existing `app/strategies/` and `app/utils/` modules)
4. Updates the entity's metadata via `DataManager` or direct ORM updates
5. Logs the attempt in `metadata_refetch_log` with timestamp, iqoqo version, and result

**`metadata_refetch_log` table schema** (inventory schema):

```text
entity_type: VARCHAR(20)     -- 'work', 'expression', 'manifestation'
entity_id: INTEGER
checked_at: TIMESTAMP        -- when we last checked
iqoqo_version: VARCHAR(50)   -- version at time of check
strategy: VARCHAR(50)        -- 'tmdb', 'discogs', 'bgg', 'igdb', 'google_books', 'musicbrainz'
found_fields: JSON           -- which fields were found/updated: {"format": true, "publisher": true, ...}
error: TEXT                  -- null or error message
```

Unique constraint on `(entity_type, entity_id, strategy)` so we can upsert.

**API throttling strategy:**

- Per-strategy rate limits defined in a config dict (e.g., TMDB: 40 req/s, Discogs: 60 req/min, BGG: 2 req/s)
- Token-bucket or simple sleep-based throttling between requests
- `--dry-run` flag reports what would be done without making API calls
- `--content-type` filter to target specific media types
- `--gap` filter: `format`, `publisher`, `genres`, `cover`, `all`

**Alternatives considered:**

- Celery task queue — rejected for initial version. Batch script is simpler, can be cron'd. Celery can be added later.
- Automatic refetch on scan — out of scope, the user explicitly asked for a batch process.
- Storing checks in `manifestation.meta` JSON — rejected because it pollutes bibliographic metadata with operational data.

## Risks / Trade-offs

| Risk                                                                                | Mitigation                                                                                     |
|-------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| Rate limiting may cause script to run for hours                                     | `--dry-run` first; `--limit N` flag to cap refetch count; log progress                         |
| External API schema changes could break strategies                                  | Each strategy has its own module with tests; graceful error handling logs failures             |
| Refetching could overwrite user-edited metadata                                     | Only update fields that are currently NULL/empty; never overwrite non-empty values             |
| New DB table adds migration complexity                                              | Alembic migration auto-generated; table is lightweight (5 columns)                             |
| Publisher fix may duplicate display if meta.publisher and column.publisher both set | Frontend deduplicates by reading `item.publisher` first, checking for equality with meta value |

## Migration Plan

1. Deploy API change (publisher field in response) — backward compatible, adds new field
2. Deploy frontend changes (genres, publisher, collection_status) — reads new API field, falls back gracefully
3. Run Alembic migration locally: `flask db migrate -m "add metadata_refetch_log"` → upgrade
4. `make refetch-metadata --dry-run` to verify detection
5. Run with `--limit 50` first to validate end-to-end
6. Schedule periodic runs via cron or manual invocation

## Open Questions

- **Q:** Should the refetch script also update `Work.meta.categories` from genre data fetched for manifestations?
  **A:** Not in v1. Focus on manifestation-level gaps. Work-level enrichment is a follow-up.
- **Q:** What iqoqo version string format? Semver? Git hash?
  **A:** Use `VERSION` file or `git describe --tags` at script runtime. Store as-is.
