## MODIFIED Requirements

### Requirement: Dual-Source Cover Contribution on Manifestation and Item Surfaces
The manifestation and item action surfaces (`manifestation-actions.tsx` and the consolidated item action surface on `/item/[id]`) MUST enable authorized users with `upload:cover` permission (and `(isOwner || isAdmin)` on item surfaces) to contribute or replace manifestation covers when a valid `manifestation_id` is present, by either capturing a photo via camera or selecting an existing image file from device storage, accessible from a single unified UI trigger per page that opens a source selection modal dialog.

On `/item/[id]`, `"Replace Cover"` / `"Contribute Cover"` MUST NOT be duplicated across both `SidebarActions` and `ItemActions`, MUST be omitted when `item.manifestation_id` is absent, and MUST detect existing cover presence via `item.cover_url || item.manifestation_meta?.["cover_url"] || item.meta?.["cover_url"]` (and `manifestation.cover_url || manifestation.meta?.["cover_url"]` on manifestation surfaces) to display `"Replace Cover"` with an overwrite warning when a cover exists. If the trigger is invoked from a `DropdownMenu`, the picker's `AlertDialog` and file `<input>` elements MUST remain mounted outside `DropdownMenuContent` so closing the menu never unmounts the dialog or cancels file selection.

The upload transport, dialog activation, client cache, and backend queue fallback MUST operate reliably end-to-end:
- `FormData` requests MUST NOT send a hardcoded boundary-less `"Content-Type": "multipart/form-data"` header; the API client MUST strip `Content-Type` for `FormData` payloads so the runtime generates `multipart/form-data; boundary=...`.
- Image resizing in `CoverUploadPicker` MUST execute inside `try/finally` so failures never leave the trigger stuck in an uploading state, `inline` and `buttonClassName` props MUST be honored, and camera/gallery `<input type="file">` controls MUST use accessible off-screen styling (`sr-only`) and activate cleanly without Radix `AlertDialog` teardown/focus-lock cancellation on desktop browsers or mobile WebViews.
- On upload completion, client handlers MUST optimistically update/invalidate React Query caches (`queryKeys.item(id)`, `queryKeys.manifestation(id)`, `["items"]`) rather than relying solely on `router.refresh()`, `useManifestationWithPolling` MUST poll whenever `cover_status` is `"pending"` OR `"processing"` (with no competing duplicate `useQuery` in `ItemActions`), and `ItemHeader` MUST read `getCoverTimestamp(meta, item.meta)` so updated `cover_status_updated_at` timestamps bust cached cover URLs across all cover surfaces.
- On the backend, `process_cover_pipeline` MUST ensure `COVERS_DIR` exists before writing, and when `POST /api/manifestations/<id>/cover` encounters `task_id is None` (queue unavailable), it MUST execute synchronous Tier 1 user-photo processing inline so the cover transitions immediately to `cover_status: "ready"` with updated `cover_url` and `cover_status_updated_at` instead of stranding the raw file in `RAW_DIR` as `"pending"`.

#### Scenario: User selects file upload from contribute cover trigger

- **GIVEN** an authorized user with `upload:cover` permission viewing a manifestation (or owned item with `manifestation_id`) without a cover
- **WHEN** the user activates the single consolidated `"Contribute Cover"` trigger
- **THEN** a source selection modal dialog opens with `"Take Photo"`, `"Choose from Gallery"`, and `"Cancel"`
- **WHEN** the user chooses `"Choose from Gallery"`
- **THEN** a native file picker opens reliably (without being cancelled by dialog focus teardown) filtering image MIME types (`image/jpeg`, `image/png`, `image/webp`, `image/*`)
- **WHEN** an image file is selected
- **THEN** the image is uploaded as `FormData` without a hardcoded boundary-less `Content-Type` header to `POST /api/manifestations/<id>/cover`, React Query `queryKeys.item(id)` / `queryKeys.manifestation(id)` caches are updated and invalidated (setting optimistic `cover_status: "processing"` or immediate `"ready"`), and a success toast is displayed

#### Scenario: User replaces existing cover with confirmation

- **GIVEN** an owned or admin-managed item with `item.manifestation_id` whose cover is present via `item.cover_url`, `item.manifestation_meta.cover_url`, or `item.meta.cover_url`
- **WHEN** `/item/[id]` renders
- **THEN** exactly ONE `"Replace Cover"` trigger is exposed on the page (no duplicate trigger across `SidebarActions` and `ItemActions`)
- **WHEN** the user activates `"Replace Cover"`
- **THEN** a source selection dialog warns that the existing cover will be overwritten and prompts for camera or gallery selection (remaining mounted even if triggered from a dropdown menu)
- **WHEN** the user selects either camera or gallery file
- **THEN** the new cover image is uploaded, `useManifestationWithPolling` polls `"pending"` and `"processing"` states until `"ready"`, and `HeroBanner`, `SidebarCover`, and any header cover display the cache-busted updated cover via `cover_status_updated_at`

#### Scenario: Cover trigger suppressed when manifestation_id is absent

- **GIVEN** an item lacking `item.manifestation_id` (such as an unlinked or virtual item) viewed by an owner with `upload:cover` permission
- **WHEN** `/item/[id]` renders
- **THEN** the `"Replace Cover"` / `"Contribute Cover"` trigger is NOT rendered

#### Scenario: Backend executes synchronous Tier 1 fallback when task queue is unavailable

- **GIVEN** an authorized upload to `POST /api/manifestations/<id>/cover` while the Celery/Redis task queue is unavailable (`start_cover_processing` returns `None`)
- **WHEN** the endpoint validates and saves the uploaded cover image
- **THEN** the backend runs synchronous Tier 1 user-photo processing inline, writes the final cover image in `COVERS_DIR`, sets `manifestation.cover_url`, `cover_source = "user_photo"`, `cover_status = "ready"`, and updates `cover_status_updated_at`, returning the updated ready state instead of leaving the raw file stranded in `RAW_DIR` as `"pending"`
