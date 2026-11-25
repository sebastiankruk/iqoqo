## ADDED Requirements

### Requirement: Full-Library Derivative Edges, Balanced Root Picker Quotas, and Bounded Work Relation Expansion

`GraphService` and `GET /api/catalog/graph/search` SHALL maintain full edge-category parity between neighborhood and library modes, fair multi-entity candidate representation, and bounded SQL/input limits:

1. **Full-Library `"derivatives"` Edges (`app/core/graph_service.py`):** When `build_library_graph()` runs with `"derivatives"` in `allowed_categories` and at least two `Work` nodes (`work` or `series`) are present, it MUST query `WorkRelation` rows where both `source_work_id` and `target_work_id` belong to `present_work_ids` (bounded by `effective_max_edges`) and emit directed `category="derivatives"` edges (`work_rel.relation_type`), strictly excluding `WorkLinkCandidate` rows.
2. **Balanced Per-Type Quotas, `series` Deduplication & `person` Type Filtering in `search_root_candidates()` (`app/core/graph_service.py`):** When multiple entity types are requested on `GET /api/catalog/graph/search`, `search_root_candidates()` MUST allocate a fair per-type quota (`max(1, effective_limit // len(requested))`) per requested type before backfilling unused slots up to `effective_limit` so abundant `Contributor` matches never starve `series`, `work`, `expression`, `manifestation`, or `item` matches; MUST exclude `Work` IDs already emitted as `entity_type="series"` from also appearing as `entity_type="work"` in the same response; and when `person` is requested without `contributor`, MUST filter `Contributor` rows to `Contributor.type == "person"` (or `Contributor.type.is_(None)`).
3. **Bounded `_expand_work()` Relation Queries & Query-String Length Cap (`app/core/graph_service.py`, `app/api/works.py`):** `_expand_work()` MUST apply `.limit(MAX_GRAPH_NODES)` to `WorkRelation` queries, and `GET /api/catalog/graph/search` MUST cap or reject `q` strings exceeding `200` characters before constructing SQL `LIKE` patterns.

#### Scenario: Full-library graph mode includes accepted cross-media WorkRelation derivative edges

- **GIVEN** two visible `Work` nodes `W_book` and `W_film` connected by `WorkRelation(source_work_id=W_film.id, target_work_id=W_book.id, relation_type="is_adaptation_of")` plus a `pending` `WorkLinkCandidate` to `W_game`
- **WHEN** a caller requests `GET /api/catalog/graph?mode=library` with `"derivatives"` enabled
- **THEN** the library graph response includes the `"derivatives"` edge (`is_adaptation_of`) between `work:<W_film>` and `work:<W_book>` and omits any edge from the `pending` `WorkLinkCandidate`

#### Scenario: Multi-type graph root search preserves fair per-type quotas, person-only filtering, and series deduplication

- **GIVEN** 30 `Contributor` rows (`25` `"person"` and `5` `"organization"`) matching `" Tolkien "`, `1` `Series` `Work` (`work_kind="series"`) matching `"Tolkien"`, and `2` regular `Work` rows matching `"Tolkien"`
- **WHEN** a caller requests `GET /api/catalog/graph/search?q=Tolkien&types=person,series,work&limit=12`
- **THEN** the response includes matching `person`, `series`, and `work` candidates (never starved by 12 `person` rows), excludes `"organization"` `Contributor` rows from `person` results, and emits the series `Work` only once under `entity_type="series"` (not duplicated under `entity_type="work"`)
