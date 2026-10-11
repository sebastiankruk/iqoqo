# book-provider-fallback-retry Specification

## Purpose

Define fallback and bounded-retry behavior for external book metadata lookups so transient Google Books failures do not block scanning, while preserving scanner behavior, provenance, and secret-free logging.

## Requirements

### Requirement: External book lookups continue after transient Google Books failures

When a valid ISBN lookup reaches Google Books and Google Books returns a rate-limit or server-side failure, the system SHALL treat that response as transient and attempt Open Library before declaring the lookup failed.

#### Scenario: Google Books rate limited and Open Library resolves

- **WHEN** Google Books returns 429 or 503 for a valid ISBN
- **AND** Open Library has metadata for that ISBN
- **THEN** the lookup SHALL return Open Library metadata
- **AND** the returned provenance SHALL identify Open Library

#### Scenario: Google Books definitive no-result

- **WHEN** Google Books completes successfully but has no items for a valid ISBN
- **THEN** the lookup SHALL attempt Open Library
- **AND** the system SHALL NOT retry Google Books solely because the first Google response had no items

### Requirement: Google Books receives one bounded retry after Open Library no-result

When Google Books fails transiently and Open Library returns no metadata for the same ISBN, the system SHALL retry Google Books exactly once before continuing to downstream providers.

#### Scenario: Transient Google failure followed by retry success

- **WHEN** Google Books first returns 429 or 503 for a valid ISBN
- **AND** Open Library has no metadata for that ISBN
- **THEN** the system SHALL retry Google Books once after a short bounded delay
- **AND** if the retry succeeds, the lookup SHALL return Google Books metadata

#### Scenario: Both Google attempts fail

- **WHEN** Google Books first returns 429 or 503
- **AND** Open Library has no metadata
- **AND** the single Google retry also fails transiently
- **THEN** the system SHALL continue to the existing downstream book providers
- **AND** SHALL NOT make another Google Books request during that lookup

### Requirement: Successful fallback preserves scanner behavior and provenance

The scanner preview SHALL return title, author, and source metadata from the provider that succeeded and SHALL record telemetry for the external lookup outcome.

#### Scenario: Fallback prevents unknown book card

- **WHEN** a user scans a valid book ISBN
- **AND** Google Books is temporarily unavailable
- **AND** Open Library returns title and author metadata
- **THEN** the scanner response SHALL include that title and author
- **AND** SHALL NOT display unknown title or unknown author

#### Scenario: Provider failures do not expose secrets

- **WHEN** an external book provider request fails
- **THEN** logs and telemetry SHALL NOT include the Google API key or request URL query parameters containing credentials

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
