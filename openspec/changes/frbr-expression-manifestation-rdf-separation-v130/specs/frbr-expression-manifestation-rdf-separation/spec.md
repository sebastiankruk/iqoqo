# frbr-expression-manifestation-rdf-separation Specification

## Purpose

Enforce strict `F2_Expression` vs `F3_Manifestation` separation in RDF serialization, eliminate synthetic tier ID aliasing, and clean duplicated cross-tier ingestion metadata.

## ADDED Requirements

### Requirement: Expression Attributes Emitted Strictly on Expression IRIs

Language (`schema:inLanguage`), topic tags (`sioc:topic`), and concert performance event metadata (`schema:MusicEvent`, `schema:startDate`, `schema:location`, `schema:performer`) MUST be emitted on `e_uri` (`Expression`) rather than `m_uri` (`Manifestation`).

#### Scenario: Serializing a live-concert Manifestation and multi-language Expression

- **GIVEN** a `Work` with a live-concert `Expression` (`expression_kind="live_performance"`, `language="en"`, `tags=["rock"]`) and a Blu-ray `Manifestation`
- **WHEN** `build_collection_rdf_graph` serializes the graph
- **THEN** `schema:inLanguage`, `sioc:topic`, and `schema:MusicEvent` triples MUST use `<base_url>/expressions/<expr_id>` as subject and MUST NOT attach to `<base_url>/manifestations/<man_id>`

### Requirement: Complete Child Enrichment and Unique Tier IRIs

Work and Expression RDF exports MUST enrich child `Expression` and `Manifestation` entities and MUST NOT alias missing IDs across tiers (`expression_id = item_id` or `work_id = expression_id`).

#### Scenario: Serializing a Work node with child Manifestation enrichments

- **GIVEN** a `Work` passed into `_enrich_graph_from_db` with child `Expression`s and `Manifestation`s carrying `ImageScan` or audio metadata
- **WHEN** RDF serialization builds the full graph
- **THEN** `seen_expressions` and `seen_manifestations` MUST be populated so child `ImageScan`/audio/LOD enrichments are included and every tier uses distinct entity IDs
