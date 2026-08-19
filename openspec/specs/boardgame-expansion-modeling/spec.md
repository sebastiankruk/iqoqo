# boardgame-expansion-modeling Specification

## Purpose

Define how board game expansions are modeled as distinct FRBRoo F1_Work entities linked to their base games via the `work_expansion_links` association table, instead of being aggregated into F16 Container Works.

## Requirements

### Requirement: Board game expansions modeled as distinct F1_Work entities

Board game expansions SHALL be modeled as distinct `frbroo:F1_Work` entities linked to their base games via a `work_expansion_links` association table, instead of being aggregated into F16 Container Works.

#### Scenario: Creating a new board game expansion

- **WHEN** a user or scanner identifies a board game expansion
- **THEN** the system SHALL create a new `F1_Work` entity for the expansion
- **AND** the system SHALL create an entry in `work_expansion_links` with `base_work_id` pointing to the base game and `expansion_work_id` pointing to the new expansion
- **AND** the expansion SHALL NOT be aggregated into any F16 Container Work

#### Scenario: Querying expansions for a base game

- **WHEN** the API retrieves a board game Work with expansions
- **THEN** the response SHALL include a list of linked expansion Works via the `work_expansion_links` table
- **AND** each expansion SHALL be a fully independent `F1_Work` entity

#### Scenario: Preventing F16 aggregation of expansions

- **WHEN** a system process attempts to aggregate a board game expansion Work into an F16 Container Work
- **THEN** the OWL/SHACL constraint SHALL prevent the aggregation
- **AND** the system SHALL raise a validation error
