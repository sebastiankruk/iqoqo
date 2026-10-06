## 1. Global Notification Placement

- [x] 1.1 Update `Providers` in `frontend/components/providers.tsx` to dynamically set Sonner `Toaster` position to `top-center` on mobile viewports (< 640px) with safe-area offsets, preserving `bottom-right` on desktop; verify by inspecting component render and existing provider tests.

## 2. Scanner Batch Workflow & Camera Auto-Start

- [x] 2.1 Add `autoStart?: boolean` prop to `BottomSheet` in `frontend/components/scanner/bottom-sheet.tsx` that triggers `startScanner()` on mount when `activeTab === "barcode"` and camera is inactive; verify with unit test.
- [x] 2.2 Update `SuccessCard` in `frontend/components/scanner/success-card.tsx` to arm `iqoqo_auto_start_camera` in `sessionStorage` on `handleAdd` and "View in Collection", and render "Scan another" button when `meta.already_in_collection` is true; verify by rendering success card in already-in-collection mode.
- [x] 2.3 Update `ScanPage` in `frontend/app/scan/page.tsx` to consume `iqoqo_auto_start_camera` from `sessionStorage` on mount, pass `autoStart` to `BottomSheet`, and wire `onScanAnother` handler to `SuccessCard` to immediately restart the camera loop; verify component prop binding.

## 3. Test Hardening & Quality Verification

- [x] 3.1 Author Vitest test cases in `frontend/__tests__/components/scanner/bottom-sheet.test.tsx` and `frontend/__tests__/components/scanner/success-card.test.tsx` verifying `autoStart`, session storage flag setting, and "Scan another" callback execution; verify with `npx vitest run __tests__/components/scanner/`.
- [x] 3.2 Run full frontend test and lint suite (`IQOQO_AI_MODE=1 make test-frontend` and `IQOQO_AI_MODE=1 make lint`) to confirm 100% test pass rate and clean linting.
