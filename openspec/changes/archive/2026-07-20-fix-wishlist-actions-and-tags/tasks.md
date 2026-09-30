---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Backend Tagging Update

- [x] 1.1 Inspect POST `/items/<id>/tags` endpoint and update it to allow tagging for wishlist items if currently restricted.
- [x] 1.2 Inspect GET `/items/<id>/tags` or item serialization to ensure tags are returned for wishlist items.
- [x] 1.3 Add or update backend test cases to verify a wishlist item can be tagged successfully.

## 2. Frontend Wishlist UI Updates

- [x] 2.1 Update the "Add to Collection" component on the manifestation page to check if the item is already on the wishlist.
- [x] 2.2 If the item is on the wishlist, replace the "Add to Wishlist" action with a link/button to view the virtual wishlist Item.
- [x] 2.3 Ensure the Tagging component on the Item page works correctly for wishlist items.
- [x] 2.4 Add or update frontend tests to cover the "Add to Collection" component's behavior when an item is already on the wishlist.
