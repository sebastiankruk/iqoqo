## Context

In earlier releases, iqoqo introduced `InstanceSettings` (`config.instance_settings`) with Fernet symmetric encryption at rest (`app/db/settings.py`) and `scripts/migrate_env_secrets_to_db.py` (`make migrate-secrets`) so operators could migrate sensitive API keys out of plaintext `.env` files into the encrypted database registry. Once migrated, `make migrate-secrets` comments out those keys in `.env`.

However, an audit of all metadata lookup and AI cover/vision utilities revealed a split brain:
1. **Unmigrated Call Sites**:
   - `app/utils/discogs.py`: `fetch_discogs_metadata`, `fetch_discogs_candidates`, and `fetch_discogs_by_id` read `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`, and `DISCOGS_USER_TOKEN` strictly via `os.environ.get(...)`. When credentials live in `InstanceSettings`, Discogs lookups immediately abort with `No Discogs credentials found. Skipping Discogs lookup.`
   - `app/utils/tmdb.py`: `fetch_video_metadata` reads `TMDB_API_KEY` and `TMDB_API_READ_ACCESS_TOKEN` strictly via `os.environ.get(...)`.
   - `app/utils/upc.py`: `fetch_upcdatabase_org` and `fetch_upc_metadata` read `UPC_DATABASE_ORG_KEY` and `UPC_ITEM_DB_KEY` strictly via `os.getenv(...)`.
   - `app/utils/igdb.py`: While `get_igdb_token()` and `get_igdb_token_status()` check both `os.getenv` and `InstanceSettings`, `fetch_game_metadata()` line 248 reads `client_id = os.getenv("IGDB_CLIENT_ID")`, causing actual game metadata queries to fail if `IGDB_CLIENT_ID` is only in `InstanceSettings` or set as `TWITCH_CLIENT_ID`.
   - `app/utils/bgg.py`: While `get_bgg_headers()` checks `InstanceSettings.get_value("BGG_API_TOKEN")`, `fetch_bgg_metadata()` line 200 checks `token = os.getenv("BGG_API_TOKEN")` and logs a false warning (`BGG_API_TOKEN not found in environment...`) on every lookup when the token is stored in the database.
   - `app/utils/vision.py` & `app/utils/llm_covers.py`: Read `GEMINI_API_KEY`, `OPENAI_API_KEY`, and `LOCAL_SD_URL` directly from `os.environ.get(...)`, bypassing `InstanceSettings`.
   - `scripts/allegro_auth.py`: Reads `ALLEGRO_CLIENT_ID` and `ALLEGRO_CLIENT_SECRET` only from `os.getenv(...)`.
2. **Literal Quote Artifacts in Encrypted DB Values**:
   - Inspecting the live database revealed `DISCOGS_CONSUMER_KEY -> '"example-consumer-key"'` (a string containing literal surrounding double quotes). If a value was stored with surrounding quotes, interpolating `f"Discogs key={consumer_key}, secret={consumer_secret}"` sends invalid quote characters in the HTTP `Authorization` header.
3. **Blind Spots in `make status` (`scripts/iqoqo-status.sh`) and `/api/system/status`**:
   - `app/api/system.py` (`GET /api/system/status`) checks `bgg_configured = bool(os.getenv("BGG_API_TOKEN"))` without checking `InstanceSettings`, and does not report configuration status for `discogs`, `tmdb`, `google_books`, or `upc`.
   - `scripts/iqoqo-status.sh` checks `bgg_token=$(load_env "BGG_API_TOKEN")` only from `.env` (reporting `anonymous / optional (BGG_API_TOKEN not configured)` even when set in DB), has no visibility into Discogs / TMDB / Google Books / UPC credentials, and in the `Environment Configuration` section counts DB-migrated keys (which are commented out in `.env`) as `Optional (not configured)` or `Missing`.

## Goals / Non-Goals

**Goals:**
- Route all external lookup and AI credential reads through a single, consistent resolution helper (`ConfigService.get_credential(key)` / `InstanceSettings` + `os.environ`) that works both inside and outside a Flask request context and strips accidental surrounding quotes/whitespace.
- Ensure every lookup utility (`discogs`, `tmdb`, `upc`, `igdb`, `bgg`, `isbn`, `allegro`) and AI utility (`vision`, `llm_covers`) seamlessly resolves credentials stored in `InstanceSettings` when `.env` variables are absent.
- Upgrade `/api/system/status` and `scripts/iqoqo-status.sh` (`make status`) so operators see accurate, source-attributed (`db` vs `env`) health and configuration status for all lookup services and environment variables.
- Enforce comprehensive unit, API, and BATS script test coverage for DB-only credential resolution and status reporting.

**Non-Goals:**
- Changing the Fernet encryption format or migrating `SECRET_KEY` / `DATABASE_URL` / `REDIS_URL` / `JWT_SECRET_KEY` into the database (these remain on `CONFIG_KEY_BLOCKLIST`).
- Modifying upstream provider rate limits (such as MusicBrainz public API 503 throttling).

## Decisions

### 1. Unified Credential Resolution & Quote Sanitization in `ConfigService`
- **Decision**: Enhance `ConfigService.get()` (and/or add a dedicated `get_clean_str(key)` / sanitization step for string credentials) and `InstanceSettings.get_value()` so that:
  1. It checks `os.environ` and `InstanceSettings.get_value(key)` safely even if called from a Celery task or CLI script where `current_app` may or may not be bound (handling `RuntimeError` gracefully).
  2. Note on priority: In `bgg.py`, `allegro.py`, and `igdb.py`, tests frequently patch `os.environ` (via `monkeypatch.setenv`) or mock `InstanceSettings.get_value`. Specifically, if `os.environ.get(key)` is set (and non-empty) OR `InstanceSettings.get_value(key)` is set (and non-empty), the credential is resolved. Wait: what should the precedence be between `InstanceSettings` and `os.environ`?
     - In `ConfigService.get(key)`: DB override (`InstanceSettings`) is checked first (when `current_app` is active), then `current_app.config`, then `os.environ`.
     - However, in unit tests that do not set up DB rows (or where an empty/default DB is active) and use `monkeypatch.setenv("DISCOGS_USER_TOKEN", "test-token")`, `InstanceSettings.get_value` returns `None`, so it naturally falls through to `os.environ.get(key)`!
     - What if `current_app.config` initialized `DISCOGS_CONSUMER_KEY = None` at import time in `app/config.py`? Look at `ConfigService.get()` lines 72-73:
       ```python
       if current_app and key in current_app.config:
           return current_app.config[key]
       ```
       **CRITICAL BUG FOUND IN `ConfigService.get()`!**
       In `app/config.py`, `DISCOGS_CONSUMER_KEY = os.environ.get("DISCOGS_CONSUMER_KEY")` is evaluated at **class definition time** as `None`! Because `"DISCOGS_CONSUMER_KEY" in current_app.config` is `True` (with value `None`), `ConfigService.get("DISCOGS_CONSUMER_KEY")` returns `None` at line 73 and **NEVER REACHES** `os.environ.get(key, default)` at line 77 if `monkeypatch.setenv` was called after `Config` was imported!
       Fixing `ConfigService.get()` so line 72 checks `if current_app and current_app.config.get(key) is not None:` ensures that `None` values on `Config` never shadow `os.environ` or `default`!
  3. **Quote Sanitization**: When a string credential is retrieved from `InstanceSettings` or `os.environ`, strip leading/trailing whitespace and unwrap matching outer double or single quotes (`"..."` or `'...'`) so values like `'"example-consumer-key"'` become `'example-consumer-key'`.
- **Alternatives Considered**: Updating only `discogs.py` with ad-hoc `InstanceSettings` imports. Rejected because `tmdb.py`, `upc.py`, `igdb.py`, `bgg.py`, `vision.py`, and `llm_covers.py` suffer from the exact same defect.

### 2. Fixing All Lookup & AI Modules
- **`app/utils/discogs.py`**: Extract a helper `_get_discogs_auth_header() -> str | None` used by `fetch_discogs_metadata`, `fetch_discogs_candidates`, and `fetch_discogs_by_id`. It resolves `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`, and `DISCOGS_USER_TOKEN` via `ConfigService.get()`, strips quotes, and returns the `Authorization` header string (`Discogs key=..., secret=...` or `Discogs token=...`) or `None`. Also add `get_discogs_status() -> dict[str, Any]` for status reporting.
- **`app/utils/tmdb.py`**: Resolve `TMDB_API_KEY` and `TMDB_API_READ_ACCESS_TOKEN` via `ConfigService.get()`.
- **`app/utils/upc.py`**: Resolve `UPC_DATABASE_ORG_KEY` and `UPC_ITEM_DB_KEY` via `ConfigService.get()`.
- **`app/utils/igdb.py`**: In `fetch_game_metadata()`, resolve `client_id` using the same fallback chain as `get_igdb_token()` (`IGDB_CLIENT_ID` -> `TWITCH_CLIENT_ID` across env and `InstanceSettings`).
- **`app/utils/bgg.py`**: In `fetch_bgg_metadata()`, check whether `Authorization` is in `headers` (returned by `get_bgg_headers()`, which already queries both env and `InstanceSettings`) before logging the missing-token warning.
- **`app/utils/vision.py` & `app/utils/llm_covers.py`**: Use `ConfigService.get()` for `GEMINI_API_KEY`, `OPENAI_API_KEY`, and `LOCAL_SD_URL`.

### 3. Enhancing `/api/system/status` and `make status` (`scripts/iqoqo-status.sh`)
- **`GET /api/system/status` (`app/api/system.py`)**:
  - Resolve `BGG_API_TOKEN` from both `os.getenv` and `InstanceSettings`, including `"source": "db" | "env" | "missing"`.
  - Add provider status blocks for `discogs`, `tmdb`, `google_books`, and `upc` indicating `configured: bool`, `auth_mode` (where applicable, e.g. `consumer_oauth` vs `user_token` for Discogs, `bearer` vs `api_key` for TMDB), and `source` (`db` | `env` | `missing`), without ever exposing secret values.
- **`scripts/iqoqo-status.sh` (`make status`)**:
  - Add a lightweight single-pass DB key presence helper (`load_db_configured_keys`) that queries the running `web` container (in `prod`/`preview`) or local `.venv/bin/python` (in `dev`) for the list of non-empty keys currently stored in `InstanceSettings`.
  - Use this DB key set in:
    1. **BoardGameGeek API**: Report `configured (DB: InstanceSettings)` or `configured (.env)` when `BGG_API_TOKEN` is present in DB or `.env`.
    2. **Metadata Lookup Providers**: Report status for **Discogs API** (`DISCOGS_CONSUMER_KEY`+`SECRET` or `DISCOGS_USER_TOKEN`), **TMDB API** (`TMDB_API_KEY` or `TMDB_API_READ_ACCESS_TOKEN`), **Google Books API** (`GOOGLE_BOOKS_API_KEY`), and **UPC Databases** (`UPC_ITEM_DB_KEY` / `UPC_DATABASE_ORG_KEY`), showing whether each is configured via `.env` or `InstanceSettings (DB)`.
    3. **Environment Configuration**: When checking `expected_keys` from `.env.example`, if a key is empty/commented in `.env` but present in `InstanceSettings (DB)`, count it as configured (`in DB`) rather than flagging it as `Missing` or `Optional (not configured)`. Report both `.env` active count and `DB (InstanceSettings)` active count clearly.

## Risks / Trade-offs

- **[Risk] Unit tests mocking `os.environ` without a Flask app context or with an initialized Flask app where `Config.KEY = None`** → **Mitigation**: Fix `ConfigService.get()` so `current_app.config.get(key)` is only returned when `is not None`, and catch `RuntimeError` / `SQLAlchemyError` when outside an app context or when DB tables are uninitialized so `os.environ` fallback always works deterministically.
- **[Risk] `make status` latency if spawning multiple `docker exec` Python processes per key** → **Mitigation**: Query all configured `InstanceSettings` keys in a single `python3 -c` invocation and cache the key names in a bash associative array/list in `scripts/iqoqo-status.sh`. Never print secret values to stdout.
