# ingestion-and-integrations Specification

## Purpose

Defines requirements for robust barcode scanning heuristics, server-side request forgery (SSRF) protections when downloading remote media assets, and consistent external taxonomy normalization.

## Requirements

### Requirement: Robust Barcode ISBN Disambiguation
The system SHALL evaluate barcode scanner input with correct boolean operator precedence, properly identifying 10-digit and 13-digit ISBN codes under all valid fallback conditions.

#### Scenario: Scanning physical book barcode

- **WHEN** a user scans a barcode containing a 13-digit EAN-13 book identifier
- **THEN** the ingestion strategy correctly recognizes the code as an ISBN and triggers bibliographic lookup

### Requirement: SSRF-Safe Remote Asset Downloading
The system SHALL route all external cover art downloads and media resource requests through an SSRF-hardened HTTP client that rejects private, loopback, and link-local IP addresses and restricts redirect hops.

#### Scenario: Ingesting manifestation cover from remote URL

- **WHEN** an external cover URL is supplied for download and caching
- **THEN** DNS resolution verifies the destination IP is public before connecting, aborting requests to private subnets (e.g. 10.0.0.0/8, 127.0.0.0/8, 169.254.169.254)

### Requirement: External Taxonomy Serialization Integrity
The system SHALL deserialize nested taxonomy structures from external providers accurately, preserving array structures without lossy unwrap operations.

#### Scenario: Loading board game mechanics in frontend

- **WHEN** board game taxonomy details are requested by the client
- **THEN** mechanics and categories are delivered as populated lists matching the stored database entities
