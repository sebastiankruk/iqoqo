## Why

Fix critical findings from v0.8.1 release review before merge.

## What Changes

- Disable account deletion API temporarily (return 501).
- Add XSS filtering (bleach) to profile bio and display name.
- Remove negative-ID hack for items API; frontend use wishlist API.
- Fix wishlist API pagination to use SQL LIMIT/OFFSET.
- Guard against data loss for orphan roadmap items in migration.
- Add SQLite guard in security migration for items constraint.
- Delete unused `contributor-editor.tsx`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none)

## Impact

- `app/api/profile.py`, `frontend/app/profile/page.tsx`
- `app/api/items.py`
- `app/api/wishlist.py`
- `migrations/versions/v0_8_1_frbr_relation_management.py`
- `migrations/versions/v0_8_1_security_constraints.py`
- `frontend/components/admin/frbr/contributor-editor.tsx`
