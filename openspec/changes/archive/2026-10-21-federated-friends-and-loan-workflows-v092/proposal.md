## Why
Enables physical media collectors across different instances to become friends, browse shared items, and request loans of physical exemplars.
## What Changes

- Enable following remote Fediverse accounts (`@user@remote.instance`).
- Enable browsing federated friends' collections and wishlists.
- Support federated 'check-if-I-have-it' in `frontend/components/item/check-inventory.tsx`.
- Enable sending `as:Offer` loan requests targeting remote Item IRIs.
- Process loan approvals/rejections in `app/api/lending.py` and record custody history.

## Capabilities

### New Capabilities
- `federated-friends-and-loans`: Cross-instance friend following, collection/wishlist discovery, and ActivityPub loan request workflows

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Expands lending workflows, social discovery, and ActivityPub activity routing.
