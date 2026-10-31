## 1. Plan and Release Registration

- [x] 1.1 Register C93 in `.context/notes/plan/0.9.x-release-plan.md` under milestone `v0.9.4` and verify markdownlint passes

## 2. Residual REST Edge Test Implementation

- [x] 2.1 Author integration tests for user library streaming export (`GET /api/items/export` and `GET /api/v1/items/export`) across all supported formats (`json-ld`, `turtle`, `nt`, `json`), invalid format 400, and unauthenticated 401 in `tests/test_items.py` and verify with pytest
- [x] 2.2 Author tests for email verification resend (`POST /api/account/email/verification-request`) covering unverified dispatch 200, 3/hour account rate limit 429, and mail failure 503 in `tests/test_account_lifecycle.py` and verify with pytest
- [x] 2.3 Author tests for borrower loan status retrieval (`GET /api/lending/items/<int:item_id>/loan-status`) covering requester active request 200 and unrequested null 200 in `tests/test_lending.py` and verify with pytest
- [x] 2.4 Author tests for LOD admin stats and cleanup (`GET /api/admin/lod/stats` and `POST /api/v1/admin/lod/cleanup`) covering 403 for non-admins, 200 with stats dictionary for admins, and cleanup dry-run execution in `tests/test_admin_frbr.py` and verify with pytest
- [x] 2.5 Author security tests for static gallery image serving (`GET /api/static/gallery/<path:filename>`) covering legitimate file serving and traversal rejection in `tests/test_system_status.py` and verify with pytest

## 3. Verification and Release Gate Finalization

- [x] 3.1 Re-run route coverage analysis script to verify 100% target endpoint coverage and run full suite of backend/frontend tests
- [x] 3.2 Run linters (`make format-python`, `make format-js`, `make lint-markdown`, `make secret-scan`, `make lint`) and verify 0 errors
