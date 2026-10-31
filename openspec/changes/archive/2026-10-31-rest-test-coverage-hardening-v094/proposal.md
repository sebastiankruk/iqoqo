# Proposal: REST Test Coverage Hardening (v0.9.4)

## Why

The `v0.9.4` REST API surface audit identified 240 of 258 non-static routes (93.0%) with direct pytest coverage, with 5 specific edge endpoints lacking explicit HTTP assertion suites: user library streaming export, email verification resend rate limiting, borrower loan status inspection, LOD administrative stats/cleanup triggers, and static gallery image traversal protection. Hardening these residual endpoints ensures 100% route verification across critical security, rate limiting, and data streaming boundaries prior to final v0.9.4 release tagging.

## What Changes

- Add pytest integration tests for authenticated user library streaming export (`GET /api/items/export` and `GET /api/v1/items/export`) across all supported formats (`json-ld`, `turtle`, `nt`, `json`) and invalid format 400 rejection.
- Add pytest tests for email verification resend (`POST /api/account/email/verification-request`), verifying 200 for unverified accounts, 3/hour account-scoped rate limiting (429), and mail delivery failure handling (503).
- Add pytest tests for borrower loan status retrieval (`GET /api/lending/items/<int:item_id>/loan-status`), verifying requester-scoped loan request serialization and null response when unrequested.
- Add pytest tests for administrative Linked Open Data stats and cleanup (`GET /api/admin/lod/stats` and `POST /api/v1/admin/lod/cleanup`), enforcing custodian/admin RBAC (403 for normal users) and verifying summary counts and dry-run execution.
- Add pytest tests for gallery static image serving (`GET /api/static/gallery/<path:filename>`), verifying legitimate asset delivery and path traversal prevention.
- Register `C93: rest-test-coverage-hardening-v094` in `.context/notes/plan/0.9.x-release-plan.md` under the `v0.9.4` milestone.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `backend-test-coverage`: Add requirements for testing user library streaming export, email verification request rate-limiting and failure handling, borrower loan status inspection, LOD admin statistics and task trigger endpoints, and static gallery asset serving security.

## Impact

- **Test Suites**: Expands `tests/test_items.py` (or new `tests/test_items_export.py`), `tests/test_account_lifecycle.py`, `tests/test_lending.py`, `tests/test_admin_frbr.py`, and `tests/test_system_status.py`.
- **APIs**: Validates HTTP status codes, error payloads, and headers for 7 routes without mutating production API contracts.
- **Dependencies**: Zero new runtime dependencies; uses existing `pytest`, `client` fixtures, and `DataManager`.
