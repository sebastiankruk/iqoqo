## MODIFIED Requirements

### Requirement: CLI audits non-canonical format values in the database

The system SHALL provide a CLI script at `scripts/fix_physical_kinds.py` using SQLAlchemy 2.0 `select()` queries that, when invoked without flags, connects to the application database and produces an audit report of all non-canonical, `NULL`, or unsynchronized format values across `Manifestation.meta['format']`, `Manifestation.format`, and `Manifestation.format_type` (including rows where `Manifestation.format` holds a canonical value such as `"dvd"` while `Manifestation.format_type` or `Manifestation.meta['format']` holds a different or more specific alias such as `"płyta vcd"`, and indicating whether `Manifestation.raw_payload` offers deterministic carrier recovery).

#### Scenario: Audit mode lists distinct non-canonical values

- **WHEN** the CLI is invoked without `--interactive` or `--apply`
- **THEN** it SHALL query `Manifestation.meta['format']`, `Manifestation.format`, and `Manifestation.format_type` via SQLAlchemy 2.0 `select()` and SHALL output a table with columns: stored value, content type, count, and up to 3 example titles

#### Scenario: Audit mode groups by the combination of format value and content type

- **WHEN** the database has `format=NULL, content_type=movie` (1 row) and `format=NULL, content_type=music` (1 row)
- **THEN** the audit table SHALL show two separate rows: "null | movie | 1 | ..." and "null | music | 1 | ..."

#### Scenario: Audit mode excludes already-canonical format values

- **WHEN** a manifestation has canonical, synchronized `"dvd"` across `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']`
- **THEN** the audit table SHALL NOT include that row

#### Scenario: Audit mode handles empty database

- **WHEN** all manifestations have canonical synchronized format values or no manifestations exist
- **THEN** the CLI SHALL output a message indicating no issues found and exit with code 0

#### Scenario: Audit mode detects column drift between meta['format'] and relational columns

- **WHEN** a manifestation has `meta['format'] = "cd"` while `Manifestation.format` or `Manifestation.format_type` is `NULL` or `"audio"`, or has `Manifestation.format = "dvd"` while `Manifestation.format_type = "płyta vcd"`
- **THEN** the audit report SHALL flag the drifted row as requiring synchronization rather than short-circuiting on `COALESCE(Manifestation.format, ...)`.

### Requirement: Deterministic raw_payload carrier recovery and ambiguous unknown_audio backfill

Both the linear Alembic backfill migration (`v1_1_1_norm_legacy_formats.py`, off `v1_1_0_serial_issn_issues`) and `scripts/fix_physical_kinds.py --apply` SHALL inspect `Manifestation.raw_payload` (passing `content_type` context for MusicBrainz `media[*].format`, Discogs `formats`/`format`, OpenLibrary, TMDb, and Allegro carrier parameters) whenever format columns contain legacy generic format values (`"music"`, `"audio"`, `"sound"`, `"movie"`, `"video"`, `"moving image"`) OR when all three format columns (`format`, `format_type`, `meta['format']`) are `NULL`/blank and `raw_payload` is present. Furthermore, when only a subset of the three format columns is populated with a canonical value (e.g., `format = NULL, format_type = NULL, meta['format'] = "vinyl"`), both the migration and `--apply` SHALL backfill all three columns to that canonical value, and whenever an unambiguous video or text carrier (`"dvd"`, `"bluray"`, `"vcd"`, `"book"`) is resolved on a row whose parent `Expression.content_type` was mis-tagged as `"music"`, both the migration and `--apply` SHALL repair `Expression.content_type` to match `FORMAT_TO_CATEGORY[target_fmt]`.

#### Scenario: MusicBrainz or Discogs raw_payload recovers specific carrier on backfill

- **GIVEN** an existing `Manifestation` with either `meta['format'] = "audio"` OR all three format columns (`format`, `format_type`, `meta['format']`) set to `NULL`, and `raw_payload` containing Discogs `formats: [{"name": "Vinyl"}]` or MusicBrainz `media: [{"format": "CD"}]`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be updated to `"vinyl"` (or `"cd"` respectively).

#### Scenario: Single-column canonical format backfills remaining NULL format columns

- **GIVEN** an existing `Manifestation` with `format = NULL`, `format_type = NULL`, and `meta['format'] = "vinyl"` (or `format_type = "dvd"` and `format = NULL`)
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST all be synchronized to `"vinyl"` (or `"dvd"`).

#### Scenario: Ambiguous music/audio/sound row without raw_payload normalizes to unknown_audio

- **GIVEN** an existing `Manifestation` with `meta['format']` in `{"music", "audio", "sound"}` and `raw_payload = NULL`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be updated to `"unknown_audio"` (NEVER `"cd"`), and audit/report output SHALL surface remaining `unknown_audio` counts for optional custodian review.

#### Scenario: Unambiguous video or book carrier recovery repairs mis-tagged Expression.content_type in both migration and CLI

- **GIVEN** an existing `Manifestation` under an `Expression` with `content_type = "music"` whose format or `raw_payload` resolves to `"dvd"`, `"bluray"`, `"vcd"`, or `"book"`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be synchronized to the canonical carrier and the parent `Expression.content_type` MUST be updated to `"movie"` (or `"text"` for `"book"`).
