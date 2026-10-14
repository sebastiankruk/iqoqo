## Why

In collection views and item cards, users can see manifestation or item details, but lack direct navigational links up the FRBR hierarchy to parent Expression and Work entities. Navigating to the conceptual Work or language Expression currently requires tedious manual searches or multiple clicks through edit panels. Adding direct, accessible navigation links from collection cards and item headers directly satisfies the planned roadmap item `#ux #v084` ("add links to Work and Expression pages from the collection views").

## What Changes

- **Collection Card Navigation Affordances:** Enhance collection grid/list views (`frontend/components/collection/`) with clickable links or badges to the parent Work (`/work/[id]`) and parent Expression details.
- **Item Header FRBR Hierarchy Links:** Ensure item and manifestation header views display an explicit, accessible FRBR breadcrumb or parent link set leading to Expression and Work views.
- **FRBR Parent Projection:** Ensure collection query payloads and item API projections include necessary parent `work_id` and `expression_id` identifiers to render links without triggering N+1 frontend requests.

## Capabilities

### New Capabilities

- `frbr-collection-navigation`: Enables users viewing collection cards or item listings to navigate up the FRBR ontology hierarchy directly to parent Work and Expression pages.

### Modified Capabilities

None.

## Impact

- **Frontend:** `frontend/components/collection/`, `frontend/components/item/item-header.tsx`, `frontend/types/frbr.ts`.
- **Backend:** `app/api/` item/collection response serialization (verify `work_id` and `expression_id` presence).
- **Tests:** Vitest component tests verifying correct href links to `/work/:id` and `/expression/:id` render on collection items.
