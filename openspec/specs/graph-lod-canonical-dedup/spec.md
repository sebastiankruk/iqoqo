# graph-lod-canonical-dedup Specification

## Purpose
Guarantee that Linked Open Data (`SemanticLink`) nodes in `GraphService` are deduplicated by canonical external URI across both bounded BFS and full-library graph modes, including `Person`/`Contributor` anchors.

## Requirements

### Requirement: Canonical LOD Node Deduplication by Normalized URI

`GraphService` MUST key LOD graph nodes by normalized `external_uri` rather than `SemanticLink.id` so duplicate `SemanticLink` rows or URI scheme/trailing-slash variants collapse into a single canonical LOD node.

#### Scenario: Person graph with duplicate LOD SemanticLink rows

- **GIVEN** a `Contributor` (e.g., `"Stephen King"`) with multiple accepted `SemanticLink` rows referencing `http://dbpedia.org/resource/Stephen_King` and `https://dbpedia.org/resource/Stephen_King/` (and/or linked works referencing the same URI)
- **WHEN** `GET /api/catalog/graph?entity_type=person&entity_id=<id>` is requested
- **THEN** the response MUST contain exactly one `entity_type: "lod"` node for that canonical URI
- **AND** `edges` MUST contain at most one `same_as` edge between any `(source, target)` pair

### Requirement: Full-Library Contributor LOD Anchor Inclusion

Full-library graph generation MUST include `contributor` `SemanticLink` anchors alongside `work`, `expression`, and `manifestation` anchors.

#### Scenario: Full-library graph includes Person LOD links

- **GIVEN** a library containing a `Contributor` node with an accepted `SemanticLink` (`entity_type="contributor"`)
- **WHEN** `GET /api/catalog/graph?mode=library` is requested with `lod` entity/edge filters enabled
- **THEN** the contributor's canonical LOD node and `same_as` edge MUST be included in the full-library anchor pass
