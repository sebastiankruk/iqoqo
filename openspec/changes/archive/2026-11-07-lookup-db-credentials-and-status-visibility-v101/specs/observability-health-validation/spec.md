## ADDED Requirements

### Requirement: Database-Aware Provider and Environment Status Reporting
Both `GET /api/system/status` and `make status` (`scripts/iqoqo-status.sh`) SHALL inspect encrypted `InstanceSettings` in addition to `.env` / process environment variables when reporting the configuration state of external lookup providers (`Allegro`, `Twitch/IGDB`, `BoardGameGeek`, `Discogs`, `TMDB`, `Google Books`, `UPC`) and environment variable completeness, without ever echoing secret values.

#### Scenario: Running make status after migrating secrets to the database
- **WHEN** an operator runs `make migrate-secrets` (which comments out sensitive keys in `.env` and stores them encrypted in `InstanceSettings`) and then runs `make status`
- **THEN** `scripts/iqoqo-status.sh` queries `InstanceSettings` for configured key names, reports DB-backed lookup providers (including BGG, Discogs, TMDB, Google Books, UPC, Allegro, and IGDB) as configured via DB, and counts DB-stored keys as configured in the `Environment Configuration` summary rather than missing or unconfigured

#### Scenario: Querying GET /api/system/status with DB-stored provider keys
- **WHEN** an authenticated client queries `GET /api/system/status` while provider keys (`BGG_API_TOKEN`, `DISCOGS_*`, `TMDB_*`, `GOOGLE_BOOKS_API_KEY`, `UPC_*`) are stored in `InstanceSettings`
- **THEN** the response reports `configured: true` and `"source": "db"` for each DB-configured provider
