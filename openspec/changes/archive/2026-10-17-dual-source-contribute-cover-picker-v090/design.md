## Context

In `v0.8.3`, `CameraCapture` was originally designed around video stream acquisition on mobile devices. While manual entry received file picker support (`file-input`), manifestation actions in `manifestation-actions.tsx` and `sidebar-actions.tsx` still render `CameraCapture` directly with a camera icon. Users on laptops or mobile devices often have saved cover art files rather than physical books ready for camera scanning.

## Goals / Non-Goals

**Goals:**
- Provide a seamless single-button interaction for "Contribute Cover" / "Replace Cover" that lets users easily choose between "Take Photo" and "Upload File".
- Preserve existing upload completion callbacks, optimistic cache updates (`cover_status: "processing"`), and toast notifications.
- Maintain existing replacement warning dialogs when `cover_url` is already present.

**Non-Goals:**
- Modifying backend image resizing, watermarking, or PIL processing pipelines.
- Replacing the advanced canvas-based Cover Art Editor (`/admin/content?tab=cover-art`).

## Decisions

### 1. Unified Single Button with Source Selection Dialog (No Dropdown Menu, No Dual Buttons)
- **Decision:** Use a single trigger button ("Contribute Cover", "Replace Cover", or "Upload Cover") across both manifestation actions (`CoverUploadPicker`) and manual item entry (`ManualEntryForm`) that directly opens an accessible modal dialog (`AlertDialog`) with explicit options:
  1. `Take Photo` (triggers hidden `<input type="file" accept="image/*" capture="environment" />`)
  2. `Choose from Gallery` / `Choose from Photos` (triggers hidden `<input type="file" accept="image/*" />`)
  3. `Cancel`
- **Rationale:** Mobile browsers (iOS Safari, Android Chrome) trigger system file/camera bottom sheets when activating file inputs. Nesting this inside a custom `DropdownMenu` created a frustrating double-prompt interaction on mobile. Similarly, placing twin buttons side-by-side in manual entry doubled button density needlessly. A single button opening a clear modal gives uniform, uncluttered UX across desktop and mobile.

### 2. Reuse Existing Upload Pipeline
- **Decision:** Route file selections through the same POST `/api/v1/manifestations/{id}/cover` endpoint used by `CameraCapture`.
- **Rationale:** Guarantees identical server-side validation (`allowed_file`, size limits, PIL normalization) and telemetry.

## Risks / Trade-offs

- **[Risk] Browser Engine File/Camera Intent Behavior (Chrome vs. Firefox):**
  - **Chrome (Android/Desktop):** Honors `capture="environment"` strictly by launching the camera directly on mobile, while non-capture file inputs open the gallery/file picker.
  - **Firefox (GeckoView on Android):** Routes all file inputs through the Android system intent chooser regardless of `capture="environment"`, presenting both Camera and Files options at the OS level. This is a known browser engine limitation in GeckoView. The unified modal remains functional and graceful: Chrome users get direct camera vs. gallery routing, while Firefox users can select either action safely without breaking.
