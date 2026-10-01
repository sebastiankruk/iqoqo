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
The system SHALL reconcile Work titles and Contributor names against DBpedia resources to establish canonical Linked Open Data URIs.

#### Scenario: Resolving a Work to its canonical DBpedia creative work entity

- **WHEN** the linking pipeline processes a Work with title and author metadata matching a DBpedia resource
- **THEN** the system associates the canonical DBpedia URI (e.g. `http://dbpedia.org/resource/...`) with the Work and records a confidence score.

#### Scenario: Resolving a Contributor to a DBpedia Person or Organization

- **WHEN** the linking pipeline resolves an author, artist, or publisher contributor
- **THEN** the system matches the entity against DBpedia foaf:Person or schema:Organization resources and stores the external URI.

#### Scenario: Disambiguating entities using catalog media context

- **WHEN** multiple candidate DBpedia resources match an entity title
- **THEN** the system uses media category (book, music album, board game) and publication year to filter and select the highest-confidence candidate.

### Requirement: WordNet Lexical Concept Linking
The system SHALL map genre, subject, and topical tags associated with catalog Works to formal WordNet synsets and lexical concepts.

#### Scenario: Linking catalog topic tags to WordNet synset URIs

- **WHEN** a Work contains recognized subject or genre tags
- **THEN** the system resolves the tags to canonical WordNet synset URIs (e.g. `http://wordnet-rdf.princeton.edu/id/...` or DBpedia WordNet synset URIs) and records the semantic association.

#### Scenario: Handling unrecognized or custom user tags

- **WHEN** a catalog tag cannot be mapped to any known WordNet synset
- **THEN** the system skips link creation for that tag and completes reconciliation for all other metadata attributes.

### Requirement: GeoNames Resolution for Publication Places
The system SHALL reconcile publication places and publisher locations associated with Manifestations against GeoNames geographic entities.

#### Scenario: Resolving publisher place of publication to a canonical GeoNames URI

- **WHEN** a Manifestation contains a publication place string (e.g., "London", "Warszawa", "New York")
- **THEN** the system queries the geographic authority, selects the primary administrative place, and links the canonical GeoNames URI (e.g. `https://sws.geonames.org/...`).

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
The system SHALL expose REST API endpoints allowing authenticated clients to query, trigger, and curate semantic links for catalog entities.

#### Scenario: Fetching semantic links for a manifestation

- **WHEN** an authenticated client issues a GET request to `/api/manifestations/<id>/semantic-links`
- **THEN** the system returns all associated external links categorized by authority (DBpedia, WordNet, GeoNames), target FRBR entity level, confidence score, and verification status with HTTP status 200.

#### Scenario: Triggering an on-demand re-linking task

- **WHEN** an authenticated client issues a POST request to `/api/manifestations/<id>/semantic-links/relink`
- **THEN** the system enqueues an asynchronous ETL task and returns HTTP status 202 Accepted with the background task ID.

#### Scenario: Deleting or overriding an incorrect semantic link

- **WHEN** an authorized user issues a DELETE request to `/api/manifestations/<id>/semantic-links/<link_id>`
- **THEN** the system removes the semantic link and returns HTTP status 204 No Content.

### Requirement: Manifestation Semantic Links UI
The system SHALL display an interactive Linked Open Data panel on manifestation detail pages presenting resolved external entities with visual indicators and direct outbound links.

#### Scenario: Viewing resolved semantic links on manifestation detail page

- **WHEN** a user navigates to a manifestation detail page that has resolved LOD links
- **THEN** the page displays a "Linked Open Data" section rendering distinct badges for DBpedia concepts, WordNet synsets, and GeoNames publisher locations with authority badges and external link icons.

#### Scenario: Opening external authority link in new tab with security attributes

- **WHEN** a user clicks on an external authority badge (such as a DBpedia or GeoNames link)
- **THEN** the browser opens the external URL in a new tab with `target="_blank"` and `rel="noopener noreferrer"` attributes.

#### Scenario: Displaying empty or loading state when no links exist

- **WHEN** a manifestation has no resolved external links and a background task is not active
- **THEN** the semantic links section displays a subtle empty state with an option to trigger background reconciliation.
