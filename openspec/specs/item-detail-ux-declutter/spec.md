# item-detail-ux-declutter Specification

## Purpose
Declutters the physical item detail view (`/item/[id]`) across mobile and desktop viewports by surfacing the single primary consumption CTA and semantic FRBR navigation above the fold, enforcing action density limits, removing redundant raw-ID hierarchy blocks, tightening UI RBAC visibility, and ensuring full English and Polish sentence-case localization.

## Requirements

### Requirement: Responsive Above-the-Fold Primary Consumption Action and Single-Cover Layout
The `/item/[id]` detail page SHALL render at most one cover image inside the main detail card across both mobile (`< 1024px`) and desktop (`>= 1024px`) viewports, and SHALL position the cover, semantic FRBR breadcrumb, title/author summary, `"Explore Graph"` entry link, and the owner-gated polymorphic primary consumption CTA above the fold on both mobile (`390x844`) and desktop (`1280x800`) viewports. Exactly one visually prominent primary CTA (`variant="default"`) SHALL be rendered per `/item/[id]` view:

- For an owned book (`status !== "read"`): `"Log Reading Progress"` (or `"Mark as Read"` when `status === "reading"`).
- For an owned audio item (`status !== "listened"`): `"Now Listening"` (or `"Mark as Listened"` when `status === "listening"`).
- For an owned video item (`status !== "watched"`): `"Mark as Watched"`.
- For an owned game item: `"Log Play"`.
- For an eligible non-owner authenticated viewer (`collection_status !== "wish_list"` and no active pending/approved loan): `"Request Loan"`.

#### Scenario: Mobile collector sees single cover, graph entry, and Now Listening above the fold

- **GIVEN** an authenticated owner viewing a physical audio CD item (`id > 0`, `status !== "listened"`) on a `390x844` mobile viewport
- **WHEN** `/item/[id]` renders
- **THEN** only one cover image is displayed in the item card (no duplicate cover between sidebar and header)
- **AND** the semantic FRBR breadcrumb, item title, `"Explore Graph"` link, and `"Now Listening"` (or `"Mark as Listened"`) primary CTA appear above the fold before secondary sidebar editors and `ItemTabs`

#### Scenario: Desktop collector sees primary CTA without scrolling past ItemTabs

- **GIVEN** an authenticated owner viewing a physical book item with extended metadata or tracklists on a `1280x800` desktop viewport
- **WHEN** `/item/[id]` renders
- **THEN** `"Log Reading Progress"` (or `"Mark as Read"`) and `"Explore Graph"` are visible above the `800px` fold without scrolling past `ItemTabs`
- **AND** `"Explore Graph"` uses secondary/outline styling so only one primary CTA dominates visual hierarchy

#### Scenario: Non-owner or anonymous visitor does not see owner consumption CTA

- **GIVEN** an unauthenticated visitor or an authenticated non-owner viewing a public physical item
- **WHEN** `/item/[id]` renders
- **THEN** the polymorphic owner consumption CTA (`"Now Listening"`, `"Log Reading Progress"`, `"Mark as Watched"`, `"Log Play"`) is NOT rendered
- **AND** an eligible non-owner sees `"Request Loan"` as the single primary action while an anonymous visitor sees read-only status badges and `"Explore Graph"`

### Requirement: Button Density Cap and Secondary Owner Control Consolidation
Every visible action bar or control container on `/item/[id]` SHALL display at most 4 simultaneously visible buttons (`<= 4`), and every core collector task (updating collection/progress status, logging reading/listening progress, opening the FRBR graph, editing metadata, printing a QR code, or replacing a cover) SHALL be reachable in at most 3 clicks/taps. Owner state `<select>` controls (`Collection status`, `Item status`) and `ReadingDurationCard` (for owned books) SHALL remain directly accessible, while secondary owner controls (`Edit Metadata`, `Make Public`/`Hide from Public`, `Print QR Code`, `Reassign Owner` when permitted, and `Named Collections` / `Taxonomy` / `Additional Scans` / `Linked Open Data` / `Admin Actions`) SHALL be grouped into compact overflow or collapsed disclosure accordion controls inside the sidebar footer stack while keeping `components/item/sidebar/*` presentation components pure-props (no direct API hooks or React Context imports inside `SidebarActions`).

#### Scenario: Owner views consolidated sidebar and header action bars

- **GIVEN** an authenticated owner with metadata and cover permissions viewing `/item/[id]`
- **WHEN** inspecting every visible action bar and sidebar container on initial render
- **THEN** no visible bar or action container exposes more than 4 simultaneous buttons
- **AND** `Collection status` and `Item status` `<select>` controls remain directly operable without extra modal hops
- **AND** `Edit Metadata`, `Make Public`/`Hide from Public`, and `Print QR Code` remain reachable within `<= 3` clicks via the consolidated owner menu

#### Scenario: Secondary cataloging tools preserve FRBR Item vs Manifestation boundaries

- **GIVEN** an owner interacting with `ReadingDurationCard`, `Collection status`, `Item status`, `Named Collections`, `Linked Open Data`, or `Print QR Code` on `/item/[id]`
- **WHEN** a state update or navigation occurs
- **THEN** reading sessions, shelf availability, progress, visibility, and QR labels remain scoped strictly to the `Item` (`F5`) record while cover provenance, external LOD semantic links, and cover replacement remain scoped to `Manifestation` (`F3`) / `Work` (`F1`)

### Requirement: Removal of Redundant FRBR Raw-ID Accordion While Preserving Semantic Breadcrumb
The `/item/[id]` action panel (`ItemActions`) SHALL NOT render the redundant `"FRBR Hierarchy"` collapsible raw-ID drawer (`Work ID`, `Expression ID`, `Manifestation ID`, `Item ID`). The `/item/[id]` header (`ItemHeader`) SHALL strictly preserve the clickable semantic FRBR breadcrumb (`Work -> Expression -> Manifestation -> Item`) and `SidebarFrbrInfo` format/language summary.

#### Scenario: Raw-ID FRBR Hierarchy accordion is absent from item actions

- **GIVEN** an authenticated user viewing `/item/[id]`
- **WHEN** the item detail page renders
- **THEN** no `"FRBR Hierarchy"` toggle button or raw `#id` definition list (`Work ID`, `Expression ID`, `Manifestation ID`, `Item ID`) is rendered in `ItemActions`

#### Scenario: Semantic FRBR breadcrumb remains clickable in item header

- **GIVEN** a physical item linked to a `Work`, `Expression`, and `Manifestation`
- **WHEN** the user views `/item/[id]`
- **THEN** `<nav aria-label="FRBR Hierarchy">` in `ItemHeader` renders clickable links to `/work/<id>`, `/expression/<id>`, and `/manifestation/<id>` with `Item` marked as `aria-current="page"`

### Requirement: UI RBAC Alignment on Item Actions and History Tab
UI controls on `/item/[id]` SHALL strictly match backend ownership and RBAC enforcement:

- `"Remove from library"` (`delete:item`), `"Replace Cover"` / `"Contribute Cover"` (`upload:cover`), and owner-scoped `"Regenerate Cover"` (`regenerate:cover`) SHALL only render when `(isOwner || isAdmin)` (or when the user holds curator `write:metadata` permission for catalog-level `"Regenerate Cover"`).
- The `"Admin Actions"` dropdown trigger SHALL NOT render for a non-owner authenticated user who holds only default `"user"` role permissions.
- The `History` tab in `ItemTabs` SHALL render only for physical items (`item.id > 0`) when the viewer is `isOwner || isBorrower || isAdmin`.
- Virtual wishlist items (`item.id <= 0`) SHALL suppress `"Explore Graph"`, `"Print QR Code"`, and `History`.

#### Scenario: Standard non-owner user views another collector's public item

- **GIVEN** an authenticated non-owner user with default `"user"` permissions (`write:item`, `update:item`, `delete:item`, `upload:cover`, `regenerate:cover`, `escalate:request`) viewing another user's public `/item/[id]`
- **WHEN** the page renders
- **THEN** `"Admin Actions"`, `"Remove from library"`, `"Replace Cover"`, `"Regenerate Cover"`, and the `History` tab are NOT rendered
- **AND** `"Requests"` / `"Ask custodians for help"` remains available to the non-custodian user

#### Scenario: Virtual wishlist item suppresses physical-only actions

- **GIVEN** a collector viewing a virtual wishlist item (`/item/-4`)
- **WHEN** the page renders
- **THEN** `"Explore Graph"`, `"Print QR Code"`, and the `History` tab are NOT rendered

### Requirement: Complete Item Detail Localization with Polish Sentence Case
All user-visible strings on `/item/[id]` (`ItemHeader`, `SidebarActions`, and `ItemActions`, including `"Explore Graph"`, polymorphic consumption CTAs, secondary action menus, `"Admin Actions"`, and `"Replace Cover"`/`"Contribute Cover"`) SHALL be resolved via `next-intl` translation keys under `ItemDetail.*` and `graph.*` with full key parity between `frontend/messages/en.json` and `frontend/messages/pl.json`. All Polish strings in `pl.json` MUST follow sentence-case rules (capitalizing only the first word and proper nouns or acronyms such as `FRBR`, `QR`, `LEGO`).

#### Scenario: Polish locale renders sentence-case item detail controls

- **GIVEN** a collector using the `pl` locale on `/item/[id]`
- **WHEN** the page renders item actions and menus
- **THEN** `"Explore Graph"` renders as `"Eksploruj graf"`, `"Admin Actions"` renders as `"Akcje administratora"`, `"Replace Cover"` renders as `"Zastąp okładkę"`, and `"Now Listening"` renders as `"Teraz słucham"`
- **AND** every new `ItemDetail.*` key in `pl.json` uses sentence case rather than English-style Title Case

### Requirement: Compressed Linked Open Data Disclosure and Admin Actions Relocation
The `/item/[id]` detail page SHALL NOT render an expanded `<SemanticLinks />` card inside `DetailsTab` or a standalone `<ItemActions />` block between `ItemTabs` and `ItemSidebar`. Instead, both `Linked Open Data` and `Admin Actions` (together with `Requests` / escalation access where permitted) SHALL live in the bottom collapsible accordion stack below `Additional Scans`, `Named Collections`, and `Taxonomy`, collapsed by default on initial render. When expanded, `SemanticLinks` SHALL use a compact, borderless layout (no outer `<Card>` chrome or tall dashed empty box) displaying concise authority badges/links and the `Scan External LOD` trigger. All RBAC rules (`Admin Actions` hidden from non-custodian standard non-owners, `History` hidden from non-owners/virtual items) SHALL remain unchanged.

#### Scenario: Mobile layout keeps owner shelf controls immediately below metadata without LOD or Admin bloat

- **GIVEN** an authenticated owner or custodian viewing `/item/[id]` on a mobile viewport (`390x844`)
- **WHEN** the page initially renders
- **THEN** `DetailsTab` ends cleanly after metadata and series info without a tall `Linked Open Data` card
- **AND** `SidebarStatusBadges`, `Availability & Condition`, `Progress`, `Edit Metadata`, and `Manage` appear immediately before the collapsed accordion stack containing `Linked Open Data` and `Admin Actions` at the bottom

#### Scenario: Expanding compressed Linked Open Data accordion row reveals compact authorities and scan CTA

- **GIVEN** an item with a `manifestation_id` and `0` or more external authority links
- **WHEN** the user clicks the collapsed `"Linked Open Data"` accordion toggle at the bottom of the sidebar stack
- **THEN** the disclosure expands inline without an outer `<Card>` border or tall dashed placeholder, showing either a single-line empty hint + `"Scan External LOD"` button or compact authority link rows with confidence and delete controls (when `canEdit` is true)

#### Scenario: Expanding Admin Actions accordion preserves custodian menu, Requests, and pending escalation visibility without double dropdown

- **GIVEN** a custodian or owner with metadata/cover/delete permissions (or a non-custodian user eligible to submit help requests)
- **WHEN** viewing the bottom accordion stack on `/item/[id]`
- **THEN** expanding the `"Admin Actions"` disclosure directly reveals inline action buttons (`Refetch Metadata`, `Edit FRBR`, `Refetch Cover`, `Regenerate Cover`, `Edit Cover Art`, `Remove from library`) without a redundant nested `"Admin Actions"` dropdown button
- **AND** when only non-custodian help requests apply, the accordion header reads `"Help Requests"` instead of `"Admin Actions"`, while a standard non-owner user lacking both admin and escalation permissions sees NO `"Admin Actions"` row at all

#### Scenario: ItemHeader renders media badge, title/authors first, then single-row Primary CTA + Explore Graph

- **GIVEN** an authenticated owner viewing `/item/[id]` on mobile (`390x844`)
- **WHEN** `ItemHeader` renders above the fold
- **THEN** the media badge appears directly beneath the FRBR breadcrumb, followed by the `<h1>` title and authors, followed by a unified action row leading with the Primary CTA (`Mark as Read` / `Log Reading Progress`) beside `Explore Graph`, above a tightly padded Quick Meta block

### Requirement: Strict WRITE_METADATA Gating on LOD Scan Trigger, Safe Sync Cover Upload Fallback, and Escalation i18n Parity

1. **`SemanticLinks` `"Scan External LOD"` RBAC Alignment (`frontend/components/manifestation/semantic-links.tsx`, `frontend/components/item/item-sidebar.tsx`):** `SemanticLinks` MUST render the `"Scan External LOD"` button (`scanButton` in both compact and full card modes) ONLY when `canEdit` is `true`, and `ItemSidebar` (along with `/work/[id]` and `/manifestation/[id]` callers) MUST compute `canEdit` strictly from `hasPermission(PermissionName.WRITE_METADATA)` (never `isOwner || hasEditPermission`), matching backend `POST /api/manifestations/<id>/reconcile` enforcement (`@require_permission(PermissionName.WRITE_METADATA)`).
2. **Synchronous Cover Upload Fallback Safety (`app/api/manifestations.py`):** When `POST /api/manifestations/<id>/cover/upload` falls back to synchronous `process_tier1_task(...)` execution because Celery/Valkey broker dispatch fails, it MUST pass `llm_permissions={}` so Tier 1 processing never crashes on missing keyword arguments or triggers unintended LLM calls.
3. **Localized Escalation Labels in `ItemActions` (`frontend/components/item/item-actions.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`):** Residual hardcoded escalation strings in `ItemActions` (`"Help Request:"` badge prefix and standalone `"Requests"` header) MUST resolve through `ItemDetail.*` translation keys with Polish sentence-case parity in `pl.json`.

#### Scenario: Anonymous visitor or standard item owner without write:metadata does not see Scan External LOD

- **GIVEN** an anonymous visitor OR an authenticated standard item owner (`write:item`, `upload:cover`, but lacking `write:metadata`) expanding `"Linked Open Data"` on `/item/[id]` or viewing `/manifestation/[id]`
- **WHEN** `SemanticLinks` renders
- **THEN** existing accepted authority links are displayed read-only and `"Scan External LOD"` is NOT rendered
- **AND** when a Custodian or Admin holding `write:metadata` views the same section, `"Scan External LOD"` IS rendered and operable

#### Scenario: Synchronous cover upload fallback succeeds when Valkey broker is unavailable

- **GIVEN** Valkey/Celery task dispatch raises an operational error during `POST /api/manifestations/<id>/cover/upload`
- **WHEN** the endpoint executes the synchronous `process_tier1_task` fallback
- **THEN** `process_tier1_task` is invoked with `llm_permissions={}` and completes HTTP `200` cover replacement without raising `TypeError`
