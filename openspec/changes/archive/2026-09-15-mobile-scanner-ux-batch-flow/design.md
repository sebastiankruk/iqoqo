## Context

See `proposal.md` for motivation and background. The physical media cataloging workflow on mobile devices involves rapid sequential interactions: barcode scanning, success card confirmation, item assignment (Shelf / Wishlist / Catalog), and cycling back to scan the next physical item in a batch.

## Goals / Non-Goals

**Goals:**
- Position Sonner toast notifications on mobile screens (< 640px) at `top-center` with safe-area offsets, eliminating any visual or tactile occlusion of the 64px fixed bottom navigation bar (`[Home | Collection | Scan | Profile]`).
- Enable seamless camera auto-start when navigating back to `/scan` following an item addition or while viewing an already-owned item.
- Provide an explicit "Scan another" action on `SuccessCard` for both new and already-in-collection items, instantly re-engaging the camera loop without full route transitions.
- Maintain full backward compatibility on desktop viewports (preserving `bottom-right` toasts).

**Non-Goals:**
- Modifying backend `/api/scan` routes or FRBR data models.
- Changing desktop navigation layouts or drawer components.
- Altering ZXing barcode library decoding algorithms or format options.

## Decisions

### Decision 1: Client-Side Viewport Detection for Sonner `position`
- **Choice**: In `frontend/components/providers.tsx`, detect mobile viewport (`window.innerWidth < 640`) in a client-safe `useEffect` hook. Set `position={isMobile ? "top-center" : "bottom-right"}` and configure `mobileOffset` with safe-area insets.
- **Rationale**: Sonner uses the `position` prop to determine CSS transform and stacking directions. Enforcing `top-center` on mobile ensures toasts animate downwards from the top notch/header, leaving the lower thumb zone and the 64px bottom navbar 100% accessible.
- **Alternatives Considered**:
  - *CSS-only `bottom: 5.5rem` offset*: Keeps toast at bottom but floats above the bar. While non-colliding, toasts still cover bottom content and deviate from the canonical MemPalace design spec (`fc68d53b`: *"Feedback: A 'Scanned!' toast notification appearing at the top."*).
  - *Global `top-center` across all devices*: Unnecessarily shifts desktop toasts away from the conventional bottom-right corner.

### Decision 2: SessionStorage Flag for Scanner Batch Intent
- **Choice**: Set `sessionStorage.setItem("iqoqo_auto_start_camera", "true")` upon completing an action in `SuccessCard` (`handleAdd` or "View in Collection"). When `/scan` mounts, it reads and immediately clears the flag (`sessionStorage.removeItem`), setting `autoStart={true}` on `<BottomSheet>`.
- **Rationale**: Tying batch intent to `sessionStorage` avoids polluting canonical URL query strings (`/scan` remains clean), works seamlessly across Next.js App Router client-side navigation (`<Link href="/scan">` and `router.push`), and auto-cleans so cold visits or external links do not unintentionally turn on the camera.
- **Alternatives Considered**:
  - *URL search parameter (`/scan?auto=1`)*: Requires updating all navigation links in Navbar and routes, risking stale query params if the user bookmarks or shares the link.
  - *Always auto-start camera on every visit to `/scan`*: Breaks user expectation if someone visits `/scan` solely to enter a title manually or upload a file.

### Decision 3: Restoring "Scan Another" on Already-In-Collection Items
- **Choice**: Render both `<Button onClick={handleViewInCollection}>View in Collection</Button>` and `<Button onClick={onScanAnother}>Scan Another</Button>` when `meta.already_in_collection` is true.
- **Rationale**: When collectors scan a stack of books or vinyl records to verify their holdings, discovering a duplicate shouldn't force them into the item details page just to get back to the scanner. A direct "Scan another" button allows immediate resumption of the scanning queue.
- **Alternatives Considered**:
  - *Only showing "View in Collection"*: Preserves the current friction where users must navigate forward to `/item/[id]` and then tap back to scan.

## Risks / Trade-offs

- **[Risk] Camera permission prompt on cold start** → *Mitigation*: The session flag is only set after the user has *already* granted camera permission and scanned at least one item. First-time visitors still see the explicit "Tap to start camera" button.
- **[Risk] SSR hydration mismatch with `isMobile`** → *Mitigation*: Initialize `isMobile` to `false` (matching server default) and update in `useEffect` on client mount.
- **[Risk] Camera stream leak on rapid tab switching** → *Mitigation*: `BottomSheet`'s existing unmount cleanup and `stopScanner` callbacks are strictly preserved.
