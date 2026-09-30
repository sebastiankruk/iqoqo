---
type: Concept
title: design
timestamp: 2026-07-22T10:18:50Z
---

## Context

The shared collection page (`/share/[token]`) is public-facing. Currently, components like `ItemCard`, `ItemHeaderActions`, and `ItemActions` expect an authenticated context or assume the viewer is the owner. This results in actionable buttons (wishlist toggles, loan requests) leaking into the public view, confusing users and offering broken functionality (since unauthenticated users can't perform these actions). Additionally, the shared collection lacks a `Navbar` and `Footer`, making it a dead end visually.

## Goals / Non-Goals

**Goals:**

- Add `Navbar` and `Footer` to the shared collection page.
- Make components aware of their context (e.g. `isSharedView` or check `userOwns`/authenticated status) to hide wishlist/loan actions.
- Ensure the shared collection view remains read-only for public guests.

**Non-Goals:**

- Implement new sharing permissions or granular access controls.
- Change the structure of the token sharing API itself.

## Decisions

1. **Navbar & Footer Inclusion:** We will wrap the layout in `app/share/[token]/page.tsx` with `<Navbar />` and `<Footer />`. We must ensure the `Navbar` does not crash for unauthenticated users (which we previously fixed by preventing global 401 redirects).
2. **Component Props & State Checks:**
   - In `item-card.tsx`, we will ensure the "remove from wishlist" button relies on `userOwns` and `isWishlist` combined, or we simply disable it if the user isn't logged in. Wait, `ItemCard` takes `onWishlistRemove`. If `onWishlistRemove` is not provided (which it won't be in shared view), we can hide the button, or explicitly check `userOwns`.
   - In `item-actions.tsx` and `item-header-actions.tsx`, we will conditionally hide the "Request loan" button if the viewer is unauthenticated, or if the item's `status` indicates it's purely a wishlist item without custody.

## Risks / Trade-offs

- **Risk:** Hiding buttons might accidentally hide them for the actual owner if they view their own shared link.
  - **Mitigation:** We can use the presence of `session` or check if the owner matches the viewer. However, shared views are typically read-only. It is acceptable for a shared link to be read-only even for the owner, as they have the internal dashboard. We will ensure components properly check the profile context if needed.
