## Why

In `v0.8.3`, manual item entry introduced a dual-source cover picker enabling collectors to choose between camera snapshot and selecting an existing image file from their device gallery. However, on the manifestation and item detail pages (`frontend/components/manifestation/manifestation-actions.tsx`, `frontend/components/item/item-actions.tsx`, and `frontend/components/item/sidebar/sidebar-actions.tsx`), the "Contribute Cover" / "Replace Cover" action button is still hard-wired solely to the camera trigger (`CameraCapture`). Collectors browsing on desktop or mobile devices who already have a high-resolution cover photo in their local photo library cannot contribute it without photographing a physical book in front of a camera.

Unifying the Contribute Cover / Replace Cover button into a dual-source trigger with a combined dropdown or unified modal satisfies user convenience while preserving strict FRBR ontological boundaries: image uploads enrich the Manifestation level (F3), update manifestation `cover_url`, and initiate asynchronous PIL normalization without polluting Work (F1) or Item (F5) condition records.

## What Changes

- Refactor `CameraCapture` and manifestation/item actions to support dual-mode cover upload: snapping a photo via camera or selecting an existing image file from the device gallery/filesystem.
- In `frontend/components/manifestation/manifestation-actions.tsx` and `frontend/components/item/sidebar/sidebar-actions.tsx`, enhance the "Contribute Cover" / "Replace Cover" control to present a unified action menu or popover allowing immediate choice between "Take Photo" and "Choose from Gallery".
- Ensure consistent upload handling and optimistic status updates (`cover_status: "processing"`) across both upload sources.
- Add frontend component unit tests verifying camera vs. file input triggering and replacement confirmation dialogs.

## Capabilities

### New Capabilities
- `dual-source-contribute-cover`: Capability to upload manifestation cover images by either capturing a photo via device camera or selecting an existing file from the local gallery/filesystem within the same UI trigger.

## Impact

- Affects `frontend/components/manifestation/manifestation-actions.tsx`, `frontend/components/item/item-actions.tsx`, and `frontend/components/item/sidebar/sidebar-actions.tsx`.
- Reuses existing backend upload endpoints (`/api/v1/manifestations/{id}/cover` and `/api/v1/items/{id}/cover`) and image processing pipeline.
- Zero database schema migrations required.
