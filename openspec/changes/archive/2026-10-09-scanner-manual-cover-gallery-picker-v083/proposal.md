## Why

Dev-note item (#v803): "adding Cover to manual entry must enable to pick existing image - not only camera". Release planning: v0.8.x, C53 (target v0.8.3).

User motivation:
> "on mobile when we create manual entry - we are only presented with camera view without ability to choose from photos I already have on my mobile - this is different to what happens when I contribute covers later on - while for manual override (which happens when item was not recognized or incorrectly recognized) I can have taken and edited the cover that is better than just snapping a photo of a cover"

Premises verified against code:
- **Confirmed: Scanner UX forces camera viewport.** In `frontend/app/scan/page.tsx:210`, the camera video stream occupies the full viewport. When scanning fails or manual entry is opened, the user has either snapped a raw camera frame or is presented with the manual entry form.
- **Confirmed: Weak file picker in `manual-entry-form.tsx`.** Lines 287-305 contain a single small outline button with an `sr-only` file input. There is no distinction between taking a live photo versus picking from the mobile photo library/gallery, and NO image preview is shown (only a tiny truncated text label showing the filename `formData.coverFile.name`).
- **Confirmed: Desired parity with cover contribution.** When contributing covers post-ingestion (in manifestation views and `MultiImageUploader`), users have explicit file selection and preview before upload. Manual override during scanning lacks this parity.

## What Changes

- **Dual Source Cover Picker:** In `frontend/components/scanner/manual-entry-form.tsx`, replace the single file input with explicit options:
  1. "Choose from Photos" / "Photo Library" (standard file picker targeting mobile gallery without `capture` constraint).
  2. "Take Photo" (triggering camera capture when camera is supported).
  3. "Use Camera Snapshot" (when a camera frame was already snapped during the scan session, e.g. `snappedCover`).
- **Visual Thumbnail Preview:** Add an interactive thumbnail preview showing the staged cover image (via `URL.createObjectURL`), with a "Replace" and "Remove" button, matching the visual language of `MultiImageUploader`.
- **Form State & Upload Binding:** Ensure the selected image binds cleanly into the submission payload in `frontend/app/scan/page.tsx:172` and uploads to `/manifestations/<id>/cover` with source `user_upload`.

## Capabilities

### New Capabilities

- `scanner-gallery-picker`: Allows collectors during manual item entry and override to pick existing edited cover photos from their device photo library/gallery with visual thumbnail preview.

### Modified Capabilities

None.

## Impact

- **Frontend:** `frontend/components/scanner/manual-entry-form.tsx`, `frontend/app/scan/page.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests:** Vitest component tests in `frontend/__tests__/components/scanner/manual-entry-form.test.tsx` verifying gallery selection, preview rendering, and submit payload binding.
