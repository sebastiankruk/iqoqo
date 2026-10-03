## ADDED Requirements

### Requirement: Bounded Public RDF Serialization

Public RDF serialization MUST validate and cap collection limits and MUST avoid materializing an unbounded public collection before beginning a streamed response.

#### Scenario: Excessive public RDF limit

- **WHEN** a public RDF request supplies a limit above the configured maximum
- **THEN** the server rejects it or clamps it to the documented maximum without loading more records than that maximum

#### Scenario: Invalid public RDF limit

- **WHEN** a public RDF request supplies a non-positive or malformed limit
- **THEN** the server returns a stable client error or applies the documented safe default

#### Scenario: Large streamed collection

- **WHEN** a public collection is requested with streaming enabled
- **THEN** database iteration and serialization remain bounded and the first response chunk can be emitted without first loading the complete collection

#### Scenario: Streamed JSON-LD response

- **WHEN** a client requests streamed JSON-LD
- **THEN** the complete response is one valid JSON-LD document, or the response explicitly uses a documented line-delimited JSON-LD media type

### Requirement: Visibility-Aware RDF Enrichment

Public RDF MUST include only metadata intentionally public for the requested profile, shared collection, or item; private user collection names, image scans, and inventory relationships MUST NOT be emitted by default.

#### Scenario: Public item belongs to private collection

- **WHEN** a public item is linked to a private user collection
- **THEN** public RDF omits the private collection resource and membership triples

#### Scenario: Public item has private image scans

- **WHEN** a public item has image scans that are not marked public
- **THEN** public RDF omits those scan paths

#### Scenario: Authenticated personal export

- **WHEN** the owner requests an authenticated data export
- **THEN** the export may include the owner’s explicitly exportable collection and scan metadata according to the export contract
