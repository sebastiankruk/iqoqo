## Why
Cataloging a physical shelf of books, vinyl records, or board games on a phone requires instant tactile feedback, continuous batch scanning without per-item redirect loops, and a $\le 3$-click manual lookup flow.

## What Changes

- **Native Camera Permissions, Torch & Haptics Bridge:** Configure native camera usage descriptions in `Info.plist` (`NSCameraUsageDescription`) and `AndroidManifest.xml` (`android.permission.CAMERA`), wire `@capacitor/haptics` (`Haptics.impact` / `Haptics.notification` guarded by `isNativeApp()`) on barcode lock and ingestion success, and support hardware torch toggling.
- **Continuous Batch Scan Mode (`BatchScanToggle` & `useBatchMode`):** Add `frontend/components/scanner/batch-scan-toggle.tsx` on `/scan`. When Batch Mode is enabled, scanning a barcode automatically adds the item to the user's collection (or displays a non-blocking toast `Added "Title" to collection`), triggers haptic feedback, and immediately resets the scanner for the next item on the shelf without navigating away from `/scan`.
- **Unified Scan & Manual Lookup Input ($\le 3$ Clicks):** Expose a direct ISBN/UPC/Title quick-search input on the primary `/scan` view so users do not have to switch tabs before typing an identifier (reducing manual addition from 4 clicks to $\le 3$ clicks per `1.0.0-ux-audit-report.md`).

## Capabilities

### New Capabilities
- `native-scanner-haptics-and-batch-mode`: Native camera permissions, `@capacitor/haptics` tactile scan confirmation, continuous `BatchScanToggle` shelf scanning, and $\le 3$-click unified scan/manual input.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/components/scanner/batch-scan-toggle.tsx`
- `frontend/components/scanner/camera-capture.tsx`, `frontend/components/scanner/success-card.tsx`
- `frontend/app/scan/page.tsx`
- `frontend/android/app/src/main/AndroidManifest.xml`, `frontend/ios/App/App/Info.plist`
