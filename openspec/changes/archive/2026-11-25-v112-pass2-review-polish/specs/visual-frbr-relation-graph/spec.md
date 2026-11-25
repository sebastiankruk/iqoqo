## ADDED Requirements

### Requirement: Order-Independent Series/Work Deduplication in Graph Root Search and 7-Category Blueprint Documentation

When `GET /api/catalog/graph/search` is invoked with both `work` and `series` included in `types` in any order (for example `types=work,series` or `types=series,work`), `GraphService.search_root_candidates()` SHALL emit any matching series `Work` at most once (under `entity_type="series"`), never duplicating the same `Work.id` in the `work` bucket. Architecture Blueprint 8 (`docs/images/architecture/08-frbr-visual-relation-graph.svg` and `frontend/public/images/help/08-frbr-visual-relation-graph.svg`) SHALL accurately document all 7 cross-schema edge categories (including `"derivatives"`).

#### Scenario: Requesting types=work,series emits a matching Series Work only once

- **GIVEN** a `Work` with `work_kind="series"` titled `"Dune Chronicles"` and a regular `Work` titled `"Dune"`
- **WHEN** a caller requests `GET /api/catalog/graph/search?q=Dune&types=work,series&limit=10`
- **THEN** `"Dune Chronicles"` appears once with `entity_type="series"` and does NOT appear again under `entity_type="work"`, while `"Dune"` appears under `entity_type="work"`
