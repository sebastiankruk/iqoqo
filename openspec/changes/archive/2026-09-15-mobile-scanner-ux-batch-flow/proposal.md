## Why

When scanning physical media items on mobile devices, the green confirmation toast ("Item added to shelf/library") renders at the bottom of the viewport and directly occludes the 4-button mobile bottom navigation bar (`[Home | Collection | Scan | Profile]`), blocking immediate access to the primary "Scan" button. Furthermore, in batch scanning workflows—including newly added items, items already in the collection, and the inline "Scan another" action—navigating back to `/scan` leaves the camera dormant, forcing the user to manually tap "Start Camera" for every single item.

Fixing these two friction points in v0.7.18 removes toast occlusion and reduces clicks per scanned item by 50%, enabling a frictionless continuous physical cataloging experience.

## What Changes

- **Non-Occluding Toast Notification**: Configure mobile toast notifications to render at `top-center` on viewport widths < 640px (with safe-area top offset), preventing collision with the fixed bottom navigation bar (`h-16`) and keeping the primary "Scan" thumb target immediately accessible.
- **Continuous Batch Camera Auto-Start**:
  - Arm scanner auto-start via lightweight session storage (`sessionStorage.setItem("iqoqo_auto_start_camera", "true")`) when an item is added to the collection or when viewing an existing item from `SuccessCard`.
  - Auto-start camera on `/scan` when the session flag is present (and clear the flag once consumed).
  - Add missing "Scan another" action to `SuccessCard` for items already in the collection.
  - Wire `onScanAnother` callback in `app/scan/page.tsx` to immediately reset results and restart the camera loop with zero extra taps.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `scanner-ux-streamline`: Add requirements for non-occluding mobile feedback notification positioning and continuous batch camera auto-start across item addition, already-in-collection items, and "Scan another" workflows.

## Impact

- **Frontend Components**:
  - `frontend/components/providers.tsx`: Dynamic mobile `top-center` positioning and safe offsets in Sonner `Toaster`.
  - `frontend/components/scanner/success-card.tsx`: Session flag arming on `handleAdd` and "View in Collection", plus "Scan another" button rendering for `already_in_collection`.
  - `frontend/components/scanner/bottom-sheet.tsx`: Support for `autoStart` prop to trigger camera stream on mount when in barcode tab.
  - `frontend/app/scan/page.tsx`: Ingestion of session flag, passing `autoStart` to `BottomSheet`, and wiring `handleScanAnother` to `SuccessCard`.
- **APIs & Dependencies**: No backend API or schema changes; zero new npm dependencies.
- **Tests**: Vitest tests in `frontend/__tests__/components/scanner/bottom-sheet.test.tsx` and `frontend/__tests__/components/scanner/success-card.test.tsx`.
