# format-mapping-cli Specification

## Purpose
TBD - created by archiving change fix-physical-kind-format-values. Update Purpose after archive.

## Requirements

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

### Requirement: Interactive mode walks the user through each distinct non-canonical value

The CLI SHALL support an `--interactive` mode that presents each distinct non-canonical format value to the user and prompts them to select a canonical format mapping.

#### Scenario: User maps a non-canonical value to a canonical format

- **WHEN** `--interactive` is invoked and a row shows `format="video", content_type="movie", count=12`
- **THEN** the CLI SHALL prompt: "Map 'video' (12 items, all movie) to which physical kind?" with a numbered list of valid movie formats including "unknown_video" and "skip"
- **AND** when the user selects "dvd", the mapping SHALL be written to `shared/format_mappings.yaml` as `video: dvd`

#### Scenario: User chooses to skip a value

- **WHEN** the user selects "skip" for a non-canonical value
- **THEN** that value SHALL NOT be added to `format_mappings.yaml` and SHALL be left unresolved (falling back to `unknown_*` at read-time)

#### Scenario: User maps NULL format for a specific content type

- **WHEN** a row shows `format=null, content_type=music, count=1`
- **THEN** the CLI SHALL prompt: "NULL format for music (1 item). Map to which physical kind?" with a numbered list of valid music formats including "skip"
- **AND** when the user selects "cd", the mapping SHALL be written as `format_normalizations.null.music: cd`

#### Scenario: User can batch-map NULL for text (books)

- **WHEN** a row shows `format=null, content_type=text, count=1580`
- **THEN** the CLI SHALL explicitly note the large count and SHALL offer a bulk option: "Map all 1580 NULL text items to 'book'?"
- **AND** when the user confirms, the mapping SHALL be written as `format_normalizations.null.text: book`

#### Scenario: Interactive mode shows existing mappings and asks before overwriting

- **WHEN** `format_mappings.yaml` already contains `video: dvd` and the user enters `--interactive` again
- **THEN** already-mapped values SHALL be skipped (not re-prompted) with a note: "'video' already mapped to 'dvd' — skipping"

### Requirement: Apply mode updates the database using mappings

The CLI SHALL support an `--apply` mode that reads `shared/format_mappings.yaml`, performs keyset-batched (`WHERE id > last_id ORDER BY id ASC LIMIT <batch_size>`) SQLAlchemy 2.0 updates across both PostgreSQL (handling `NULL` `meta` via `COALESCE(CAST(meta AS jsonb), '{}'::jsonb)`) and SQLite, and synchronizes all three format locations (`Manifestation.meta['format']`, `Manifestation.format`, and `Manifestation.format_type`). The SQL statements MUST be written in a syntax compatible with both PostgreSQL and SQLAlchemy parameter binding to avoid `SyntaxError`s during execution.

#### Scenario: Apply mode updates exact-match mappings

- **WHEN** `--apply` is invoked and `format_mappings.yaml` contains `video: dvd`
- **THEN** all manifestations with case-insensitive `meta['format'] = 'video'` (or `format = 'video'` or `format_type = 'video'`) SHALL have `meta['format']`, `Manifestation.format`, and `Manifestation.format_type` all set to `'dvd'`
- **AND** the database operation SHALL execute successfully without syntax errors caused by bind parameter conflicts (e.g., `::text` casting) or `NULL` `meta` payloads.

#### Scenario: Apply mode updates NULL mappings with content-type scoping

- **WHEN** `--apply` is invoked and `format_mappings.yaml` contains `format_normalizations.null.music: unknown_audio`
- **THEN** all manifestations with `NULL` format across the target fields AND whose expression has `content_type = 'music'` SHALL have `meta['format']`, `Manifestation.format`, and `Manifestation.format_type` set to `'unknown_audio'`

#### Scenario: Apply mode reports changes made

- **WHEN** `--apply` completes successfully
- **THEN** the CLI SHALL output a summary: number of rows updated, grouped by mapping rule applied (including `raw_payload` recoveries vs. `unknown_audio` fallbacks)

#### Scenario: Apply mode with --dry-run previews changes without modifying

- **WHEN** `--apply --dry-run` is invoked
- **THEN** the CLI SHALL show the planned changes and the count of affected rows, but SHALL NOT modify the database

#### Scenario: Apply mode validates mappings before executing

- **WHEN** `--apply` is invoked and a mapping targets a non-existent `MediaFormat` value
- **THEN** the CLI SHALL exit with an error before executing any UPDATEs and SHALL report the invalid target format

### Requirement: CLI gracefully handles absent or empty mapping file

The CLI SHALL not fail when `shared/format_mappings.yaml` is missing or has no `format_normalizations` section.

#### Scenario: Audit still works without mapping file

- **WHEN** `format_mappings.yaml` does not exist and the CLI is invoked in audit mode
- **THEN** the audit report SHALL be generated normally

#### Scenario: Apply mode refuses with empty mapping file

- **WHEN** `--apply` is invoked and no mappings are defined
- **THEN** the CLI SHALL output "No format mappings defined. Run --interactive first." and exit with code 1

### Requirement: Makefile provides a convenient entry point

The project's `Makefile` SHALL provide a `fix-physical-kinds` target that invokes `scripts/fix_physical_kinds.py` with the correct Python environment.

#### Scenario: make fix-physical-kinds runs audit mode

- **WHEN** `make fix-physical-kinds` is invoked
- **THEN** it SHALL execute `scripts/fix_physical_kinds.py` in audit mode (no flags)

#### Scenario: make target passes through arguments

- **WHEN** `make fix-physical-kinds ARGS="--interactive"` is invoked
- **THEN** the script SHALL be executed with `--interactive`

### Requirement: Deterministic raw_payload carrier recovery and ambiguous unknown_audio backfill

Both the linear Alembic backfill migration (`v1_1_1_norm_legacy_formats.py`, off `v1_1_0_serial_issn_issues`) and `scripts/fix_physical_kinds.py --apply` SHALL inspect `Manifestation.raw_payload` (passing `content_type` context for MusicBrainz `media[*].format`, Discogs `formats`/`format`, OpenLibrary, TMDb, and Allegro carrier parameters) whenever format columns contain legacy generic format values (`"music"`, `"audio"`, `"sound"`, `"movie"`, `"video"`, `"moving image"`) OR when all three format columns (`format`, `format_type`, `meta['format']`) are `NULL`/blank and `raw_payload` is present. Furthermore, when only a subset of the three format columns is populated with a canonical value (e.g., `format = NULL, format_type = NULL, meta['format'] = "vinyl"`) OR when any format column contains mixed-case characters (e.g., uniform `"Vinyl"`, `"Vinyl"`, `"Vinyl"`), both the migration and `--apply` SHALL synchronize all three columns to the lowercased canonical value, and whenever an unambiguous video or text carrier (`"dvd"`, `"bluray"`, `"vcd"`, `"book"`) is resolved on a row whose parent `Expression.content_type` was mis-tagged as `"music"`, both the migration and `--apply` SHALL repair `Expression.content_type` to match `FORMAT_TO_CATEGORY[target_fmt]`.

#### Scenario: MusicBrainz or Discogs raw_payload recovers specific carrier on backfill

- **GIVEN** an existing `Manifestation` with either `meta['format'] = "audio"` OR all three format columns (`format`, `format_type`, `meta['format']`) set to `NULL`, and `raw_payload` containing Discogs `formats: [{"name": "Vinyl"}]` or MusicBrainz `media: [{"format": "CD"}]`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be updated to `"vinyl"` (or `"cd"` respectively).

#### Scenario: Single-column canonical format backfills remaining NULL format columns

- **GIVEN** an existing `Manifestation` with `format = NULL`, `format_type = NULL`, and `meta['format'] = "vinyl"` (or `format_type = "dvd"` and `format = NULL`), or with uniform mixed-case `"Vinyl"` across all three format fields
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST all be synchronized to lowercased `"vinyl"` (or `"dvd"`).

#### Scenario: Ambiguous music/audio/sound row without raw_payload normalizes to unknown_audio

- **GIVEN** an existing `Manifestation` with `meta['format']` in `{"music", "audio", "sound"}` and `raw_payload = NULL`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be updated to `"unknown_audio"` (NEVER `"cd"`), and audit/report output SHALL surface remaining `unknown_audio` counts for optional custodian review.

#### Scenario: Unambiguous video or book carrier recovery repairs mis-tagged Expression.content_type in both migration and CLI

- **GIVEN** an existing `Manifestation` under an `Expression` with `content_type = "music"` whose format or `raw_payload` resolves to `"dvd"`, `"bluray"`, `"vcd"`, or `"book"`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be synchronized to the canonical carrier and the parent `Expression.content_type` MUST be updated to `"movie"` (or `"text"` for `"book"`).

### Requirement: SQLAlchemy 2.0 keyset-batched backfill without legacy .query or full-table heap loads

All queries and mutations in `scripts/fix_physical_kinds.py` and the Alembic backfill migration SHALL use SQLAlchemy 2.0 `select()` / `update()` constructs and keyset pagination (`id > last_id ORDER BY id ASC LIMIT <batch_size>`) without legacy `.query` / `db.session.query` calls or unbounded `.all()` heap loads.

#### Scenario: Large manifestation table backfills in bounded keyset batches

- **WHEN** `scripts/fix_physical_kinds.py --apply` or the Alembic migration processes a table exceeding one batch size (`500` rows)
- **THEN** it SHALL iterate deterministically by `Manifestation.id > last_id` in bounded batches, synchronize all affected rows, and remain idempotent on re-run.
