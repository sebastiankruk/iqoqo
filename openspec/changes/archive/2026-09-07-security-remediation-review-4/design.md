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

### Decision 1: Surgical Allowlist without Wildcards (12 Endpoints)

- **Choice**: Permit only the verified 12 Google endpoints strictly required by `agy` (`antigravity-unleash.goog:443`, `antigravity.google:443`, `cloudcode-pa.googleapis.com:443`, `daily-cloudcode-pa.googleapis.com:443`, `autopush-cloudcode-pa.sandbox.googleapis.com:443`, `generativelanguage.googleapis.com:443`, `www.googleapis.com:443`, `play.googleapis.com:443`, `accounts.google.com:443`, `oauth2.googleapis.com:443`, `lh3.googleusercontent.com:443`, `fonts.gstatic.com:443`).
- **Rationale**: Empirically verified via live execution. Testing confirmed `www.googleapis.com:443` must remain because `/home/sebastiankruk/.local/bin/agy` hardcodes `https://www.googleapis.com/oauth2/v2/userinfo` to fetch user identity during startup OAuth validation; if blocked, `agy` fails immediately with exit code 1 (`Forbidden`). Furthermore, `play.googleapis.com:443` is hardcoded in the Go binary for Google Clearcut telemetry logging (`play.googleapis.com/log`); if blocked, the internal event queue fills up and multi-turn streaming responses stall with `subscriber fell behind updates, stalled for 28s`. `play.googleapis.com/log` is strictly an append-only logging endpoint and cannot be used for arbitrary data hosting. The allowlist completely blocks `storage.googleapis.com`, `docs.google.com`, `script.google.com`, and `drive.google.com`.
- **Alternatives Considered**: Completely removing `www.googleapis.com` or `play.googleapis.com` (rejected: breaks startup OAuth token validation and causes streaming response stalls). Keeping wildcard `*.googleapis.com` (rejected: exposes GCS bucket exfiltration risk).

### Decision 2: Attachment Access Requirement with `all()`

- **Choice**: In `_validate_screenshot_access(filename)`, replace `not any(...)` with `not all(_can_read_ticket(user, it) for it in matching_tickets)`.
- **Rationale**: If a filename is linked to multiple tickets (whether via bug, duplicate upload, or malicious manual creation), the requester must have valid authorization to read every single ticket referencing it.
- **Alternatives Considered**: Restricting attachments strictly by ticket ID in the URL path (rejected because it would require breaking changes to existing client screenshot URLs and migration).

### Decision 3: Host Validation Fail-Closed Fallback

- **Choice**: In `frontend/app/api/auth-exchange/route.ts`, fallback to `process.env.NEXT_PUBLIC_FRONTEND_URL` hostname if available, or `"localhost:3000"`.
- **Rationale**: `url.host` reflects the untrusted request header directly. When host validation fails, using a static, safe host completely eliminates open redirect opportunities.

### Decision 4: Inbound Prompt Payload Sanitization and Defense-in-Depth Guardrails

- **Choice**: In `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py`, add `sanitize_task_payload(text: str) -> str` to regex scrub `googleapis.com` domains, Drive/Docs URLs, cloud storage targets, base64 data URIs, and large unbroken binary blobs (500+ alphanumeric chars) from incoming task payloads before passing them to the `agy` CLI. Additionally, inject explicit security policy guardrails in `combined_prompt` instructing the agent never to transmit data or credentials to external network addresses.
- **Rationale**: While `www.googleapis.com:443` and `play.googleapis.com:443` are strictly required at the proxy level for `agy` operation, prompt-injection attackers might attempt to direct `agy` to exfiltrate tokens or data to Google endpoints. Sanitizing payloads at the ingest layer strips domain targets, prevents 35KB+ base64 zip dumps from choking the Gemini token stream, and prompt guardrails ensure the agent strictly adheres to egress policy.
- **Alternatives Considered**: Completely blocking `www.googleapis.com` or `play.googleapis.com` at the proxy (empirically tested and rejected: `agy` binary hardcodes these for startup UserInfo and Clearcut telemetry).

## Risks / Trade-offs

- **[Risk] Google CloudCode Endpoint Migration** → Google Antigravity may in future releases route traffic to a new regional subdomain.  
  *Mitigation*: The allowlist includes both production and daily/autopush `cloudcode-pa` endpoints; regression tests and CI capture proxy blocks immediately.
- **[Risk] Multiple users legitimately sharing an attachment filename** → Highly improbable given 128-bit UUID generation (`feedback-<uuid4>.jpg`), but if it ever happens and one user lacks access, access will fail closed rather than leaking data.
