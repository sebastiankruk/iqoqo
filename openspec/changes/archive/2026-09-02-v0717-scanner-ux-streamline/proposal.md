## Why

Scanner UX make caveman confused. Top buttons "Inventory" vs "Catalog" not clear — users not understand if item goes to their own shelf or into global catalog database. TopBar buttons and format labels have no translations (hardcoded English). Meanwhile, existing two-circle counter-rotating waiting animation is liked and should be preserved. Extra network refetches slow down item addition flow.

## What Changes

- **TopBar Policy Naming & Complete Localization**: Rename scanner target policies ("Shelf" for personal inventory, "Wishlist", "Catalog Only" for contributing metadata without adding to shelf) with explanatory hints. Localize all TopBar labels, formats, and policy selectors in `messages/en.json` and `messages/pl.json`.
- **Disambiguation Sheet Single CTA**: Streamline candidate cards on `disambiguation-sheet.tsx` for clean, single-tap selection with localized strings.
- **Scanner Metadata Zero-Refetch Pipeline**: Keep scan metadata in component state and pass directly to `success-card.tsx` to eliminate redundant GET network fetches.
- **Preserve Waiting Animation**: Retain existing smooth two-circle counter-rotating waiting indicator animation without replacing it.

## Capabilities

### New Capabilities
- `scanner-ux-streamline`: Streamline scanner flow with clear policy naming ("Shelf" / "Catalog Only"), full TopBar localization, single-tap candidate selection, zero-refetch metadata passing, and preserved two-circle waiting animation.

### Modified Capabilities

## Impact

- `frontend/components/scanner/top-bar.tsx`
- `frontend/components/scanner/disambiguation-sheet.tsx`
- `frontend/components/scanner/success-card.tsx`
- `frontend/messages/en.json`
- `frontend/messages/pl.json`
- Scanner unit, component, and Playwright E2E tests.
