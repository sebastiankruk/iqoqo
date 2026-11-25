## MODIFIED Requirements

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

## ADDED Requirements

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
