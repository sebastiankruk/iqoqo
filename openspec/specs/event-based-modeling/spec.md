# event-based-modeling Specification

## Purpose
Specify shared FRBRoo event-contribution entities across media strategies and level-appropriate mapping.
## Requirements
### Requirement: FRBRoo event entities are shared across all media strategies

The system SHALL treat the FRBRoo event-contribution entities — Composition Event (`WorkContribution`), Performance Event (`ExpressionContribution`), and Publication Event (`ManifestationContribution`) — as shared catalog-schema entities usable by every media strategy (text, audio, video, board game, puzzle), and SHALL NOT create parallel per-media contribution tables.

#### Scenario: Every strategy populates the shared contribution tables

- **WHEN** any media strategy ingests contributor data (author, composer, performer, director, publisher, studio, label)
- **THEN** the contributor SHALL be recorded through `Contributor` linked via exactly one of the three shared event-contribution entities appropriate to its FRBR level

### Requirement: Each event type maps to its FRBR level

Composition Events SHALL attach contributors only at the Work level (creators: authors, composers, game designers). Performance Events SHALL attach contributors only at the Expression level (realizers: performers, translators, narrators, cast). Publication Events SHALL attach contributors only at the Manifestation level (producers: publishers, labels, studios).

#### Scenario: Contributor roles respect FRBR level boundaries

- **WHEN** a contributor with a creator role (e.g. author) is ingested
- **THEN** the system SHALL link them via a Composition Event at the Work level and SHALL NOT attach them as a Manifestation-level contributor

#### Scenario: Publisher attaches at manifestation level only

- **WHEN** a publisher, label, or studio is ingested
- **THEN** the system SHALL link it via a Publication Event at the Manifestation level and SHALL NOT attach it to the Work or Expression

### Requirement: Event contribution data is available in API payloads

Entity API responses for Works, Expressions, and Manifestations SHALL expose their respective event contributions so clients can render creators, performers, and publishers without querying internal tables.

#### Scenario: Manifestation payload carries publication event data

- **WHEN** a client fetches a manifestation detail payload
- **THEN** the response SHALL include its Publication Event contributors (e.g. publisher/label/studio) when present
