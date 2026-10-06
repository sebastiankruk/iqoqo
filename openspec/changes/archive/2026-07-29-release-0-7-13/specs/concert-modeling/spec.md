## ADDED Requirements

### Requirement: Concerts are modeled as Performance Event Expressions

A concert release SHALL be modeled as an `Expression` of a musical or audiovisual `Work` with a performance-kind marker (e.g. `expression.kind = 'live_performance'`), linked to Performance Event contribution data (performers, and where available venue/date), and realized in a `Manifestation` carrying the physical carrier format (CD, DVD, or BluRay). Concert identity SHALL NOT be encoded as a genre tag, a format value, or an item-level flag.

#### Scenario: Concert BluRay is a performance expression with a video manifestation

- **WHEN** a live concert recording is cataloged on BluRay
- **THEN** the graph SHALL contain a Work linked to an Expression marked as a live performance, linked to a Manifestation categorized `movie` (or `music` for audio-only carriers) with format `bluray`

#### Scenario: Concert is never flattened into tags

- **WHEN** any concert release is ingested or edited
- **THEN** no genre/tag field and no physical `Item` attribute SHALL be used as the sole indicator that the release is a concert

### Requirement: Facets distinguish live performances from studio releases

Faceted navigation and search filters SHALL be able to distinguish live performance Expressions from studio releases of the same underlying Work, deriving the distinction from the Expression-level performance marker.

#### Scenario: Facet separates studio album from live concert recording

- **WHEN** a catalog contains both a studio album Expression and a live performance Expression of the same musical Work
- **THEN** facet counts and filtering SHALL treat them as distinct and SHALL NOT conflate them into a single undifferentiated bucket

### Requirement: Performance metadata is exposed on entity payloads

API payloads for Expressions and Manifestations representing concerts SHALL include the performance contribution data (performers, and venue/date when present) sourced from the Performance Event contribution entities.

#### Scenario: Concert manifestation payload includes performers

- **WHEN** a client fetches the detail payload of a concert manifestation
- **THEN** the response SHALL include the performance contributors recorded for its Expression
