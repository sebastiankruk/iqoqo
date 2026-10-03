## ADDED Requirements

### Requirement: Event entities respect FRBR level boundaries

The FRBRoo event-contribution entities SHALL attach strictly to their corresponding FRBR level: Composition Events (`WorkContribution`) at the Work, Performance Events (`ExpressionContribution`) at the Expression, and Publication Events (`ManifestationContribution`) at the Manifestation. Physical attributes and item-level data SHALL NEVER be attached to any event entity.

#### Scenario: Event contribution never carries physical attributes

- **WHEN** a contribution row of any event type is created
- **THEN** it SHALL reference only its level-appropriate entity (Work, Expression, or Manifestation) plus a `Contributor`, and SHALL NOT store barcodes, conditions, shelf locations, or acquisition data

### Requirement: Container Work aggregation boundary

Board game containers SHALL be modeled exclusively through the FRBRoo F16 Container Work pattern using `ContainerAggregation`. Format values, genre tags, or item notes SHALL NOT be used as a substitute for container structure.

#### Scenario: Container structure is never simulated by tags

- **WHEN** a board game's contents (rulebook, board, pieces) are recorded
- **THEN** they SHALL be represented as `ContainerAggregation` rows and SHALL NOT be encoded as tags or as part of the manifestation format value

### Requirement: Concert hierarchy boundary

A concert release SHALL follow the hierarchy musical/audiovisual Work → live-performance Expression (Performance Event) → audio or video Manifestation → Item. A concert SHALL NOT be modeled as a distinct top-level media category, nor as a Work-level genre.

#### Scenario: Concert graph passes ontology validation

- **WHEN** a concert release is validated against the FRBR boundary rules
- **THEN** its Expression SHALL carry the performance marker and performance contributors, and its Manifestation SHALL carry the carrier format, with no concert indicator stored on the Work or the Item
