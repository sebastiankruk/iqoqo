## 1. Security & Profile

- [x] 1.1 Update `app/api/profile.py:delete_profile()` to return 501 and error message, and verify tests expecting 200 are updated to 501.
- [x] 1.2 Update `frontend/app/profile/page.tsx` to disable the delete button and add tooltip, and verify the button is unclickable.
- [x] 1.3 Update `app/api/profile.py:update_profile()` to apply `bleach.clean()` on `bio` and `display_name`, and verify HTML stripping with a test.

## 2. API Cleanup & Optimization

- [x] 2.1 Remove negative ID logic from `app/api/items.py`, and verify negative IDs return 404 from items endpoints in tests.
- [x] 2.2 Update frontend code referencing negative item IDs to use `/api/wishlist` endpoints, and verify frontend wishlist usage doesn't pass negative IDs.
- [x] 2.3 Update `app/api/wishlist.py` to replace `.all()` with SQL `LIMIT`/`OFFSET` pagination, and verify tests pass for wishlist pagination.

## 3. Database Migrations

- [x] 3.1 Update `migrations/versions/v0_8_1_frbr_relation_management.py` to assign a sentinel `work_id` for orphan roadmap items, and verify with a migration test.
- [x] 3.2 Update `migrations/versions/v0_8_1_security_constraints.py` to add SQLite path that disables legacy users owning items, and verify with a migration test.

## 4. Dead Code Removal

- [x] 4.1 Delete `frontend/components/admin/frbr/contributor-editor.tsx` and its test, and verify the frontend builds successfully without it.
