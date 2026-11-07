## 1. Core Credential Resolution & Quote Sanitization

- [ ] 1.1 Fix `ConfigService.get()` in `app/core/config_service.py` so `current_app.config.get(key)` only returns when `is not None` (preventing `None` class attributes on `Config` from shadowing `os.environ` or `default`), and add string credential sanitization that strips whitespace and unwraps accidental outer double/single quotes (`"..."` / `'...'`).
- [ ] 1.2 Ensure `InstanceSettings.get_value()` / `normalise_setting_value()` in `app/db/settings.py` strips accidental outer quotes on sensitive string credentials (`SENSITIVE_SETTING_KEYS` / `is_sensitive_key`) so existing DB rows with literal `'"..."'` decrypt cleanly.

## 2. External Metadata Lookup & AI Provider Wiring

- [ ] 2.1 Update `app/utils/discogs.py` (`fetch_discogs_metadata`, `fetch_discogs_candidates`, `fetch_discogs_by_id`) to resolve `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`, and `DISCOGS_USER_TOKEN` from `ConfigService.get()` / `InstanceSettings` and `os.environ` via a shared `_get_discogs_auth_header()` helper, plus add `get_discogs_status()`.
- [ ] 2.2 Update `app/utils/tmdb.py` (`fetch_video_metadata`) and `app/utils/upc.py` (`fetch_upcdatabase_org`, `fetch_upc_metadata`) to resolve `TMDB_API_KEY`, `TMDB_API_READ_ACCESS_TOKEN`, `UPC_DATABASE_ORG_KEY`, and `UPC_ITEM_DB_KEY` from `ConfigService.get()` / `InstanceSettings` and `os.environ`.
- [ ] 2.3 Fix `app/utils/igdb.py` (`fetch_game_metadata`) to resolve `client_id` across `IGDB_CLIENT_ID` and `TWITCH_CLIENT_ID` from both `os.getenv` and `InstanceSettings`, and fix `app/utils/bgg.py` (`fetch_bgg_metadata`) so the missing-token warning checks the resolved `headers` from `get_bgg_headers()` rather than only `os.getenv("BGG_API_TOKEN")`.
- [ ] 2.4 Update `app/utils/vision.py` (`_extract_via_gemini`), `app/utils/llm_covers.py` (`generate_cover_cloud`, `generate_cover_gemini`, `generate_cover_local`, `fetch_llm_cover`), and `scripts/allegro_auth.py` to resolve `GEMINI_API_KEY`, `OPENAI_API_KEY`, `LOCAL_SD_URL`, `ALLEGRO_CLIENT_ID`, and `ALLEGRO_CLIENT_SECRET` from `ConfigService.get()` / `InstanceSettings` and `os.environ`.

## 3. System Status API & `make status` (`scripts/iqoqo-status.sh`) Visibility

- [ ] 3.1 Enhance `GET /api/system/status` in `app/api/system.py` to inspect `InstanceSettings` alongside `os.getenv` for `BGG_API_TOKEN` and include structured status & source (`db` | `env` | `missing`) for `discogs`, `tmdb`, `google_books`, and `upc` without exposing secret values.
- [ ] 3.2 Enhance `scripts/iqoqo-status.sh` (`make status`) to query non-empty key names from `InstanceSettings` in a single batch probe, report DB-backed credentials in `BoardGameGeek API` and a `Metadata Lookup Providers` section (`Discogs`, `TMDB`, `Google Books`, `UPC`), and count DB-stored keys as configured (`in DB`) in the `Environment Configuration` summary.

## 4. Test Suite Updates & Verification

- [ ] 4.1 Add backend unit tests in `tests/` verifying DB-only credential resolution (`os.environ` cleared, credentials stored in `InstanceSettings`, including literal-quote sanitization) for `discogs`, `tmdb`, `upc`, `igdb`, `bgg`, `vision`, `llm_covers`, and `ConfigService`.
- [ ] 4.2 Add backend API tests for `GET /api/system/status` and BATS tests in `tests/bash/` for `scripts/iqoqo-status.sh` verifying that DB-migrated credentials are reported as configured (`db`) rather than missing or unconfigured.
