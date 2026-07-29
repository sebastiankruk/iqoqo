# relational-metadata-normalization Specification

## Purpose
TBD - created by archiving change release-0-7-13. Update Purpose after archive.
## Requirements
### Requirement: Core bibliographic properties live in relational columns

The system SHALL store core bibliographic properties of `Work`, `Expression`, `Manifestation`, and `Item` entities in dedicated, typed relational columns rather than only inside the loose `meta` JSON blob. Core properties are those queried, filtered, or sorted across media types (including, at minimum, manifestation physical format, publisher, release date, and standard identifiers such as EAN/ISBN).

#### Scenario: Manifestation format is queryable relationally

- **WHEN** a query filters or sorts manifestations by physical format
- **THEN** the system SHALL resolve the value from a dedicated relational column on the `manifestations` table, not by extracting `meta['format']` at query time

#### Scenario: Per-media long-tail keys remain in meta

- **WHEN** a per-media, provider-specific, or rarely-queried property (e.g. `track_list`, `matrix_number`, `min_players`) is stored
- **THEN** it SHALL remain in the `meta` JSONB column governed by the documented `*_META_KEYS` constants and SHALL NOT be promoted to a relational column in this release

### Requirement: Reversible batched ETL migration backfills normalized columns

The system SHALL provide a single Alembic migration revision that creates the new relational columns and indexes and backfills them from existing `meta` JSON data using server-side batched updates. The migration SHALL be reversible (downgrade drops the new columns without touching `meta`) and SHALL leave `meta` intact as a fallback read source.

#### Scenario: Upgrade backfills existing rows

- **WHEN** the migration upgrade runs against a database containing rows with core properties only in `meta`
- **THEN** every such row SHALL have its core properties copied into the new relational columns with zero data loss

#### Scenario: Downgrade preserves meta data

- **WHEN** the migration downgrade runs after a successful upgrade
- **THEN** the new relational columns SHALL be dropped and all original `meta` JSON content SHALL remain unchanged

### Requirement: Column-first reads with meta fallback during transition

For the duration of this release, the service layer (`frbr_service.py`, `data_manager.py`) SHALL read normalized properties column-first and fall back to `meta` when the column is NULL, so a partially backfilled database never serves missing data.

#### Scenario: NULL column falls back to meta

- **WHEN** a row has a core property present in `meta` but NULL in the new relational column
- **THEN** reads of that property SHALL return the `meta` value

### Requirement: External payloads preserved in raw_payload audit column

The system SHALL store verbatim external provider payloads (BGG, Discogs, TMDB, MusicBrainz, Allegro) in a read-only `raw_payload` JSONB column at ingestion time, separate from curated `meta`, to guarantee provenance and re-scraping resilience.

#### Scenario: Ingestion stores the untouched provider payload

- **WHEN** a media strategy ingests metadata from an external provider
- **THEN** the unmodified provider response SHALL be persisted to `raw_payload` before any curation or normalization is applied

### Requirement: Migration correctness is proven by ETL pipeline tests

The change SHALL ship pytest coverage that runs the migration against representative flat-SQL/JSON fixtures and asserts row-count parity, per-key value parity, and FRBR graph integrity (Work → Expression → Manifestation → Item links intact) after upgrade.

#### Scenario: Migration test detects data loss

- **WHEN** the ETL migration test suite runs against fixture data containing core properties only in `meta`
- **THEN** it SHALL fail if any row count, property value, or FRBR parent-child link differs between pre-migration and post-migration snapshots
