# metadata-refetch Specification

## Purpose
TBD - created by archiving change fix-collection-metadata-display-and-refetch. Update Purpose after archive.
## Requirements
### Requirement: Script detects entities with missing metadata
The system SHALL provide a script that queries the database for manifestations, expressions, and works with specified metadata gaps (missing `format`, `publisher`, `genres`/`categories`, or `cover_url`).

#### Scenario: Detect missing format

- **WHEN** script runs with `--gap format`
- **THEN** it SHALL list all manifestations where `meta->>'format'` IS NULL or empty
- **AND** report the total count per content_type

#### Scenario: Detect missing publisher

- **WHEN** script runs with `--gap publisher`
- **THEN** it SHALL list all manifestations where `publisher` column IS NULL AND `meta->>'publisher'` IS NULL or empty

#### Scenario: Detect missing genres

- **WHEN** script runs with `--gap genres`
- **THEN** it SHALL list all works where both `meta->>'categories'` and `meta->>'genres'` are NULL, empty, or `[]`

#### Scenario: Filter by content type

- **WHEN** script runs with `--content-type movie`
- **THEN** it SHALL only process entities whose Expression `content_type` is `"movie"`

### Requirement: Script tracks refetch attempts to avoid redundant work
The system SHALL maintain a `metadata_refetch_log` table in the `inventory` schema with columns: `entity_type`, `entity_id`, `checked_at`, `iqoqo_version`, `strategy`, `found_fields`, `error`. A unique constraint on `(entity_type, entity_id, strategy)` SHALL allow upsert semantics.

#### Scenario: Skip already-checked entity

- **WHEN** script encounters a manifestation that already has a `metadata_refetch_log` entry for the same strategy with `iqoqo_version` matching the current version
- **AND** the previous check found no metadata
- **THEN** it SHALL skip that entity unless `--force` is passed

#### Scenario: Retry older version check

- **WHEN** script encounters a manifestation with a `metadata_refetch_log` entry where `iqoqo_version` is older than current
- **THEN** it SHALL re-attempt the refetch and update the log

#### Scenario: Log successful refetch

- **WHEN** an external API returns metadata that fills a gap
- **THEN** the script SHALL insert or update a `metadata_refetch_log` row with the current timestamp, version, strategy name, and list of fields found

### Requirement: Script respects per-strategy API rate limits
The system SHALL throttle API requests per external strategy according to a configurable rate-limit table. Strategies and their default limits: TMDB (40 req/s), Discogs (60 req/min), BGG (2 req/s), IGDB (4 req/s), MusicBrainz (1 req/s), Google Books (no limit defined).

#### Scenario: Throttle between requests

- **WHEN** script makes consecutive requests to the same strategy
- **THEN** it SHALL enforce a minimum delay between requests based on the strategy's rate limit

#### Scenario: Rate limit exceeded

- **WHEN** an external API returns HTTP 429 (Too Many Requests)
- **THEN** the script SHALL wait for the `Retry-After` header duration before retrying
- **AND** log a warning

### Requirement: Script updates entity metadata without overwriting existing data
The system SHALL only populate metadata fields that are currently NULL or empty. It SHALL never overwrite non-empty fields with externally-fetched data.

#### Scenario: Skip populated field

- **WHEN** script fetches a `format` value for a manifestation that already has a non-empty `meta->>'format'`
- **THEN** it SHALL NOT overwrite the existing format value

#### Scenario: Fill empty field

- **WHEN** script fetches a `publisher` value for a manifestation where the `publisher` column IS NULL
- **THEN** it SHALL populate the `publisher` column with the fetched value

### Requirement: Dry-run mode reports without making changes
The system SHALL support a `--dry-run` flag that reports what entities would be refetched and what gaps would be filled, without making any API calls or database writes.

#### Scenario: Dry-run output

- **WHEN** script runs with `--dry-run`
- **THEN** it SHALL output a table listing each entity, its content_type, the gap detected, and which strategy would be used
- **AND** it SHALL NOT make any HTTP requests

### Requirement: Makefile integration
The system SHALL provide a `make refetch-metadata` target that invokes the script with default settings. Additional `REFETCH_ARGS` variable SHALL be supported for passing flags.

#### Scenario: Run via Makefile

- **WHEN** user runs `make refetch-metadata`
- **THEN** the script SHALL execute with `--gap all` as default

#### Scenario: Run with custom args

- **WHEN** user runs `REFETCH_ARGS="--dry-run --gap format --content-type movie" make refetch-metadata`
- **THEN** the script SHALL execute with those arguments
