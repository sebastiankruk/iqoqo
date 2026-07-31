# concert-modeling Specification

## Purpose
Define performance event expressions and concert audio/video recording metadata modeling.
## Requirements
### Requirement: Expression kind settable through UI and escalation

A concert Expression's `kind` (e.g. `live_performance`) SHALL be settable and correctable through the FRBR editor UI by admins, and requestable through the escalation system by non-admin users. The concert identification SHALL NOT depend solely on ingestion-time auto-detection — manual correction SHALL be available through the same operational paths used for other expression metadata.

#### Scenario: Admin corrects misclassified expression kind via UI

- **WHEN** an admin discovers an Expression that should be a concert (or should no longer be a concert)
- **THEN** the admin SHALL be able to open the FRBR editor, change the `kind` dropdown, and save — without needing to delete and re-ingest the record

#### Scenario: Non-admin requests kind correction via escalation

- **WHEN** a non-admin user discovers an Expression with an incorrect `kind` value
- **THEN** the user SHALL be able to submit a correction request through the escalation system, and a Custodian SHALL be able to approve and apply the change

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
