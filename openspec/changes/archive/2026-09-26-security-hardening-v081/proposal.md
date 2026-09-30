## Why

During the v0.7.18 comprehensive pre-release architectural review, 30 moderate security findings (`MOD-SEC-01` through `MOD-SEC-30`) were identified across authentication, authorization, input validation, database integrity constraints, rate limiting, and operational configuration. This change implements "C12: Security Hardening" in the v0.8.1 release milestone and addresses the 29 findings in its scope. `MOD-SEC-22` (account-deletion confirmation) is deliberately deferred to the dedicated `account-deletion-email-confirmation-v083` change targeted for v0.8.3 so its identity-confirmation and deletion lifecycle can be designed and tested separately.

## What Changes

- **Authentication & Credential Hardening**:
  - Enforce minimum password length of >= 8 characters on user registration and password update endpoints (`MOD-SEC-09`).
  - Add CHECK constraint on `users` table ensuring either `password_hash` or `google_id` is present (`MOD-SEC-30`).
  - Validate non-empty, strong admin password during script initialization in `init_auth.py` (`MOD-SEC-28`).
  - Check `user.is_active` status in `generate_admin_token.py` before minting administrative tokens (`MOD-SEC-29`).
  - Replace JWT-in-URL redirect with one-time authorization code exchange payload flow (`MOD-SEC-12`).
  - Sanitize OAuth and registration error messages to prevent internal stack or system information leakage (`MOD-SEC-13`).

- **Input Sanitization & Injection Defense**:
  - Replace naive regex tag stripping in `_sanitize_text` with robust `bleach.clean(tags=[], attributes={}, protocols=[], strip=True)` for user-supplied notes, feedback, and comments (`MOD-SEC-18`).
  - Require HTTPS for submitted `avatar_url` values and enforce SSRF protections against loopback and cloud metadata ranges (`MOD-SEC-15`).
  - Fix IGDB query builder payload injection by escaping backslashes before quotes in search terms (`MOD-SEC-20`).
  - Strip ISBN values and internal tracebacks from error responses in `lookup_isbn` (`MOD-SEC-14`).
  - Sanitize and strictly validate database schema prefixes against an allowlist before string interpolation in full-text search SQL queries (`MOD-SEC-08`).

- **Database Integrity & Enum CheckConstraints**:
  - Add `CheckConstraint` on `User.visibility` validating values in `('private', 'shared', 'public')` (`MOD-SEC-01`).
  - Add `CheckConstraint` on `Item.status` and `Item.collection_status` ensuring allowed lifecycle and inventory states (`MOD-SEC-02`).
  - Add `CheckConstraint` on `UserWorkIntent.status` for intent lifecycle states (`MOD-SEC-03`).
  - Prevent self-borrowing with database-level enforcement plus clear API and frontend handling for lending requests (`MOD-SEC-04`).
  - Verify the existing `RoadmapItem` constraint requires exactly one of `work_id`, `expression_id`, or `manifestation_id` (`MOD-SEC-05`), preserving expression-only roadmap targets. Item-level roadmap targeting is deferred to the v0.8.3 roadmap change.
  - Add `CheckConstraint("aggregated_type IN ('work', 'item')")` on `ContainerAggregation` (`MOD-SEC-07`).
  - Audit lazy-loaded `Manifestation.author` and `Work.expressions` across catalog and collection list views to ensure eager loading and prevent N+1 queries and authorization leaks (`MOD-SEC-06`).

- **Rate Limiting & Token Cache Optimization**:
  - Add rate limiting to public endpoints including RSS feeds (`/api/public/feed.xml`) and user search/public profiles (`MOD-SEC-16`).
  - Add rate limiting to collection share creation (`/api/sharing`) to prevent resource exhaustion and link spam (`MOD-SEC-19`).
  - Move `_is_token_revoked` token revocation lookup to a Redis cache check with PostgreSQL fallback to prevent database connection saturation on authenticated requests (`MOD-SEC-10`).
  - Apply `@optional_auth` to public social feedback and notes retrieval endpoints (`MOD-SEC-17`).
  - Document and rate limit the existing unauthenticated `/api/stats/global` endpoint to mitigate denial of service scraping (`MOD-SEC-11`); return only aggregate counts and generic errors.

- **Infrastructure, Defaults & Operational Hardening**:
  - Restrict file permissions to `0o600` via `os.open` when writing cached IGDB tokens (`MOD-SEC-21`).
  - Differentiate HTTP 404 (Not Found) from HTTP 50x (Server Error) in shared collection viewer rather than treating all errors as non-existent tokens (`MOD-SEC-23`).
  - Preserve the active Next.js 16 `frontend/proxy.ts` convention and its redirect tests; remove the deprecated Edge runtime export from the Apple icon route (Node.js is the default), and verify the build is warning-free and the generated icon renders (`MOD-SEC-24`).
  - Update `docker-compose.yml` to remove default `changeme` password for PostgreSQL and require explicit `.env` configuration (`MOD-SEC-25`).
  - Verify the existing import-time `Config` validation in `app/config.py` fails closed on weak or placeholder `SECRET_KEY` values at production startup; add regression tests without duplicating validation in `config_service.py` (`MOD-SEC-26`).
  - Default `ALLOW_LLM=false` in `.env.example` to prevent unintentional LLM token usage and billing exposure (`MOD-SEC-27`).

- **Explicitly Out of Scope**:
  - Account-deletion confirmation (`MOD-SEC-22`) is deferred to `account-deletion-email-confirmation-v083`, targeted for v0.8.3.

## Capabilities

### New Capabilities
- `security/hardening-v081`: Security hardening addressing 29 in-scope moderate security findings across input sanitization, authentication, enum constraints, rate limiting, token caching, SSRF prevention, and deployment defaults. `MOD-SEC-22` is deferred to a dedicated v0.8.3 change.

### Modified Capabilities
<!-- None: core domain models and APIs remain stable; all changes harden security boundaries and enforce database integrity -->

## Impact

- **Backend APIs (`app/api/`)**:
  - `app/api/auth.py`: Password length validation (>= 8 chars), sanitized error responses.
  - `app/api/profile.py`: Safe `avatar_url` validation and rate-limited user search.
  - `app/api/social.py`: `bleach.clean()` sanitization for feedback and notes, `@optional_auth` on read endpoints.
  - `app/api/manifestations.py`: Error response sanitation without leaking internal parameters.
  - `app/api/public.py`: Rate limiting on `/api/public/feed.xml`.
  - `app/api/sharing.py`: Rate limiting on collection share token creation.
  - `app/api/decorators.py`: Redis caching for token blocklist check.
  - `app/api/system.py`: Documented access expectations, 30/minute rate limiting, and sanitized errors on `/api/stats/global`.
- **Database Models & Migrations (`app/db/`, `migrations/`)**:
  - `app/db/auth.py`: CheckConstraints for `User.visibility`, CHECK constraint for password or Google ID.
  - `app/db/core.py`: CheckConstraints for `Item.status`, `Item.collection_status`, `UserWorkIntent.status`.
  - `app/db/lending.py` and migrations: Database trigger enforcing the cross-table self-borrow invariant.
  - `app/db/roadmap.py`: Verify the existing exactly-one Work/Expression/Manifestation target constraint; do not add Item-level roadmap targeting in this change.
  - `app/db/games.py`: CheckConstraint on `ContainerAggregation.aggregated_type`.
  - `migrations/versions/`: New Alembic migration adding CheckConstraints across affected tables.
- **Core Services & Utilities (`app/core/`, `app/utils/`)**:
  - `app/core/search_service.py`: Strict schema prefix allowlist validation.
  - `app/config.py`: Import-time production `SECRET_KEY` strength and placeholder verification; no duplicate check in `app/core/config_service.py`.
  - `app/utils/igdb.py`: Backslash escaping in query construction, `0o600` token file permissions.
- **Frontend (`frontend/`)**:
  - Lending request UI: Prevent or clearly reject attempts by an item owner to request their own item.
  - `frontend/app/share/[token]/page.tsx`: Proper error boundary distinguishing 404 from 500.
  - `frontend/proxy.ts`: Retain active protected-page redirect behavior and its tests; this UI routing layer is not a substitute for backend authorization.
  - `frontend/app/apple-icon.tsx`: Remove deprecated `runtime = "edge"` config and verify generated PNG output.
- **Deployment & Operational Scripts (`docker-compose.yml`, `scripts/`, `.env.example`)**:
  - `docker-compose.yml`: Safe database credentials requirement.
  - `scripts/init_auth.py`: Non-empty admin password check.
  - `scripts/generate_admin_token.py`: Active user verification.
  - `.env.example`: Secure default settings (`ALLOW_LLM=false`).
