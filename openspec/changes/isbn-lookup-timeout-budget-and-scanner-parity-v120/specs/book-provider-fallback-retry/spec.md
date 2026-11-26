## MODIFIED Requirements

### Requirement: Multi-Provider Metadata and Cover Gap Filling

The system SHALL query secondary configured metadata providers using the canonical item identifier to populate missing cover images and bibliographic fields when the primary provider result contains gaps. Optional secondary gap-filling requests SHALL execute without HTTP retries (`max_retries=0`) and SHALL be skipped when remaining wall-clock budget is below the minimum viable threshold.

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
- **AND** the combined lookup duration reaches the global timeout threshold (6.0 seconds) or remaining budget is below the minimum viable threshold
- **THEN** the system SHALL skip or abort pending secondary provider queries without HTTP retries and return the primary metadata result without failing the lookup.

## ADDED Requirements

### Requirement: Minimum Viable Timeout Floor and Polish BN Budget Reservation

The ISBN lookup orchestrator SHALL enforce a minimum viable per-request timeout floor so external providers are never queried with sub-viable read timeouts (such as 0.2s), and SHALL reserve viable budget for Biblioteka Narodowa when resolving Polish ISBNs (`97883` or `97983`) after primary provider failure or no-result.

#### Scenario: Sub-viable remaining budget skips optional enrichment

- **WHEN** a primary provider already resolved metadata for an ISBN
- **AND** remaining wall-clock budget is insufficient for a minimum viable secondary request
- **THEN** the system SHALL return the primary metadata immediately instead of issuing a guaranteed-to-timeout enrichment request.

#### Scenario: Polish ISBN fallback reserves viable budget for Biblioteka Narodowa

- **WHEN** a Polish ISBN (`97883...` or `97983...`) receives no result or a transient failure from Google Books
- **THEN** Open Library fallback SHALL NOT exhaust the entire wall-clock budget across multi-attempt HTTP retries
- **AND** Biblioteka Narodowa (`data.bn.org.pl` / `katalogi.bn.org.pl`) SHALL receive a viable read timeout floor of at least 1.5 seconds.
