# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.8.x   | :white_check_mark: |
| 0.7.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please email the maintainer or create a private security advisory on GitHub.

## Recent Security Updates

### Session, Credential & Egress Hardening (October 2026)

#### Authentication & Session Integrity

- **Logout Now Actually Revokes the Token**: `POST /api/auth/logout` resolved in the browser to the Next.js route handler, which deleted the session cookie and nothing else. Next route handlers take precedence over the `/api/:path*` rewrite, so Flask's blocklisting of the token's `jti` was unreachable from any browser request — the JWT stayed valid until it expired, and any copy of it (a proxy log, a shared machine, an exfiltrated cookie) still authenticated after sign-out. The handler now forwards the token to Flask as a `Bearer` header before clearing the cookie.
- **Login No Longer Reveals Which Addresses Are Registered**: an unknown email returned without running the password hash, measured at **0.00 ms against 90.40 ms** for a registered address with a wrong password. Scrypt dominates the request, so the gap enumerates every registered account far more reliably than the identical `"Invalid credentials"` body hides it. Login now always performs a password verification, comparing against a throwaway hash of a fresh per-process random value when there is nothing to check. The measured gap is **−0.28 ms**. Note that rate limiting and the minimum password length do **not** mitigate a timing oracle.
- **Profile Bio Length Enforced on Every Write Path**: the limit was applied to the primary profile-update route only, so other write paths accepted arbitrarily long biographies.

#### Egress & Privileged Operations

- **Linked-Open-Data Mutation Routes Require `write:metadata`**: the semantic-link relink and delete endpoints were declared `@require_auth` with no permission check, letting any signed-in standard user schedule outbound authority lookups for any manifestation, or delete links the reconciler had established. The relink route is an egress trigger reachable from the inside — the same amplification the SSRF allowlist prevents from the outside.
- **Browser RUM Credential Is Provisioned, Not Shipped**: the OpenObserve RUM ingest token was baked into the frontend bundle. It is now provisioned at deploy time by `scripts/provision_rum_token.py` and injected server-side.
- **Bounded DNS Resolution Pool** *(corrected — see the August 2026 entry, which described the vulnerable mechanism as the fix)*: a single process-wide pool behind a bounded semaphore that fails closed with `SSRFError` on exhaustion.

#### Scanning & Supply Chain

- **Secret Scanner No Longer Exempts the OpenSpec Tree**: a path allowlist covering `openspec/` silenced every credential ever added to a change proposal or delta spec — and did not even work, because CI reported 17 findings from the scan range of already-redacted text. The allowlist is now keyed on the three historical commits, and OpenSpec files are in scope for every current and future commit.
- **Unauthenticated Test-Reset Endpoint Requires a Shared Secret**: `POST /api/lending/test/reset` mutates state with no authentication of its own; requests must now present a matching `X-E2E-Reset-Secret`, and the endpoint refuses every request when `E2E_RESET_SECRET` is unset rather than falling open.
- **QR Label Print Escapes Catalog Data**: the print path builds an HTML string for `document.write()`. Work titles, author lines and `expression.content_type` all pass through `escapeHtml()`.

### Secret Encryption & Operational Hardening (September 2026)

#### Symmetric Encryption at Rest & Secret Migration

- **Fernet Secret Encryption**: Encrypted all sensitive external API credentials, OAuth tokens, and secret keys stored in `InstanceSettings` using symmetric Fernet encryption keyed from `SECRET_KEY`. Added credential masking (`sk-...`, `AIza...`) across API endpoints and Admin UI.
- **Automated Secret Migration Utility**: Added `scripts/migrate_env_secrets_to_db.py` and `make migrate-secrets` to safely migrate credentials from plaintext `.env` to encrypted database storage and comment out source variables.

#### Web & Operational Hardening

- **SSRF Redirect Type Safety**: Enforced string type coercion and strict URL scheme validation for redirect `Location` headers in cover fetches (`app/utils/covers.py`).
- **Archive Path Traversal (Zip Slip) Protection**: Validated canonical target paths in `scripts/restore_covers.py` before extracting zip archives to prevent directory traversal.
- **Host Header Poisoning & Open Redirect Mitigation**: Enforced host allowlisting with secure fail-closed fallback in auth exchange routes (`frontend/app/api/auth-exchange/route.ts`).
- **Feedback Screenshot IDOR Containment**: Upgraded permission checks to strict `all()` verification across matching tickets in `_validate_screenshot_access` (`app/api/feedback.py`).
- **Operational Script Guards**: Enforced typed interactive confirmation prompts and production environment blocks (`FLASK_ENV=production`) on destructive scripts (`clone.sh`, `init_db.py --reset`, `migrate_legacy.py --clear`).

### Subprocess & Network Hardening (August 2026)

#### Subprocess Command Injection Prevention

- **POSIX Option Delimiters**: Enforced `--` end-of-options delimiters in all `subprocess.run()` invocations calling `rclone` across background tasks, cover image processing, and LLM utilities (`app/core/tasks.py`, `app/utils/images.py`, `app/utils/llm_covers.py`), eliminating argument injection vulnerabilities from user-controlled paths or filenames.

#### Network & SSRF Resilience

- **SSRF-Safe HTTP Client**: Integrated `app/utils/http_client.py` for fetching external assets, blocking private and link-local IP ranges (RFC 1918, localhost, AWS metadata `169.254.169.254`).
- **Bounded DNS Resolution Pool**: `_resolve_with_timeout` submits lookups to a single process-wide `ThreadPoolExecutor` behind a bounded semaphore, and **fails closed with `SSRFError` when the pool has no capacity** — it never falls back to an unchecked or unbounded resolution. The previous implementation built a *new* single-worker pool per call and then called `executor.shutdown(wait=False)`, which releases the executor object while leaving its worker thread alive; a sustained DNS stall therefore accumulated live threads until the process exhausted its thread budget and the web tier went down with it. A blocked lookup is now abandoned rather than cancelled, because a thread already inside the C-level resolver cannot be interrupted — which is exactly why the worker count is capped.
- **Redirect URL Type Coercion**: Enforced strict string coercion on redirect `Location` headers in `safe_get()` to avoid `TypeError` denial-of-service crashes.
- **XXE Prevention**: Enforced `defusedxml` across XML parsers (`app/utils/bgg.py`, `app/api/items.py`) to block entity expansion and external entity retrieval attacks.

### Resolved Vulnerabilities (February 2026)

#### Python Dependencies

| Package                | Version  | CVE(s)                                      | Severity | Status          |
|------------------------|----------|---------------------------------------------|----------|-----------------|
| opencv-python-headless | 4.8.1.78 | Multiple CVEs (see below)                   | High     | Fixed (4.13.0+) |
| flask-cors             | 4.0.2    | CVE-2024-6866, CVE-2024-6844, CVE-2024-6839 | High     | Fixed (6.0.0+)  |
| gunicorn               | 21.2.0   | CVE-2024-1135, CVE-2024-6827                | High     | Fixed (22.0.0)  |

**OpenCV Vulnerabilities Fixed:**

- CVE-2023-4863: Bundled libwebp binaries vulnerability (High)
- Multiple Out-of-bounds Write vulnerabilities (High)
- Multiple Out-of-bounds Read vulnerabilities (High/Moderate)
- NULL Pointer Dereference (High)
- Divide By Zero (Moderate)

**Actions Taken:**

- Updated `opencv-python-headless` from 4.8.1 to 4.13.0
- Updated `Flask-CORS` from 4.0.x to 6.0.x (fixes CVE-2024-6866, CVE-2024-6844, CVE-2024-6839)
- Enabled strict, environment-driven CORS configuration (disabled by default, explicit origin allowlist)
- Updated `gunicorn` from version 21.2 to 22.0

#### Node.js Dependencies

| Package     | Version | Vulnerability               | Severity | Status          |
|-------------|---------|-----------------------------|----------|-----------------|
| markdown-it | 13.0.0  | GHSA-38c4-r59v-3vqw (ReDoS) | Moderate | Fixed (14.1.0+) |

**Actions Taken:**

- Updated `markdownlint-cli2` from 0.20.0 to 0.21.0 (which uses markdown-it 14.1.0+)

### Known Issues

#### Development Dependencies (Acceptable Risk)

| Package | Version | Vulnerability               | Severity | Risk Assessment |
|---------|---------|-----------------------------|----------|-----------------|
| ajv     | 6.12.6  | GHSA-2g4f-4pwh-qvx6 (ReDoS) | Moderate | Low             |

**Details:**

- **Vulnerability:** Regular Expression Denial of Service (ReDoS) when using `$data` option
- **Affected Component:** `ajv` version < 8.18.0, used by `eslint` (dev dependency)
- **CVSS Score:** 0 (no score assigned)
- **Exploitation Requirements:**
  - Only affects ESLint during development/linting
  - Requires specific `$data` option to be enabled
  - Not present in production code or dependencies
- **Mitigation:**
  - This is a development-only dependency used for code linting
  - The vulnerability cannot be exploited in production
  - ESLint does not use the `$data` option in our configuration
  - Updating to ajv 8.x would break ESLint compatibility
- **Timeline:** Will be resolved when ESLint updates its dependencies to ajv 8.x

**Why This Is Acceptable:**

1. **Scope:** Development dependencies only, not shipped to production
2. **Exploitability:** Low - requires specific configuration not used in this project
3. **Impact:** Limited to development environment performance
4. **Trade-off:** Breaking ESLint functionality is a worse outcome than accepting this minimal risk

## Security Best Practices

When contributing to this project:

1. **Dependencies:** Regularly check for updates to dependencies
2. **Auditing:** Run `npm audit` and `.venv/bin/pip-audit` before committing
3. **Virtual Environment:** Always use the Python virtual environment (`.venv/`)
4. **Review:** Review all dependency updates for breaking changes

## Automated Security Checks

- **GitHub Dependabot:** Automatically monitors dependencies for vulnerabilities
- **CI/CD:** Linting and testing run on all pull requests
- **Regular Reviews:** Security advisories are reviewed monthly
