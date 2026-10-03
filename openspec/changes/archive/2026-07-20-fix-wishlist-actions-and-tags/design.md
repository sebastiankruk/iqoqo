---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

Users can add items to their wishlist. The UI currently doesn't reflect an item's presence on the wishlist effectively when viewing a manifestation, still offering "Add to Wishlist" in the "Add to Collection" component. Moreover, there is no direct navigation from the manifestation page to the created virtual wishlist Item, and tags cannot be added to wishlist items.

## Goals / Non-Goals

**Goals:**

- Update "Add to Collection" UI state when the item is on the wishlist.
- Provide a button to view the wishlist Item.
- Enable tagging for wishlist items in the backend and frontend.

**Non-Goals:**

- Modifying how collection items are added or managed.
- Changing the tagging data model itself.

## Decisions

- **UI Update for Wishlist State**: We will modify the Add to Collection button/dropdown to check if the user already has a wishlist Item for the current manifestation. If yes, the primary action could be "View Wishlist Item" or we can show a clear label/button to navigate to it, while hiding or disabling the "Add to Wishlist" option.
- **Tagging Support**: Wishlist items are basically Item entities with a specific custody status (e.g., `wishlist`). We will ensure the `ItemTag` and related backend APIs do not unnecessarily filter out items with wishlist status. The frontend Tagging component should be rendered for wishlist items just like collection items.

## Risks / Trade-offs

- [Risk] Backend tagging API might have hardcoded checks for collection custody. → [Mitigation] We will review the tagging endpoint (`POST /items/<id>/tags`) and ensure it allows tagging regardless of custody status, or explicitly allows wishlist status.
