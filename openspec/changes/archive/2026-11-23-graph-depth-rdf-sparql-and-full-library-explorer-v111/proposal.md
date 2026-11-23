## Why

The visual FRBR relation graph explorer (`/graph` and `GET /api/catalog/graph`) currently hard-caps neighborhood traversal at `depth <= 2` (`MAX_GRAPH_DEPTH = 2`), lacks an explicit edge-count ceiling (`max_edges`), executes unbatched per-node SQL queries inside `GraphService.build_neighborhood()`, and only renders when anchored to a single `work`, `expression`, `manifestation`, or `item`. As a result, collectors cannot inspect 3–4 hop FRBR/series/expansion/contributor connections or explore a filterable full-library concept graph across their catalog, while committing blindly to either an RDF/SPARQL-backed graph engine or extended SQL traversal without preview-database measurements risks latency spikes or OOM failures inside the 512 MB `sparql-runner` budget.

## What Changes

- **Depth 1–4 Neighborhood Traversal & Bounded Caps:** Extend `GET /api/catalog/graph`, `GraphService`, OpenAPI docs, and `/graph` from `depth` `1..2` to `1..4` with deterministic node (`max_nodes`) and edge (`max_edges`) caps, per-hop fairness/prioritization, truncation metadata, and radial SVG layout rings for `hop >= 3`.
- **Full-Library Concept Graph Explorer Mode:** Add a filterable full-library concept explorer mode accessible directly from `/graph` (and top-level navigation) without requiring a single entity anchor, supporting entity-type filters (`work`, `contributor`/`person`, `series`, `manifestation`, `item`, `expression`, `map`, `lod`) and edge-category filters (`frbr`, `series`, `parts_expansions`, `contributors`, `maps`, `lod`) within strict node/edge caps, multi-component deterministic layout packing, auto-fit zoom, and `CAPACITOR_BUILD=true` static-export compatibility.
- **Benchmark-Gated Query Backend Decision (Open):** Keep the query backend architecture (**Option A: Bounded SQL / Batched Frontier BFS / Recursive CTE** vs. **Option B: N+1-fixed, parity-completed RDF/SPARQL via `sparql_service`/`sparql-runner`** vs. **Option C: Hybrid**) explicitly open in `design.md`, gated by a mandatory prerequisite benchmark on the cloned preview PostgreSQL database before committing implementation.
- **Privacy, Consent & Read-Only Guard Parity:** Eliminate the existing per-item N+1 visibility/consent loop in `sparql_service.build_graph()`, align `FederationConsent.federated_collection == False` exclusion across graph and SPARQL projections, preserve three-tier `Item` visibility (`public`, `friends_only`, `private`, plus legacy `shared`) and `SemanticLink.status == "accepted"` filtering, and ensure read-only compatibility under `FEDERATION_HEAD_MODE=true`.
- **Clean Scope Boundaries with v1.1.2 Proposals:**
  - **Out of Scope (`C142`):** Decluttering `/item/[id]` and repositioning `"Explore Graph"` / `"Now Listening"` buttons on item detail pages belong to `C142` (`item-page-ux-declutter-and-graph-entry-v112`).
  - **Out of Scope (`C143`):** Extending anchored neighborhood `entity_type` roots (`VALID_GRAPH_ENTITY_TYPES` / `RECENTERABLE_TYPES`) to `person`/`contributor` and `series` and adding a dedicated multi-root autocomplete object picker belong to `C143` (`graph-multi-root-person-and-object-picker-v112`). `C140` keeps anchored `VALID_GRAPH_ENTITY_TYPES` at `("work", "expression", "manifestation", "item")` while exposing `contributor`/`person` and `series` in the unanchored full-library concept explorer.
  - **Out of Scope (`C144`):** Modeling or reconciling new cross-media `Work -> Work` adaptation/derivative links (`frbroo:R2_is_derivative_of`) belongs to `C144` (`cross-media-frbr-work-linking-reconciliation-v112`).

## Capabilities

### New Capabilities

_None — all behavioral changes extend existing graph exploration and SPARQL/federated access specifications._

### Modified Capabilities

- `visual-frbr-relation-graph`: Extend neighborhood graph traversal depth from `1..2` to `1..4`, enforce explicit `max_edges` alongside `max_nodes` with truncation metadata, add the full-library concept graph explorer endpoint/UI mode with entity-type filters and `hop >= 3` / multi-component layouts, and mandate preview-database performance benchmarking before locking the underlying query backend.
- `sparql-federated-access-rights`: Eliminate per-item N+1 visibility queries in `build_graph()`, enforce `FederationConsent.federated_collection` and three-tier `Item` visibility parity across SPARQL and graph projections, require RDF relation parity (`WorkExpansionLink`, `ContainerAggregation`, `Expression`-scoped accepted `SemanticLink`), and confirm read-only `FEDERATION_HEAD_MODE` compatibility.

## Impact

- **Backend (`app/`):** `app/core/graph_service.py`, `app/api/works.py`, `app/api/docs.py`, `app/core/sparql_service.py`, `app/api/sparql.py`, `app/core/frbr_service.py` (parity for RDF enrichment if benchmark selects Option B/C), and a new preview-DB benchmark harness script under `scripts/`.
- **Frontend (`frontend/`):** `frontend/app/graph/page.tsx`, `frontend/components/graph/frbr-relation-graph.tsx`, `frontend/components/dashboard/navbar.tsx`, `frontend/lib/api/hooks/catalog.ts`, `frontend/lib/api/hooks/query-keys.ts`, `frontend/types/frbr.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Testing & Ops:** `tests/test_catalog_graph_api.py`, `tests/test_sparql_performance.py`, `tests/test_sparql_federated_access.py`, `tests/test_federation_head_mode.py`, `frontend/__tests__/app/graph/page.test.tsx`, `frontend/__tests__/components/graph/frbr-relation-graph.test.tsx`, `frontend/__tests__/e2e/relation_graph.spec.ts`, and `CAPACITOR_BUILD=true` static export verification. No database schema migration is required unless benchmark findings dictate materialized/indexed support (which would follow the single-linear Alembic DAG rule).
