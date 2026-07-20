# format-mapping-cli Specification

## Purpose
TBD - created by archiving change fix-physical-kind-format-values. Update Purpose after archive.
## Requirements
### Requirement: CLI audits non-canonical format values in the database

The system SHALL provide a CLI script at `scripts/fix_physical_kinds.py` that, when invoked without flags, connects to the application database and produces an audit report of all non-canonical and NULL `meta['format']` values.

#### Scenario: Audit mode lists distinct non-canonical values

- **WHEN** the CLI is invoked without `--interactive` or `--apply`
- **THEN** it SHALL query `Manifestation.meta['format']` and SHALL output a table with columns: stored value, content type, count, and up to 3 example titles

#### Scenario: Audit mode groups by the combination of format value and content type

- **WHEN** the database has `format=NULL, content_type=movie` (1 row) and `format=NULL, content_type=music` (1 row)
- **THEN** the audit table SHALL show two separate rows: "null | movie | 1 | ..." and "null | music | 1 | ..."

#### Scenario: Audit mode excludes already-canonical format values

- **WHEN** a manifestation has `meta['format'] = "dvd"` (a valid MediaFormat value)
- **THEN** the audit table SHALL NOT include that row

#### Scenario: Audit mode handles empty database

- **WHEN** all manifestations have canonical format values or no manifestations exist
- **THEN** the CLI SHALL output a message indicating no issues found and exit with code 0

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

The CLI SHALL support an `--apply` mode that reads `shared/format_mappings.yaml` and performs SQL UPDATEs to fix all matching `Manifestation.meta['format']` values.

#### Scenario: Apply mode updates exact-match mappings

- **WHEN** `--apply` is invoked and `format_mappings.yaml` contains `video: dvd`
- **THEN** all manifestations with `meta['format'] = 'video'` SHALL have their `meta['format']` set to `'dvd'`

#### Scenario: Apply mode updates NULL mappings with content-type scoping

- **WHEN** `--apply` is invoked and `format_mappings.yaml` contains `format_normalizations.null.music: cd`
- **THEN** all manifestations with `meta['format'] IS NULL` AND whose expression has `content_type = 'music'` SHALL have their `meta['format']` set to `'cd'`

#### Scenario: Apply mode reports changes made

- **WHEN** `--apply` completes successfully
- **THEN** the CLI SHALL output a summary: number of rows updated, grouped by mapping rule applied

#### Scenario: Apply mode with --dry-run previews changes without modifying

- **WHEN** `--apply --dry-run` is invoked
- **THEN** the CLI SHALL show the SQL statements that would be executed and the count of affected rows, but SHALL NOT modify the database

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
