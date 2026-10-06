## 1. Backend Fixes

- [x] 1.1 Update `app/api/feedback.py` to enforce strict basename matching for screenshot authorization and verify tests pass.

## 2. Frontend Fixes

- [x] 2.1 Update `frontend/app/api/auth-exchange/route.ts` to validate the `X-Forwarded-Host` against authorized domains and verify the auth test suite passes.

## 3. Infrastructure Fixes

- [x] 3.1 Update `deploy/Dockerfile` to remove `rclone.conf` secret copying and verify the image builds without errors.
- [x] 3.2 Update `deploy/nginx.conf` to explicitly pass `$http_host` to `X-Forwarded-Host` in the auth-exchange location block and verify syntax with `nginx -t` (or locally).
- [x] 3.3 Update `docker-compose.yml` to remove the deprecated `.allegro_token.json` mounts and verify `docker compose config` is valid.
