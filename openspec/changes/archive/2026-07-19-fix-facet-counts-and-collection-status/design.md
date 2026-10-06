---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

Currently, the facet counts for non-item views (Works, Expressions, Manifestations) improperly use an `INNER JOIN` to `Item` when `owner_id` is present, even if `scope=global` or if cross-FRBR filters are disabled. This limits the total count to only those items the user owns (e.g., ~300 instead of 1000+).
Furthermore, when users filter by `collection_status` in Works or Expressions views, the main catalog queries only check `Item.status`, failing to check `Item.collection_status`. As a result, users see 0 results when cross-filtering Works by their items' collection status (e.g., "wish_list").

## Goals / Non-Goals

**Goals:**

- Fix the facet count queries in `data_manager.py` to ensure global views correctly show the total number of distinct entities (Works, Expressions, Manifestations) in the catalog.
- Fix cross-FRBR collection status filtering in `works.py` (for both Works and Expressions views) and `manifestations.py` to correctly filter by `Item.collection_status` in addition to `Item.status`. This ensures manifestations, expressions, and works views are all fixed in the exact same way.

**Non-Goals:**

- Changes to the frontend React components.

## Decisions

- **Modify `_needs_item_join` logic in `data_manager.py`:** We will adjust the logic so that `owner_id is not None` does NOT unilaterally force an `INNER JOIN` on global views. The `INNER JOIN` to `Item` will only be used if a user-specific filter (like tags, collections, statuses) is actively applied or if the view scope requires it. For global views without user-specific filters, a `LEFT JOIN` or no join will be used.
- **Update main catalog API endpoints:** In `works.py` (which handles both Works and Expressions views) and `manifestations.py`, we will identically modify the `statuses_list` filter from `Item.status.in_(statuses_list)` to `or_(Item.status.in_(statuses_list), Item.collection_status.in_(statuses_list))` to correctly capture both types of statuses across all non-item views.

## Risks / Trade-offs

- **Performance:** Using `LEFT JOIN` on large tables like `Manifestation` and `Item` may slow down facet counts. We mitigate this by using `INNER JOIN` only when item-level filters are active, and utilizing `COUNT(DISTINCT ...)` carefully.
