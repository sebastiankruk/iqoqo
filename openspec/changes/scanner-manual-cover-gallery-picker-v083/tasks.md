## 1. UI Component Enhancement

- [ ] 1.1 Update `frontend/components/scanner/manual-entry-form.tsx` with dedicated "Choose from Photos" picker and camera option; verify file selection triggers file change handler
- [ ] 1.2 Implement thumbnail preview with remove and change buttons and Object URL lifecycle management; verify component renders preview when file is provided
- [ ] 1.3 Add mobile-accessible buttons and translations for gallery picker controls; verify localized labels in en/pl message files

## 2. Scan Page Integration & Verification

- [ ] 2.1 Update `frontend/app/scan/page.tsx` to handle staged gallery cover files and verify proper multipart form data binding on submission
- [ ] 2.2 Add Vitest component test in `frontend/__tests__/components/scanner/manual-entry-form.test.tsx` verifying file drop, gallery selection, thumbnail preview rendering, and form submission
- [ ] 2.3 Verify manual item creation with uploaded custom cover end-to-end
