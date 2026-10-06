# Proposal: v0.7.17 Security Review 4 Remediation

## Why

Security review 4 of the v0.7.17 release candidate identified three critical/high/medium security findings:
1. Critical: Broad wildcard domain allowlisting in `deploy/sandbox_proxy/allowlist.conf` allows prompt injection attackers inside `mykg-agy-daemon` to exfiltrate the mounted Antigravity OAuth token to unauthenticated Google endpoints (such as Google Forms, Google Apps Script, and Google Cloud Storage buckets).
2. High: Attachment validation in `app/api/feedback.py` uses `any()` instead of `all()` when evaluating ticket access permissions, allowing an attacker who discovers a victim's screenshot filename to access the victim's file via an identical filename collision on a newly created ticket.
3. Medium: In `frontend/app/api/auth-exchange/route.ts`, when incoming `Host` header validation fails, the fallback defaults to `url.host`, which in Next.js is derived directly from the untrusted incoming request header itself, enabling open redirects to arbitrary domains.

Remediating these vulnerabilities hardens the sandbox egress boundary, eliminates the IDOR vector in user feedback attachments, and closes the open redirect flaw in authentication token exchange.

## What Changes

- **Harden Sandbox Egress Allowlist**: Remove broad wildcard domains (`*.google.com`, `*.googleapis.com`, `*.googleusercontent.com`, `*.google`, `*.goog`) and replace them with the exact 12 Google Antigravity, CloudCode, Gemini, and OAuth endpoints required for `agy` CLI operation.
- **Enforce Strict Ticket Attachment Authorization**: In `app/api/feedback.py`, replace `any()` with `all()` in `_validate_screenshot_access` so that access to an attachment is granted only if the user has authorization for every ticket referencing that filename.
- **Fail-Closed Host Header Fallback in Auth Exchange**: In `frontend/app/api/auth-exchange/route.ts`, replace the unsafe `url.host` fallback with `fallbackHost` (`NEXT_PUBLIC_FRONTEND_URL` hostname or `"localhost:3000"`).
- **Update Automated Verification Suites**: Update `tests/test_sandbox_proxy.py`, `tests/bash/mykg_tooling.bats`, `tests/test_feedback_tickets.py`, and `frontend/__tests__/app/api/auth-exchange.test.ts` to reflect the hardened behaviors and assert regression prevention.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ai-sandbox-egress-filtering`: Restrict AI sandbox egress exclusively to verified, surgical Google Gemini, Antigravity, CloudCode, and OAuth endpoints with zero broad wildcard domains.
- `feedback-screenshot-rclone`: Enforce that feedback screenshot retrieval requires authorization across all tickets containing the matching attachment.

## Impact

- `deploy/sandbox_proxy/allowlist.conf`: Updated ruleset.
- `app/api/feedback.py`: Updated access check.
- `frontend/app/api/auth-exchange/route.ts`: Hardened fallback logic.
- Automated test suites in Python, TypeScript (Vitest), and Bash (Bats).
