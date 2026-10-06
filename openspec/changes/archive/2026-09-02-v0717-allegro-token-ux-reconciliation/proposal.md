## Why

The current Allegro token management has two issues:
1. The "Authorize / Refresh Allegro Token" button is at the bottom of the admin settings form, which is disconnected from the Allegro Client ID / Secret input group, causing poor UX.
2. The system status check (`make status` and `/api/system/status`) reports an expired token even after a refresh because it incorrectly reads a stale local `.allegro_token.json` file instead of checking the active OAuth token cache in Redis / database.

## What Changes

- Reposition the Allegro token refresh CTA next to credential inputs in the frontend.
- Reconcile token freshness check with central auth state in backend utilities.
- Fix the status endpoint to check the Redis/DB token cache.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None.

## Impact

- `frontend/components/admin/instance-settings.tsx`
- `app/utils/allegro.py`
- `app/api/system.py`
- `frontend/__tests__/components/admin/instance-settings-allegro.test.tsx`
