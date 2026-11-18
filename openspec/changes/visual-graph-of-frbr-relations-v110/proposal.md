## Why

iqoqo models rich bibliographic and semantic graphs — four-tier FRBR hierarchies (`Work → Expression → Manifestation → Item`), `Series` (`WorkSeriesMembership`), container/box-set parts (`WorkPart`), board game expansions (`WorkExpansionLink`), contributors (`WorkContribution`), attached cartographic maps, and accepted Linked Open Data authorities (`SemanticLink`s to DBpedia, WordNet, GeoNames, OpenCollections). Currently users can only traverse these connections one link at a time across separate detail pages, with no visual graph view of how elements relate.

## What Changes

- **Backend Visibility-Safe Catalog Graph API (`GET /api/catalog/graph`)**:
  - Add a bounded neighborhood graph endpoint (`app/api/catalog.py` or `app/api/works.py`, documented in `app/api/docs.py`) accepting `entity_type` (`work | expression | manifestation | item`), `entity_id`, `depth` (`1` or `2`, clamped), and optional `edge_types` filter.
  - Return typed `nodes` (distinct IDs like `work:42`, `expression:10`, `manifestation:88`, `item:201`, `series:5`, `contributor:12`, `lod:dbpedia:...`, `map:...`) and typed `edges` (`realizes`, `embodies`, `exemplifies`, `in_series`, `has_part`, `is_expansion_of`, `contributed_by`, `has_map`, `same_as`), capped to `max_nodes <= 150` to prevent browser or server overload.
  - Enforce `Item` visibility isolation strictly: only include `Item` nodes visible to the caller (`public`, `friends_only` for authenticated accepted friends, `private` exclusively for the owner).
- **Dedicated Full-Screen `/graph` Explorer Page (`frontend/app/graph/page.tsx`)**:
  - Build a dedicated full-screen interactive graph explorer compatible with `CAPACITOR_BUILD=true` static export (resolving `?type=<entity_type>&id=<id>&depth=<1|2>` via `useSearchParams()` inside a `<Suspense>` boundary).
  - Render an interactive pan/zoom/drag 2D SVG/Canvas graph with zero heavy third-party lock-in (or lightweight deterministic force/radial layout), color-coded FRBR node badges, edge-type filter pills (`FRBR`, `Series`, `Parts & Expansions`, `Contributors`, `Maps`, `LOD`), node search/highlight, click-to-inspect side drawer (`"Recenter Graph on This Node"`, `"Open Entity Page"`), and full EN/PL localization.
- **Entity Page Entry Points (`"Explore Graph"`)**:
  - Add an `"Explore Graph"` button linking to `/graph?type=<entity_type>&id=<id>` on `/work/[id]`, `/expression/[id]`, `/manifestation/[id]`, and `/item/[id]` (`item-header.tsx` / `item-actions.tsx`).

## Capabilities

### New Capabilities
- `visual-frbr-relation-graph`: Bounded, visibility-respecting neighborhood graph API (`GET /api/catalog/graph`) and dedicated full-screen interactive `/graph` explorer reachable from Work, Expression, Manifestation, and Item pages.

### Modified Capabilities

## Impact

- **Backend (`app/`)**: `app/core/graph_service.py` (new), `app/api/works.py` (or `catalog` blueprint), `app/api/docs.py`.
- **Frontend (`frontend/`)**: `frontend/app/graph/page.tsx`, `frontend/components/graph/frbr-relation-graph.tsx`, `frontend/components/work/work-detail-client.tsx`, `frontend/components/expression/expression-detail-client.tsx`, `frontend/components/manifestation/manifestation-detail-client.tsx`, `frontend/components/item/item-header.tsx`, `frontend/lib/api/hooks/`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests (`tests/`, `frontend/__tests__/`)**: `tests/test_catalog_graph_api.py`, `tests/test_openapi_spec.py`, Vitest `/graph` tests, Playwright E2E `/work/[id]` → `/graph` navigation test.
