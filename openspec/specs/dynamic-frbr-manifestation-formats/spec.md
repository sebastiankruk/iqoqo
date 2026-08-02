# dynamic-frbr-manifestation-formats Specification

## Purpose
TBD

## Requirements

### Requirement: Taxonomy-Driven Grouped Format Selection
The FRBR Editor SHALL use a grouped select widget for Manifestation types, sourced dynamically from the system taxonomy, replacing the static hardcoded list.

#### Scenario: User selects a specific format
- **WHEN** the user opens the Type dropdown in the Manifestation Editor
- **THEN** they see broad media categories (like "Music", "Movie", "Text") as `optgroup` headers
- **AND** they see specific formats (like "Blu-ray Pure Audio", "Audiobook CD", "Graphic Novel") as selectable `option` items within those groups.

### Requirement: Taxonomy Sync Synchronization Testing
The system SHALL include tests that verify the FRBR Editor Manifestation options exactly match the canonical entries defined in `shared/taxonomy.yaml`.

#### Scenario: Taxonomy expands with a new format
- **WHEN** a new format (e.g., "bluray_audio") is added to `shared/taxonomy.yaml` under the "Music" category
- **THEN** the automated taxonomy sync test SHALL pass only if the newly generated format is accessible via the ManifestationEditor select component.
