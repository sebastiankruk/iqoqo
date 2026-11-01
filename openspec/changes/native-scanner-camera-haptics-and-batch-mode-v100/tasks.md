## 1. Native Camera Permissions, Haptics & Continuous Batch Scan (`frontend/`)

- [ ] 1.1 Configure `NSCameraUsageDescription` and `NSPhotoLibraryAddUsageDescription` in `frontend/ios/App/App/Info.plist` and `android.permission.CAMERA` in `frontend/android/app/src/main/AndroidManifest.xml`.
- [ ] 1.2 Implement `frontend/components/scanner/batch-scan-toggle.tsx` (`BatchScanToggle` and `useBatchMode` hook) with `isNativeApp()`-guarded `@capacitor/haptics` feedback and consecutive-barcode cooldown debounce.
- [ ] 1.3 Wire `BatchScanToggle` and unified quick-lookup input into `frontend/app/scan/page.tsx` so manual ISBN/title lookup takes $\le 3$ clicks from the dashboard and batch scans auto-reset with toast feedback instead of redirecting away from `/scan`.
- [ ] 1.4 Localize all new scanner/batch-mode strings in `frontend/messages/en.json` and `frontend/messages/pl.json` (sentence case).

## 2. Verification & Tests

- [ ] 2.1 Author unit tests in `frontend/__tests__/components/scanner/batch-scan-toggle.test.tsx`.
- [ ] 2.2 Author Playwright E2E mobile scanner tests in `frontend/__tests__/e2e/mobile_scanner.spec.ts` verifying batch scan toggle, continuous scan loop, and $\le 3$-click manual lookup.
- [ ] 2.3 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
