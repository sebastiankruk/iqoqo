## 1. API Credentials Migration

- [x] 1.1 Add `CONFIG_KEY_BLOCKLIST` to `app/core/config_service.py` to prevent reading boot keys (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`) from the DB. Verify by running backend tests and ensuring DB overrides for these keys are ignored.
- [x] 1.2 Remove external API keys (e.g., TMDB, IGDB, OpenAI) from `.env.example` and add a comment indicating they belong in the Admin UI. Verify by checking `git diff` for `.env.example`.
- [x] 1.3 Audit and update `frontend/components/admin/settings-form.tsx` to securely manage the 16 target secrets. Verify by confirming the UI correctly handles mask/reveal actions for the newly added keys.

## 2. API Security Hardening

- [x] 2.1 Add `@limiter.limit` decorators to `/api/profile/search` (`profile.py`), RSS feeds (`public.py`), and collection creation (`sharing.py`). Verify by triggering the rate limit in local development and observing a 429 response.
- [x] 2.2 Add strict URL validation for `avatar_url` updates in `app/api/profile.py` to block `javascript:` and SSRF vectors. Verify by submitting a malformed URL and asserting a 400 Bad Request.
- [x] 2.3 Replace the naive regex XSS filter with `bleach.clean()` in `app/api/social.py`. Verify by running the social feedback backend tests with an XSS payload.
- [x] 2.4 Add `@optional_auth` to `get_social_feedback` and `get_social_notes` in `app/api/social.py`. Verify by ensuring unauthenticated reads still work but optionally capture user context safely.

## 3. Ops Robustness and Stability

- [x] 3.1 Add a `timeout=30` parameter to `subprocess.run(["rclone", ...])` calls in `app/api/feedback.py`. Verify by running feedback screenshot tests.
- [x] 3.2 Harden the guard on `reset_lending_test_state` in `app/api/lending.py` to prevent accidental triggering in production. Verify by manually hitting the endpoint outside of test mode and receiving a 403.
- [x] 3.3 Replace unbounded memory load in `fetch_global_fresh_arrivals` (`app/api/public.py`) with SQL-level uniqueness constraints (e.g., `DISTINCT ON`). Verify by checking the emitted SQL query or running backend tests.
