# semantic/data-export Specification

## Purpose

Enables users to export their complete personal library collection in canonical Linked Data (JSON-LD, RDF Turtle) and hierarchical JSON formats using chunked streaming and strict FRBR ontology mappings.

## Requirements

### Requirement: Authenticated Personal Collection Export Endpoint

The system MUST provide an authenticated HTTP GET endpoint at `/api/v1/items/export` that exports the authenticated user's library items and associated metadata. Unauthenticated requests MUST be rejected with HTTP 401 Unauthorized.

#### Scenario: Unauthenticated export request rejected

- **WHEN** an unauthenticated client sends a GET request to `/api/v1/items/export`
- **THEN** the server returns HTTP 401 Unauthorized and produces no export payload.

#### Scenario: Authenticated user requests personal library export

- **WHEN** an authenticated user sends a valid GET request to `/api/v1/items/export`
- **THEN** the server responds with HTTP 200 OK and streams only the items owned by or in the custody of the authenticated user.

### Requirement: Multi-Format Semantic Serialization

The export endpoint MUST support a `format` query parameter accepting `json-ld`, `turtle`, and `json`, defaulting to `json-ld` when unspecified. If an unsupported format is requested, the system MUST return HTTP 400 Bad Request with a descriptive error message.

#### Scenario: Exporting in JSON-LD format

- **WHEN** an authenticated user requests `/api/v1/items/export?format=json-ld`
- **THEN** the response `Content-Type` is `application/ld+json` and the body contains a valid JSON-LD document with `@context` and `@graph` representing the collection.

#### Scenario: Exporting in RDF Turtle format

- **WHEN** an authenticated user requests `/api/v1/items/export?format=turtle`
- **THEN** the response `Content-Type` is `text/turtle` and the body contains a valid RDF Turtle graph document.

#### Scenario: Exporting in standard JSON format

- **WHEN** an authenticated user requests `/api/v1/items/export?format=json`
- **THEN** the response `Content-Type` is `application/json` and the body contains a structured hierarchical JSON array of user items.

#### Scenario: Requesting unsupported export format

- **WHEN** an authenticated user requests `/api/v1/items/export?format=xml`
- **THEN** the server returns HTTP 400 Bad Request indicating `xml` is not a supported export format.

### Requirement: Canonical FRBR Hierarchy and Namespace Bindings

The exported semantic representations MUST preserve the complete FRBR Group 1 entity hierarchy without shortcuts: Item (F4) -> Manifestation (F3) -> Expression (F2) -> Work (F1). In JSON-LD exports, the top-level `@context` MUST include prefix bindings for FRBR (`http://purl.org/vocab/frbr/core#`), Schema.org (`https://schema.org/`), Dublin Core Terms (`http://purl.org/dc/terms/`), and iqoqo (`https://iqoqo.org/ontology#`). Physical attributes including `isbn13` MUST be bound exclusively to Manifestations, never to Works.

#### Scenario: Validating FRBR tier nesting and ISBN placement

- **WHEN** the export payload is generated for a book collection
- **THEN** each exported Item references its parent Manifestation, which references its parent Expression, which references its parent Work, and `isbn13` is located strictly on the Manifestation entity.

#### Scenario: Validating JSON-LD namespace bindings

- **WHEN** a JSON-LD export payload is parsed by a standard JSON-LD processor
- **THEN** the `@context` successfully resolves `frbr:Work`, `frbr:Expression`, `frbr:Manifestation`, `frbr:Item`, Schema.org terms, and Dublin Core terms without undefined prefix errors.

### Requirement: Chunked Streaming for Large Collections

The export endpoint MUST stream the response using chunked transfer encoding (`Transfer-Encoding: chunked`) to allow exporting arbitrarily large collections without server memory exhaustion or connection timeouts, accompanied by an `attachment` `Content-Disposition` header with a timestamped filename.

#### Scenario: Streaming response headers and filename disposition

- **WHEN** an export request is processed
- **THEN** the response headers include `Content-Disposition: attachment; filename="iqoqo-export-<timestamp>.<ext>"` and the body is delivered as a chunked stream.

#### Scenario: Large collection streaming without buffering entire payload

- **WHEN** a user with a large library (10,000+ items) initiates an export
- **THEN** the server begins streaming chunks immediately and completes the download without exceeding standard process memory limits.

### Requirement: User Profile Export Interface

The user profile page MUST provide an "Export Collection" section that allows users to select between JSON-LD, RDF Turtle, and standard JSON formats, initiates the streaming download upon action, and displays clear visual progress and toast notifications.

#### Scenario: Selecting format and downloading collection

- **WHEN** a user visits `/profile`, selects "JSON-LD (Canonical Linked Data)", and clicks the "Export Collection" button
- **THEN** the browser triggers a file download for the streaming export and displays a success notification upon stream initiation.

#### Scenario: Handling export download failure

- **WHEN** the export request fails due to a network or server error
- **THEN** the user interface displays an error notification describing the failure without crashing the profile view.
