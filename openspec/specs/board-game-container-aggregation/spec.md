# board-game-container-aggregation Specification

## Purpose
TBD - created by archiving change release-0-7-13. Update Purpose after archive.
## Requirements
### Requirement: Board games are modeled as FRBRoo F16 Container Works

A board game box SHALL be modeled as an FRBRoo F16 Container Work whose contents are expressed through the shared `ContainerAggregation` entity: the rulebook SHALL be aggregated as a `Work`, and physical components (board, pieces, cards, dice) SHALL be aggregated as components. The container relationship SHALL NOT be simulated through format values or tags.

#### Scenario: Board game ingestion creates container aggregation

- **WHEN** a board game is ingested with known contents (rulebook plus components)
- **THEN** the system SHALL create a container Work linked via `ContainerAggregation` rows to the rulebook Work and to each component entry

#### Scenario: Aggregation type integrity is enforced

- **WHEN** a `ContainerAggregation` row is written
- **THEN** it SHALL reference exactly one aggregated target — either a Work (e.g. rulebook) or an item-level component — enforced by the existing database check constraint

### Requirement: Container contents are visible on the manifestation view

The manifestation detail view and its API payload SHALL expose the aggregated contents of a board game container (component names, quantities, and linked rulebook) so collectors can see what the box contains.

#### Scenario: Manifestation payload lists box contents

- **WHEN** a client fetches the detail payload of a board game manifestation whose Work is a container
- **THEN** the response SHALL include the aggregated contents with component names and quantities
