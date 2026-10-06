## Why

A recent security review (v0.7.17 Security Review 3) identified several critical and high vulnerabilities in the previous fix attempt. We need to remediate these immediately to prevent authorization bypass, token leakage, and exposure of cloud storage credentials in Docker layers.

## What Changes

- Implement strict basename matching and ownership validation for feedback screenshots (`app/api/feedback.py`) to fix authorization bypass.
- Add host validation against authorized domains for the `X-Forwarded-Host` header (`frontend/app/api/auth-exchange/route.ts`) to prevent open redirects.
- Remove `COPY rclone.conf*` from `deploy/Dockerfile` so secrets are strictly injected at runtime instead of being baked into the image.
- Explicitly set `X-Forwarded-Host` in `deploy/nginx.conf` for the `auth-exchange` proxy pass.
- Remove deprecated `.allegro_token.json` mount from `docker-compose.yml`.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- **app/api/feedback.py**: Screenshot authorization logic.
- **frontend/app/api/auth-exchange/route.ts**: Authentication exchange redirect URL generation.
- **deploy/Dockerfile**: Docker image building process.
- **deploy/nginx.conf**: Nginx reverse proxy headers for auth.
- **docker-compose.yml**: Volume mounts for development/production.
