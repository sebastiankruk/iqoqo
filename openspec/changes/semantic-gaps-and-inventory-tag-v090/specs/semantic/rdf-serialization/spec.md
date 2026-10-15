## ADDED Requirements

### Requirement: External LOD Semantic Link Triples Serialization

The system SHALL serialize verified and accepted external Linked Open Data links (`SemanticLink` records with `status == 'accepted'`) as `owl:sameAs` and `schema:sameAs` triples connecting the internal entity IRI to external authority URIs (such as DBpedia, GeoNames, and WordNet) across public entity endpoints and collection RDF graphs.

#### Scenario: Serializing accepted manifestation external links
- **WHEN** a manifestation has an accepted semantic link pointing to a DBpedia resource
- **THEN** the serialized RDF graph contains `owl:sameAs` and `schema:sameAs` triples linking the manifestation IRI to the DBpedia URI.

#### Scenario: Excluding unverified or rejected links
- **WHEN** an entity has semantic links with status `suggested` or `rejected`
- **THEN** the output RDF graph does not emit `owl:sameAs` or `schema:sameAs` assertions for those unverified or rejected URIs.

#### Scenario: Serializing work-tier external links
- **WHEN** a work has an accepted semantic link to an external authority
- **THEN** the output RDF graph asserts `owl:sameAs` and `schema:sameAs` triples between the work IRI and the external resource URI.

### Requirement: Work Series Membership Serialization

The system SHALL serialize Work series memberships (`WorkSeriesMembership`) into RDF graphs, linking the member Work to the series Work container using `schema:partOfSeries` and annotating the sequential ordinal position using `schema:position`.

#### Scenario: Serializing work with series membership
- **WHEN** a Work belongs to a series with sequence number 3
- **THEN** the serialized RDF graph contains a `schema:partOfSeries` assertion referencing the series Work IRI, and asserts `schema:position` with value 3.

#### Scenario: Serializing work without series membership
- **WHEN** a Work does not belong to any series
- **THEN** the output graph does not emit `schema:partOfSeries` properties for that Work.
