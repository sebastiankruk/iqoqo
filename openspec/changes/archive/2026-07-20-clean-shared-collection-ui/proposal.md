---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

Unauthenticated users accessing a shared collection public link can see UI elements intended only for the collection owner or logged-in users, such as "remove from wishlist" toggles, "Request loan" buttons on wishlist items, and duplicate progress badges. Furthermore, the shared collection page lacks basic site navigation context like the global Navbar and Footer, making it feel disjointed from the rest of the application. Cleaning up this public UI provides a safer, read-only experience for unauthenticated viewers and integrates the public view properly into the site design.

## What Changes

- Ensure the public Shared Collection page includes the global `Navbar` and `Footer` components.
- Hide the "remove from wishlist" (Heart) quick action on `ItemCard` for unauthenticated/non-owner views.
- Hide duplicate "On wish list" or "Want to read" buttons in the `ItemHeader` and `ItemActions` view when the user does not own the item or is unauthenticated.
- Ensure the "Request loan" button is strictly hidden for unauthenticated users, and is completely omitted if the item is purely a wishlist item (nobody owns it yet).

## Capabilities

### New Capabilities

- `shared-collection-ui`: Enhances the visual layout and contextual integration of the public shared collections page.

### Modified Capabilities

- `wishlist-management`: Hide wishlist modification actions from unauthenticated users or non-owners viewing shared content.
- `item-custody`: Hide loan request options on wishlist items (which are not borrowable) and for unauthenticated users.

## Impact

- `frontend/app/share/[token]/page.tsx` (Navbar, layout adjustments)
- `frontend/components/collection/item-card.tsx` (Wishlist heart toggle visibility)
- `frontend/components/item/item-actions.tsx` (Wishlist/progress button visibility)
- `frontend/components/item/item-header-actions.tsx` (Request loan button logic)
