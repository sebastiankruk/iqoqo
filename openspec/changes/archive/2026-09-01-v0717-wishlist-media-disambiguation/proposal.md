## Why

Currently, non-book wishlist items (like Vinyl records, Audiobooks, and Board Games) render with generic Book icons and properties across wishlist and roadmap views. This happens because the ingestion of UserWorkIntent records defaults the client-side polymorphic discriminator to TextWork when manifestation-level format attributes are not fully traversed down the FRBR hierarchy. This degrades the user experience by misrepresenting the actual media type in the wishlist. 

## What Changes

- Update the serialization of `UserWorkIntent` to include `work_type` and the primary `expression.medium_type`.
- Introduce polymorphic media type badge rendering for wishlist cards, based on `work_type` and `medium_type` properties.
- **BREAKING**: None.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `user-work-intent-wishlist`: Modify requirements to ensure `work_type` and `expression.medium_type` are included in serialization and appropriately mapped in the UI for disambiguation of non-book items (e.g., Audiobooks, Vinyls, Board Games).

## Impact

- **API/Serialization**: `app/core/frbr_service.py` is updated to expose the format attributes in `UserWorkIntent` payloads.
- **Frontend UI**: `frontend/components/collection/item-card.tsx` and `frontend/lib/media-badge.ts` will dynamically inspect the new properties and render the correct media category badges (Music, BoardGame, Movie, Book).
- **Tests**: E2E and unit tests to ensure format metadata correctly traverses the hierarchy and the UI accurately reflects it.
