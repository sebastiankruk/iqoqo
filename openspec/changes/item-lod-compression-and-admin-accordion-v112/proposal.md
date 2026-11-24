## Why

Even after `C142`, the `/item/[id]` mobile layout places a tall `Linked Open Data` card inside `DetailsTab` and a standalone `Admin Actions` row directly above the sidebar's core owner controls (`Availability & Condition`, `Progress`, `Edit Metadata`, and `Manage`). Compressing Linked Open Data and relocating both LOD and `Admin Actions` / `Requests` into the bottom accordion stack restores immediate access to primary shelf controls while unifying all secondary disclosures in one collapsible stack.

## What Changes

- **Compress `SemanticLinks` (`Linked Open Data`):** Add a compact borderless rendering mode that omits the outer card chrome and tall dashed empty box, placing external authority links, confidence metadata, and `Scan External LOD` into a dense accordion body.
- **Relocate LOD out of `DetailsTab`:** Remove `<SemanticLinks />` from `frontend/components/item/item-tabs.tsx` so `DetailsTab` strictly focuses on item metadata and series context without vertical blank space when `0` authorities are linked.
- **Move `Admin Actions` & `Requests` out of the main column:** Remove standalone `<ItemActions />` from the bottom of the main column (`order-1` in `frontend/components/item/item-page-client.tsx`) so it no longer precedes `SidebarStatusBadges` and `SidebarActions` on mobile.
- **Unify bottom accordion stack:** Add collapsible `"Linked Open Data"` (showing link count when known) and `"Admin Actions"` (preserving `Requests` / escalation trigger and pending escalation status card) disclosures to the bottom accordion list in `ItemSidebar` / `SidebarActions` below `Additional Scans`, `Named Collections`, and `Taxonomy`, while keeping `sidebar/` presentation components pure-props.

## Capabilities

### New Capabilities

<!-- None -->

### Modified Capabilities

- `item-detail-ux-declutter`: Compress `Linked Open Data` into a dense collapsible disclosure and relocate both `Linked Open Data` and `Admin Actions` (`ItemActions`) into the bottom sidebar accordion stack.

## Impact

- **Frontend Components:** `frontend/components/item/item-page-client.tsx`, `frontend/components/item/item-tabs.tsx`, `frontend/components/item/item-sidebar.tsx`, `frontend/components/item/sidebar/sidebar-actions.tsx`, `frontend/components/item/item-actions.tsx`, `frontend/components/manifestation/semantic-links.tsx`
- **Localization:** `frontend/messages/en.json`, `frontend/messages/pl.json` (sentence-case `pl` keys if new accordion labels are needed)
- **Tests:** `frontend/__tests__/components/item/*`, `frontend/__tests__/e2e/item_detail_ux.spec.ts`
