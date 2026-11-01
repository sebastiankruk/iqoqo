## Context

In iQoQo, external API keys and secrets were previously read purely from `.env`. In recent releases, credentials were consolidated into the encrypted `instance_settings` database table to support runtime updates via the admin dashboard without server restarts. The backend `app/api/admin.py` includes `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `API_KEYS`, but `frontend/components/admin/instance-settings.tsx` defines static `API_SERVICE_GROUPS` configuration that omitted these two items from the Google group.

## Goals / Non-Goals

**Goals:**
- Expose `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `frontend/components/admin/instance-settings.tsx` within the Google Services group.
- Leverage existing secret masking (`_mask_api_key`), toggle-reveal, source badge (`DB`/`ENV`/`MISSING`), and save handlers already present in `InstanceSettings`.
- Provide automated unit test coverage in Vitest verifying rendering, masking, and update requests.

**Non-Goals:**
- Modifying backend authentication logic (`app/api/auth.py`) or database models (`app/db/settings.py`) — both already support these settings.
- Automatically syncing Google Cloud Console redirect URIs — administrator still must configure authorized redirect URIs in Google Cloud Console.

## Decisions

### Decision 1: Place Google OAuth settings inside the existing Google Services group
- **Rationale**: The Google Services group already houses `GOOGLE_BOOKS_API_KEY` and `GEMINI_API_KEY`. Adding `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` directly keeps Google configurations cohesive and avoids introducing a separate redundant card.
- **Alternative considered**: Creating a separate "OAuth Providers" card. Rejected because current API integrations are grouped by service/provider (Allegro, Twitch/IGDB, Google, etc.).

### Decision 2: Set field types to `api` (masked/secret)
- `GOOGLE_CLIENT_SECRET` is marked `type: "api"`, which triggers masking (`***...`) and reveals on demand via `/api/admin/settings/reveal`.
- `GOOGLE_CLIENT_ID` is marked `type: "api"`, which protects client ID while allowing administrators to view and copy the configured value.

## Risks / Trade-offs

- **[Risk] Decryption failure on cloned databases**: If a database is cloned from an instance with a different `SECRET_KEY`, values in DB cannot be decrypted and will display as empty/unset.
  - *Mitigation*: The UI displays the `MISSING` or `DB` badge appropriately, and typing a new value into the input field will encrypt it using the current environment's `SECRET_KEY` via `PUT /api/admin/settings`.
