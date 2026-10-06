## 1. Backend Utility Refactor

- [x] 1.1 In `app/utils/allegro.py`, update token reading and writing functions to use the central cache (e.g., `redis` / `InstanceSettings`) instead of `_TOKEN_FILE`. Verify that unit tests for `allegro.py` pass and the file logic correctly writes to the cache.
- [x] 1.2 In `app/api/system.py`, create the `/api/system/status` endpoint to report Allegro token freshness by checking the new centralized token storage. Verify the endpoint returns `{"success": True, "data": {"allegro_token_active": True/False, ...}}` when invoked.

## 2. Frontend UI Update

- [x] 2.1 In `frontend/components/admin/instance-settings.tsx`, relocate the Allegro token refresh CTA next to the Allegro client ID/secret credential inputs. Verify with Vitest that the button is inside the Allegro credential group.

## 3. Scripts Update

- [x] 3.1 In `scripts/iqoqo-status.sh`, update the Allegro API token check to inspect the new token cache logic (either by hitting the `/api/system/status` endpoint or using a Python script against Redis/DB) instead of `.allegro_token.json`. Verify by running `make status` and checking the output correctly reflects the token state.
