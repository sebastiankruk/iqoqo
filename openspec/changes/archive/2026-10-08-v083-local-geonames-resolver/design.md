## Context

`GeoNamesClient` in `app/core/lod_linking_service.py` currently resolves publisher cities exclusively via remote HTTP requests to `https://secure.geonames.org/searchJSON`. As documented in `proposal.md`, remote requests suffer from authentication errors (`value: 10`), account activation delays, network timeouts (5s each), and external rate limits.

This design introduces a local, offline SQLite gazetteer database built from the official GeoNames `cities15000` dataset, enabling instant, credential-free geographic reconciliation while keeping container footprint small.

## Goals / Non-Goals

**Goals:**
- Provide a dedicated offline SQLite gazetteer (`data/geonames_cities.db`) containing ~25,000 populated places with population >= 15,000.
- Update `GeoNamesClient.resolve_location` to implement offline-first resolution: local SQLite lookup first, with graceful fallback to remote API when missing.
- Provide a standalone build script (`scripts/init_geonames_db.py`) to download and build the database file with size and integrity validation.
- Implement case-insensitive matching across `name` and `asciiname`, ordering by population descending to select prominent cities in disambiguation scenarios.
- Keep the uncompressed database file under 15 MB to respect the strict 650 MB container image budget.

**Non-Goals:**
- Indexing non-populated geographic features (mountains, lakes, rivers) from `allCountries.zip` (1.5 GB).
- Introducing heavy GIS/spatial libraries (e.g., `geopy`, `shapely`, `geopandas`, PostGIS).
- Modifying the `catalog.semantic_links` relational schema or FRBR link associations.

## Decisions

### Decision 1: SQLite Storage Format Over In-Memory JSON or PostgreSQL Table
- **Choice**: Store gazetteer in a dedicated SQLite database (`data/geonames_cities.db` or path from `GEONAMES_DB_PATH`).
- **Rationale**:
  - Uses standard library `sqlite3` (zero new pip packages).
  - B-tree indexing allows sub-millisecond lookups with zero heap overhead when idle.
  - Avoids polluting PostgreSQL migrations and backup dumps with static external reference gazetteer data.
- **Alternatives Considered**:
  - *In-memory Python dict/JSON*: Consumes ~25 MB of resident RAM in every Celery worker and Flask process.
  - *PostgreSQL table*: Requires Alembic migrations, slows down database backups, and complicates testing.

### Decision 2: Gazetteer Dataset Selection (`cities15000`)
- **Choice**: GeoNames `cities15000.zip` (3.3 MB compressed, ~10 MB raw TSV, ~12 MB SQLite).
- **Rationale**:
  - Book, music, and film publication locations in library catalogs are almost exclusively major urban and cultural centers (London, Warsaw, New York, Paris, Tokyo, Berlin, etc.).
  - Covers ~25,000 world cities while consuming less than 2% of the container storage budget.
- **Alternatives Considered**:
  - *`cities5000` (5.7 MB zip)*: Extra ~25,000 smaller towns, but doubles SQLite size to ~24 MB. Can be supported as an optional CLI flag in the init script.
  - *`allCountries` (1.5 GB zip)*: Prohibited due to container size budget.

### Decision 3: Database Schema and Disambiguation Strategy
- **Schema**:
  ```sql
  CREATE TABLE cities (
      geoname_id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      asciiname TEXT NOT NULL,
      country_code TEXT NOT NULL,
      lat REAL,
      lng REAL,
      fcode TEXT,
      population INTEGER
  );
  CREATE INDEX idx_cities_name_lower ON cities(LOWER(name));
  CREATE INDEX idx_cities_asciiname_lower ON cities(LOWER(asciiname));
  ```
- **Disambiguation Query**:
  ```sql
  SELECT geoname_id, name, country_code, lat, lng, fcode
  FROM cities
  WHERE LOWER(name) = ? OR LOWER(asciiname) = ?
  ORDER BY population DESC
  LIMIT 1;
  ```
  Ordering by `population DESC` ensures that prominent cities (e.g., London, UK over London, Ontario) are chosen by default when multiple matches exist.

### Decision 4: Resolver Execution Flow in `GeoNamesClient`
1. Check in-memory Redis cache (`lod:geonames:{normalized.lower()}`).
2. Check if local SQLite database exists at `GEONAMES_DB_PATH` (default `data/geonames_cities.db`).
3. If database exists: execute query. If matched, construct canonical result (`https://sws.geonames.org/{geoname_id}/`, coordinates, country) and return.
4. If not found locally (or database file is absent): fall back to remote GeoNames API if username is configured.
5. If remote API fails (HTTP 401, error 10, or timeout): log warning and return `None` (do not cache `None` permanently).

### Decision 5: Docker Container Packaging and Self-Contained Execution
- **Container-Native**: All operations execute strictly inside Docker containers (`worker` running Celery and `web` running Gunicorn). No host daemons, host databases, or external processes are required.
- **Image Bundling & Volume Support**:
  - The database file is placed in `data/geonames_cities.db` (or mounted volume).
  - Can be built into the Docker image via `deploy/Dockerfile` (`RUN python scripts/init_geonames_db.py --dest /usr/src/app/data/geonames_cities.db`) during build, or populated into the existing `shared/` mounted volume (`./shared:/usr/src/app/shared`).
  - At ~12 MB, bundling it into the image adds <2% to the final layer, keeping runtime images strictly within the container size budget.

### Decision 6: Sync Tooling & Status Health Reporting
- **Sync / Re-download Script**: `scripts/init_geonames_db.py` supports `--force` flag to re-download `cities15000.zip` and re-index the database on demand. Exposed as `make init-geonames` / `make geonames-sync`.
- **Health Reporting via `make status`**: `scripts/iqoqo-status.sh` includes a dedicated check under external/semantic services:
  - Verifies presence and row count of `cities` in SQLite database.
  - Outputs `✅ ready (<count> cities)` when populated, or `⚠️ missing or empty (run 'make init-geonames')` when missing or unpopulated.

## Risks / Trade-offs

- **[Risk] Small towns / villages (<15,000 population) missing from local database**
  - *Mitigation*: Fallback to remote GeoNames API remains available if user has working credentials.
- **[Risk] Database file missing in development or minimal environments**
  - *Mitigation*: Resolver checks file existence (`os.path.exists`) before attempting SQLite connection; falls back cleanly without crashing.
- **[Risk] Container image size inflation**
  - *Mitigation*: Database size is capped at ~12 MB, leaving container well below the 650 MB limit.
