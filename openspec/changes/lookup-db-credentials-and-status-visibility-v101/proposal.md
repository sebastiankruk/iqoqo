## Why

After migrating sensitive API credentials and lookup keys from `.env` into encrypted `InstanceSettings` database rows (`make migrate-secrets`), multiple external lookup services (`discogs.py`, `tmdb.py`, `upc.py`, `igdb.py`'s `fetch_game_metadata`, `vision.py`, `llm_covers.py`, and `bgg.py`'s warning probe) continued reading exclusively from `os.environ` / `os.getenv`, causing barcode scans and metadata lookups to silently fail with "credentials not found" warnings even when valid credentials exist in the database. Simultaneously, `make status` (`scripts/iqoqo-status.sh`) and `GET /api/system/status` only inspect `.env` for several providers (such as BGG, Discogs, TMDB, UPC, and Google Books) and omit DB-stored settings from both provider health sections and the `Environment Configuration` summary, misleading operators into believing DB-migrated credentials are unconfigured or missing.

## What Changes

- **Unified DB + Env Credential Resolution Across All Lookup & AI Providers**:
  - Update `app/utils/discogs.py` (`fetch_discogs_metadata`, `fetch_discogs_candidates`, `fetch_discogs_by_id`) to resolve `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`, and `DISCOGS_USER_TOKEN` via `ConfigService.get()` / `InstanceSettings.get_value()` with environment fallback, and strip any accidental surrounding double/single quotes (`"..."`) persisted during `.env` migration.
  - Update `app/utils/tmdb.py` (`fetch_video_metadata`) to resolve `TMDB_API_KEY` and `TMDB_API_READ_ACCESS_TOKEN` from `ConfigService.get()` / `InstanceSettings` and environment.
  - Update `app/utils/upc.py` (`fetch_upcdatabase_org`, `fetch_upc_metadata`) to resolve `UPC_DATABASE_ORG_KEY` and `UPC_ITEM_DB_KEY` from `ConfigService.get()` / `InstanceSettings` and environment.
  - Fix `app/utils/igdb.py` (`fetch_game_metadata`) so `Client-ID` resolves `IGDB_CLIENT_ID` / `TWITCH_CLIENT_ID` from both environment and `InstanceSettings` (matching `get_igdb_token()`), rather than failing when `os.getenv("IGDB_CLIENT_ID")` is unset.
  - Fix `app/utils/bgg.py` (`fetch_bgg_metadata`) so the `BGG_API_TOKEN` presence check uses the resolved token from `get_bgg_headers()` (which checks `InstanceSettings`) instead of logging a false-positive warning when `os.getenv("BGG_API_TOKEN")` is empty.
  - Update `app/utils/vision.py` (`_extract_via_gemini`) and `app/utils/llm_covers.py` (`generate_cover_cloud`, `generate_cover_gemini`, `generate_cover_local`, `fetch_llm_cover`) to resolve `GEMINI_API_KEY`, `OPENAI_API_KEY`, and `LOCAL_SD_URL` from `ConfigService.get()` / `InstanceSettings` and environment.
  - Update `scripts/allegro_auth.py` to fall back to `InstanceSettings` when `ALLEGRO_CLIENT_ID` / `ALLEGRO_CLIENT_SECRET` are stored in the database.
- **Database-Aware Provider & Environment Diagnostics in `/api/system/status` and `make status`**:
  - Enhance `GET /api/system/status` (`app/api/system.py`) to check `InstanceSettings` in addition to `os.getenv` for `BGG_API_TOKEN` and report structured configuration status (including credential source `env` vs `db`) across lookup providers (`allegro`, `igdb`, `bgg`, `discogs`, `tmdb`, `google_books`, `upc`).
  - Enhance `scripts/iqoqo-status.sh` (`make status`) to query `InstanceSettings` (via the running `web` container or local Python app context) for DB-migrated keys so:
    1. Provider health sections (`Allegro API`, `Twitch / IGDB API`, `BoardGameGeek API`, and lookup provider readiness for `Discogs`, `TMDB`, `Google Books`, `UPC`) accurately report `configured (DB)` or `configured (.env)` instead of `not configured` when `.env` keys are commented out after `make migrate-secrets`.
    2. The `Environment Configuration` audit distinguishes keys configured in `.env`, keys migrated to encrypted `InstanceSettings` (`DB`), and genuinely unconfigured keys.
- **Comprehensive Test Suite Updates**:
  - Add unit and integration tests covering DB-backed credential resolution (`InstanceSettings` with `os.environ` cleared) for `discogs`, `tmdb`, `upc`, `igdb`, `bgg`, `vision`, and `llm_covers`, including quote-sanitization edge cases.
  - Add API and BATS/script tests verifying `/api/system/status` and `scripts/iqoqo-status.sh` accurately report DB-backed credentials.

## Capabilities

### New Capabilities
- `lookup-db-credential-resolution`: Unified resolution of external metadata lookup and AI provider credentials from encrypted `InstanceSettings` (DB) and environment variables, with quote sanitization and full provider status reporting in `/api/system/status` and `make status`.

### Modified Capabilities
- `ingestion-and-integrations`: External metadata lookup providers (Discogs, TMDB, UPCitemdb, upcdatabase.org, IGDB/Twitch, BGG, Google Books) MUST resolve API credentials from encrypted `InstanceSettings` when not present in process environment variables.
- `observability-health-validation`: `make status` (`scripts/iqoqo-status.sh`) and `/api/system/status` MUST inspect encrypted `InstanceSettings` in addition to `.env` when reporting external integration health and environment configuration completeness.

## Impact

- **Backend Lookup & AI Utilities**: `app/utils/discogs.py`, `app/utils/tmdb.py`, `app/utils/upc.py`, `app/utils/igdb.py`, `app/utils/bgg.py`, `app/utils/vision.py`, `app/utils/llm_covers.py`, `app/core/config_service.py`.
- **System Status & CLI Scripts**: `app/api/system.py`, `scripts/iqoqo-status.sh`, `scripts/allegro_auth.py`.
- **Release Plan**: Registered as `C101b` (`lookup-db-credentials-and-status-visibility-v101`) under milestone `v1.0.1` in `.context/notes/plan/1.0.x-release-plan.md`.
- **Test Suites**: `tests/test_discogs.py` (or lookup unit tests), `tests/test_tmdb.py`, `tests/test_upc.py`, `tests/test_igdb.py`, `tests/test_bgg.py`, `tests/test_system_status.py`, `tests/bash/iqoqo_status.bats`.
