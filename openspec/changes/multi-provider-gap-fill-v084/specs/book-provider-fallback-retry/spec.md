## ADDED Requirements

### Requirement: Multi-Provider Metadata and Cover Gap Filling
The system SHALL query secondary configured metadata providers using the canonical item identifier to populate missing cover images and bibliographic fields when the primary provider result contains gaps.

#### Scenario: Primary provider returns metadata without cover art

- **WHEN** Google Books successfully resolves an ISBN with rich title and author metadata but no cover image
- **AND** Open Library has a valid cover image for the same ISBN
- **THEN** the system SHALL enrich the resolved metadata with the Open Library cover image
- **AND** SHALL NOT overwrite the title, author, or description returned by Google Books
- **AND** SHALL record both providers in the entity provenance tracking.

#### Scenario: Primary provider returns cover but missing publication details

- **WHEN** a primary provider returns a cover image and title but missing publisher or publication date
- **AND** a secondary provider has publisher details for the same canonical identifier
- **THEN** the system SHALL fill the missing publisher details from the secondary provider.

#### Scenario: Overall lookup timeout ceiling respected

- **WHEN** secondary provider queries are initiated to fill missing metadata fields
- **AND** the combined lookup duration reaches the global timeout threshold (3.0 seconds)
- **THEN** the system SHALL abort pending secondary provider queries and return the primary metadata result without failing the lookup.
