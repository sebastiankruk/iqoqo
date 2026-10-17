## 1. UI Component Refactoring

- [x] 1.1 Create or adapt `CoverUploadPicker` component combining live camera stream and file gallery selector with replacement confirmation
- [x] 1.2 Update `frontend/components/manifestation/manifestation-actions.tsx` to replace single-mode `CameraCapture` with the dual-source picker
- [x] 1.3 Update `frontend/components/item/sidebar/sidebar-actions.tsx` and `item-actions.tsx` to utilize the dual-source cover contribution button

## 2. Testing & Verification

- [x] 2.1 Add Vitest component test for `CoverUploadPicker` verifying camera option vs file selection triggering
- [x] 2.2 Verify optimistic mutation cache update (`cover_status: "processing"`) upon file upload
- [x] 2.3 Verify replacement confirmation modal appears when existing cover is present
