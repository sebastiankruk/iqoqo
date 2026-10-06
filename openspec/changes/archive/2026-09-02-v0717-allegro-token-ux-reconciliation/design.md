## Context
The Allegro integration currently relies on a local `.allegro_token.json` file for token storage. This causes inconsistencies where the web UI might refresh the token and store it in Redis or a database (or a different location) while the system script (`make status`) and backend utility functions still check the old file, incorrectly reporting it as expired.

## Goals / Non-Goals
**Goals:**
- Move Allegro token storage to a central auth state (Redis / DB cache) accessible by both the backend API and background scripts.
- Update `app/utils/allegro.py` to check token freshness against this central cache.
- Expose a new `/api/system/status` endpoint in `app/api/system.py` to report on token status.
- Update the frontend instance settings UI to position the Allegro token refresh button next to the credential inputs for better UX.
- Ensure the `scripts/iqoqo-status.sh` script utilizes the new centralized check or endpoint rather than the local JSON file.

**Non-Goals:**
- Changes to the underlying Allegro OAuth flow mechanics (other than where it saves/checks the token).
- Full refactor of other admin settings.

## Decisions
1. **Token Storage**: We will use Redis for the token cache, similar to other caching mechanisms in the app, or the `InstanceSettings` model if a database is more persistent. Since `app/utils/allegro.py` needs to check it, we will use Redis via `app.core.cache` or the `DataManager`/`InstanceSettings` database mechanism. Given tokens are ephemeral, Redis is appropriate, but the token flow might need persistence. We will check how `app/api/auth.py` saves it. If `app/api/auth.py` saves to Redis or DB, we will align with that.
2. **System Status Check**: We will add a new endpoint `/api/system/status` that returns system statuses including Allegro token freshness. The `make status` script will query this endpoint if available, or invoke a Python command that queries the Redis/DB directly.
3. **UI Positioning**: The Allegro token refresh button will be relocated from the bottom of the form into the Allegro section inside `InstanceSettingsForm`.

## Risks / Trade-offs
- **Risk**: `make status` might be run when the API is down.
  - *Mitigation*: The `make status` script will fall back to querying the Redis/DB directly via a Python snippet importing the updated `app/utils/allegro.py` functions, ensuring it works even if the API is offline.
