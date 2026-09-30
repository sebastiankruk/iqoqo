# Design Document: Admin API Configuration Consolidation

## Architecture & UI Layout
The `InstanceSettings` component (`frontend/components/admin/instance-settings.tsx`) replaces 10+ disconnected `CardWrapper` instances with 5 logical `API_SERVICE_GROUPS`:

1. **Allegro Integration** (`ALLEGRO_CLIENT_ID`, `ALLEGRO_CLIENT_SECRET`, Authorize Allegro Account button)
2. **Twitch / IGDB Video Games API** (`TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`)
3. **Google Services** (`GOOGLE_BOOKS_API_KEY`, `GEMINI_API_KEY`)
4. **Media & Catalog Databases** (`DISCOGS_USER_TOKEN`, `TMDB_API_KEY`, `BGG_API_TOKEN`, `UPC_DATABASE_ORG_KEY`)
5. **AI & Cover Generation** (`OPENAI_API_KEY`, `LOCAL_SD_URL`)

## Backend API & Credentials Fallback

1. `app/api/admin.py`: Include `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` in `API_KEYS` set.
2. `app/api/auth.py`: `/api/auth/allegro/device-flow` and `/api/auth/allegro/device-token` endpoints check request parameters and automatically resolve masked (`***`) or blank `client_id` / `client_secret` against `InstanceSettings.get_value()` and `Config` / environment defaults.
3. `app/utils/igdb.py`: `get_igdb_token()` falls back to `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` and DB `InstanceSettings`.
