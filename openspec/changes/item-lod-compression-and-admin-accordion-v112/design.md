## Context

Per the `/ux-audit` inspection of `/home/sebastiankruk/Downloads/iqoqo/Screenshot_20261124-221036.png` and `iqoqo-ux-auditor` heuristics:
- **Current DOM Order (Mobile `< 1024px`):**
  `Navbar` -> `HeroBanner` -> `Main Column (order-1)` [`ItemHeader` -> `ItemTabs` (`DetailsTab` -> `ExtendedMetadata` -> Series -> **Expanded `<SemanticLinks />` Card**) -> **Standalone `<ItemActions />`**] -> `Sidebar (order-2)` [`SidebarCover` -> `SidebarStatusBadges` -> `SidebarLendingInfo` -> `ReadingDurationCard` -> `SidebarIdentifiers` -> `SidebarActions` (`Availability`, `Progress`, `Edit Metadata` + `Manage`, then collapsible `Additional Scans`, `Named Collections`, `Taxonomy`) -> `SidebarFrbrInfo`].
- **Desktop (`>= 1024px`):** Left 30% sidebar (`order-1`) and right 70% main column (`order-2`). Removing `<SemanticLinks />` from `DetailsTab` and `<ItemActions />` from `ItemPageClient` and moving both to the bottom of `SidebarActions` eliminates the ~300px mobile obstruction above `SidebarActions` while keeping desktop `DetailsTab` purely descriptive metadata.

## Goals / Non-Goals

- **Goals:**
  - Compress `SemanticLinks` into a compact borderless disclosure panel without outer `<Card>` padding/borders or tall dashed empty box.
  - Move both `Linked Open Data` and `Admin Actions` / `Requests` into the bottom collapsible accordion list below `Taxonomy` inside the sidebar footer stack (`SidebarActions`).
  - Collapse both disclosures by default so `<= 4` buttons remain visible per action container and owner shelf controls appear immediately on mobile scroll.
  - Preserve `components/item/sidebar/*` pure-props invariant (no API hooks or React Context imports inside `sidebar-actions.tsx`).
- **Non-Goals:**
  - Changing backend LOD, escalation, or FRBR metadata endpoints.
  - Changing FRBR ownership/custodian RBAC permissions.

## Decisions

1. **Composition Slots Preserve `SidebarActions` Pure-Props Contract:**
   `ItemSidebar` (which already calls `useProfile()`) constructs `<SemanticLinks manifestationId={item.manifestation_id} canEdit={...} compact />` and `<ItemActions item={item} compact />` (or passes them via optional `linkedOpenDataNode?: React.ReactNode` and `adminActionsNode?: React.ReactNode` props to `SidebarActions`), keeping `frontend/components/item/sidebar/sidebar-actions.tsx` 100% pure-props without importing hooks.
2. **Default-Collapsed Disclosure Pattern Matching `Additional Scans` / `Named Collections` / `Taxonomy`:**
   Use the identical `border-t border-border/40 pt-2` full-width chevron button row style in `SidebarActions` for:
   - **Linked Open Data** (rendered when `Boolean(item.manifestation_id)`): header shows localized `"Linked Open Data"` label (and optional badge count `(n)` when preloaded or compact toggle). Expanding mounts `<SemanticLinks manifestationId={item.manifestation_id} canEdit={hasEditPermission || isOwner} compact />`.
   - **Admin Actions** (or `"Admin & Requests"` when custodian/owner/requester): rendered when `adminActionsNode` is provided (if user has `showAdminActions` or `showRequestsSection`). Pending help request status card, if present, stays visible right above or inside the Requests section without rendering redundant uncollapsed card wrappers.
3. **`SemanticLinks` `compact` Prop:**
   Default `compact = false` keeps backward compatibility for `/manifestation/[id]` (if used there) while `compact = true` renders a flat `<div className="space-y-2.5">` instead of `<Card className="mt-6 ...">`, replaces the `py-5` dashed empty box with a single concise muted text line (`t("noLinks")`) + compact `outline` `"Scan External LOD"` button (`h-7 text-xs`), and uses condensed padding (`py-1.5`) on authority rows.

## Risks / Trade-offs

- **Vitest / E2E Test Updates:** Existing tests asserting `"Linked Open Data"` inside `DetailsTab` or `"Admin Actions"` directly visible without expanding the accordion in `item-actions.test.tsx` / `item_detail_ux.spec.ts` must click/expand the disclosure or test the compact mode explicitly.
- **Mobile Scroll Reachability:** Placing LOD and `Admin Actions` inside the sidebar bottom accordion ensures both desktop (bottom of left rail) and mobile (bottom of item card) share one predictable home for secondary cataloging/admin tools (`<= 2` clicks to trigger any action).
