## Why

Adding the 8th media format (`magazine`) in C132 pushed the `/scan` top bar icon row past mobile viewport width (`~390px`), where `flex justify-center overflow-x-auto` clipped the outer icons (`Book` and `LEGO`) off both edges. In addition, showing 8 format icons + 3 policy pills + quick lookup + batch toggle + 3 bottom-sheet tabs created **17 simultaneously visible buttons** and duplicated search between the top `Lookup` bar and the BottomSheet `Manual Search` tab.

## What Changes

- **Single-Line Compact Control Row (`TopBar`)**:
  - Replace the 8 format icon buttons and 3 destination policy pills with two compact Shadcn `DropdownMenu` / `Popover` selector pills:
    - **Format Selector Pill** (`[Format: <Active> ▾]`, `data-testid="format-selector-trigger"`) opening a touch-friendly vertical list of all `SCAN_FORMATS` with icon + full localized label.
    - **Destination Policy Pill** (`[Dest: Shelf | Wishlist | Catalog Only ▾]`, `data-testid="policy-selector-trigger"`) opening a picker with localized policy labels and descriptions.
  - Place `BatchScanToggle` (`Batch ON/OFF` + queue badge/menu) inline on the **same single horizontal row** immediately alongside the Format and Destination pills (`[Format ▾] [Dest ▾] [Batch]`).
- **Full-Width Unified Lookup Bar (`app/scan/page.tsx`)**:
  - Expand the unified quick lookup form (`data-testid="unified-lookup-input"` + `data-testid="unified-lookup-submit"`) to **100% width** on the row below the control strip, free from sibling button crowding.
- **2-Tab `BottomSheet` (`Barcode` + `Snap Cover`, Drop Redundant `Manual Search`)**:
  - **MODIFIED**: Remove the redundant `"Manual Search"` (`scanner-tab-manual`) tab from `BottomSheet`, leaving `"Barcode"` and `"Snap Cover"`.
  - Keep manual entry effortlessly accessible via a discreet secondary text link (`"Can't scan? Enter details manually"`, `data-testid="enter-manually-link"`) and automatic lookup-failure / timeout fallbacks.

## Capabilities

### New Capabilities

### Modified Capabilities
- `scanner-ux-streamline`: Compact `/scan` `TopBar` into a single-line `[Format ▾] [Dest ▾] [Batch]` control row, expand the unified lookup bar to 100% width, and streamline `BottomSheet` to 2 capture tabs (`Barcode`, `Snap Cover`) by dropping the duplicate `Manual Search` tab.

## Impact

- **Frontend Components (`frontend/`)**: `frontend/components/scanner/top-bar.tsx`, `frontend/components/scanner/bottom-sheet.tsx`, `frontend/app/scan/page.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Frontend Unit & E2E Tests**: `frontend/__tests__/components/scanner/top-bar.test.tsx`, `frontend/__tests__/components/scanner/bottom-sheet.test.tsx`, `frontend/__tests__/app/scan/page.test.tsx`, and E2E suites migrating from `scanner-tab-manual` / `"Manual Search"` to `unified-lookup-input` / `enter-manually-link` (`scanner_workflow.spec.ts`, `serial_scanner.spec.ts`, `ux_audit.spec.ts`, `i18n_localization.spec.ts`, `acquisition_workflow.spec.ts`, `allegro_fallback_ingestion.spec.ts`, `lending_workflow.spec.ts`, `lego_workflow.spec.ts`, `wishlist_workflow.spec.ts`, `wishlist_media_types.spec.ts`, `audio_workflow.test.ts`, `boardgame_workflow.test.ts`, `puzzle_workflow.test.ts`, `video_workflow.test.ts`).
