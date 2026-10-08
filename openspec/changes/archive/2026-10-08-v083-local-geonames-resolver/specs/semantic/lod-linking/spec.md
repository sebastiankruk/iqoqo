## MODIFIED Requirements

### Requirement: GeoNames Resolution for Publication Places
The system SHALL reconcile publication places and publisher locations associated with Manifestations against GeoNames geographic entities, prioritizing an offline-first local gazetteer database and gracefully falling back to remote services.

#### Scenario: Resolving publisher place of publication to a canonical GeoNames URI

- **WHEN** a Manifestation contains a publication place string (e.g., "London", "Warszawa", "New York")
- **THEN** the system queries the geographic authority (prioritizing the local offline GeoNames gazetteer database and falling back to remote web services when configured), selects the primary administrative place, and links the canonical GeoNames URI (e.g. `https://sws.geonames.org/{geonameId}/`).

#### Scenario: Fallback to remote GeoNames API when place is missing locally

- **WHEN** a publication place is not found in the local offline gazetteer and a valid GeoNames username is configured
- **THEN** the system queries the remote GeoNames web service API to resolve the canonical location and records the match.

#### Scenario: Graceful handling of unconfigured or failing remote GeoNames API

- **WHEN** a publication place is not in the local gazetteer and the remote GeoNames API returns an authorization error (HTTP 401 / code 10), times out, or lacks credentials
- **THEN** the system logs a diagnostic warning and continues reconciliation without raising an unhandled exception or corrupting catalog state.

#### Scenario: Preserving geographic metadata in external link attributes

- **WHEN** a GeoNames location is successfully resolved
- **THEN** the system records the GeoNames ID, canonical URI, country code, and geographic coordinates alongside the link reference.
