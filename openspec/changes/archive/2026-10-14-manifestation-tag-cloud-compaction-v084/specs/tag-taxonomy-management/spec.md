## ADDED Requirements

### Requirement: Entity Tag Display Compaction and Provenance
The system SHALL compact large entity tag lists into a bounded, responsive tag cloud with expandable overflow controls and display source provenance metadata for each tag.

#### Scenario: Compacting large tag clouds in entity views
- **WHEN** an entity has more than 10 associated tags
- **THEN** the interface renders the top 10 tags alongside an expandable "+X more" interactive toggle
- **AND** clicking the toggle expands all tags in place with a smooth disclosure animation.

#### Scenario: Displaying tag source provenance
- **WHEN** a user hovers or inspects an ingested tag in the tag cloud
- **THEN** the system displays a tooltip indicating the origin provider (e.g. "Source: Discogs (Style)", "Source: OpenLibrary (Subject)", or "Source: User Curation").
