## Purpose
Support standalone cartographic maps/atlases and `iqoqo:hasMapAttachment` (`frbroo:R15_has_part`) map supplements on Books, Board Games, and Video Games with Item-level insert completeness tracking.

## ADDED Requirements

### Requirement: Standalone Cartographic Map & Entity Map Supplement Modeling

The system SHALL support cataloging standalone cartographic media (`cartographic_map`, `atlas` with `map_scale` and `map_projection`) AND attaching map supplements (`iqoqo:hasMapAttachment` / `frbroo:R15_has_part`) to Books, Board Games, and Video Games, while tracking physical insert presence (`map_insert_present`) on the `Item` (F5) tier.

#### Scenario: Attaching a fold-out or cloth map to a Book or Game Manifestation
- **GIVEN** an existing Book or Video Game `Manifestation`
- **WHEN** an authenticated contributor uploads or attaches a map supplement (`map_type="cloth_map"`, `title="Map of Skyrim"`)
- **THEN** the `Manifestation` records the map attachment, RDF serialization emits `iqoqo:hasMapAttachment`, and individual `Item` owners can toggle `map_insert_present` on their physical copy.
