## ADDED Requirements

### Requirement: Accepted Cross-Media Derivative Work Triples Serialization

`build_collection_rdf_graph()` (including ORM enrichment and dict-item enrichment) SHALL emit `frbroo:R2_is_derivative_of` and `schema:isBasedOn` triples for confirmed cross-media `Work -> Work` relations (`WorkRelation`), oriented strictly from the derived `Work` IRI to the source/original `Work` IRI, across Turtle, N-Triples, and JSON-LD exports. Unconfirmed (`pending`/`suggested`) and `dismissed` candidates MUST NOT be emitted into RDF or JSON-LD outputs.

#### Scenario: Serializing confirmed cross-media adaptation to RDF and JSON-LD

- **GIVEN** a collection containing an item whose `Work` is a film adaptation (`W_film`) linked via a confirmed `WorkRelation` to the source novel `Work` (`W_book`)
- **WHEN** `build_collection_rdf_graph()` and `serialize_collection_to_rdf()` export the collection in Turtle, N-Triples, or JSON-LD
- **THEN** the output RDF graph MUST contain `<W_film_iri> frbroo:R2_is_derivative_of <W_book_iri>` and `<W_film_iri> schema:isBasedOn <W_book_iri>` with bound `frbroo:` and `schema:` prefixes, and MUST NOT assert the inverse direction `<W_book_iri> frbroo:R2_is_derivative_of <W_film_iri>`.

#### Scenario: Suppressing pending and dismissed cross-media candidates in RDF exports

- **GIVEN** a `Work` referenced in an exported collection that only has `pending` or `dismissed` entries in `WorkLinkCandidate`
- **WHEN** `build_collection_rdf_graph()` constructs the export graph
- **THEN** no `frbroo:R2_is_derivative_of` or `schema:isBasedOn` triples SHALL be emitted for those unconfirmed or dismissed candidates.
