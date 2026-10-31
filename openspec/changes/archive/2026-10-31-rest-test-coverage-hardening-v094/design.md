# Technical Design: REST Test Coverage Hardening (v0.9.4)

## Context

The v0.9.4 REST API coverage audit documented 258 non-static endpoints. 240 endpoints are directly tested by pytest suites, while 5 specific operational and security edge boundaries lack dedicated test assertions. Production implementations of these routes already exist in `app/api/items.py`, `app/api/account.py`, `app/api/lending.py`, `app/api/admin.py`, and `app/api/system.py`.

## Goals / Non-Goals

**Goals:**
- Author comprehensive, resilient pytest suites covering all 5 edge endpoint areas with zero production regression.
- Validate HTTP response status codes, payload structures, pagination/streaming boundaries, authentication gates, and rate-limiting behaviors.
- Ensure all tests execute fast and deterministically under `IQOQO_AI_MODE=1 pytest`.

**Non-Goals:**
- Mutate existing REST endpoint routing paths or schemas.
- Introduce mock servers where existing SQLite/PostgreSQL in-memory fixtures suffice.

## Decisions

### 1. Test Location and File Organization
- **User Library Export**: Add tests to `tests/test_items.py` (or a dedicated `tests/test_user_items_export.py`) following existing `test_streaming_export.py` patterns. Use standard `client` and authenticated user fixtures.
- **Email Verification Request**: Add tests to `tests/test_account_lifecycle.py` alongside existing account lifecycle tests. Mock `mail_service` / `account_lifecycle.send_verification` to test normal dispatch, rate limit (3/hr via loop), and `MailUnavailableError` exception mapping.
- **Loan Status**: Add test to `tests/test_lending.py` verifying borrower perspective loan status responses.
- **LOD Admin Stats & Cleanup**: Add tests to `tests/test_admin_frbr.py` verifying custodian/admin RBAC and response schema.
- **Gallery Static Image**: Add test to `tests/test_system_status.py` verifying file retrieval from `GALLERY_DIR` and path traversal safety.

*Alternatives Considered*: Placing all 5 tests into a single catch-all test file. Rejected in favor of co-locating tests with their respective domain modules to maintain architectural coherence and accurate CodeGraph / blast radius tracking.

### 2. Rate-Limiting Testing Strategy
- The email verification endpoint uses Flask-Limiter (`@limiter.limit("3 per hour", key_func=_rate_limit_key)`).
- Tests will fire consecutive requests to assert that the 4th request returns HTTP 429 Too Many Requests, ensuring protection against victim mailbox flooding.

## Risks / Trade-offs

- [Flask-Limiter state leak between tests] → Mitigation: Ensure limiter reset or use distinct test user fixtures for rate-limiting tests so adjacent tests are unaffected.
- [Static gallery directory dependency] → Mitigation: Use `tmp_path` fixture or existing test asset directory to verify `send_from_directory` behavior safely without relying on production filesystem state.
