## 1. Custodian Provider Merge Integrity (Critical Fix)

- [x] 1.1 Extract real candidate values from `manifestation.raw_payload` and `_provenance` in `frontend/components/admin/provider-merge-dialog.tsx` instead of synthesized mock strings, and verify candidate extraction with Vitest tests.
- [x] 1.2 Re-synchronize `selectedProviders` state reactively in `ProviderMergeDialog` when `tree` or candidate fields update, and verify state synchronization with component tests.
- [x] 1.3 Update top-level `manifestation.cover_url` column alongside `manif_meta["cover_url"]` in `apply_custodian_provider_merge` (`app/core/frbr_service.py`), and verify cover URL persistence in pytest.
- [x] 1.4 Enforce canonical hierarchy lock order (`Work -> Expression -> Manifestation`) using `with_for_update()` in `apply_custodian_provider_merge` (`app/core/frbr_service.py`), and verify locking order in service tests.

## 2. Multi-Series Synchronization & Persistence (Critical Fix)

- [x] 2.1 Serialize `series_memberships` in `get_frbr_tree` (`app/api/admin.py`) and `_get_physical_item_detail` (`app/api/items.py`), and verify with backend API endpoint tests.
- [x] 2.2 Refactor `update_work` in `app/core/frbr_service.py` to use set-based reconciliation with SQLAlchemy 2.0 `select()`, eliminating the empty-list `ArgumentError` filter crash, string-to-int comparison mismatch, and N+1 queries, verified by pytest.
- [x] 2.3 Add `lazy="selectin"` to `WorkSeriesMembership.series` in `app/db/contributions.py` to eliminate N+1 queries when accessing series titles.
- [x] 2.4 Update `WorkEditor` in `frontend/components/admin/frbr/work-editor.tsx` to use `apiClient`, cancel in-flight queries via `AbortController`, display `sm.title` in attached badges, and remove synchronous `setState` in async wrapper, verified by frontend unit tests.

## 3. Metadata Display Projection & Catalog Navigation (Moderate Fixes)

- [x] 3.1 Include `display` projection in `get_manifestation_detail` (`app/api/manifestations.py`) by calling `build_display_projection(m.meta)`, and verify `/api/manifestations/<id>` emits `display`.
- [x] 3.2 Update `isKnownMetaSpelling` in `frontend/lib/meta.ts` and `extended-metadata.tsx` to case-insensitively suppress dedicated section keys, and verify no key leakage into "Additional Details".
- [x] 3.3 Precompute lowercased keys set once at module level in `app/core/meta_display.py` and filter internal `_`-prefixed keys.
- [x] 3.4 Restore `<DiscoveryPivot>` in `frontend/components/item/extended-metadata.tsx` and `extended-metadata-boardgame.tsx` for categories and mechanics tags to preserve interactive click-to-filter catalog navigation.
- [x] 3.5 Remove duplicate `<TagCloud>` rendering between `ItemHeader` (`frontend/components/item/item-header.tsx`) and `DetailsTab` (`frontend/components/item/item-tabs.tsx`).

## 4. Rich Text SSR Sanitization Hardening (Moderate Fix)

- [x] 4.1 Update `sanitizeRichHtml` in `frontend/components/ui/rich-text.tsx` to strip `<script>` and `<style>` blocks with their inner bodies and sanitize/entity-encode malformed HTML tags during SSR passes, verified by Vitest unit tests.

## 5. Item Ownership Account Discovery & RBAC (Moderate Fix)

- [x] 5.1 Implement SQL `limit` and `offset` pagination and search filtering in `get_ownership_accounts` (`app/api/admin.py`), and verify with backend tests.
- [x] 5.2 Add `custodian` role check in `frontend/app/admin/ownership/page.tsx` (`isAdminOrCustodianOrContributor`) to match RBAC policies.

## 6. Catalog Search Stability & Provider Bounds (Reliability Fixes)

- [x] 6.1 Add deterministic tie-breaker (`ORDER BY rank DESC, id DESC`) to `_pg_manifestation_fts` and `_pg_item_fts` in `app/core/search_service.py` to prevent pagination instability.
- [x] 6.2 Pass remaining time budget down as socket timeout to `_lookup_google_books_outcome` and `_lookup_open_library_outcome` in `app/utils/isbn.py`.
- [x] 6.3 Move `STATUS_LABELS` from `frontend/components/item/item-sidebar.tsx` to `frontend/components/item/sidebar/constants.ts` to eliminate circular module dependencies.
- [x] 6.4 Update `docs/CHANGELOG.md` with entries for completed v0.8.4 features (C63, C66, C67, C68, C69).

## 7. Full Test Suite & Quality Verification

- [x] 7.1 Run backend test suite (`IQOQO_AI_MODE=1 pytest tests/test_frbr_admin.py tests/test_items.py tests/test_search.py`) and verify all tests pass.
- [x] 7.2 Run frontend test suite (`IQOQO_AI_MODE=1 npm run test -- --run`) and verify all tests pass.
- [x] 7.3 Run linters and secret scans (`IQOQO_AI_MODE=1 make lint`) and verify clean report.
