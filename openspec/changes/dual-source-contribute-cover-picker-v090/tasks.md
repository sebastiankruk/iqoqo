## 1. UI Component Refactoring

- [ ] 1.1 Create or adapt `CoverUploadPicker` component combining live camera stream and file gallery selector with replacement confirmation
- [ ] 1.2 Update `frontend/components/manifestation/manifestation-actions.tsx` to replace single-mode `CameraCapture` with the dual-source picker
- [ ] 1.3 Update `frontend/components/item/sidebar/sidebar-actions.tsx` and `item-actions.tsx` to utilize the dual-source cover contribution button

## 2. Testing & Verification

- [ ] 2.1 Add Vitest component test for `CoverUploadPicker` verifying camera option vs file selection triggering
- [ ] 2.2 Verify optimistic mutation cache update (`cover_status: "processing"`) upon file upload
- [ ] 2.3 Verify replacement confirmation modal appears when existing cover is present
