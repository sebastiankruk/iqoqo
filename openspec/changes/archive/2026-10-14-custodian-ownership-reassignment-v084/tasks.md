## 1. Backend Authorization & Endpoints
 
- [x] 1.1 Implement `@admin_or_custodian_required` decorator in `app/api/decorators.py` and verify role resolution.
- [x] 1.2 Update `/api/admin/ownership/accounts`, `/api/admin/ownership/source-items`, `/api/admin/ownership/preview`, and `/api/admin/ownership/reassign` in `app/api/admin.py` to require admin or custodian.
- [x] 1.3 Add pytest test cases in `tests/test_item_reassignment.py` verifying custodian role with `write:users` can successfully preview and execute item reassignment, while users without the role or permission are rejected with 403.
 
 ## 2. Frontend Navigation & Page Access
 
- [x] 2.1 Update `frontend/components/admin/admin-sidebar.tsx` to render "Item Ownership" under the "Custodians" navigation section when the user is an admin or custodian with `write:users` permission.
- [x] 2.2 Update `frontend/app/admin/ownership/page.tsx` role check to permit custodians alongside administrators.
- [x] 2.3 Update Vitest tests in `frontend/__tests__/app/admin/ownership.test.tsx` and `frontend/__tests__/components/admin/admin-sidebar.test.tsx` to verify custodian access and menu item rendering.
 
 ## 3. End-to-End Verification
 
- [x] 3.1 Run backend pytest suite on item reassignment (`pytest tests/test_item_reassignment.py`) and verify clean pass.
- [x] 3.2 Run frontend Vitest test suite on admin sidebar and ownership page and verify clean pass.
