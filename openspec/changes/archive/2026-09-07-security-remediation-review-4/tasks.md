## 1. Sandbox Egress Allowlist Hardening (SEC-01)

- [x] 1.1 Update `deploy/sandbox_proxy/allowlist.conf` to replace broad wildcard domains with exact 12 Google Antigravity, CloudCode, Gemini, and OAuth endpoints
- [x] 1.2 Update `tests/test_sandbox_proxy.py` to assert that wildcards and `storage.googleapis.com` are blocked, while surgical CloudCode and Antigravity endpoints pass
- [x] 1.3 Update `tests/bash/mykg_tooling.bats` to check for surgical allowlist entries instead of wildcards
- [x] 1.4 Run pytest and bats to verify proxy egress enforcement passes
- [x] 1.5 Verify `play.googleapis.com:443` is retained for Clearcut telemetry and document `www.googleapis.com:443` OAuth2 UserInfo requirement
- [x] 1.6 Update `tests/test_sandbox_proxy.py` and `tests/bash/mykg_tooling.bats` to verify `play.googleapis.com:443` is permitted and exfiltration endpoints are blocked

## 2. Feedback Ticket Attachment IDOR Fix (SEC-02)

- [x] 2.1 Update `app/api/feedback.py` to replace `any()` with `all()` in `_validate_screenshot_access`
- [x] 2.2 Add regression test in `tests/test_feedback_tickets.py` verifying that cross-ticket filename collision with an unauthorized ticket results in HTTP 403 Forbidden
- [x] 2.3 Run pytest on feedback ticket test suite to verify authorization containment

## 3. Auth Exchange Host Header Validation Hardening (SEC-03)

- [x] 3.1 Update `frontend/app/api/auth-exchange/route.ts` to replace `url.host` fallback with secure fallback host (`NEXT_PUBLIC_FRONTEND_URL` or `"localhost:3000"`)
- [x] 3.2 Update `frontend/__tests__/app/api/auth-exchange.test.ts` to verify poisoned `Host` header fails closed to `localhost:3000`
- [x] 3.3 Run Vitest test suite to verify auth-exchange tests pass

## 4. Daemon Prompt Payload Sanitization & Egress Guardrails (SEC-01 Follow-up)

- [x] 4.1 Implement `sanitize_task_payload` in `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py` to redact `googleapis.com`, exfiltration URLs, base64 data URIs, and binary blobs
- [x] 4.2 Inject explicit security policy guardrails into `combined_prompt` in `.agents/skills/iqoqo-mykg/scripts/agy_daemon.py`
- [x] 4.3 Add unit tests in `tests/test_iqoqo_mykg.py` asserting prompt sanitization (including binary blobs) and guardrail injection
- [x] 4.4 Run pytest and bats to verify all daemon and proxy security tests pass

## 5. Documentation, Spec Sync & Quality Verification

- [x] 5.1 Update `openspec/specs/ai-sandbox-egress-filtering/spec.md` with modified requirements
- [x] 5.2 Document Option 1 allowlist narrowing and daemon payload sanitization in `docs/CHANGELOG.md`
- [x] 5.3 Run full linter and test suite (`make lint`, `make test`)
