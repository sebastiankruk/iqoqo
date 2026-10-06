---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

The backend currently filters and aggregates publisher data exclusively using the `Manifestation.publisher` relational column. However, real-world data often stores publisher information inside unstructured JSON fields like `Manifestation.meta['Publisher']` or `meta['publisher']` (which the frontend correctly uses to render clickable publisher links). As a result, users click on a publisher on an item's page, but the backend filter returns 0 results, and the publisher is completely missing from the faceted navigation sidebar.

## What Changes

- Modify API filtering logic in `manifestations.py`, `items.py`, and `search_service.py` to check both the `publisher` column and the relevant `meta` JSON fields (`Publisher`, `publisher`, `label`) when a publisher filter is active.
- Update `taxonomies.py` to extract distinct publishers by coalescing the `publisher` column with the JSON `meta` fields so they appear in the filter lists.
- Update `DataManager.get_faceted_stats` to use a coalesced publisher expression for grouping and counting, ensuring `publisherCounts` accurately reflects items regardless of where their publisher data is stored.

## Capabilities

### Modified Capabilities

- `faceted-navigation`: Update publisher taxonomy extraction, filtering, and aggregation to support JSON metadata fields alongside relational columns.

## Impact

- **Backend APIs**: `app/api/manifestations.py`, `app/api/items.py`, `app/api/taxonomies.py`
- **Core Services**: `app/core/data_manager.py`, `app/core/search_service.py`
- **Database**: No schema changes required; relies on SQLAlchemy JSON operators (`coalesce`, `as_string()`).
