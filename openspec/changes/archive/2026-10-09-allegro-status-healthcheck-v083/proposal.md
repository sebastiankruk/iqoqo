## Why

Dev-note item (#important #bugs #DevOps #v083): "Check Allegro authentication in WebUI - `make status prod` shows warning". Release planning: v0.8.x, C58 (target v0.8.3).

Premises verified against code:
- **Root Cause 1: `/api/system/status` requires authentication.** In `scripts/iqoqo-status.sh:707,730`, the status script attempts an unauthenticated HTTP GET to `/api/system/status`. In `app/api/system.py:151`, `@api_bp.route("/system/status")` is decorated with `@require_auth`. The unauthenticated request returns HTTP 401, causing the HTTP check to fail unconditionally.
- **Root Cause 2: Standalone python probe lacks Flask application context.** When the HTTP check fails, `iqoqo-status.sh:718,741` falls back to `from app.utils.allegro import get_allegro_token_status`. That function accesses `InstanceSettings.get_value()`, which invokes `db.session.execute(...)`. Outside of a Flask `app_context()`, SQLAlchemy raises `RuntimeError: Working outside of application context.`.
- **Root Cause 3: Generic `query_failed` mapped to false warning.** In `iqoqo-status.sh:722,745`, the caught exception prints `{"configured": cid, "allegro_token_active": False, "reason": "query_failed"}`. Line 776 maps any unhandled reason to `warn "not active (OAuth handshake pending in Instance Settings)"`.
- **Result:** Even when Allegro is fully configured and authenticated, `make status prod` (and dev) ALWAYS warns that Allegro is not active or handshake is pending.

## What Changes

- **Public/Local Health Status Probe:** Either expose unauthenticated integration health on a lightweight status/healthcheck endpoint (or loopback-only check), or invoke the Python script with proper `create_app().app_context()`.
- **Proper Application Context in Status Probe:** Update `scripts/iqoqo-status.sh` to initialize Flask application context via `from app import create_app; app = create_app(); with app.app_context(): ...` when executing the Python fallback.
- **Accurate Status Discrimination:** Cleanly distinguish between:
  1. `NOT_CONFIGURED` (`info`): missing credentials.
  2. `ACTIVE` (`pass`): token valid or active refresh token present.
  3. `EXPIRED` (`warn`): token and refresh token expired, requiring re-authorization.
  4. `HANDSHAKE_PENDING` (`warn`): credentials present in settings, device authorization pending.
  5. `PROBE_ERROR` (`warn`/`fail`): database or probe script failure, distinctly labeled rather than blamed on Allegro auth.
- **WebUI Verification:** Ensure the Instance Settings UI (`/admin/settings`) and status checks reflect consistent state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `allegro-oauth`: Adds requirement for accurate healthcheck probing and CLI status inspection reflecting real token lifecycle states.

## Impact

- **Scripts:** `scripts/iqoqo-status.sh` (app context initialization, status discrimination).
- **Backend:** `app/utils/allegro.py`, `app/api/system.py` (ensure public health check or admin status reporting consistency).
- **Tests:** Pytest for `get_allegro_token_status` covering all token states; bats test verifying `scripts/iqoqo-status.sh` Allegro inspection output.
