---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Backend Modifications for Facet Counts

- [x] 1.1 In `app/core/data_manager.py` where `get_faceted_stats` is defined, adjusted the `COUNT()` logic to reflect the correct FRBR level based on the `view` parameter.
- [x] 1.2 Updated `func.count(DISTINCT X.id)` target to use `Manifestation.id` for global, `Work.id` for works, `Expression.id` for expressions, and `Item.id` for items. The `_build_item_ids_subq` now accepts a `target_entity` parameter controlling which entity IDs are returned.
- [x] 1.3 Ensured unauthorized requests (no `user_id`) gracefully skip user-specific count queries. The `/stats/facets` endpoint now uses `@optional_auth` instead of `@require_auth`. User-specific facet counts (status, tags, collections) return empty/zero when `owner_id` is None. The subquery uses LEFT JOIN to Items for unauthenticated views.

## 2. Backend Modifications for Cross-Filtering

- [x] 2.1 In `_build_item_ids_subq`, added join logic so Works/Expressions/Manifestations can be filtered by Manifestation-level attributes (`media_category` / `Expression.content_type`, `physical_kind` / `Manifestation.meta["format"]`). The subquery now starts from the target entity and joins down through the FRBR hierarchy.
- [x] 2.2 Added join logic allowing Works/Expressions/Manifestations to be filtered by all Item-level attributes (`status`, `progress`, `tags`, `storage_location`, `named_collections`). Item-level filters are only applied when `owner_id` is present.
- [x] 2.3 `SELECT DISTINCT` is used on the primary entity being returned via `distinct(target_id_col).label("id")` in the subquery and `COUNT(DISTINCT target_clause)` in count queries.
- [x] 2.4 For unauthenticated requests, the subquery uses LEFT JOIN to Item instead of INNER JOIN, preventing exclusion of public catalog entities without user-owned Items.
- [x] 2.5 Work-level facets (Genre, Language, Publisher) work correctly with count fixes from §1. Genre filtering uses the `apply_genre_filter` helper, and publisher filtering uses `Manifestation.publisher`.
- [x] 2.6 Add `statuses` and `formats` parameter support to `/works/shelf` endpoint in `app/api/works.py` (with cross-FRBR join logic matching the existing tags/collections pattern)
- [x] 2.7 Add `statuses` and `formats` parameter support to `/expressions/shelf` endpoint in `app/api/works.py`

## 3. Frontend Facet Conditional Logic

- [x] 3.1 In `components/sidebar-filters.tsx`, the `isLoggedIn` prop is already obtained from the parent `page.tsx`.
- [x] 3.2 User-specific facet groups (`Collection Status`, `Progress`, `Tags`, `Storage Location`, `Named Collections`) are conditionally hidden when `isLoggedIn` is false.
- [x] 3.3 The `useFacetStats` hook and `filtersForFacets` now pass the correct `view` parameter. Scope is set to `"user"` when `isLoggedIn` is true (regardless of viewMode).
- [x] 3.4 Remove `!isHierarchyView` guard from Physical Kind section in sidebar-filters.tsx (line 391) so Physical Kind facet is visible and functional in Works/Expressions views
- [x] 3.5 Remove `!isHierarchyView` guard from Collection Status section in sidebar-filters.tsx (line 423) so it's visible at all FRBR levels (per spec: "WHEN the user is authenticated AND viewing any FRBR level... THEN the Collection Status facet SHALL be rendered")
- [x] 3.6 Remove `!isHierarchyView` guard from Progress section in sidebar-filters.tsx (line 463)
- [x] 3.7 Add `formats` and `statuses` params to `useInfiniteWorksShelf` hook and pass them from page.tsx
- [x] 3.8 Add `formats` and `statuses` params to `useInfiniteExpressionsShelf` hook and pass them from page.tsx

## 4. Testing & Verification

- [x] 4.1 Backend test `test_cross_frbr_filter_works_by_item_status` verifies filtering Works by Item `status` returns expected Works without duplicates.
- [x] 4.2 Backend test `test_faceted_stats_manifestations_view_global_unauthenticated` verifies `media_category` counts for Global Library correctly reflect Manifestations and aren't 0 for unauthenticated users.
- [x] 4.3 Frontend tests in `sidebar-filters.test.tsx` assert user-specific facets (Collection Status, Tags, Collections) are absent for unauthenticated users, and global facets remain visible.
