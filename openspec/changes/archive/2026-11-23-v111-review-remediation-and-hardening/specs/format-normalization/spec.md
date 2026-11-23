## MODIFIED Requirements

### Requirement: Format filter resolves non-canonical values

When a client passes `?format=unknown_video`, `?format=unknown_audio`, or `?format=dvd`, the backend (`CatalogFilterBuilder._apply_format`, `SearchService` PostgreSQL FTS and SQLite `ILIKE`, `DataManager.get_filtered_works`, and `expand_format_filter`) SHALL evaluate `LOWER(COALESCE(Manifestation.format, Manifestation.format_type, Manifestation.meta['format']))` case-insensitively against lowercased expanded format tokens, expanding canonical filters across both `shared/format_mappings.yaml` (using pre-computed lowercased reverse alias lookups) and `FORMAT_ALIAS_TO_CATEGORY` aliases plus matching `NULL` rows (`OR COALESCE(Manifestation.format, Manifestation.format_type, Manifestation.meta['format']) IS NULL`) whenever `filter_includes_null_format()` is true, and SHALL apply `excluded_formats` inside SQL/FTS queries prior to `LIMIT`.

#### Scenario: Filter by unknown_video returns unresolved items

- **WHEN** the client requests `?format=unknown_video`
- **THEN** the response SHALL include all movie items whose `format`, `format_type`, or `meta['format']` normalizes to `"unknown_video"` (including unmapped `"video"`/`"movie"`/`"moving image"` values and movie items with `NULL` format across both PostgreSQL FTS and SQLite search paths)

#### Scenario: Filter by canonical format includes normalized items

- **WHEN** `"video"` is mapped to `"dvd"` and the client requests `?format=dvd` against rows storing `"DVD"`, `"Płyta DVD"`, or `"video"`
- **THEN** the response SHALL include all matching items across `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` in `CatalogFilterBuilder`, PostgreSQL FTS, SQLite search, and `DataManager.get_filtered_works`

#### Scenario: Filter by unknown_audio catches legacy music/audio/sound aliases and NULL audio rows

- **WHEN** the database contains music items with `format = "music"`, `format_type = "audio"`, `meta['format'] = "sound"`, and `NULL` format
- **THEN** `expand_format_filter(["unknown_audio"])` and `?format=unknown_audio` queries MUST return all four items across PostgreSQL FTS, SQLite `ILIKE`, `CatalogFilterBuilder`, and `DataManager.get_filtered_works`.

### Requirement: Ingest and write paths prevent generic category strings from persisting as carrier formats

External audio/video enrichers (`app/utils/musicbrainz.py`, `app/utils/discogs.py`, `app/utils/tmdb.py`) and all `Manifestation` write and validation paths (`IngestService.ingest_from_meta`, `ingest_audio_from_barcode`, `ingest_video_from_barcode`, `ingest_from_isbn`, `ingest_game_from_barcode`, `ingest_puzzle_from_barcode`, `app/core/f3_validation.py`, `app/api/scanner.py`, `add_item_manual`, `persist_isbn_manifestation`, `update_manifestation`, `frbr_service.create_manifestation`, `frbr_service.update_manifestation`, and `DataManager.import_data`) SHALL extract specific canonical `MediaFormat` carriers where available, SHALL normalize explicit carrier aliases (e.g., `"płyta dvd"`, `"płyta blu-ray"`, `"płyta vcd"`, `"książka papierowa"`, `"lp"`) to their canonical `MediaFormat` when `strict=False`, and SHALL normalize any residual generic category tokens (`"music"`, `"audio"`, `"sound"`, `"movie"`, `"video"`, `"moving image"`) to canonical `MediaFormat` placeholders (`"unknown_audio"`, `"unknown_video"`) rather than persisting category names or guessing `"cd"`.

#### Scenario: MusicBrainz and Discogs enrichers extract full audio carrier vocabulary with unknown_audio fallback

- **WHEN** MusicBrainz `media[*].format` or Discogs `formats[*].name`/`descriptions`/`format` specifies `"CD"`, `"Vinyl"`/`"LP"`, `"Cassette"`, `"SACD"`, `"MiniDisc"`, `"CD/DVD"`, or `"Blu-ray Audio"`
- **THEN** the enricher SHALL return the corresponding canonical `MediaFormat` (`"cd"`, `"vinyl"`, `"cassette"`, `"sacd"`, `"minidisc"`, `"cd_dvd_combo"`, `"bluray_audio"`)
- **AND** when the upstream carrier is absent or unrecognized, the enricher SHALL return `"unknown_audio"` instead of `"audio"`.

#### Scenario: Ingest and manual write paths reject or normalize generic category strings

- **WHEN** an ingest call, scanner preview/save, manual item creation, `create_manifestation`/`update_manifestation`, or `validate_format_type(..., strict=False)` receives `"format": "music"`, `"audio"`, `"sound"`, `"movie"`, `"video"`, `"moving image"`, or a configured alias such as `"płyta dvd"` or `"płyta vcd"`
- **THEN** the validated and persisted `Manifestation` MUST store the canonical `MediaFormat` (`"unknown_audio"`, `"unknown_video"`, `"dvd"`, or `"vcd"`), never the raw category or un-normalized alias string, and strict F3 validation (`strict=True`) SHALL reject un-normalized category strings when bypassed.
