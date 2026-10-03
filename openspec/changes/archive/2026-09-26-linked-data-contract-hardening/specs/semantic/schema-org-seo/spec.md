## ADDED Requirements

### Requirement: Expression-Kind-Aware Schema.org Mapping

Schema.org mapping MUST account for FRBR Expression kind as well as content type and physical format, including mapping live-performance/concert expressions to event semantics where applicable.

#### Scenario: Live performance expression

- **WHEN** a manifestation belongs to an Expression with `live_performance` kind
- **THEN** backend RDF and frontend SSR structured data use the documented MusicEvent mapping and preserve performer/date/location fields when available

#### Scenario: Ordinary expression precedence

- **WHEN** an ordinary expression has a content type and physical format
- **THEN** the documented content-type/format mapping remains unchanged
