## Why

In the FRBR ontology, physical items (`Item`, F4) represent concrete exemplars on a shelf, whereas wishlist entries (`UserWorkIntent`) represent abstract desires toward Works (F1), Expressions (F2), or Manifestations (F3). Currently, virtual wishlist items are synthesized inside `/api/items` using an ad-hoc negative-ID convention (`id = -intent.id`), creating leaky abstractions, fragile routing, and type instability across both backend and frontend. Furthermore, `UserWorkIntent` only binds to `Work.id`, preventing users from expressing desires for specific editions, translations, or container media (F15 Complex Works and F16 Container Works). Separating the wishlist into a dedicated `/api/wishlist` CRUD service and isolating frontend views establishes strict FRBR boundary integrity for v0.8.1 (C10: Wishlist API Separation).

## What Changes

- **Dedicated Wishlist Endpoint**: Create `/api/wishlist` REST blueprint providing complete CRUD operations (`GET`, `POST`, `PUT`/`PATCH`, `DELETE`) for `UserWorkIntent` with standard positive integer IDs.
- **Negative-ID Removal**: **BREAKING**: Remove negative-ID synthesis and routing from `/api/items` endpoints (`GET /api/items`, `GET /api/items/<id>`, `PUT /api/items/<id>`, `DELETE /api/items/<id>`, `/api/items/<id>/collections`), and remove negative ID hacks in `app/core/item_access.py` and `app/api/schemas.py`.
- **FRBR F15/F16 Binding Support**: Extend `UserWorkIntent` with optional foreign keys `expression_id` (`catalog.expressions.id`) and `manifestation_id` (`catalog.manifestations.id`), enabling wishlist items to target specific expressions (e.g., audiobooks, translations) or specific manifestations (e.g., specific printings, F16 board game boxes, F15 complex work parts) with hierarchy consistency validation.
- **Database Migration**: Add a linear Alembic migration adding `expression_id` and `manifestation_id` to `user_work_intents` with appropriate foreign key constraints, indexes, and unique constraints.
- **Frontend View & State Separation**: Decouple frontend inventory views (`/collection`) from wishlist views, introducing dedicated API hooks (`useWishlist`, `useCreateWishlistItem`, `useDeleteWishlistItem`), updating types in `frontend/types/frbr.ts`, and removing negative ID checks from UI components.

## Capabilities

### New Capabilities
- `wishlist/api-separation`: Dedicated `/api/wishlist` CRUD service for `UserWorkIntent`, removal of negative-ID adapters from `/api/items`, support for binding intents to specific FRBR Expression and Manifestation entities (F15/F16), and separate frontend wishlist presentation and state management.

### Modified Capabilities

## Impact

- **API**: `/api/wishlist` becomes the canonical endpoint for wishlist items; `/api/items` strictly handles physical `Item` (F4) records; consumers passing negative IDs to `/api/items` will receive 404/422.
- **Database Schema**: `inventory.user_work_intents` table receives nullable `expression_id` and `manifestation_id` columns with indexes and foreign keys.
- **Backend Services**: `app/api/items.py`, `app/api/wishlist.py`, `app/core/item_access.py`, `app/core/frbr_service.py`, and `app/api/schemas.py` updated to enforce clean FRBR boundaries.
- **Frontend**: `frontend/lib/api/hooks.ts`, `frontend/lib/api/intents.ts`, `frontend/types/frbr.ts`, and inventory/wishlist components and pages updated to use dedicated endpoints and models without negative IDs.
