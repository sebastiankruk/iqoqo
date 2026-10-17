## 1. UI Component Refactoring

- [x] 1.1 Create or adapt `CoverUploadPicker` component with single-button trigger opening direct modal choice (Take Photo vs. Choose from Gallery)
- [x] 1.2 Update `frontend/components/manifestation/manifestation-actions.tsx` to replace single-mode `CameraCapture` with `CoverUploadPicker`
- [x] 1.3 Update `frontend/components/item/sidebar/sidebar-actions.tsx` and `item-actions.tsx` to utilize `CoverUploadPicker`
- [x] 1.4 Unify `frontend/components/scanner/manual-entry-form.tsx` from twin buttons to a single "Upload Cover" button with source selection modal

## 2. Testing & Verification

- [x] 2.1 Update Vitest component test for `CoverUploadPicker` verifying single-button direct dialog opening and source triggers
- [x] 2.2 Update Vitest component test for `manual-entry-form.test.tsx` verifying single "Upload Cover" button and modal behavior
- [x] 2.3 Verify optimistic mutation cache update (`cover_status: "processing"`) upon file upload
- [x] 2.4 Verify replacement confirmation modal appears when existing cover is present
