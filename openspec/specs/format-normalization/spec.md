# format-normalization Specification

## Purpose
Define format string resolution, custom format alias mappings, and unknown format fallback rules.

## Requirements

### Requirement: Format normalizer resolves non-canonical values at read-time

The system SHALL provide a `FormatNormalizer` that accepts a raw format string and a content type and returns a canonical `MediaFormat` value. The normalizer SHALL be invoked whenever `Manifestation.meta['format']` is read for display, filtering, or facet computation.

#### Scenario: Canonical format passes through unchanged

- **WHEN** the raw format value is a known `MediaFormat` constant (e.g., `"dvd"`, `"vinyl"`, `"board_game"`)
- **THEN** the normalizer SHALL return the value unchanged

#### Scenario: Non-canonical value mapped via user configuration

- **WHEN** the raw format value is `"video"` and `shared/format_mappings.yaml` contains `format_normalizations.video: dvd`
- **THEN** the normalizer SHALL return `"dvd"`

#### Scenario: Non-canonical value without user mapping falls back to placeholder

- **WHEN** the raw format value is `"audio"` and no mapping exists in `shared/format_mappings.yaml`
- **THEN** the normalizer SHALL resolve the value's category using `FORMAT_ALIAS_TO_CATEGORY` (finding `"audio" → music`) and SHALL return the placeholder `"unknown_audio"`

#### Scenario: NULL format with user-specified content-type mapping

- **WHEN** the raw format value is `None` (NULL in DB), content type is `"movie"`, and `shared/format_mappings.yaml` contains `format_normalizations.null.movie: dvd`
- **THEN** the normalizer SHALL return `"dvd"`

#### Scenario: NULL format without mapping falls back to placeholder

- **WHEN** the raw format value is `None`, content type is `"movie"`, and no NULL mapping exists
- **THEN** the normalizer SHALL return `"unknown_video"`

#### Scenario: Completely unrecognized value falls back to category placeholder

- **WHEN** the raw format value is `"xyz123"`, content type is `None`, and no mapping or alias exists
- **THEN** the normalizer SHALL return `"unknown_text"` (the most generic fallback)

> [!CONFIRMATION] Data loss?
>
> - **Question**: Wouldn't such approach mean we no longer know the original raw value so we don't know what mapping to provide next time?
> - **Answer**: no, we do that are read time - db is not touched

### Requirement: Unknown placeholder formats are valid MediaFormat values

The taxonomy SHALL include `unknown_video`, `unknown_audio`, and `unknown_text` as valid `MediaFormat` identifiers, each belonging to its respective media category.

#### Scenario: unknown_video belongs to movie category

- **WHEN** `MediaFormat.UNKNOWN_VIDEO` is looked up in `FORMAT_TO_CATEGORY`
- **THEN** it SHALL resolve to `"movie"`

#### Scenario: unknown_audio belongs to music category

- **WHEN** `MediaFormat.UNKNOWN_AUDIO` is looked up in `FORMAT_TO_CATEGORY`
- **THEN** it SHALL resolve to `"music"`

#### Scenario: unknown_text belongs to text category

- **WHEN** `MediaFormat.UNKNOWN_TEXT` is looked up in `FORMAT_TO_CATEGORY`
- **THEN** it SHALL resolve to `"text"`

#### Scenario: Unknown format labels are human-readable

- **WHEN** the UI renders a format badge for `unknown_video`
- **THEN** it SHALL display "Unknown Video Format" (not the raw ID)

### Requirement: User format mappings are stored in shared/format_mappings.yaml

The system SHALL read user-defined format normalizations from `shared/format_mappings.yaml`, a git-tracked YAML file in the project root's `shared/` directory.

#### Scenario: Mapping file is absent or empty

- **WHEN** `shared/format_mappings.yaml` does not exist or contains no `format_normalizations` key
- **THEN** the normalizer SHALL operate with no user-defined mappings and SHALL fall back to `unknown_*` placeholders for non-canonical values

#### Scenario: Mapping file contains exact-value mappings

- **WHEN** the mapping file defines `format_normalizations.audio: cd`
- **THEN** the normalizer SHALL map `"audio"` to `"cd"` regardless of content type

#### Scenario: Mapping file contains NULL with content-type scoping

- **WHEN** the mapping file defines `format_normalizations.null.music: cd` and `format_normalizations.null.movie: dvd`
- **THEN** the normalizer SHALL map NULL+content_type `"music"` to `"cd"` and NULL+content_type `"movie"` to `"dvd"` independently

#### Scenario: Mapping file contains invalid format values

- **WHEN** `format_mappings.yaml` maps a value to `"nonexistent_format"`
- **THEN** the normalizer SHALL log a warning and SHALL fall back to the `unknown_*` placeholder for that value

### Requirement: Format normalizer is idempotent

Applying the normalizer to an already-canonical value SHALL produce the same value, and applying it twice SHALL produce the same result as applying it once.

#### Scenario: Double normalization of canonical value

- **WHEN** `normalize_format("dvd", "movie")` is called twice
- **THEN** both calls SHALL return `"dvd"`

#### Scenario: Double normalization of mapped non-canonical value

- **WHEN** `"video"` is mapped to `"dvd"` and `normalize_format("dvd", "movie")` is called
- **THEN** the normalizer SHALL return `"dvd"` (canonical values pass through, not re-mapped)

### Requirement: Facet aggregation uses normalized format values

When computing Physical Kind facet counts for the faceted navigation panel, the system SHALL resolve each manifestation's format across `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` and SHALL normalize each value with `Expression.content_type` context before grouping, ensuring non-canonical values and `NULL` formats are counted under their resolved canonical format (or `unknown_*` placeholder).

#### Scenario: Facet counts group normalized values

- **WHEN** the database contains 3 manifestations with `meta['format'] = "video"` (all mapped to `"dvd"`) and 2 with `meta['format'] = "dvd"`
- **THEN** the Physical Kind facet SHALL show count 5 for `"dvd"`, not separate counts for `"video"` and `"dvd"`

#### Scenario: Unresolved values count under unknown placeholder

- **WHEN** 4 manifestations with content type `"movie"` have `meta['format'] = "video"` and no user mapping exists
- **THEN** the Physical Kind facet SHALL show count 4 for `"unknown_video"`

#### Scenario: Facet counts include NULL and promoted-column formats with content-type context

- **WHEN** the database contains 2 music manifestations with `NULL` format across `format`, `format_type`, and `meta['format']`, and 1 music manifestation with `Manifestation.format = "vinyl"` and `meta['format'] = NULL`
- **THEN** the Physical Kind facet SHALL include count 2 under `"unknown_audio"` and count 1 under `"vinyl"`.

### Requirement: Format filter resolves non-canonical values

When a client passes `?format=unknown_video`, `?format=unknown_audio`, or `?format=dvd`, the backend (`CatalogFilterBuilder`, `SearchService` PG FTS and SQLite `ILIKE`, and `expand_format_filter`) SHALL evaluate `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']`, expanding canonical filters across both `shared/format_mappings.yaml` and `FORMAT_ALIAS_TO_CATEGORY` aliases plus matching `NULL` rows when an `unknown_*` placeholder is requested.

#### Scenario: Filter by unknown_video returns unresolved items

- **WHEN** the client requests `?format=unknown_video`
- **THEN** the response SHALL include all movie items whose `format`, `format_type`, or `meta['format']` normalizes to `"unknown_video"` (including unmapped `"video"`/`"movie"` values and movie items with `NULL` format)

#### Scenario: Filter by canonical format includes normalized items

- **WHEN** `"video"` is mapped to `"dvd"` and the client requests `?format=dvd`
- **THEN** the response SHALL include items with raw format `"video"` (normalized to `"dvd"`) AND items with raw format `"dvd"` across `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']`

#### Scenario: Filter by unknown_audio catches legacy music/audio/sound aliases and NULL audio rows

- **WHEN** the database contains music items with `format = "music"`, `format_type = "audio"`, `meta['format'] = "sound"`, and `NULL` format
- **THEN** `expand_format_filter(["unknown_audio"])` and `?format=unknown_audio` queries MUST return all four items.

### Requirement: Normalizer resolves BluRay audio raw values to bluray_audio

The `FormatNormalizer` SHALL resolve raw format values denoting BluRay audio releases (including `Blu-ray Audio`, `BD-A`, `BluRay HiFi`, `Pure Audio Blu-ray`) to the canonical `bluray_audio` music format when the content type is `music`, via user-configurable mappings in `shared/format_mappings.yaml` and/or built-in aliases in `shared/taxonomy.yaml`.

#### Scenario: Blu-ray Audio raw value resolves canonically

- **WHEN** the normalizer receives raw value `Blu-ray Audio` with content type `music` and a mapping exists in `shared/format_mappings.yaml`
- **THEN** the normalizer SHALL return `bluray_audio`

#### Scenario: Unmapped BluRay audio alias falls back within music category

- **WHEN** the normalizer receives a BluRay-audio raw value with no user mapping but a built-in alias exists
- **THEN** the normalizer SHALL return `bluray_audio` and SHALL NOT fall back to a video placeholder such as `unknown_video`

### Requirement: Ingest and write paths prevent generic category strings from persisting as carrier formats

External audio/video enrichers (`app/utils/musicbrainz.py`, `app/utils/discogs.py`, `app/utils/tmdb.py`) and all `Manifestation` write paths (`IngestService.ingest_from_meta`, `ingest_audio_from_barcode`, `ingest_video_from_barcode`, `ingest_from_isbn`, `ingest_game_from_barcode`, `ingest_puzzle_from_barcode`, `app/api/scanner.py`, `add_item_manual`, `persist_isbn_manifestation`, `update_manifestation`, `frbr_service.create_manifestation`, `frbr_service.update_manifestation`, and `DataManager.import_data`) SHALL extract specific canonical `MediaFormat` carriers where available and SHALL normalize any residual generic category tokens (`"music"`, `"audio"`, `"sound"`, `"movie"`, `"video"`) to canonical `MediaFormat` placeholders (`"unknown_audio"`, `"unknown_video"`) rather than persisting category names or guessing `"cd"`.

#### Scenario: MusicBrainz and Discogs enrichers extract full audio carrier vocabulary with unknown_audio fallback

- **WHEN** MusicBrainz `media[*].format` or Discogs `formats[*].name`/`descriptions`/`format` specifies `"CD"`, `"Vinyl"`/`"LP"`, `"Cassette"`, `"SACD"`, `"MiniDisc"`, `"CD/DVD"`, or `"Blu-ray Audio"`
- **THEN** the enricher SHALL return the corresponding canonical `MediaFormat` (`"cd"`, `"vinyl"`, `"cassette"`, `"sacd"`, `"minidisc"`, `"cd_dvd_combo"`, `"bluray_audio"`)
- **AND** when the upstream carrier is absent or unrecognized, the enricher SHALL return `"unknown_audio"` instead of `"audio"`.

#### Scenario: Ingest and manual write paths reject or normalize generic category strings

- **WHEN** an ingest call, scanner preview/save, manual item creation, or `create_manifestation`/`update_manifestation` receives `"format": "music"`, `"audio"`, `"sound"`, `"movie"`, or `"video"`
- **THEN** the persisted `Manifestation` MUST store the canonical `MediaFormat` (`"unknown_audio"` or `"unknown_video"`), never the raw category string, and strict F3 validation SHALL reject un-normalized category strings when bypassed.

### Requirement: Multi-field Manifestation format synchronization and raw_payload preservation

Every `Manifestation` creation, update, and import path (`IngestService`, `frbr_service`, `scanner.py`, `items.py`, `manifestations.py`, `DataManager.import_data`) SHALL synchronize the canonical normalized value across `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']`, and `IngestService` barcode/metadata ingestion SHALL preserve the upstream provider dict in `Manifestation.raw_payload` whenever an external payload was retrieved.

#### Scenario: Audio barcode ingest populates all three format columns and raw_payload

- **GIVEN** an upstream MusicBrainz or Discogs payload for a vinyl LP barcode
- **WHEN** `IngestService.ingest_audio_from_barcode` (or `ingest_from_meta`) creates a `Manifestation`
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST all equal `"vinyl"`, and `Manifestation.raw_payload` MUST retain the upstream release payload.

#### Scenario: Display projection reads synchronized or normalized format without falling back to raw category names

- **WHEN** `meta_display.build_display_projection` or `_serialize_shared_collection_item` formats a `Manifestation` whose legacy columns diverge
- **THEN** it SHALL resolve the canonical `FormatNormalizer` output rather than surfacing un-normalized `"music"`, `"audio"`, or `"sound"`.

### Requirement: Default checked-in format mappings do not guess cd for ambiguous audio

The git-tracked `shared/format_mappings.yaml` configuration SHALL map `"audio"`, `"music"`, and `"sound"` to `"unknown_audio"` rather than unconditionally guessing `"cd"`, ensuring non-CD audio releases without carrier evidence are never mislabeled as compact discs.

#### Scenario: Checked-in shared/format_mappings.yaml resolves audio, music, and sound to unknown_audio

- **WHEN** `FormatNormalizer.normalize(val, "music")` runs against the checked-in `shared/format_mappings.yaml` for `"audio"`, `"music"`, or `"sound"`
- **THEN** each call SHALL return `"unknown_audio"` rather than `"cd"`.
