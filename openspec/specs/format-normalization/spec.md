# format-normalization Specification

## Purpose
TBD - created by archiving change fix-physical-kind-format-values. Update Purpose after archive.
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

When computing Physical Kind facet counts for the faceted navigation panel, the system SHALL normalize each manifestation's format value before grouping, ensuring non-canonical values are counted under their resolved canonical format (or `unknown_*` placeholder).

#### Scenario: Facet counts group normalized values

- **WHEN** the database contains 3 manifestations with `meta['format'] = "video"` (all mapped to `"dvd"`) and 2 with `meta['format'] = "dvd"`
- **THEN** the Physical Kind facet SHALL show count 5 for `"dvd"`, not separate counts for `"video"` and `"dvd"`

#### Scenario: Unresolved values count under unknown placeholder

- **WHEN** 4 manifestations with content type `"movie"` have `meta['format'] = "video"` and no user mapping exists
- **THEN** the Physical Kind facet SHALL show count 4 for `"unknown_video"`

### Requirement: Format filter resolves non-canonical values

When a client passes `?format=unknown_video` or `?format=dvd`, the backend SHALL return items whose normalized format matches the filter value. Items whose raw format normalizes to the same canonical value SHALL be included.

#### Scenario: Filter by unknown_video returns unresolved items

- **WHEN** the client requests `?format=unknown_video`
- **THEN** the response SHALL include all movie items whose `meta['format']` normalizes to `"unknown_video"`

#### Scenario: Filter by canonical format includes normalized items

- **WHEN** `"video"` is mapped to `"dvd"` and the client requests `?format=dvd`
- **THEN** the response SHALL include items with raw format `"video"` (normalized to `"dvd"`) AND items with raw format `"dvd"`

