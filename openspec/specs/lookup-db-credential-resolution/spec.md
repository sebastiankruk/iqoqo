# lookup-db-credential-resolution Specification

## Purpose
Provides unified credential resolution and sanitization for external lookup and AI services across database InstanceSettings and process environment.

## Requirements

### Requirement: Unified Database and Environment Credential Resolution for Lookup and AI Providers
The system SHALL resolve API credentials for all external metadata lookup services (`discogs`, `tmdb`, `upc`, `igdb`, `bgg`, `isbn`, `allegro`) and AI cover/vision services (`vision`, `llm_covers`) from encrypted `InstanceSettings` database records and process environment variables via `ConfigService`, and SHALL strip surrounding whitespace and accidental literal double or single quotes (`"..."` or `'...'`) from retrieved string credentials.

#### Scenario: Resolving Discogs credentials stored only in InstanceSettings

- **WHEN** `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`, or `DISCOGS_USER_TOKEN` are absent from `os.environ` but stored in `InstanceSettings`
- **THEN** `fetch_discogs_metadata`, `fetch_discogs_candidates`, and `fetch_discogs_by_id` authenticate with Discogs using the decrypted database credentials instead of skipping the lookup

#### Scenario: Sanitizing literal surrounding quotes in stored credentials

- **WHEN** a credential value in `InstanceSettings` or `os.environ` contains accidental surrounding quotes (e.g., `'"example-consumer-key"'`)
- **THEN** the credential resolver strips the outer quotes so the outbound HTTP `Authorization` header or query parameter contains the clean token string (`example-consumer-key`)

#### Scenario: Resolving TMDB, UPC, IGDB, Vision, and LLM Cover credentials from InstanceSettings

- **WHEN** `TMDB_API_KEY`, `TMDB_API_READ_ACCESS_TOKEN`, `UPC_DATABASE_ORG_KEY`, `UPC_ITEM_DB_KEY`, `IGDB_CLIENT_ID`, `TWITCH_CLIENT_ID`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `LOCAL_SD_URL` are stored in `InstanceSettings` and unset in `os.environ`
- **THEN** the respective lookup and generation functions (`fetch_video_metadata`, `fetch_upcdatabase_org`, `fetch_upc_metadata`, `fetch_game_metadata`, `_extract_via_gemini`, `generate_cover_cloud`, `generate_cover_gemini`, `generate_cover_local`, `fetch_llm_cover`) use the decrypted `InstanceSettings` values

#### Scenario: Suppressing false-positive BGG missing token warning when token is in InstanceSettings

- **WHEN** `BGG_API_TOKEN` is unset in `os.environ` but configured in `InstanceSettings`
- **THEN** `fetch_bgg_metadata` attaches the `Bearer` header without logging a warning that `BGG_API_TOKEN` was not found in the environment

#### Scenario: Avoiding None values in Flask app.config shadowing environment variables

- **WHEN** `app/config.py` defines a credential attribute whose initial `os.environ.get(...)` value was `None` at import time, and a caller or test later sets that variable in `os.environ`
- **THEN** `ConfigService.get()` ignores the `None` attribute on `current_app.config` and falls through to return the non-empty value from `os.environ`
