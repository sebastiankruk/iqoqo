---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

Faceted navigation counts for non-item views (Works, Expressions, Manifestations) are currently incorrect. Instead of showing global counts (e.g., 1000+), they show only the count of the user's items (e.g., ~300). Furthermore, filtering by `collection_status` on these non-item views incorrectly returns no results because the query filters by `Item.status` instead of `Item.collection_status` for statuses like `wish_list`.

## What Changes

- Fix facet counts in Global Library: ensure that when counting Works/Expressions/Manifestations globally, the counts are not inappropriately constrained by an `INNER JOIN` to the user's `Item` records. Global views should show the total count of those entities.
- Fix cross-FRBR `collection_status` filtering: ensure that when a user filters by `statuses`, the catalog queries for non-item views filter by both `Item.status` and `Item.collection_status`, matching the intent of cross-FRBR filtering.

## Capabilities

### New Capabilities
None.

### Modified Capabilities

- `faceted-navigation`: Correcting the implementation of FRBR-aware facet counts to not erroneously restrict Global Library views to the user's owned items, and fixing cross-FRBR filtering for `collection_status`.

## Impact

- `app/core/data_manager.py`: `_build_item_ids_subq` to adjust `_needs_item_join` logic and `get_faceted_stats` to fix the overly restrictive `INNER JOIN` logic on global views.
- `app/api/works.py` (handles both Works and Expressions views): Main search queries will correctly apply `Item.collection_status` when filtering by `statuses_list`.
- `app/api/manifestations.py`: Main search queries will identically apply `Item.collection_status` when filtering by `statuses_list`.
