---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

The current `CollectionDataManager` and aggregation functions rely too heavily on the "My items" (Item-level) view when returning facet counts and determining which facets to show. This results in the UI displaying Item counts even when browsing Works, Expressions, or the Global Library. Furthermore, filtering Works/Expressions by Item-level attributes (Collection Status, Progress, Tags, Storage Location, Named Collections) or Manifestation-level attributes (Media Category, Physical Kind) either returns no results or incorrect data, because the current query logic doesn't accurately bubble up lower-level entity attributes to filter the broader entities. Unauthenticated users also see an incorrect 0-count state for Media Categories because the application tries to aggregate based on their non-existent Item context rather than using global Manifestation/Work context. Additionally, the sidebar hides certain facets (Physical Kind, Collection Status, Progress) at Works/Expressions level via `!isHierarchyView` guards in `sidebar-filters.tsx` that need to be removed.

## Goals / Non-Goals

**Goals:**

- Dynamically adjust facet count aggregations based on the requested `view` parameter (e.g., `works`, `expressions`, `global`, `items`).
- Enable filtering of Works and Expressions by attributes of their underlying entities — all Item-level facets (`status`, `progress`, `tags`, `storage_location`, `named_collections`) and all Manifestation-level facets (`media_category`, `physical_kind`).
- Implement conditional logic to hide user-specific facets (Collection Status, Progress, Tags, Storage Location, Named Collections) when there is no authenticated user.
- Ensure unauthorized users see global counts for Media Category.

**Non-Goals:**

- Completely rewriting the overall filtering infrastructure; we will adapt the existing `get_paginated_collection` and `get_facet_aggregations` logic.
- Adding new UI facets that don't currently exist.
- Changing how data is inserted/updated (read-only changes).

## Decisions

1. **Dynamic Count Aggregations:**
   - Instead of always running `COUNT(Item.id)` or defaulting to it, the `get_facet_aggregations` function will vary its `func.count(DISTINCT entity.id)` target based on the active FRBR level.
   - For Global Library: `COUNT(DISTINCT Manifestation.id)`
   - For Works: `COUNT(DISTINCT Work.id)`
   - For Expressions: `COUNT(DISTINCT Expression.id)`
   - For Items: `COUNT(DISTINCT Item.id)`

2. **Cross-Entity Filtering Joins:**
   - In `_apply_filters`, if a filter belongs to a lower-level entity, the query builder will safely outer-join or selectively join these lower entities to allow `where` conditions. Lower-level facets and their source entities:
     - **Item-level** (require join Item → Manifestation → Expression → Work): `status`, `progress`, `tags`, `storage_location`, `named_collections`
     - **Manifestation-level** (require join Manifestation → Expression → Work): `media_category`, `physical_kind`
   - Example: If in `works` view and `status='wishlist'` is requested, join `Work -> Expression -> Manifestation -> Item` and filter `Item.status == 'wishlist'`.
   - To prevent duplicate records in the result set when joining lower entities, we ensure the final query uses `DISTINCT` on the target entity (e.g., `SELECT DISTINCT works.*`).

3. **Authentication Context Handling:**
   - In the frontend component (`sidebar-filters.tsx` or similar), we will conditionally render the "Collection Status" and "Progress" facets based on whether a valid session/user object is present.
   - In the backend, if no `user_id` is provided, we must skip injecting Item-specific joins that force an empty result set, allowing the system to naturally return the broader Manifestation/Expression/Work counts.

## Risks / Trade-offs

- **Performance Risk:** Joining `Item` up to `Work` for filtering could slow down queries if there are millions of items.
  - _Mitigation:_ Ensure `Item.status` and foreign keys are adequately indexed. Using `EXISTS` or `ANY` subqueries rather than direct `JOIN` with `DISTINCT` might be more efficient. We will rely on SQLAlchemy's capabilities to generate efficient SQL.
- **Complexity in Query Builder:** Modifying `_apply_filters` to handle all Item-level and Manifestation-level facets with cross-level joins can become complex.
  - _Mitigation:_ Apply cross-filtering to all known lower-level facets whose attributes live on Items (Status, Progress, Tags, Storage Location, Named Collections) or Manifestations (Media Category, Physical Kind), but use a mapping-driven approach rather than a fully generic engine to keep the code maintainable.
