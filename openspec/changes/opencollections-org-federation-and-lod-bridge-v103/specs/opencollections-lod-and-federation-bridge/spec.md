## Purpose

Provide SSRF-safe metadata harvesting, FRBR four-tier normalization, and JSON-LD/RDF Linked Open Data interoperability with `opencollections.org`.

## ADDED Requirements

### Requirement: SSRF-Safe OpenCollections Lookup & FRBR Normalization
The system SHALL provide an `OpenCollectionsLookupStrategy` (`app/strategies/opencollections.py` and `app/utils/opencollections.py`) that queries `opencollections.org` via the SSRF-safe `http_client`, records outbound provider telemetry, and maps returned records into FRBR `Work`, `Expression`, and `Manifestation` entities with `_provenance` and `lod_links.opencollections_uri`.

#### Scenario: Custodian enriches a Work/Manifestation from OpenCollections
- **GIVEN** an authenticated custodian or lookup request querying an identifier or title via `OpenCollectionsLookupStrategy`
- **WHEN** `opencollections.org` returns a matching bibliographic/cultural record
- **THEN** the strategy normalizes creators, title, publication date, and `opencollections_uri` into the FRBR hierarchy and records `"opencollections"` provenance without creating fake identifiers on failure.

### Requirement: JSON-LD Shared Collection & Manifestation Cross-Linking
The Linked Open Data endpoints (`/api/lod/manifestations/<id>` and `/api/lod/collections/<token>`) SHALL include `opencollections_uri` in `owl:sameAs` / `rdfs:seeAlso` triples when present on the entity's `lod_links`.

#### Scenario: JSON-LD export includes OpenCollections URI
- **GIVEN** a `Manifestation` or `Work` linked to an `opencollections.org` URI in `meta["lod_links"]["opencollections_uri"]`
- **WHEN** a client requests `GET /api/lod/manifestations/<id>` with `Accept: application/ld+json`
- **THEN** the JSON-LD graph includes the `opencollections.org` IRI in `sameAs`.
