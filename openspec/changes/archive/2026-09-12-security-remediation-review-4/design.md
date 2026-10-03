# Design: v0.7.17 Security Review 4 Remediation

## Context

See [proposal.md](proposal.md) for vulnerability motivation and context.
The system uses:
- Python Flask backend with SQLAlchemy ORM and Celery background tasks.
- Next.js 16 App Router frontend with Vitest test suite.
- Docker Compose AI sandbox (`docker-compose.ai_sandbox.yml`) running `mykg-agy-daemon` on an isolated internal network connected to a Python forward proxy (`deploy/sandbox_proxy/proxy.py`).

## Goals / Non-Goals

**Goals:**
- Eliminate unauthenticated Google service egress vectors from the AI sandbox without breaking `agy` CLI operations.
- Enforce strict authorization across all tickets referencing a screenshot attachment to prevent IDOR via collision.
- Ensure host validation in `frontend/app/api/auth-exchange/route.ts` fails closed against poisoned `Host` and `X-Forwarded-Host` headers.
- Maintain full test suite green across Bats, Pytest, and Vitest.

**Non-Goals:**
- Modifying the underlying FRBR database schema or adding new database tables.
- Rewriting the forward proxy architecture into an external C/Go binary (Python asyncio proxy is sufficient and zero-dependency).
- Changing ticket submission logic or attachment file storage mechanisms.

## Decisions

### Decision 1: Surgical Allowlist without Wildcards
- **Choice**: Permit only the verified 12 Google endpoints required by `agy` (`antigravity-unleash.goog:443`, `antigravity.google:443`, `cloudcode-pa.googleapis.com:443`, `daily-cloudcode-pa.googleapis.com:443`, `autopush-cloudcode-pa.sandbox.googleapis.com:443`, `generativelanguage.googleapis.com:443`, `www.googleapis.com:443`, `play.googleapis.com:443`, `accounts.google.com:443`, `oauth2.googleapis.com:443`, `lh3.googleusercontent.com:443`, `fonts.gstatic.com:443`).
- **Rationale**: Empirically verified via live execution. Gemini's proposed 5-domain allowlist omitted `cloudcode-pa` and `antigravity-unleash`, causing `agy` to crash on license check (`loadCodeAssist`). The surgical list blocks `storage.googleapis.com`, `docs.google.com`, and `script.google.com` while keeping `agy` fully operational.
- **Alternatives Considered**: Keeping wildcard `*.googleapis.com` (rejected due to GCS bucket exfiltration risk).

### Decision 2: Attachment Access Requirement with `all()`
- **Choice**: In `_validate_screenshot_access(filename)`, replace `not any(...)` with `not all(_can_read_ticket(user, it) for it in matching_tickets)`.
- **Rationale**: If a filename is linked to multiple tickets (whether via bug, duplicate upload, or malicious manual creation), the requester must have valid authorization to read every single ticket referencing it.
- **Alternatives Considered**: Restricting attachments strictly by ticket ID in the URL path (rejected because it would require breaking changes to existing client screenshot URLs and migration).

### Decision 3: Host Validation Fail-Closed Fallback
- **Choice**: In `frontend/app/api/auth-exchange/route.ts`, fallback to `process.env.NEXT_PUBLIC_FRONTEND_URL` hostname if available, or `"localhost:3000"`.
- **Rationale**: `url.host` reflects the untrusted request header directly. When host validation fails, using a static, safe host completely eliminates open redirect opportunities.

## Risks / Trade-offs

- **[Risk] Google CloudCode Endpoint Migration** → Google Antigravity may in future releases route traffic to a new regional subdomain.  
  *Mitigation*: The allowlist includes both production and daily/autopush `cloudcode-pa` endpoints; regression tests and CI capture proxy blocks immediately.
- **[Risk] Multiple users legitimately sharing an attachment filename** → Highly improbable given 128-bit UUID generation (`feedback-<uuid4>.jpg`), but if it ever happens and one user lacks access, access will fail closed rather than leaking data.
