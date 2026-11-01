## Why
Once standalone maps and book/game map attachments are stored via `C105`, collectors need an interactive high-resolution pan/zoom viewer to inspect intricate cartographic details (town names, game board regions, fantasy world geography) on both desktop and mobile touchscreens, plus a collection filter facet to find all items with maps.

## What Changes

- **Interactive Pan/Zoom `<MapViewerModal />` (`frontend/components/item/map-viewer-modal.tsx`):** Build a Shadcn Dialog-based high-resolution map inspector supporting zoom in/out (`1x`–`5x`), drag/touch-pan, 90-degree rotation, reset view, and multi-map tab switching when a book or board game includes multiple maps.
- **Map Attachment Section & Upload Trigger on Detail Views:** Surface map attachments and the `"Inspect Map"` / `"Add Map Supplement"` triggers on `/item/[id]`, `/manifestation/[id]`, and `/work/[id]` (respecting the $\le 4$ visible buttons density limit by grouping inside the gallery/supplements panel).
- **`"Has Map"` Collection Facet Filter (`app/api/filters.py`, `sidebar-filters.tsx`):** Add a `"Has Map"` filter option in the collection sidebar/drawer so users can filter their library to items/manifestations that include cartographic maps.

## Capabilities

### New Capabilities
- `interactive-map-viewer-and-facet`: High-resolution pan/zoom/rotate `<MapViewerModal />` component on entity detail pages and `"Has Map"` collection facet filtering.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/components/item/map-viewer-modal.tsx`
- `frontend/components/item/item-tabs.tsx`, `frontend/components/manifestation/manifestation-actions.tsx`
- `frontend/components/collection/sidebar-filters.tsx`, `frontend/components/collection/filter-bar.tsx`
- `app/api/filters.py`, `app/core/search_service.py`
- `frontend/messages/en.json`, `frontend/messages/pl.json`
- `frontend/__tests__/components/item/map-viewer-modal.test.tsx`, `frontend/__tests__/e2e/maps_workflow.spec.ts`
