## Why

In `v0.8.3`, manual item entry introduced a dual-source cover picker enabling collectors to choose between camera snapshot and selecting an existing image file from their device gallery. However, on the manifestation and item detail pages (`frontend/components/manifestation/manifestation-actions.tsx`, `frontend/components/item/item-actions.tsx`, and `frontend/components/item/sidebar/sidebar-actions.tsx`), the "Contribute Cover" / "Replace Cover" action button is still hard-wired solely to the camera trigger (`CameraCapture`). Collectors browsing on desktop or mobile devices who already have a high-resolution cover photo in their local photo library cannot contribute it without photographing a physical book in front of a camera.

Unifying the Contribute Cover / Replace Cover button into a single-button trigger with a unified source selection modal dialog (Take Photo vs. Choose from Gallery) eliminates mobile double-prompt friction and redundant buttons across both manifestation action bars and manual item entry, while preserving strict FRBR ontological boundaries: image uploads enrich the Manifestation level (F3), update manifestation `cover_url`, and initiate asynchronous PIL normalization without polluting Work (F1) or Item (F5) condition records.

## What Changes

- Introduce `CoverUploadPicker` replacing hard-wired `CameraCapture` in manifestation and item actions (`manifestation-actions.tsx`, `item-actions.tsx`, `sidebar-actions.tsx`) with a single-button trigger opening a direct source selection modal dialog ("Take Photo", "Choose from Gallery", "Cancel").
- Unify `frontend/components/scanner/manual-entry-form.tsx` from redundant twin buttons ("Choose from Photos" and "Take Photo") to a single "Upload Cover" button opening the unified source selection modal.
- Ensure consistent upload handling and optimistic status updates (`cover_status: "processing"`) across both upload sources.
- Update frontend component unit tests (`cover-upload-picker.test.tsx` and `manual-entry-form.test.tsx`) verifying single-button direct dialog opening, input triggering, and replacement confirmations.

## Capabilities

### New Capabilities
- `dual-source-contribute-cover`: Capability to upload manifestation cover images by either capturing a photo via device camera or selecting an existing file from the local gallery/filesystem from a single-button modal dialog across manifestation actions and manual entry.

## Impact

- Affects `frontend/components/scanner/cover-upload-picker.tsx`, `frontend/components/scanner/manual-entry-form.tsx`, `frontend/components/manifestation/manifestation-actions.tsx`, `frontend/components/item/item-actions.tsx`, and `frontend/components/item/sidebar/sidebar-actions.tsx`.
- Reuses existing backend upload endpoints (`/api/v1/manifestations/{id}/cover` and `/api/v1/items/{id}/cover`) and image processing pipeline.
- Zero database schema migrations required.
