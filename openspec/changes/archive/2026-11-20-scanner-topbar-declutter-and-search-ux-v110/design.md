## Context

Following the `C132` addition of `magazine` as the 8th format in `SCAN_FORMATS`, `/scan` accumulated **17 simultaneous buttons** on a `~390px` mobile viewport:
- TopBar header (`Back` + optional `Flash`)
- TopBar 8 circular format buttons overflowing `justify-center` and clipping `Book` & `LEGO` on mobile
- TopBar 3 policy pills (`SHELF`, `WISHLIST`, `CATALOG ONLY`)
- Cramped quick lookup input + `Lookup` button squeezed beside `Batch mode OFF`
- BottomSheet 3 tabs (`Barcode`, `Snap Cover`, `Manual Search`) duplicating text search

## Goals / Non-Goals

**Goals:**
- Reduce default visible mobile controls on `/scan` to comply with clean action hierarchy and `< 40%` chrome height above the camera viewfinder.
- Fit **Format Selector**, **Destination Policy Selector**, and **Batch Toggle** on **one single responsive horizontal line** inside `TopBar`.
- Give the unified quick lookup bar **100% horizontal width** so ISBN, ISSN, GS1 `977`, Discogs IDs, and titles remain readable on `390px` mobile screens.
- Eliminate search duplication by removing the `"Manual Search"` (`scanner-tab-manual`) tab from `BottomSheet` while retaining a direct secondary `"Enter details manually"` (`enter-manually-link`) fallback and lookup-timeout fallback.

**Non-Goals:**
- Changing backend `/api/lookup` or `/api/scan` endpoints.
- Changing `ManualEntryForm` fields or camera OCR behavior.

## Decisions

1. **Single-Line Compact Control Row (`[Format ▾] [Dest ▾] [Batch]`) in `TopBar`:**
   - Replace the 8 format buttons + 3 policy pills with Shadcn `DropdownMenu` triggers (`format-selector-trigger` and `policy-selector-trigger`) rendered in a single horizontal `flex items-center justify-between gap-1.5` bar alongside an optional `rightAccessory` prop where `scan/page.tsx` mounts `BatchScanToggle` (styled compactly so all 3 pills stay on one line at `390px`).
   - Selecting Format opens a clean dropdown menu listing every entry in `SCAN_FORMATS` with icon + full localized label (`role="menuitemradio"` / checkmark on active item), preventing horizontal clipping even as additional formats are added in future releases.
   - Selecting Destination opens a dropdown menu listing `Shelf`, `Wishlist`, and `Catalog Only` with localized hint subtext.
2. **100%-Width Unified Lookup Bar in `scan/page.tsx`:**
   - Move `BatchScanToggle` out of the lookup row into `TopBar`'s single-line control row (`rightAccessory`), leaving the `<form onSubmit={handleQuickLookup}>` row at `w-full` (`100%` width) across mobile and desktop viewports.
   - Ensure lookup timeout/404 failure still offers one-tap transition to `ManualEntryForm` pre-filled with the query (`onExtractionFailure` / `handleShowManualForm(query)`), preserving automated E2E timeout fallback flows.
3. **Streamlined 2-Tab `BottomSheet` (`Barcode` + `Snap Cover`):**
   - Drop `"manual"` from `BottomSheet`'s segmented tabs (`tabs = ["barcode", "cover"]`).
   - Render a subtle secondary text button (`data-testid="enter-manually-link"`) underneath the tab content so users with damaged/missing barcodes can still open `ManualEntryForm` directly without keeping a second search input inside the sheet.

## Risks / Trade-offs

- **Existing unit & E2E tests referencing `scanner-tab-manual` / `"Manual Search"`** → Update all existing Vitest and Playwright E2E specs (`bottom-sheet.test.tsx`, `top-bar.test.tsx`, `scanner_workflow.spec.ts`, `serial_scanner.spec.ts`, `ux_audit.spec.ts`, `i18n_localization.spec.ts`, and workflow specs) to interact with `format-selector-trigger`, `policy-selector-trigger`, `unified-lookup-input`, and `enter-manually-link`.
- **Discoverability of Format/Destination state** → Pill labels always display the currently selected Format icon + short localized name and active Destination (`Shelf` / `Wishlist` / `Catalog`), keeping current state glanceable at zero extra taps.
