## 1. Backend Serialization

- [x] 1.1 Update `app/api/items.py` virtualization logic to extract and append `work_type` and `medium_type` (from the primary expression/manifestation) to the `UserWorkIntent` response payload. Verify by adding a test in `tests/test_wishlist_media.py` ensuring Vinyl, Audio, and Game entities return the correct values.

## 2. Frontend Utilities

- [x] 2.1 Update `frontend/lib/media-badge.ts` to dynamically inspect `item.work_type` and `item.medium_type` in addition to content type, generating the appropriate category labels and icons (e.g. Music, BoardGame, Movie, Book). Verify by adding a Vitest test for the badge utility showing correct mappings.

## 3. Frontend UI

- [x] 3.1 Modify `frontend/components/collection/item-card.tsx` to consume `work_type` and `medium_type` from the intent payload, passing them into the media badge renderer. Verify by creating an E2E test in `frontend/__tests__/e2e/wishlist_media_types.spec.ts` that catalogs a Vinyl to the Wishlist and verifies the correct turntable icon and audio metadata appear in the wishlist grid.
