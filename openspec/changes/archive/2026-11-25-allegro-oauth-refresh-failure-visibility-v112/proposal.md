## Why

In production (v1.1.1), an invalidated or expired Allegro OAuth refresh token (`400 invalid_grant` from `https://allegro.pl/auth/oauth/token`) silently breaks Polish ISBN fallback lookups and cover art retrieval while both `make status` and `/api/system/status` falsely report Allegro as `active`. Because `fetch_allegro_candidates` falls back to `client_credentials` (which Allegro rejects with `403 AccessDenied` on `/sale/products` and `/offers/listing`) and swallows those 403s at debug/silent level, operators get no actionable signal to re-authorize Allegro until book scans start returning 404 or `fallback_pil` covers.

Target release: **v1.1.2**.

## What Changes

- **Persist irreversible Allegro OAuth refresh failure state**: When `_refresh_user_token()` receives a non-transient OAuth grant rejection (`400` with `error == "invalid_grant"` or `401`), record `refresh_failed: true`, `refresh_error`, and `refresh_failed_at` in `ALLEGRO_TOKEN_DATA` (both DB `InstanceSettings` and Redis cache) without deleting `ALLEGRO_CLIENT_ID` or `ALLEGRO_CLIENT_SECRET`.
- **Stop false-positive active status**: Update `get_allegro_token_status()` and `has_allegro_user_token()` so a token marked `refresh_failed` reports `allegro_token_active: false` and `reason: "reauth_required"` (instead of `active`), and is excluded from user-context API calls until re-authorized via Device Flow (`save_allegro_token()` clears the failure flags).
- **Avoid hammering Allegro auth on dead refresh tokens**: Short-circuit repeated `refresh_token` POSTs in `get_allegro_token()` once `refresh_failed` is persisted, preventing redundant failed OAuth calls on every scan or cover fetch.
- **Surface Allegro `401`/`403` access denials in logs and status tooling**: Log clear `WARNING` diagnostics (endpoint, HTTP status, token mode — never secrets/tokens) in `fetch_allegro_candidates()` when `/sale/products` or `/offers/listing` returns `401`/`403`, and handle `reason == "reauth_required"` explicitly in `scripts/iqoqo-status.sh` and the Instance Settings UI (`frontend/components/admin/instance-settings.tsx`).
- **Admin on-demand probe support**: Support `probe_remote=True` in `get_allegro_token_status()` (wired from `GET /api/system/status?probe=true`, matching `get_igdb_token_status`) so admins can actively verify an expired token's refreshability on demand.

## Capabilities

### New Capabilities

<!-- No brand-new top-level capability; extends existing allegro-oauth specification. -->

### Modified Capabilities

- `allegro-oauth`: Extend Allegro status inspection, token lifecycle failure persistence, `403`/`401` diagnostic visibility, and `make status` / Instance Settings re-authorization signaling when an Allegro refresh token is rejected with `invalid_grant`.

## Impact

- **Backend**: `app/utils/allegro.py`, `app/api/system.py`
- **Operations / CLI**: `scripts/iqoqo-status.sh`
- **Frontend**: `frontend/components/admin/instance-settings.tsx` (status badge / re-auth prompt for `reauth_required`)
- **Tests**: Backend unit tests (`tests/test_allegro*.py`, `tests/test_system_status*.py`), script tests for `iqoqo-status.sh`, and frontend unit tests for Instance Settings Allegro status display.
- **No schema migrations**: Uses existing encrypted `ALLEGRO_TOKEN_DATA` JSON object in `InstanceSettings`.
