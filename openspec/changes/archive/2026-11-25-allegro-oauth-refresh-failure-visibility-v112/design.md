## Context

In production (v1.1.1), Polish book scans and cover fetches rely on Allegro as a fallback when Google Books, Open Library, and Biblioteka Narodowa lack metadata or cover art (Biblioteka Narodowa provides bibliographic metadata for Polish ISBNs but no cover images).

During a production incident, an Allegro User Context OAuth token aged 165.8h failed to refresh with `HTTP 400 {"error": "invalid_grant"}`. Three interacting gaps hid the outage:

1. `_refresh_user_token()` raised `HTTPError`, which `get_allegro_token()` caught and logged only as a generic warning while leaving the dead token untouched in Redis and `InstanceSettings("ALLEGRO_TOKEN_DATA")`.
2. `get_allegro_token_status()` computed `is_active = not is_expired or bool(tokens.get("refresh_token"))`, so both `make status` (`scripts/iqoqo-status.sh`) and `GET /api/system/status` reported `allegro_token_active: true, reason: "active"`.
3. `has_allegro_user_token()` returned `True` based solely on the presence of `access_token`, so `fetch_allegro_candidates()` fell back to `client_credentials` and still called `/sale/products` and `/offers/listing`, receiving `403 AccessDenied` on both and silently dropping the error (`debug` level on `/offers/listing`, ignored on `/sale/products`).

## Goals / Non-Goals

**Goals:**
- Persist non-transient Allegro refresh-token rejection (`400 invalid_grant` / `401`) on `ALLEGRO_TOKEN_DATA` so every process, healthcheck, and UI reflects `reauth_required` immediately.
- Prevent repeated failed OAuth refresh POSTs and invalid `/offers/listing` calls once a refresh token is known-dead.
- Ensure `make status`, `GET /api/system/status`, and the Admin Instance Settings UI surface `reauth_required` clearly with a re-authorization prompt.
- Log `401`/`403` denials from Allegro `/sale/products` and `/offers/listing` at `WARNING` level with token mode (`user_context` vs `client_credentials`) and zero secret leakage.
- Keep `save_allegro_token()` self-healing so completing the Device Code flow clears all failure flags atomically in cache and DB.

**Non-Goals:**
- Changing the Allegro OAuth Device Code flow UX or adding automatic browser login.
- Adding new non-Allegro Polish cover providers (out of scope for this change).
- Altering database schema or adding Alembic migrations (`ALLEGRO_TOKEN_DATA` is already an encrypted JSON setting in `InstanceSettings`).

## Decisions

### 1. Persist `refresh_failed` inside `ALLEGRO_TOKEN_DATA` instead of deleting the token row
- **Decision**: On `400` (`error == "invalid_grant"`) or `401` in `_refresh_user_token()`, merge `refresh_failed: True`, `refresh_error: <oauth_error_code>`, and `refresh_failed_at: time.time()` into the existing `ALLEGRO_TOKEN_DATA` dict and persist via `save_allegro_token(..., preserve_failure=True)` (or a dedicated helper `_mark_allegro_refresh_failed()`).
- **Rationale**: Preserving `created_at` and the failure metadata lets `get_allegro_token_status()` distinguish `reauth_required` (was authorized, refresh rejected) from `handshake_pending` (never authorized), and keeps `token_age_hours` visible for debugging.
- **Alternative considered**: Deleting `ALLEGRO_TOKEN_DATA` on `invalid_grant`. Rejected because operators would see `handshake_pending` instead of knowing their previously active token was revoked/expired.

### 2. Only treat `400 invalid_grant` and `401` as irreversible failures
- **Decision**: Network timeouts, connection errors, `429`, and `5xx` responses MUST NOT set `refresh_failed: True`. Only HTTP `401` or HTTP `400` whose JSON body contains `error == "invalid_grant"` (or `unauthorized_client`) triggers persistence.
- **Rationale**: Prevents temporary Allegro outages or DNS blips from permanently disabling user-context lookups until manual intervention.

### 3. Return `(token, auth_mode)` internally from token acquisition
- **Decision**: Introduce an internal helper `_get_allegro_token_with_mode() -> tuple[str | None, Literal["user_context", "client_credentials"] | None]` (keeping public `get_allegro_token() -> str | None` backward-compatible). `fetch_allegro_candidates()` uses `auth_mode` to gate `/offers/listing` (`auth_mode == "user_context"`) and include `auth_mode` in `401`/`403` warning logs.
- **Rationale**: Eliminates the race/mismatch where `get_allegro_token()` fell back to `client_credentials` while `has_allegro_user_token()` still returned `True`.

### 4. Admin `probe_remote=True` in `get_allegro_token_status()`
- **Decision**: Add optional `probe_remote: bool = False` parameter to `get_allegro_token_status()` and pass `probe_remote=probe_remote` from `GET /api/system/status` (already admin-gated in `app/api/system.py`). When `probe_remote=True` and the token is expired with a refresh token and not yet marked `refresh_failed`, invoke `_refresh_user_token()` so admins get live verification without waiting for a book scan.
- **Rationale**: Mirrors `get_igdb_token_status(probe_remote=probe_remote)` in `app/api/system.py` and keeps default status checks fast and offline-safe.

### 5. Sanitize error details before persisting or logging
- **Decision**: Extract only the short OAuth `error` code (e.g., `"invalid_grant"`) — never store or log `error_description` verbatim, because Allegro echoes the full JWT refresh token inside `error_description` (`"Invalid refresh token: eyJhbGci..."`).
- **Rationale**: Prevents accidental credential/token leakage into logs, OpenObserve, or API status payloads.

## Risks / Trade-offs

- **Allegro `error_description` contains raw JWT refresh token** → Explicitly extract only `payload.get("error")` (bounded allowlist/short string) and redact/omit `error_description` in logs, persisted `refresh_error`, and status API responses.
- **Redis cache vs DB drift across gunicorn/celery workers** → `_mark_allegro_refresh_failed()` writes both `InstanceSettings.set_value("ALLEGRO_TOKEN_DATA", ...)` and `cache.set("allegro_token_data", ...)` inside the existing `allegro_refresh_lock` distributed lock; `save_allegro_token()` strips `refresh_failed`/`refresh_error`/`refresh_failed_at` before saving to both stores.
- **False `reauth_required` if two workers race during token rotation** → `_refresh_user_token()` already re-reads `fresh_tokens` inside `cache.lock("allegro_refresh_lock", timeout=30)` and returns early if another worker already refreshed (`fresh_age <= 11 * 3600`). Preserving that double-check prevents a stale worker from triggering `invalid_grant` on an already-rotated refresh token.

## Migration Plan

- No database migration required.
- On deploy to v1.1.2, any instance with an already-expired broken refresh token will flip to `reason: "reauth_required"` on the first lookup or admin `?probe=true` check, immediately alerting via `make status` and Instance Settings UI.
- Rollback: Revert code; existing `ALLEGRO_TOKEN_DATA` JSON keys (`refresh_failed`, etc.) are ignored by v1.1.1 code.
