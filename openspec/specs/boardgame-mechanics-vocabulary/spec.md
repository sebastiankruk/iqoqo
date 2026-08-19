# boardgame-mechanics-vocabulary Specification

## Purpose

Define how the system maintains a local copy of the BGG board game mechanics taxonomy in a `boardgame_mechanics` table, replacing free-text mechanics input with controlled vocabulary references.

## Requirements

### Requirement: Controlled vocabulary for board game mechanics

The system SHALL maintain a local copy of the BGG board game mechanics taxonomy in a `boardgame_mechanics` database table, replacing free-text `mechanics` field input with controlled vocabulary references.

#### Scenario: Selecting mechanics for a board game

- **WHEN** a user edits board game metadata and sets the mechanics field
- **THEN** the system SHALL present available mechanics from the `boardgame_mechanics` table
- **AND** the user SHALL select from the controlled vocabulary rather than entering free text

#### Scenario: Mechanics vocabulary is seeded from local BGG data

- **WHEN** the database is initialized or migrated
- **THEN** the `boardgame_mechanics` table SHALL be populated from `data/bgg_mechanics.json`
- **AND** each entry SHALL include `id`, `name`, `description`, and `bgg_id` fields

#### Scenario: Updating mechanics vocabulary

- **WHEN** an admin runs the mechanics vocabulary update script
- **THEN** new mechanics SHALL be added and existing ones SHALL be updated from the latest local BGG taxonomy file
- **AND** mechanics not present in the update SHALL NOT be deleted (soft deprecation)
