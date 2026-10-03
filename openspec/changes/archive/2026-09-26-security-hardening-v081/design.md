## Context

See `proposal.md` for overall motivation.

Following the resolution of critical security findings in v0.7.18, the codebase still contains 30 moderate security findings identified during the pre-release audit. This change addresses 29; account-deletion confirmation (`MOD-SEC-22`) is deferred to the dedicated v0.8.3 change `account-deletion-email-confirmation-v083`. The in-scope findings span:
- Authentication & credential flows (missing password minimums, unconstrained user credentials).
- Injection risks & input sanitization (naive regex XSS stripping, unbounded avatar URLs, IGDB payload injection, raw search schema interpolation).
- Missing database constraints (unrestricted visibility and lifecycle status strings, self-borrowing loans).
- Denial of service & performance vectors (unthrottled public RSS/search endpoints, per-request DB queries for token revocation, N+1 query storms in catalog views).
- Insecure defaults in operational scripts and container definitions.

This design specifies the implementation architecture across the Flask backend, PostgreSQL 18 schema, Redis 8 cache layer, Next.js frontend, and deployment infrastructure.

## Goals / Non-Goals

**Goals:**
- Resolve the 29 in-scope MOD-SEC findings in a unified, testable v0.8.1 hardening release; defer `MOD-SEC-22` for dedicated v0.8.3 design and implementation.
- Enforce defense-in-depth: database-level `CheckConstraint` rules backing application-layer validations.
- Accelerate token revocation checks from SQL roundtrips to Redis in-memory lookups.
- Standardize all user-input HTML sanitization on `bleach.clean()`.
- Eliminate sensitive information disclosure in error responses and administrative token utilities.
- Secure operational configuration templates and container defaults.

**Non-Goals:**
- Full architectural decomposition of monolithic frontend components (deferred to scheduled v0.8.0 / v0.8.2 component overhauls).
- Reworking the core FRBR hierarchy or changing REST entity routes (e.g. negative-ID wishlist item transition is preserved).
- Introducing breaking changes to external client authentication protocols.
- Implementing account-deletion confirmation, which is tracked separately so the email ownership-confirmation flow and deletion lifecycle receive focused design and testing.

## Decisions

### Decision 1: Input Sanitization via Bleach over Custom Regexes (`MOD-SEC-18`)
- **Rationale:** Regular expressions for HTML tag stripping are notoriously vulnerable to evasion (malformed brackets, nested tags, mixed-case protocol handlers, attribute injection). The `bleach` library is already integrated into the backend environment. We standardize all user content ingress (`app/api/social.py:41`, feedback tickets, comments) on:
  ```python
  bleach.clean(value, tags=[], attributes={}, protocols=[], strip=True).strip()
  ```
- **Alternatives Considered:**
  - `html.escape()`: Escapes entities (`&lt;`), which causes double-escaping issues when frontend components render strings or markdown.
  - Hardened regex: Still susceptible to parser differential attacks.

### Decision 2: Database-Level Integrity Constraints via Alembic Migration (`MOD-SEC-01`, `02`, `03`, `04`, `05`, `07`, `30`)
- **Rationale:** Application-level validation is bypassed during batch scripts, direct SQL seeds, or future endpoint additions. We introduce explicit PostgreSQL `CheckConstraint` declarations in SQLAlchemy models and generate a clean Alembic migration:
  - `users.visibility`: `CHECK (visibility IN ('private', 'shared', 'public'))`
  - `users.credentials`: `CHECK (password_hash IS NOT NULL OR google_id IS NOT NULL)`
  - `items.status`, `items.collection_status`, and `user_work_intents.status`: retain and test the existing constraints using `ITEM_STATUSES`, `COLLECTION_STATUSES`, and `WORK_INTENT_STATUSES` from the taxonomy module.
  - `roadmap_items`: retain the existing `check_roadmap_item_single_frbr_level` constraint, which requires exactly one of `work_id`, `expression_id`, or `manifestation_id`. This preserves expression-only roadmap entries; do not add Item-level targets in this change.
  - `container_aggregations.aggregated_type`: add `CHECK (aggregated_type IN ('work', 'item'))` alongside the existing stronger type/target consistency constraint.
  - `loan_requests.self_borrow`: a PostgreSQL trigger that joins the referenced item and rejects insert/update when the requester is its owner. An ordinary `CHECK` constraint cannot safely enforce this cross-table comparison. The API/service also validates before persistence and returns a clear client error; the frontend hides or disables the action for the owner and handles server-side rejection.
- **Alternatives Considered:**
  - PostgreSQL ENUM types: Harder to alter and migrate when new states are introduced; CheckConstraints provide identical validation guarantees with easier future migrations.
  - API-only self-borrow validation: Rejected because direct SQL writes and future code paths would bypass the lending invariant.

### Decision 3: Redis Cache Layer for Token Revocation (`MOD-SEC-10`)
- **Rationale:** In `@require_auth`, verifying whether a token's JTI exists in `token_blocklist` incurs a PostgreSQL query on every single API invocation. We implement a two-tier check:
  1. Check Redis key `token:revoked:<jti>`. If exists, reject immediately.
  2. If Redis key is missing, check PostgreSQL `token_blocklist`.
  3. When a token is revoked (e.g. at logout), write to both PostgreSQL and Redis with `EXPIRE` set to the remaining token lifetime.
  4. If Redis is unavailable or disconnected, fail open to the database query seamlessly.
- **Alternatives Considered:**
  - In-process Python cache: Fails across multi-worker Gunicorn deployments.

### Decision 4: Avatar URL Protocol & SSRF Allowlisting (`MOD-SEC-15`)
- **Rationale:** `avatar_url` must be restricted to safe schemes (`https://` or absolute paths on the local instance static root `/static/`). We parse the URL with `urllib.parse.urlparse`:
  - Enforce HTTPS for every submitted avatar URL.
  - Disallow relative paths, `javascript:`, `data:`, `file:`, and plaintext `http://`.
  - Resolve external hostname IPs and block RFC 1918 private ranges, loopback (`127.0.0.1`), and cloud metadata (`169.254.169.254`).
- **Alternatives Considered:**
  - Fetching and re-hosting all avatars: Unnecessary disk overhead for self-hosted instances.

### Decision 5: Rate Limiting Public Endpoints (`MOD-SEC-16`, `MOD-SEC-19`, `MOD-SEC-11`)
- **Rationale:** Public endpoints lack authentication barriers and are vulnerable to scraping or resource exhaustion. Using `Flask-Limiter` with client IP key:
  - `/api/public/feed.xml`: `@limiter.limit("60 per minute")`
  - `/api/profile/search`: `@limiter.limit("30 per minute")`
  - `/api/sharing`: `@limiter.limit("30 per minute")` (per user)
  - Existing `/api/stats/global`: `@limiter.limit("30 per minute")`; expose aggregate counts only and return generic client errors.
- **Alternatives Considered:**
  - Global Nginx rate limiting: Difficult to maintain consistently across varying deployment options (Docker, preview scripts, bare metal).

### Decision 6: Secure Defaults in Docker & Configuration (`MOD-SEC-25`, `MOD-SEC-26`, `MOD-SEC-27`, `MOD-SEC-21`, `MOD-SEC-28`, `MOD-SEC-29`)
- **Rationale:**
  - In `docker-compose.yml`, remove `POSTGRES_PASSWORD=changeme` default; require the variable from `.env`.
  - Verify the existing import-time checks in `app/config.py` crash startup if `SECRET_KEY` is weak or a known placeholder; add subprocess regression tests and do not duplicate validation in `app/core/config_service.py`.
  - In `.env.example`, set `ALLOW_LLM=false`.
  - In `app/utils/igdb.py`, write token cache using `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)`.
  - In `scripts/init_auth.py`, assert `len(password) >= 8`.
  - In `scripts/generate_admin_token.py`, query `user.is_active` and abort if False.

### Decision 7: Follow Current Next.js Runtime and Proxy Conventions (`MOD-SEC-24`)
- **Rationale:** In the installed Next.js 16.3.5 docs, `proxy.ts` is the active convention for request routing, while the Edge Runtime is deprecated. Retain `frontend/proxy.ts` and its redirect tests because they protect page navigation; they are not backend authorization. Remove only the `runtime = "edge"` export from `frontend/app/apple-icon.tsx`; Node.js is the default. Verify the warning is absent from build/startup output and that `/apple-icon` still produces a rendered PNG.
- **Alternatives Considered:**
  - Delete `proxy.ts`: Rejected because it would remove active login redirect behavior and its tests.
  - Set `runtime = "nodejs"` explicitly: Unnecessary because Node.js is the documented default; Next.js recommends removing the deprecated export.

## Risks / Trade-offs

- **[Risk] Existing database rows violate new CheckConstraints** →
  *Mitigation*: Provide migration pre-flight validation that checks for existing non-compliant rows (e.g., NULL credentials or legacy statuses) and updates them before applying `ALTER TABLE ... ADD CONSTRAINT`.
- **[Risk] Redis failure blocks token verification** →
  *Mitigation*: Wrap Redis calls in a `try...except` block that logs a warning and falls back immediately to the PostgreSQL database table.
- **[Risk] Strict password length breaks automated test fixtures** →
  *Mitigation*: Audit existing test helpers (`tests/conftest.py`) to ensure all test passwords (e.g., `'password123'`, `'testpass123'`) meet the 8-character minimum.

## Migration Plan

1. **Alembic Migrations**:
   - The lending-trigger revision enforces the cross-table self-borrow invariant.
   - The security-constraints revision replaces the legacy user visibility check and adds user authentication-method and container aggregation discriminator checks. Existing item, intent, and roadmap constraints remain in place and are verified rather than duplicated.
   - Preflight user authentication rows and aggregation types; fail with a clear error instead of silently deleting accounts or rewriting unrelated rows.
2. **Rollback Strategy**:
   - Alembic `downgrade()` drops only newly added constraints and restores the legacy visibility check. It refuses to downgrade while `shared`-visibility users exist. The roadmap target constraint remains unchanged.
3. **Deployment**:
   - Apply backend code changes.
   - Run database migrations (`flask db upgrade`).
   - Re-deploy frontend Next.js application.
