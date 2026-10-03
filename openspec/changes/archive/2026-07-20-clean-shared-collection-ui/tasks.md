---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:50Z
---

## 1. Global Navigation for Shared View

- [x] 1.1 Update `frontend/app/share/[token]/page.tsx` to include `NavbarWithSuspense` (or `Navbar`) and `Footer`.
- [x] 1.2 Verify that `Navbar` doesn't crash when rendering for an unauthenticated user (already fixed by removing the global 401 redirect, but confirm layout behaves well without session).

## 2. Item Card View Adjustments

- [x] 2.1 Update `frontend/components/collection/item-card.tsx` to hide the "remove from wishlist" toggle (heart icon overlay). The toggle should only render if `isWishlist` AND the component is not in a read-only shared view (e.g. check `userOwns` or `isSharedView`).
- [x] 2.2 Verify that `userOwns` correctly maps to the viewer's ownership, or simply ensure `onWishlistRemove` is strictly typed/required and if missing, the button hides.

## 3. Item Actions Details View Adjustments

- [x] 3.1 Update `frontend/components/item/item-actions.tsx` to hide the primary wishlist status buttons ("On wish list", "Want to read") if the viewer is unauthenticated or not the owner.
- [x] 3.2 Update `frontend/components/item/item-header-actions.tsx` to hide the "Request loan" button if the viewer is unauthenticated.
- [x] 3.3 Further restrict "Request loan" in `frontend/components/item/item-header-actions.tsx` so that it is completely hidden if the item's global custody is purely a wishlist placeholder (e.g. `userOwns` is false and nobody has physical custody).

## 4. Test Verification

- [x] 4.1 Update or add frontend Vitest tests in `frontend/__tests__/components/collection/item-card.test.tsx` to ensure wishlist heart icon is hidden when `isSharedView` or non-owner context is active.
- [x] 4.2 Verify frontend Vitest tests pass for `item-actions.tsx` and `item-header-actions.tsx` with unauthenticated contexts.
