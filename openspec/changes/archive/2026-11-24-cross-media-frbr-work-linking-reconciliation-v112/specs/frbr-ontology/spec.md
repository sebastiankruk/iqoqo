## ADDED Requirements

### Requirement: Cross-Media Derivative Work Boundary

Cross-media adaptations and derivative creations (such as a novel and its film, audiobook, or board-game adaptation) MUST remain distinct `frbroo:F1_Work` entities connected by explicit `Work -> Work` derivative/adaptation relations (`frbroo:R2_is_derivative_of`) rather than collapsing separate mediums into a single `Work` via `frbr_merge`. Media/format attributes MUST remain on `Expression.content_type` and `Manifestation.format` and MUST NOT be promoted onto `Work` to distinguish mediums.

#### Scenario: Distinct creative mediums remain separate Works after cross-media linking

- **GIVEN** a novel `Work` (*Harry Potter and the Philosopher's Stone*, child `Expression.content_type = "text"`) and a film `Work` (*Harry Potter and the Philosopher's Stone*, child `Expression.content_type = "movie"`)
- **WHEN** a custodian confirms a cross-media `is_adaptation_of` link from the film `Work` to the novel `Work`
- **THEN** both `Work` records remain distinct rows with their respective `Expression` and `Manifestation` subtrees intact, no `frbr_merge` operation occurs, and neither `Work` stores physical carrier or format attributes.
