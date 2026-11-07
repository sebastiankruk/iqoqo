## ADDED Requirements

### Requirement: Database-Backed Credential Fallback Across External Metadata Providers
All external metadata lookup adapters (`app/utils/discogs.py`, `app/utils/tmdb.py`, `app/utils/upc.py`, `app/utils/igdb.py`, `app/utils/bgg.py`, `app/utils/isbn.py`, `app/utils/allegro.py`) MUST resolve their required API keys, consumer secrets, and bearer tokens from encrypted `InstanceSettings` whenever those credentials are not set in process environment variables.

#### Scenario: Barcode scan for music release with DB-migrated Discogs credentials
- **WHEN** an operator has migrated Discogs credentials from `.env` to `InstanceSettings` using `make migrate-secrets` and a user scans an audio barcode
- **THEN** `AudioLookupStrategy` and `BookLookupStrategy` / `DefaultFallbackStrategy` execute the Discogs API lookup using the decrypted database credentials

#### Scenario: Video game metadata lookup with DB-migrated IGDB or Twitch client ID
- **WHEN** `IGDB_CLIENT_ID` or `TWITCH_CLIENT_ID` is stored only in `InstanceSettings`
- **THEN** `fetch_game_metadata` populates the `Client-ID` request header from `InstanceSettings` and completes the IGDB API request
