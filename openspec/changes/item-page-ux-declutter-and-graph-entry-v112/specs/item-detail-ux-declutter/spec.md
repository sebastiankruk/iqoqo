## Purpose

Declutters the physical item detail view (`/item/[id]`) across mobile and desktop viewports by surfacing the single primary consumption CTA and semantic FRBR navigation above the fold, enforcing action density limits, removing redundant raw-ID hierarchy blocks, tightening UI RBAC visibility, and ensuring full English and Polish sentence-case localization.

## ADDED Requirements

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
Every visible action bar or control container on `/item/[id]` SHALL display at most 4 simultaneously visible buttons (`<= 4`), and every core collector task (updating collection/progress status, logging reading/listening progress, opening the FRBR graph, editing metadata, printing a QR code, or replacing a cover) SHALL be reachable in at most 3 clicks/taps. Owner state `<select>` controls (`Collection status`, `Item status`) and `ReadingDurationCard` (for owned books) SHALL remain directly accessible, while secondary owner controls (`Edit Metadata`, `Make Public`/`Hide from Public`, `Print QR Code`, `Reassign Owner` when permitted, and `Named Collections` / `Taxonomy` / `Additional Scans`) SHALL be grouped into compact overflow or disclosure controls while keeping sidebar presentation components pure-props (no direct hook or React Context imports).

#### Scenario: Owner views consolidated sidebar and header action bars
- **GIVEN** an authenticated owner with metadata and cover permissions viewing `/item/[id]`
- **WHEN** inspecting every visible action bar and sidebar container on initial render
- **THEN** no visible bar or action container exposes more than 4 simultaneous buttons
- **AND** `Collection status` and `Item status` `<select>` controls remain directly operable without extra modal hops
- **AND** `Edit Metadata`, `Make Public`/`Hide from Public`, and `Print QR Code` remain reachable within `<= 3` clicks via the consolidated owner menu

#### Scenario: Secondary cataloging tools preserve FRBR Item vs Manifestation boundaries
- **GIVEN** an owner interacting with `ReadingDurationCard`, `Collection status`, `Item status`, `Named Collections`, or `Print QR Code` on `/item/[id]`
- **WHEN** a state update or navigation occurs
- **THEN** reading sessions, shelf availability, progress, visibility, and QR labels remain scoped strictly to the `Item` (`F5`) record while cover provenance and cover replacement remain scoped to `Manifestation` (`F3`)

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
