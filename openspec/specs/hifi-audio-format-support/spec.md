# hifi-audio-format-support Specification

## Purpose
TBD - created by archiving change release-0-7-13. Update Purpose after archive.
## Requirements
### Requirement: BluRay HiFi Pure Audio is a canonical music format

The system SHALL recognize BluRay HiFi Pure Audio as a canonical physical format identifier `bluray_audio` within the `music` media category, defined in `shared/taxonomy.yaml` with a human-readable label ("Blu-ray Pure Audio"), and propagated to all generated taxonomy artifacts (backend constants and frontend types) via `make generate-taxonomy`.

#### Scenario: Taxonomy regeneration includes the new format

- **WHEN** `make generate-taxonomy` runs after the taxonomy update
- **THEN** the generated backend constants and frontend type definitions SHALL include `bluray_audio` under the `music` category with its label

### Requirement: Raw BluRay audio aliases resolve to the canonical format

The format normalization layer SHALL resolve common raw values for BluRay audio releases — including `Blu-ray Audio`, `BD-A`, `BluRay HiFi`, and `Pure Audio Blu-ray` — to the canonical `bluray_audio` identifier via `shared/format_mappings.yaml` and/or `format_aliases`.

#### Scenario: Vendor raw value normalizes to bluray_audio

- **WHEN** an ingested manifestation carries a raw format value of `Blu-ray Audio` and content type `music`
- **THEN** the format normalizer SHALL return `bluray_audio`

### Requirement: Audio on BluRay carriers is classified as music, not video

When a studio album or other music Work is released on a BluRay audio carrier, the audio lookup strategy (`app/strategies/audio.py`) and ingestion pipeline SHALL classify the manifestation under the `music` category with format `bluray_audio`, and SHALL NOT classify it as a `movie`/`bluray` video manifestation.

#### Scenario: Music Work on BluRay stays in music category

- **WHEN** a barcode lookup returns a music release whose carrier is BluRay Pure Audio
- **THEN** the resulting manifestation SHALL be categorized `music` with format `bluray_audio` and SHALL NOT appear in video/movie facet counts

#### Scenario: Classification boundary is pinned by strategy tests

- **WHEN** the strategy test suite runs
- **THEN** at least one test SHALL assert that a BluRay-audio music release resolves to `music`/`bluray_audio` and at least one SHALL assert that a concert/video BluRay does not resolve to `bluray_audio`
