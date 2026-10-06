# board-game-ingestion Specification

## Purpose

Define BoardGameGeek metadata ingestion: authenticated attribution-aware fetching, the requirement that a BGG failure never aborts the rest of a record's metadata, and cleaning of user-supplied search text before it reaches the upstream API.

## Requirements

### Requirement: BoardGameGeek metadata is fetched with explicit attribution

BoardGameGeek metadata MUST be fetched over the API with the configured token as a
request header, and every stored record MUST carry attribution naming BoardGameGeek
as its source.

#### Scenario: Metadata is fetched for a title

- **WHEN** BGG metadata is requested for a title and the API responds
- **THEN** the configured API token is sent as a request header
- **AND** the fetched record is attributed to BoardGameGeek

#### Scenario: No BGG token is configured

- **WHEN** BGG metadata is requested and no token is configured
- **THEN** the lookup does not proceed
- **AND** ingestion degrades to the other metadata providers rather than failing
  the whole operation

### Requirement: Ingestion falls back rather than failing the record

A BGG lookup failure MUST NOT abort ingestion of the rest of a record's metadata.
The failure is confined to the BGG tier.

#### Scenario: BoardGameGeek is unreachable

- **WHEN** the BGG request fails or times out
- **THEN** the other provider tiers still populate the record
- **AND** the failure is logged with the identifier it affected

#### Scenario: BoardGameGeek returns no match

- **WHEN** the BGG lookup returns nothing for a title
- **THEN** no BGG fields are written
- **AND** the record is still created from the other providers

### Requirement: User-supplied search text is cleaned before being sent upstream

A search term MUST be cleaned before being used as an upstream query, so
whitespace and control characters cannot produce a malformed request URL.

#### Scenario: A user searches with padded whitespace

- **WHEN** a BGG search term contains leading or trailing whitespace
- **THEN** the term is trimmed before it is sent upstream

#### Scenario: A title contains characters that must be URL-encoded

- **WHEN** a search term contains reserved characters
- **THEN** it is encoded before being placed in the request URL
