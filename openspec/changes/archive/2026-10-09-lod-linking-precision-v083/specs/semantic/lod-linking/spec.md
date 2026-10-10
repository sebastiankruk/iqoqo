## MODIFIED Requirements

### Requirement: DBpedia Entity Linking for Works and Contributors
The system SHALL reconcile Work titles and Contributor names against DBpedia resources using class-constrained candidate ranking and confidence scoring to prevent false-positive links.

#### Scenario: Resolving a Work to its canonical DBpedia creative work entity

- **WHEN** the linking pipeline processes a Work with title and author metadata matching a DBpedia resource
- **THEN** the system matches against candidate resources restricted to creative work ontology classes compatible with the expression content type
- **AND** the system calculates a composite confidence score incorporating label similarity, contributor corroboration, and candidate rank margin
- **AND** if the score meets or exceeds the auto-apply threshold, the link is created with status `accepted`, otherwise if meeting the suggestion threshold it is created with status `suggested`.

#### Scenario: Resolving a Contributor to a DBpedia Person or Organization

- **WHEN** the linking pipeline resolves an author, artist, or publisher contributor
- **THEN** the system restricts matches to DBpedia `foaf:Person` or `schema:Organization` resources and rejects non-agent entities.

#### Scenario: Disambiguating entities using catalog media context

- **WHEN** multiple candidate DBpedia resources match an entity title
- **THEN** the system uses media category (book, music album, board game), creator corroboration, and publication year to filter and rank candidates, rejecting disambiguation pages and list resources.

### Requirement: GeoNames Resolution for Publication Places
The system SHALL reconcile publication places and publisher locations associated with Manifestations against GeoNames geographic entities with feature-class restrictions to prevent non-place matches, prioritizing an offline-first local gazetteer database and gracefully falling back to remote services.

#### Scenario: Resolving publisher place of publication to a canonical GeoNames URI

- **WHEN** a Manifestation contains a publication place string (e.g., "London", "Warszawa", "New York")
- **THEN** the system queries GeoNames filtering by populated place feature classes (`P`), selects the canonical place matching country and admin bounds, and links the GeoNames URI.

#### Scenario: Fallback to remote GeoNames API when place is missing locally

- **WHEN** a publication place is not found in the local offline gazetteer and a valid GeoNames username is configured
- **THEN** the system queries the remote GeoNames web service API to resolve the canonical location and records the match.

#### Scenario: Graceful handling of unconfigured or failing remote GeoNames API

- **WHEN** a publication place is not in the local gazetteer and the remote GeoNames API returns an authorization error (HTTP 401 / code 10), times out, or lacks credentials
- **THEN** the system logs a diagnostic warning and continues reconciliation without raising an unhandled exception or corrupting catalog state.

#### Scenario: Preserving geographic metadata in external link attributes

- **WHEN** a GeoNames location is successfully resolved
- **THEN** the system records the GeoNames ID, canonical URI, country code, and geographic coordinates alongside the link reference.

### Requirement: Semantic Links Retrieval and Management API
The system SHALL expose REST API endpoints allowing authenticated clients to query, trigger, and curate semantic links for catalog entities, including link review status.

#### Scenario: Fetching semantic links for a manifestation

- **WHEN** an authenticated client issues a GET request to `/api/manifestations/<id>/semantic-links`
- **THEN** the system returns all associated external links categorized by authority (DBpedia, WordNet, GeoNames), target FRBR entity level, confidence score, verification status, and review status (`accepted`, `suggested`, `rejected`) with HTTP status 200.

#### Scenario: Triggering an on-demand re-linking task

- **WHEN** an authenticated client issues a POST request to `/api/manifestations/<id>/semantic-links/relink`
- **THEN** the system enqueues an asynchronous ETL task and returns HTTP status 202 Accepted with the background task ID.

#### Scenario: Deleting or overriding an incorrect semantic link

- **WHEN** an authorized user issues a DELETE request to `/api/manifestations/<id>/semantic-links/<link_id>`
- **THEN** the system marks the link as rejected or removes it, recording the decision in EntityAuditLog, and returns HTTP status 204 No Content.

#### Scenario: Accepting or rejecting a suggested semantic link

- **WHEN** an authorized user issues a PATCH request to `/api/manifestations/<id>/semantic-links/<link_id>` with `status="accepted"` or `status="rejected"`
- **THEN** the system updates the link status, records an audit event, and returns HTTP status 200 OK.
