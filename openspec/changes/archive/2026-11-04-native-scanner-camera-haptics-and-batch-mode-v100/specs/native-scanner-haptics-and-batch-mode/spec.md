## Purpose
Provide native camera permissions, haptic scan confirmation, continuous batch shelf-scanning mode, and a $\le 3$-click unified scan/manual lookup flow.

## ADDED Requirements

### Requirement: Continuous Batch Scan Mode with Native Haptics

The scanner page (`/scan`) SHALL provide a `BatchScanToggle` (`useBatchMode`) that, when enabled, triggers `Haptics.impact` (on native platforms), adds the scanned item to the user's collection with a toast notification, and immediately resets the scanner without redirecting to `/item/[id]`.

#### Scenario: User scans a barcode with Batch Mode enabled on native mobile
- **GIVEN** the user is on `/scan` with `Batch Mode` enabled
- **WHEN** a barcode is decoded and matched
- **THEN** the item is added, a haptic impact is triggered (if `isNativeApp()`), a toast confirms addition, and `/scan` remains active for the next item.

### Requirement: Unified Scan & Manual Search Input ($\le 3$ Clicks)

The `/scan` landing view SHALL expose a direct text input for ISBN/UPC/Title lookup alongside the camera viewfinder so a user can manually look up and add an item in $\le 3$ clicks/taps from the dashboard.

#### Scenario: User manually looks up an ISBN from `/scan` without tab switching
- **GIVEN** an authenticated user navigates from Dashboard (`/`) to Scan (`/scan`) (Click 1)
- **WHEN** the user enters an ISBN into the unified quick-lookup input and taps Search (Click 2) and taps Add to Library (Click 3)
- **THEN** the item is added to the library within 3 clicks.
