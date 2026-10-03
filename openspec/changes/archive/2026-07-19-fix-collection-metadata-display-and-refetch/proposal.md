---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

A database audit against the iqoqo dev instance (1901 items, 1920 manifestations, 1636 works) revealed four issues causing poor metadata display on the collection and item detail pages: genres read from wrong data source, publishers invisible despite existing in the DB, collection_status silently hidden on cards, and 82% of manifestations lacking a `format` key. Additionally, there is no process to batch-refetch missing metadata from external APIs with throttling and version tracking — so once metadata is missing, nothing ever fills it in.

## What Changes

- **Fix genre/category display**: Frontend reads categories from `work.meta` (where they live) instead of `manifestation.meta` (where they rarely exist). Merge both sources.
- **Fix publisher display**: Item detail API now serializes `Manifestation.publisher` column in responses. Frontend reads publisher from both the column and legacy `manifestation.meta.publisher`.
- **Fix collection_status in faceted navigation**: The filter sidebar's "Collection Status" section showed no values (all counts zero, all options disabled). Fixed by: COALESCE-ing NULL `collection_status` to `"available"` in the facet stats query so hidden items contribute to the correct bucket; adding a dedicated `borrowed_count` field to the API response for the virtual "borrowed" status; and removing the `disabled` attribute from zero-count facets so all filter options remain interactive. Cards continue to suppress `"available"` as the default status.
- **Metadata refetch pipeline**: A new `scripts/refetch_metadata.py` script with a `make refetch-metadata` entrypoint. Batch-refetches metadata from external APIs (TMDB, Discogs, BGG, IGDB, MusicBrainz, Google Books) for manifestations/expressions/works with known gaps. Tracks last-check timestamp and iqoqo version per entity in a new `metadata_refetch_log` table. Supports API throttling, dry-run mode, and filter by content_type/format gap.

## Capabilities

### New Capabilities

- `metadata-refetch`: Batch metadata enrichment pipeline with per-entity version tracking, API throttling, and gap detection

### Modified Capabilities

_None. Existing spec-level requirements are unchanged — these are implementation fixes (bugs 2 & 4, design issue 3) plus a new operational capability._

## Impact

- **API**: `app/api/items.py` — `_get_physical_item_detail()` adds `"publisher": manifestation.publisher` to response. `get_items()` serialization paths also updated.
- **Frontend**: `components/item/extended-metadata.tsx` — genre source changed to `work.meta`. `components/item/item-header.tsx` — publisher reads from new API field + legacy location. `components/collection/item-card.tsx` — collection_status visibility logic updated.
- **Database**: New `metadata_refetch_log` table (inventory schema) for tracking refetch timestamps and versions.
- **New files**: `scripts/refetch_metadata.py`, Makefile entry `refetch-metadata`, possibly an Alembic migration.
