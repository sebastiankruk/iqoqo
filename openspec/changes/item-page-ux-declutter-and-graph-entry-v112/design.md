## Context

See `proposal.md` for motivation and capability scope. On `/item/[id]`, `ItemPageClient` (`frontend/components/item/item-page-client.tsx`) currently renders `<aside><ItemSidebar /></aside>` before the main column (`<ItemHeader />`, `<ItemTabs />`, `<ItemActions />`), duplicates the cover image in both `SidebarCover` and `ItemHeader`, stacks 10+ ungrouped controls inside `SidebarActions`, places `"Explore Graph"` inside `ItemHeader` below the mobile sidebar stack, and buries the polymorphic primary consumption CTA (`"Now Listening"`, `"Log Reading Progress"`, `"Mark as Watched"`, `"Log Play"`) inside `ItemActions` at the bottom of the page below `ItemTabs`. Concurrently, `"Replace Cover"` fails end-to-end across duplicate triggers, missing `manifestation_id` and `cover_url` fallback guards, hardcoded `FormData` `Content-Type` headers, Radix `AlertDialog` close/click timing, `router.refresh()`-only cache handling, `"pending"`-only polling, and stranded backend uploads when Celery/Redis is unavailable.

Design constraints inherited from canonical specs and codebase architecture:
- **FRBR Ontological Boundaries:** `Work -> Expression -> Manifestation -> Item` must remain strict (`frbr-ontology`, `frbr-collection-navigation`). Cover mutations (`POST /api/manifestations/<id>/cover`) and cover provenance belong to `Manifestation` (`F3`); consumption status, reading duration (`ReadingDurationCard`), availability, visibility, and QR labels belong to `Item` (`F5`).
- **Sidebar Pure-Props Architecture:** `frontend/__tests__/components/item/sidebar/sidebar-architecture.test.ts` forbids `sidebar-cover.tsx`, `sidebar-status-badges.tsx`, `sidebar-lending-info.tsx`, `sidebar-identifiers.tsx`, `sidebar-actions.tsx`, and `sidebar-frbr-info.tsx` from importing `useItemSidebarActions` or React Context (`createContext` / `.Provider`).
- **Existing E2E Selector Continuity:** `audio_workflow.test.ts`, `lending_workflow.spec.ts`, and `frbr_type_change_workflow.spec.ts` rely on `select[aria-label="Collection status"]`, `select[aria-label="Item status"]`, `"Availability & Condition"`, `"Additional Scans"`, `"Request Loan"`, and `"Ask custodians for help"`.

## Goals / Non-Goals

**Goals:**
- Achieve `iqoqo-ux-auditor` compliance on `/item/[id]` across mobile (`390x844`) and desktop (`1280x800`): `<= 4` visible buttons per bar/container, `1` clear primary CTA per view, and `<= 3` clicks/taps for every core collector flow.
- Surface cover, semantic FRBR breadcrumb, `"Explore Graph"` (`graph.exploreGraph`), and the polymorphic primary consumption CTA above the fold on both mobile (`390x844`) and desktop (`1280x800`), with zero duplicate cover rendering.
- Fix `"Replace Cover"` / `"Contribute Cover"` reliably end-to-end across frontend trigger consolidation, `FormData` transport, Radix dialog/file-input activation, React Query cache/polling, and backend synchronous Tier 1 fallback.
- Convert `"Admin Actions"` on `/item/[id]` to a labeled Shadcn `DropdownMenu`, remove the redundant raw-ID `"FRBR Hierarchy"` accordion, align UI RBAC with backend ownership rules, and complete `next-intl` localization (`en.json` + sentence-case `pl.json`).

**Non-Goals:**
- Database schema changes or Alembic migrations (zero backend model changes required).
- Refactoring `/manifestation/[id]` (`ManifestationActions`) accordion layout beyond aligning cover polling (`"pending" | "processing"`), `cover_url` fallback, and `onUploadComplete` React Query invalidation where shared with `CoverUploadPicker`.
- Removing `"Replace Cover"` (explicitly rejected per `ORIGINAL_REQUEST.md`).
- Altering `ItemHeader`'s semantic FRBR breadcrumb (`frbr-collection-navigation`) or `ReadingDurationCard` (`item-reading-duration-tracking`).

## Decisions

### 1. Responsive Layout Order, Single Cover Rendering, and Above-the-Fold Primary CTA
- **Decision:** Reorder `ItemDetail`'s responsive grid (`item-page-client.tsx`) so on mobile (`< lg`), the main header summary renders first (`order-1 lg:order-2` on main column wrapper or split top summary header) while `<aside>` `ItemSidebar` renders `order-2 lg:order-1`. Eliminate duplicate covers by rendering `ItemHeader`'s cover only below `lg` (`lg:hidden`) and `SidebarCover` only at `lg+` (`hidden lg:flex lg:-mt-28`, removing `-mt-28` negative margin conflict on mobile). Extract or render the polymorphic primary consumption CTA (`data-testid="primary-consumption-cta"`, `variant="default"`) in `ItemHeader`'s top action row alongside `"Explore Graph"` (`data-testid="explore-graph-link"`, secondary outline styling) rather than at the bottom of `ItemActions`.
- **Alternatives Considered:**
  - *Alternative A — Duplicate `"Explore Graph"` and `"Now Listening"` inside `ItemSidebar` while keeping `<aside>` first on mobile:* Rejected because it preserves two cover images on mobile, splits CTA state across two components, and leaves the title and FRBR breadcrumb below the sidebar stack.
  - *Alternative B — Keep `"Now Listening"` in `ItemActions` at the bottom of the right column:* Rejected because `ItemTabs` (`ExtendedMetadata`, audio tracklists, series parts, `SemanticLinks`) regularly exceeds `800px`, pushing the primary CTA below the fold on both desktop and mobile.
- **Trade-offs:** Moving the polymorphic CTA into `ItemHeader` (or a shared `ItemPrimaryCta` subcomponent mounted in `ItemHeader`) requires updating `item-actions-polymorphism.test.tsx` and `item-header-actions.test.tsx` expectations, while keeping admin actions strictly out of `ItemHeader` as asserted by `item-header-actions.test.tsx:80`.

### 2. Secondary Owner Action Consolidation in `SidebarActions` (`<= 4` Buttons/Bar)
- **Decision:** Keep `Collection status` (`select[aria-label="Collection status"]`) and `Item status` (`select[aria-label="Item status"]`) directly visible in `SidebarActions`, plus `ReadingDurationCard` (for owned books) and `"Request Loan"` (for eligible non-owners). Consolidate owner secondary controls (`"Edit Metadata"`, `"Make Public"`/`"Hide from Public"`, `"Print QR Code"`, and `"Reassign Owner"` when permitted) into at most 2 visible bar items: primary quick edit (`"Edit Metadata"`) + a labeled `"Manage"` Shadcn `DropdownMenu` (`data-testid="sidebar-manage-menu"`). Collapse secondary cataloging editors (`Named Collections`, `TaxonomyEditor`, `MultiImageUploader` `"Additional Scans"`) under compact disclosure toggles (`<= 4` visible buttons in any container). Keep all state/mutations in `useItemSidebarActions` (`item-sidebar.tsx`), passing pure props to `SidebarActions`.
- **Alternatives Considered:**
  - *Alternative A — Collapse `Collection status` and `Item status` selects behind an edit modal:* Rejected because collectors frequently toggle shelf/progress state in 1 tap and existing Playwright specs (`audio_workflow.test.ts`, `lending_workflow.spec.ts`) interact directly with those `<select>` elements.
  - *Alternative B — Move sidebar state into a React Context:* Rejected because `sidebar-architecture.test.ts` explicitly prohibits `createContext` and `useItemSidebarActions` imports inside `components/item/sidebar/*`.

### 3. Remove Raw-ID `"FRBR Hierarchy"` Accordion and Convert `"Admin Actions"` to Labeled `DropdownMenu`
- **Decision:** Delete `isHierarchyOpen` and the raw-ID `<dl>` (`Work ID`, `Expression ID`, `Manifestation ID`, `Item ID`) from `ItemActions`, leaving `ItemHeader`'s `<nav aria-label="FRBR Hierarchy">` breadcrumb and `SidebarFrbrInfo` intact. Replace `ItemActions`'s `"Admin Actions"` collapsible button + inline grid (`isPanelOpen`) with a **labeled** Shadcn `DropdownMenu` (`data-testid="admin-actions-menu-trigger"`, text `"Admin Actions"` / `"Akcje administratora"`). Mount all confirmation `<AlertDialog>`s (`deleteConfirmOpen`, `regenerateConfirmOpen`) and any hoisted cover-picker `<AlertDialog>`/`<input type="file">` **outside** `<DropdownMenuContent>` at the component root, controlled via React state.
- **Alternatives Considered:**
  - *Alternative A — Unlabeled `[...]` icon overflow trigger:* Rejected (also barred by `user-requests-manifestation-layout` UX rationale) because collectors and administrators need clear semantic discovery (`"Admin Actions"`).
  - *Alternative B — Mount `<CoverUploadPicker>` directly inside `<DropdownMenuItem>`:* Rejected because selecting a Radix `DropdownMenuItem` closes and unmounts `DropdownMenuContent`, destroying `<AlertDialog>` and `<input type="file">` before the file-change event fires.

### 4. End-to-End `"Replace Cover"` Fix (Single Trigger, `FormData`, Dialog Timing, Polling, Backend Fallback)
- **Decision:**
  1. **Single Consolidated Trigger & Guards:** Render **exactly one** `"Replace Cover"` / `"Contribute Cover"` entry point on `/item/[id]` (hoisted as a single controlled `CoverUploadPicker` in `ItemSidebar` `"Manage"` menu or `SidebarCover` action for `(isOwner || isAdmin) && hasPermission(UPLOAD_COVER) && Boolean(item.manifestation_id)`, and removed as a duplicate from `ItemActions`, or vice versa—never rendered twice). Compute `hasCover` consistently via `Boolean(item.cover_url || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"])` (and `manifestation.cover_url || manifestation.meta?.["cover_url"]` on manifestation pages).
  2. **`FormData` Boundary Fix:** Remove hardcoded `headers: { "Content-Type": "multipart/form-data" }` in `cover-upload-picker.tsx:113` and update `apiClient` (`frontend/lib/api/client.ts`) request interceptor to delete `Content-Type` whenever `config.data instanceof FormData` so the runtime/browser automatically generates the multipart boundary. Move `resizeImageFile(...)` inside `try { ... } finally { setUploading(false); }` and destructure/apply `inline` + `buttonClassName`.
  3. **Radix `AlertDialog` + Native File Picker Activation:** Change file `<input>`s in `CoverUploadPicker` from `className="hidden"` (`display: none`) to `className="sr-only"`, and trigger `cameraInputRef.current?.click()` / `galleryInputRef.current?.click()` **before** closing/deferring `setConfirmOpen(false)` (closing cleanly once triggered or via `requestAnimationFrame`) so Radix `FocusScope`/`aria-hidden` cleanup never drops user activation in Safari or Capacitor WebViews.
  4. **React Query Cache & Polling Unification:** Replace `router.refresh()`-only `handleUploadComplete` in `useItemSidebarActions` (and `ManifestationDetailClient`) with optimistic `queryClient.setQueryData(queryKeys.item(id), ...)` (`cover_status: "processing"`, or `"ready"` + `cover_url` + `cover_status_updated_at` when backend returns sync-ready) and `queryClient.invalidateQueries` for `queryKeys.item(id)`, `queryKeys.manifestation(manifestationId)`, and `["items"]`. Update `useManifestationWithPolling` (`frontend/lib/api/hooks/catalog.ts:825`) to poll both `"pending"` and `"processing"` at `3000ms` (including `meta.cover_status`), remove the duplicate competing `useQuery` in `ItemActions:98-112`, and update `ItemHeader:92` to call `getCoverTimestamp(meta, item.meta)`.
  5. **Backend Synchronous Tier 1 Fallback:** Ensure `os.makedirs(COVERS_DIR, exist_ok=True)` inside `process_cover_pipeline` (`app/utils/covers.py`). In `POST /api/manifestations/<id>/cover` (`app/api/manifestations.py:965`), when `start_cover_processing(...)` returns `None` (Celery/Redis unavailable), execute synchronous Tier 1 user-photo processing (`process_cover_pipeline(..., user_image_path=filepath)` or inline resize + badge + save to `COVERS_DIR/{identifier}_user.jpg`), updating `manifestation.cover_url`, `cover_source="user_photo"`, `cover_status="ready"`, and `cover_status_updated_at`, and returning the `"ready"` cover payload instead of stranding the raw file in `RAW_DIR` as `"pending"`.
- **Alternatives Considered:**
  - *Backend `503` fail-fast on `task_id is None` (matching `regenerate_cover`):* Rejected because user-supplied photo processing requires zero external APIs (<50ms local PIL resize + badge) and single-container/no-Redis deployments must still allow collectors to replace covers.
  - *Keep per-component polling `useQuery` inside `ItemActions`:* Rejected because `ItemActions` returns `null` when `!profile` and duplicated `useManifestationWithPolling` observers on `queryKeys.item(id)`.

### 5. RBAC Alignment & Sentence-Case i18n
- **Decision:** Gate `ItemActions` `"Remove from library"` on `(isOwner || isAdmin) && hasPermission(DELETE_ITEM)`, gate `"Replace Cover"` on `(isOwner || isAdmin) && hasPermission(UPLOAD_COVER) && Boolean(item.manifestation_id)`, gate `"Regenerate Cover"` on `(isOwner || isAdmin || hasPermission(WRITE_METADATA)) && hasPermission(REGENERATE_COVER)`, compute `showAdminActions` strictly from those gated flags (hiding `"Admin Actions"` from non-owner default `"user"` viewers), and restrict `ItemTabs` `History` tab to `item.id > 0 && (isOwner || isBorrower || isAdmin)`. Externalize all hardcoded English strings in `ItemHeader`, `SidebarActions`, and `ItemActions` under `ItemDetail.*` and `graph.exploreGraph` with Polish sentence case in `frontend/messages/pl.json`.

## Full-Page DOM Layout Snapshot

### Mobile (`390x844`, `< lg`) — Before vs. After

```text
BEFORE (390x844)                              AFTER (390x844)
-------------------------------------------   -------------------------------------------
1. Navbar                                     1. Navbar
2. HeroBanner (200px)                         2. HeroBanner (200px, compact breadcrumb)
3. <aside> ItemSidebar (FULL STACK ~1,200px)  3. <main> ItemHeader (ABOVE THE FOLD <= 844px)
   - SidebarCover (-mt-28) [COVER #1]            - Single Cover (lg:hidden) [ONLY COVER]
   - SidebarStatusBadges                         - nav[aria-label="FRBR Hierarchy"] breadcrumb
   - SidebarLendingInfo / Identifiers            - Media Badge + [Explore Graph] (outline)
   - SidebarActions (10+ ungrouped controls:     - Title <h1> + Author links + Quick Meta
     Select x2, Edit, Public, QR, Replace        - [Primary CTA: Now Listening / Log Reading
     Cover #1, MultiImageUploader, Named           Progress / Mark as Watched / Log Play]
     Collections, TaxonomyEditor, Reassign)        (OR Request Loan for eligible non-owner)
   - ReadingDurationCard                      4. <aside> ItemSidebar (order-2 lg:order-1)
   - SidebarFrbrInfo                             - SidebarCover (hidden lg:flex) [not rendered]
4. <main> ItemHeader (~1,300px+ down!)           - SidebarStatusBadges + Lending + Identifiers
   - Duplicate Cover Image [COVER #2]            - SidebarActions (<= 4 buttons/bar:
   - FRBR Breadcrumb                               Select x2 + Edit Metadata + [Manage v] menu;
   - Media Badge + [Explore Graph]                 collapsible Organize & Scans disclosure)
   - Title + Quick Meta                          - ReadingDurationCard + SidebarFrbrInfo
5. ItemTabs (Details/Reviews/Gallery/History) 5. ItemTabs (Details/Reviews/Gallery/History)
6. ItemActions (BOTTOM OF PAGE)               6. ItemActions (compact footer)
   - [Now Listening] (buried at bottom!)         - Requests accordion + pending card (if eligible)
   - [FRBR Hierarchy] (raw IDs)                  - Labeled [Admin Actions v] DropdownMenu
   - [Requests] / [Admin Actions] (+ Replace       (hoisted AlertDialogs & single CoverUploadPicker)
     Cover #2 + 6 inline buttons)
```

### Desktop (`1280x800`, `lg+`) — Before vs. After

```text
BEFORE (1280x800)                             AFTER (1280x800)
-------------------------------------------   -------------------------------------------
Left 30% (<aside> ItemSidebar)                Left 30% (<aside> ItemSidebar, lg:order-1)
- SidebarCover [COVER #1] + Provenance        - SidebarCover (hidden lg:flex, -mt-28) [ONLY COVER]
- StatusBadges + Lending + Identifiers        - CoverProvenance + StatusBadges + Lending + IDs
- 10+ ungrouped SidebarActions controls       - Collection & Progress <select>s + Edit + [Manage v]
- ReadingDurationCard + SidebarFrbrInfo       - Collapsed Organize/Scans + ReadingDuration + FRBRInfo

Right 70% (<main>)                            Right 70% (<main>, lg:order-2)
- ItemHeader:                                 - ItemHeader (ABOVE 800px FOLD):
  - Duplicate Cover [COVER #2] (left 1/4)       - FRBR Breadcrumb (Work > Expr > Manif > Item)
  - FRBR Breadcrumb + Badge + Explore Graph     - Media Badge + [Explore Graph] (secondary)
  - Title + Meta                                - Title + Authors + Quick Meta
- ItemTabs (600-1400px tall)                    - [Primary CTA: Now Listening / Log Reading Progress]
- ItemActions (BELOW 800px FOLD):             - ItemTabs (Details / Reviews / Gallery / History)
  - [Now Listening] (buried below tabs!)      - ItemActions (compact footer):
  - [FRBR Hierarchy] (raw IDs)                  - Requests (non-custodians) + [Admin Actions v] menu
  - [Requests] + [Admin Actions] accordion
```

## Interaction Friction Map

| Collector Flow | Before (Taps & Failure Mode) | After (Taps & Target Behavior) | Max Taps |
|---|---|---|---|
| **Start Listening / Reading** (`"Now Listening"` / `"Log Reading Progress"`) | Scroll past 10+ sidebar blocks & `ItemTabs` -> **1 tap** (below fold / bottom of mobile page) | Visible above fold in `ItemHeader` -> **1 tap** (`PATCH /api/items/<id>`) | **1** (`<= 3`) |
| **Open Relation Graph** (`"Explore Graph"`) | Scroll ~1,300px on mobile past sidebar + duplicate cover -> **1 tap** | Visible above fold in `ItemHeader` -> **1 tap** (`/graph?type=item&id=<id>`) | **1** (`<= 3`) |
| **Update Shelf / Progress** (`Collection status` / `Item status`) | Direct `<select>` in sidebar -> **2 taps** (open + choose) | Direct `<select>` in sidebar -> **2 taps** (preserved) | **2** (`<= 3`) |
| **Replace Cover** (`"Replace Cover"`) | Duplicate triggers, missing guards, `FormData`/dialog failure, stale cache (broken) | Open `"Manage"` / `"Admin Actions"` -> `"Replace Cover"` (1–2) -> `"Choose from Gallery"`/`"Take Photo"` (1) -> file select -> optimistic + polled refresh | **3** (`<= 3`) |
| **Print QR / Make Public** | Direct sidebar buttons among 10+ controls -> **1 tap** | Open `"Manage"` menu -> `"Print QR Code"` / `"Hide from Public"` -> **2 taps** | **2** (`<= 3`) |
| **Admin: Remove from Library** | Scroll to bottom -> Expand `"Admin Actions"` -> `"Remove from library"` -> Confirm (**4 steps**, leaked to non-owners) | Open `"Admin Actions"` dropdown -> `"Remove from library"` -> Confirm `AlertDialog` (**3 steps**, owner/admin only) | **3** (`<= 3`) |

## Risks / Trade-offs

- **Existing Vitest Selector Churn:** Existing tests (`item-actions.test.tsx`, `item-actions-polymorphism.test.tsx`, `item-sidebar.test.tsx`, `sidebar-baseline.test.tsx`, `sidebar/sidebar-actions.test.tsx`) assert inline English labels (`"Edit Metadata"`, `"Make Public"`, `"Print QR Code"`) and click `"Admin Actions"` expecting an inline panel rather than a Radix `DropdownMenu` portal. -> *Mitigation:* Explicitly schedule updates to those Vitest specs in `tasks.md` while keeping `data-testid="explore-graph-link"`, `data-testid="qrcode-btn"`, and `select[aria-label="Collection status" | "Item status"]` stable.
- **Radix `DropdownMenu` + `AlertDialog` / File Input Unmount:** Closing a `DropdownMenu` unmounts `DropdownMenuContent` immediately; hosting `CoverUploadPicker` or `AlertDialog` inside it breaks file selection and focus management. -> *Mitigation:* Hoist all `AlertDialog`s and `CoverUploadPicker`'s dialog/inputs outside `DropdownMenuContent`, using `sr-only` inputs and safe `.click()` activation before modal teardown.
- **Synchronous Cover Fallback CPU on Web Worker:** Running Tier 1 `process_cover_pipeline` synchronously when `task_id is None` executes image decode/resize/save inside the Flask request thread. -> *Mitigation:* Tier 1 user-photo path performs only local Pillow resize + JPEG write + badge overlay (<50ms, no external HTTP or LLM calls), preventing stranded `RAW_DIR` files when Celery/Redis is down.
- **Polish Sentence-Case & Missing Key Drift:** Introducing new `ItemDetail.*` keys risks Title Case translations or missing `pl.json` keys. -> *Mitigation:* Include an automated `en.json` vs `pl.json` key-parity and sentence-case verification task in `tasks.md`.

## Open Questions

None. All behavioral decisions (keeping `"Replace Cover"` and fixing it end-to-end, labeled `"Admin Actions"` dropdown, removing the redundant raw-ID `"FRBR Hierarchy"` accordion while preserving `ItemHeader` breadcrumb, and synchronous Tier 1 fallback when `task_id is None`) are resolved by `proposal.md` and the delta specs.
