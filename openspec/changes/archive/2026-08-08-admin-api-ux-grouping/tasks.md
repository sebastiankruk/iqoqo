# Tasks: Admin API Configuration UX Grouping & Twitch Support

- [x] Add `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` to `API_KEYS` in `app/api/admin.py` <!-- id: 0 -->
- [x] Add database/env fallback for masked/missing credentials in `/api/auth/allegro/device-flow` and `/api/auth/allegro/device-token` in `app/api/auth.py` <!-- id: 1 -->
- [x] Update `get_allegro_token()` in `app/utils/allegro.py` to support `InstanceSettings` DB fallback <!-- id: 2 -->
- [x] Update `get_igdb_token()` in `app/utils/igdb.py` to support `TWITCH_CLIENT_ID`/`TWITCH_CLIENT_SECRET` and `InstanceSettings` DB fallback <!-- id: 3 -->
- [x] Redesign `frontend/components/admin/instance-settings.tsx` to group API settings into unified service cards (Allegro, Twitch/IGDB, Google, Media Databases, AI/Cover Generation) <!-- id: 4 -->
- [x] Verify frontend build (`npm run build`) and Python formatting (`make format-python`) <!-- id: 5 -->
