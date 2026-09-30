---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

Currently, when a user adds a manifestation to their wishlist, the UI does not clearly reflect this status. The "Add to Collection" component still offers "Add to Wishlist" as an option, and there is no direct link to navigate to the resulting wishlist Item. Furthermore, tags cannot be applied to wishlist items, limiting organization for planned acquisitions. This change is needed to provide a coherent user experience for managing wishlists.

## What Changes

- Update the "Add to Collection" UI to reflect if an item is already on the wishlist.
- Provide a clear navigation path (button/link) to the generated wishlist Item from the manifestation page.
- Allow tags to be assigned and saved to items that are in the wishlist state, identical to how tags are applied to collection items.
- Ensure backend logic for tagging supports wishlist items.

## Capabilities

### New Capabilities

- `wishlist-management`: Define the UI/UX flows and tagging requirements specifically for items in a wishlist state versus items fully in the collection.

### Modified Capabilities

-

## Impact

- Frontend: Add to Collection component logic, wishlist item display, tagging UI.
- Backend: Tagging API endpoints if they currently filter out wishlist items.
