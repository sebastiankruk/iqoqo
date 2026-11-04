## ADDED Requirements

### Requirement: Biblioteka Narodowa Fallback for Polish Publications
When an ISBN lookup corresponds to a Polish publication (ISBN-13 prefix 978-83 or 979-83) and primary providers yield no metadata or fail transiently, the system SHALL query the National Library of Poland (Biblioteka Narodowa) open REST API before declaring the lookup failed.

#### Scenario: Polish ISBN resolves via Biblioteka Narodowa
- **WHEN** a user or background process looks up a Polish ISBN (prefix 97883... or 97983...)
- **AND** Google Books and Open Library return no metadata
- **THEN** the system SHALL query `https://data.bn.org.pl/api/bibs.json?isbnIssn={isbn}`
- **AND** if records are returned, the system SHALL extract and return title, author, publisher, publication year, and genres
- **AND** the returned metadata provenance SHALL record Biblioteka Narodowa as the data source.

### Requirement: Stored Google Books API Key Retrieval
When performing Google Books volume lookups or candidate searches, the system SHALL read the API key from central instance settings before falling back to environment variables to prevent unauthenticated IP quota exhaustion.

#### Scenario: Google Books queries use stored instance settings key
- **WHEN** looking up ISBN metadata or candidate books from Google Books
- **AND** a valid Google Books API key exists in encrypted instance settings
- **THEN** all outbound Google Books requests SHALL attach the key as a parameter
- **AND** logs SHALL redact the key parameter value in error and telemetry reporting.

## MODIFIED Requirements

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
- **AND** the combined lookup duration reaches the global timeout threshold (6.0 seconds)
- **THEN** the system SHALL abort pending secondary provider queries and return the primary metadata result without failing the lookup.
