## Why

The v0.8.4 final release review conducted by Gemini Argon and Principal Code Review revealed 2 critical data corruption/loss bugs and 8 moderate architectural/reliability defects across custodian provider merging, multi-series synchronization, rich text SSR sanitization, metadata display projection, catalog search ranking, and item ownership account discovery. Fixing these issues before finalizing the v0.8.4 tag is essential to prevent catalog data loss and production crashes.

## What Changes

- **Custodian Provider Merge Integrity (`custodian-provider-merge`)**:
  - Replace synthetic mock values (`${workTitle} (OpenLibrary)`, etc.) with real candidate extraction from `manifestation.raw_payload` and provider responses in `provider-merge-dialog.tsx`.
  - Re-synchronize `selectedProviders` state when `tree` or `customFields` change instead of binding once at mount.
  - Update top-level `manifestation.cover_url` column alongside `manifestation.meta["cover_url"]` during provider merge so merged cover art is not shadowed.
  - Enforce canonical hierarchy lock ordering (`Work -> Expression -> Manifestation`) using `with_for_update()` before reading/mutating entities to avoid transaction deadlocks.

- **Multi-Series Synchronization & Persistence (`frbr-ontology`)**:
  - Serialize `series_memberships` in `get_frbr_tree` (`app/api/admin.py`) and `_get_physical_item_detail` (`app/api/items.py`) so existing memberships are preserved during Work edits and displayed on item pages.
  - Fix SQLAlchemy 2.0 query crash in `frbr_service.update_work` when clearing series memberships by avoiding literal Python `bool` in `.filter()`, and use SQLAlchemy 2.0 `select()` syntax.
  - Fix string-to-int comparison bug and target Work ID vs membership ID conflation in `update_work`.
  - Add `lazy="selectin"` to `WorkSeriesMembership.series` relationship in `app/db/contributions.py` to eliminate N+1 queries.
  - Update `WorkEditor` to use `apiClient` with `AbortController`, display actual series titles, and avoid synchronous setState anti-patterns.

- **Metadata Display Projection & Catalog Navigation (`metadata-display-projection`)**:
  - Include `display` projection in `GET /api/manifestations/<id>` response in `app/api/manifestations.py` to prevent detail page fallback leakage.
  - Expand key suppression in `isKnownMetaSpelling` or `fallbackEntries` to case-insensitively cover all dedicated section keys.
  - Precompute lowercased keys set in `app/core/meta_display.py` and filter out internal `_`-prefixed keys.
  - Restore interactive `<DiscoveryPivot>` click-to-filter navigation for categories/genres in `extended-metadata.tsx` and mechanics in `extended-metadata-boardgame.tsx`.
  - De-duplicate tag cloud between `ItemHeader` and `item-tabs.tsx`.

- **Rich Text SSR Sanitization Hardening (`editor/rich-text-rendering`)**:
  - Strip `<script>` and `<style>` blocks with contents, and safely escape or neutralize HTML markup during SSR passes when DOMPurify context is unavailable.

- **Item Ownership Account Discovery & RBAC (`item-ownership-reassignment`)**:
  - Enforce SQL `LIMIT`/`OFFSET` pagination and bounds on `GET /api/v1/admin/ownership/accounts`.
  - Harmonize RBAC role checks to include `custodian` in `frontend/app/admin/ownership/page.tsx`.

- **Search Stability & Provider Timeout Bounds**:
  - Add deterministic tie-breaker (`ORDER BY rank DESC, id DESC`) in `app/core/search_service.py` to prevent pagination instability.
  - Pass remaining time budget down as timeout to socket operations in `app/utils/isbn.py`.
  - Move `STATUS_LABELS` in `item-sidebar.tsx` to break circular module dependencies.
  - Update documentation and changelog in `docs/CHANGELOG.md` for completed 0.8.4 features.

## Capabilities

### New Capabilities
<!-- None: all capabilities are refinements to existing specifications -->

### Modified Capabilities
- `custodian-provider-merge`: Candidate values must be extracted from actual provider payloads or stored metadata rather than synthesized mocks; merge must synchronize top-level `cover_url` and lock entities in canonical FRBR hierarchy order.
- `frbr-ontology`: FRBR hierarchy tree endpoints and physical item details must serialize `series_memberships`, and Work updates must safely synchronize multi-series memberships without data loss or SQLAlchemy 2.0 query exceptions.
- `metadata-display-projection`: Manifestation detail endpoint must emit server display projections, suppression of known metadata keys must be case-insensitive, and catalog navigation pivots must remain interactive.
- `editor/rich-text-rendering`: Server-side rendering fallback for rich text must strip script/style blocks and neutralize executable markup to prevent SSR XSS vulnerabilities.
- `item-ownership-reassignment`: Ownership account discovery must enforce SQL pagination bounds and accept administrator and custodian roles.

## Impact

- **Backend APIs**: `app/api/admin.py`, `app/api/items.py`, `app/api/manifestations.py`, `app/core/frbr_service.py`, `app/core/search_service.py`, `app/core/meta_display.py`, `app/utils/isbn.py`, `app/db/contributions.py`.
- **Frontend Components**: `frontend/components/admin/provider-merge-dialog.tsx`, `frontend/components/admin/frbr/work-editor.tsx`, `frontend/components/item/extended-metadata.tsx`, `frontend/components/item/item-tabs.tsx`, `frontend/components/item/item-header.tsx`, `frontend/components/ui/rich-text.tsx`, `frontend/app/admin/ownership/page.tsx`, `frontend/components/item/item-sidebar.tsx`.
- **Documentation**: `docs/CHANGELOG.md`.
