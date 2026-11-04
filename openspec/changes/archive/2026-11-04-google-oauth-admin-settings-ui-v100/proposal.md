## Why

Google OAuth credentials (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`) were migrated from `.env` to the encrypted `InstanceSettings` database table in the backend, but the frontend Admin Settings UI (`/admin/settings?tab=apikeys`) omitted the input fields for these keys. Consequently, instance administrators cannot view, configure, or update Google OAuth credentials from the web interface, and cloned environments without matching `.env` secrets silently disable Google login.

## What Changes

- Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` inputs to the Google Services group in `frontend/components/admin/instance-settings.tsx`.
- Enable secret masking and toggle-reveal functionality for `GOOGLE_CLIENT_SECRET` and `GOOGLE_CLIENT_ID` in the admin settings UI.
- Ensure the settings card persists both keys to the backend `PUT /api/admin/settings` endpoint and re-evaluates OAuth readiness.
- Add frontend unit tests in `frontend/__tests__/components/admin/instance-settings.test.tsx` verifying Google OAuth fields render, reveal, and save properly.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `admin-api`: Add requirement for Google OAuth client credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) in the frontend external API settings UI.

## Impact

- Affected frontend components: `frontend/components/admin/instance-settings.tsx`.
- Affected test suites: `frontend/__tests__/components/admin/instance-settings.test.tsx`.
- No database schema migrations required (backend `InstanceSettings` and `API_KEYS` in `app/api/admin.py` already support these keys).
