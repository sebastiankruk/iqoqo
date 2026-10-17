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

### 1. Unified Dropdown or Split-Action Trigger
- **Decision:** Wrap the primary "Contribute Cover" / "Replace Cover" button with a choice trigger (e.g., Shadcn `DropdownMenu` or a dual-mode trigger modal) providing explicit options:
  1. `Take Photo` (activates camera capture modal via media stream)
  2. `Choose File` (triggers hidden `<input type="file" accept="image/*" />`)
- **Rationale:** Keeps the button footprint clean on mobile and responsive sidebars while instantly disambiguating the source.

### 2. Reuse Existing Upload Pipeline
- **Decision:** Route file selections through the same POST `/api/v1/manifestations/{id}/cover` endpoint used by `CameraCapture`.
- **Rationale:** Guarantees identical server-side validation (`allowed_file`, size limits, PIL normalization) and telemetry.

## Risks / Trade-offs

- **[Risk] Mobile browser file vs camera ambiguity:** On many mobile browsers, `<input type="file" accept="image/*" />` natively offers "Camera" and "Photo Library". However, on desktop browsers, file inputs only open file dialogs while WebRTC camera capture provides live webcams. Providing an explicit dual-action menu serves both desktop and mobile flawlessly.
