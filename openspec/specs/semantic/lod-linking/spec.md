# semantic/lod-linking Specification

## Purpose

Provides asynchronous background entity linking and ETL pipelines to resolve library catalog items to external Linked Open Data authorities (DBpedia, WordNet, and GeoNames) with FRBR-compliant relationship scoping and interactive manifestation detail UI.

## Requirements

### Requirement: Asynchronous LOD Reconciliation Pipeline
The system SHALL provide an asynchronous background pipeline that matches catalog entities against external Linked Open Data authorities without blocking user requests or API responses.

#### Scenario: Automatic background linking on manifestation creation

- **WHEN** a new Manifestation is created or enriched in the catalog
- **THEN** the system enqueues a background reconciliation task that resolves external links and persists matched LOD identifiers without delaying the creation response.

#### Scenario: On-demand collection batch reconciliation

- **WHEN** an authorized user triggers a semantic re-linking job for a collection or set of manifestations
- **THEN** the system schedules batch ETL worker tasks, applies external API rate limiting, and updates the task progress status.

#### Scenario: Graceful handling of external provider unavailability

- **WHEN** an external LOD authority (DBpedia, WordNet, or GeoNames) times out or returns an HTTP error during background reconciliation
- **THEN** the system logs the failure, leaves existing links intact, and marks the task for subsequent retry without corrupting catalog entity data.

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

### Requirement: WordNet Lexical Concept Linking
The system SHALL map genre, subject, and topical tags associated with catalog Works to formal WordNet synsets and lexical concepts.

#### Scenario: Linking catalog topic tags to WordNet synset URIs

- **WHEN** a Work contains recognized subject or genre tags
- **THEN** the system resolves the tags to canonical WordNet synset URIs (e.g. `http://wordnet-rdf.princeton.edu/id/...` or DBpedia WordNet synset URIs) and records the semantic association.

#### Scenario: Handling unrecognized or custom user tags

- **WHEN** a catalog tag cannot be mapped to any known WordNet synset
- **THEN** the system skips link creation for that tag and completes reconciliation for all other metadata attributes.

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

### Requirement: FRBR-Compliant Semantic Link Association and Scoping
The system MUST associate external semantic links strictly with their corresponding FRBR hierarchy level according to bibliographic ontology rules.

#### Scenario: Associating author and subject concepts with Work entities

- **WHEN** external links for creative concepts, themes, or intellectual authorship are resolved
- **THEN** the system associates these links directly with the Work (F1) or Contributor, never with an Item (F4).

#### Scenario: Associating publication and edition data with Manifestation entities

- **WHEN** external links for publisher locations, physical formats, or edition identifiers (ISBN, OCLC) are resolved
- **THEN** the system associates these links with the Manifestation (F3), never promoting edition-specific attributes to the Work (F1).

#### Scenario: Preserving Item separation from abstract catalog semantics

- **WHEN** semantic linking tasks execute
- **THEN** physical or digital Item copies (F4) remain separate from abstract LOD links, inheriting catalog semantics via their parent Manifestation.

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

### Requirement: Manifestation Semantic Links UI
The system SHALL display an interactive Linked Open Data panel on manifestation detail pages and item detail views presenting resolved external entities with visual indicators, responsive action controls, and direct outbound links.

#### Scenario: Viewing resolved semantic links on manifestation detail page

- **WHEN** a user navigates to a manifestation detail page that has resolved LOD links
- **THEN** the page displays a "Linked Open Data" section rendering distinct badges for DBpedia concepts, WordNet synsets, and GeoNames publisher locations with authority badges and external link icons.

#### Scenario: Opening external authority link in new tab with security attributes

- **WHEN** a user clicks on an external authority badge (such as a DBpedia or GeoNames link)
- **THEN** the browser opens the external URL in a new tab with `target="_blank"` and `rel="noopener noreferrer"` attributes.

#### Scenario: Displaying empty or loading state when no links exist

- **WHEN** a manifestation has no resolved external links and a background task is not active
- **THEN** the semantic links section displays a subtle empty state with an option to trigger background reconciliation.

#### Scenario: Responsive scan button containment across screen sizes

- **WHEN** a user views the Linked Open Data card on a mobile or narrow display, or under languages with long localized scan button labels
- **THEN** the card header uses a responsive wrapping layout preventing button bounds from overflowing or breaking out of the container card frame
- **AND** the button label truncates safely while preserving full tooltip title information.

#### Scenario: Inspecting inherited semantic links on item detail views

- **WHEN** a user navigates to an Item holding detail page whose parent Manifestation has resolved or pending semantic links
- **THEN** the item view renders the Linked Open Data card displaying inherited links and providing an accessible trigger to run LOD reconciliation directly.
