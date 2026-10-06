## Why

To improve security and user experience, we need to trigger the existing Allegro OAuth Device Code flow via the UI to eliminate SSH access requirements. Additionally, we must verify and test the Twitch API integration to ensure stable functionality for streaming-related features.

## What Changes

- Add a UI flow for Allegro OAuth in `frontend/components/admin/instance-settings.tsx` to provide API keys and open the authorization URL.
- Update backend auth handling in `app/api/auth.py` and `app/utils/allegro.py` to expose endpoints that start the Allegro Device Code flow and eliminate the need for manual SSH commands.
- Add and execute verification tests for the Twitch API integration to ensure it works correctly end-to-end.

## Capabilities

### New Capabilities

- `allegro-oauth`: UI-driven initiation of the Allegro OAuth 2.0 Device Code flow, replacing manual token entry via SSH.
- `twitch-integration`: Verified connection and functional tests for interacting with the Twitch API.

### Modified Capabilities

## Impact

- `frontend/components/admin/instance-settings.tsx`
- `app/api/auth.py`
- `app/utils/allegro.py`
- Test suites for Twitch integration.
