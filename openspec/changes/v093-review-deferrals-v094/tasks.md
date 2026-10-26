## 1. Shell Script Syntax & HTTP Signature CLI Test Suites

- [ ] 1.1 In `tests/bash/scripts_syntax.bats`, add syntax validation tests (`bash -n`) for `scripts/iqopretest.sh`, `scripts/verify_federation_preview.sh`, and `deploy/wait-for-postgres.sh`, and verify via `IQOQO_AI_MODE=1 bats tests/bash/scripts_syntax.bats` *(Note: BGG2/IGDB, FTS, OpenAPI, PAT/TOTP, and i18n code fixes were pulled forward into `v093-take3-review-remediation` in `v0.9.3`)*
- [ ] 1.2 Author `tests/test_verify_http_signature.py` testing `scripts/verify_http_signature.py` CLI argument parsing, SHA-256 Digest header verification, signing string assembly, clock-skew rejection, and RSA-SHA256 signature verification, and verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_verify_http_signature.py`

## 2. Auxiliary Frontend UI Component Unit Tests

- [ ] 2.1 Author component tests `frontend/__tests__/components/cookie-consent.test.tsx` (localStorage consent detection & banner dismissal) and `frontend/__tests__/components/mode-toggle.test.tsx` (theme switching & accessible buttons), and verify via `IQOQO_AI_MODE=1 npm --prefix frontend test -- cookie-consent mode-toggle`
