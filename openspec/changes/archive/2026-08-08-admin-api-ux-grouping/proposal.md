# Consolidate Admin API Configuration UX & Add Twitch Credentials

## Why

1. **Fragmented UI**: Admin API settings were split into 10+ standalone cards with high density and poor grouping.
2. **Allegro Auth Scattering**: `ALLEGRO_CLIENT_ID`, `ALLEGRO_CLIENT_SECRET`, and the "Authorize Allegro" button were scattered across 3 separate tiles.
3. **Allegro Auth Failure**: When device flow authorization was triggered from the UI, masked (`***`) values were sent to the backend without fallback resolution to stored database settings or environment variables, causing authentication failures.
4. **Missing Twitch / IGDB Credentials**: There were no UI input fields to configure Twitch Client ID and Client Secret (`TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`) required for IGDB video game artwork lookups.

## What

- **Unified Service Cards**: Group external API settings in `InstanceSettings` into 5 logical service cards:
  - **Allegro Integration** (Client ID, Client Secret, Authorize Account button)
  - **Twitch / IGDB Video Games API** (Twitch Client ID, Twitch Client Secret)
  - **Google Services** (Google Books API Key, Gemini API Key)
  - **Media & Catalog Databases** (Discogs Token, TMDB Key, BGG Token, UPC Database Key)
  - **AI & Cover Generation** (OpenAI Key, Local Stable Diffusion URL)
- **Backend Fallback Resolution**: Update `/api/auth/allegro/device-flow` and `/api/auth/allegro/device-token` to automatically resolve masked (`***`) or omitted credentials against stored DB settings (`InstanceSettings`) and `Config`/env variables.
- **IGDB Token Helper Enhancement**: Update `get_igdb_token()` to support `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` and `InstanceSettings` DB fallback.
