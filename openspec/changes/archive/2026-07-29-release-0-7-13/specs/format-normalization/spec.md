## ADDED Requirements

### Requirement: Normalizer resolves BluRay audio raw values to bluray_audio

The `FormatNormalizer` SHALL resolve raw format values denoting BluRay audio releases (including `Blu-ray Audio`, `BD-A`, `BluRay HiFi`, `Pure Audio Blu-ray`) to the canonical `bluray_audio` music format when the content type is `music`, via user-configurable mappings in `shared/format_mappings.yaml` and/or built-in aliases in `shared/taxonomy.yaml`.

#### Scenario: Blu-ray Audio raw value resolves canonically

- **WHEN** the normalizer receives raw value `Blu-ray Audio` with content type `music` and a mapping exists in `shared/format_mappings.yaml`
- **THEN** the normalizer SHALL return `bluray_audio`

#### Scenario: Unmapped BluRay audio alias falls back within music category

- **WHEN** the normalizer receives a BluRay-audio raw value with no user mapping but a built-in alias exists
- **THEN** the normalizer SHALL return `bluray_audio` and SHALL NOT fall back to a video placeholder such as `unknown_video`
