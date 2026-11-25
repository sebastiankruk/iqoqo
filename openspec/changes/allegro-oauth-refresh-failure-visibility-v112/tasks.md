## 1. Allegro Token Refresh Failure Persistence (`app/utils/allegro.py`)

- [ ] 1.1 Add `_mark_allegro_refresh_failed(tokens, error_code)` helper to persist `refresh_failed: True`, sanitized `refresh_error` (OAuth error code only, never `error_description`/JWT), and `refresh_failed_at` to both Redis cache and encrypted `InstanceSettings("ALLEGRO_TOKEN_DATA")` without touching `ALLEGRO_CLIENT_ID` or `ALLEGRO_CLIENT_SECRET`.
- [ ] 1.2 Update `save_allegro_token()` to strip `refresh_failed`, `refresh_error`, and `refresh_failed_at` when fresh Device Flow or refreshed tokens are saved.
- [ ] 1.3 Update `_refresh_user_token()` to inspect HTTP `400` (`error in ("invalid_grant", "unauthorized_client")`) and HTTP `401` responses, call `_mark_allegro_refresh_failed()`, and leave transient (`5xx`, `429`, timeout, network) failures unpersisted.
- [ ] 1.4 Introduce `_get_allegro_token_with_mode()` (keeping `get_allegro_token()` backward-compatible) that short-circuits `refresh_token` POSTs when `tokens.get("refresh_failed")` is `True`, and update `has_allegro_user_token()` to return `False` when `refresh_failed` is `True`.

## 2. Allegro API Diagnostics & Status Endpoint (`app/utils/allegro.py`, `app/api/system.py`)

- [ ] 2.1 Update `fetch_allegro_candidates()` to use `_get_allegro_token_with_mode()`, gate `/offers/listing` strictly on `auth_mode == "user_context"`, and log secret-free `WARNING` diagnostics (endpoint, HTTP status, `auth_mode`) when `/sale/products` or `/offers/listing` returns `401` or `403`.
- [ ] 2.2 Update `get_allegro_token_status(probe_remote: bool = False)` to return `allegro_token_active: False`, `reason: "reauth_required"`, `refresh_error`, and `refresh_failed_at` when `refresh_failed` is `True`, and to attempt `_refresh_user_token()` when `probe_remote=True` on an expired refreshable token.
- [ ] 2.3 Wire `probe_remote=probe_remote` into `get_allegro_token_status(probe_remote=probe_remote)` inside `GET /api/system/status` in `app/api/system.py`.

## 3. CLI Status Tooling & Instance Settings UI

- [ ] 3.1 Update `scripts/iqoqo-status.sh` Allegro status check to handle `reason == "reauth_required"` explicitly with a `warn` message instructing the operator to re-authorize Allegro in Instance Settings (including sanitized `refresh_error` if present).
- [ ] 3.2 Update `frontend/components/admin/instance-settings.tsx` to display a clear re-authorization required warning badge/banner when `/api/system/status` reports Allegro `reason === "reauth_required"`.

## 4. Automated Tests & Verification

- [ ] 4.1 Add backend unit tests covering: `400 invalid_grant` persisting `refresh_failed` without leaking JWT `error_description`, transient `503`/timeout not poisoning token state, short-circuiting repeated refresh POSTs, `save_allegro_token()` clearing failure flags, `get_allegro_token_status(probe_remote=True)`, and `403` warning logging with `auth_mode` in `fetch_allegro_candidates()`.
- [ ] 4.2 Add shell/script test covering `scripts/iqoqo-status.sh` warning output for `reason == "reauth_required"`.
- [ ] 4.3 Add frontend Vitest test verifying Instance Settings renders the re-authorization warning when Allegro status is `reauth_required`.
- [ ] 4.4 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make secret-scan`, and targeted pytest/Vitest suites to verify all checks pass cleanly.
