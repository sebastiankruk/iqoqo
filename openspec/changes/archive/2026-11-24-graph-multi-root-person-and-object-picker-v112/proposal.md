## Why

Currently, `/graph` and `GET /api/catalog/graph` only anchor on the four core FRBR Group 1 entities (`work`, `expression`, `manifestation`, `item`). Collectors cannot start graph exploration from a `Person` / `Contributor` (`F10_Person` / `F11_Corporate_Body`) or a `Series` (`Work` container), cannot recenter onto contributor nodes during traversal, and hit a passive dead-end card when opening `/graph` without query parameters.

## What Changes

- **Multi-Root `GraphService` & `GET /api/catalog/graph` (`app/core/graph_service.py`, `app/api/works.py`)**:
  - Extend `VALID_GRAPH_ENTITY_TYPES` to accept `person` (aliased with `contributor`) and `series` alongside `work`, `expression`, `manifestation`, and `item`.
  - Implement `_expand_contributor()` and `Contributor` anchor loading/serialization in `GraphService` so anchoring on a `person` or `contributor` (covering both `Contributor.type == "person"` and `"organization"`) traverses `WorkContribution`, `ExpressionContribution`, `ManifestationContribution`, and accepted `SemanticLink(entity_type="contributor")` edges, while also enqueuing hop-1 contributors for depth-2 traversal from other roots.
  - Resolve `series` roots via `Work` records tagged `work_kind == "series"` or referenced by `WorkSeriesMembership.series_work_id` / `WorkPart.container_work_id` onto canonical `work:<id>` nodes so series memberships expand without duplicating nodes.
- **Dedicated Visibility-Safe Root Picker Search API (`app/api/works.py`, `app/core/graph_service.py`)**:
  - Add `GET /api/catalog/graph/search` (`@optional_auth`, `@limiter.limit("60 per minute")`, SQL-`LIMIT`-clamped `1..25`) supporting diacritic-insensitive search across `person`/`contributor`, `series`, `work`, `expression`, `manifestation`, and `item`, enforcing strict three-tier `Item` visibility (`public`, `friends_only`, `private`) in SQL before `LIMIT` and remaining enabled in `FEDERATION_HEAD_MODE`.
  - Leave `READ_METADATA`-gated `/api/admin/frbr/search` and `/api/admin/works/search` untouched to preserve admin RBAC boundaries.
- **Interactive `/graph` Root Object Picker & Multi-Root Recentering (`frontend/app/graph/page.tsx`, `frontend/components/graph/`)**:
  - Build a keyboard-accessible `<GraphRootPicker />` (`role="combobox"` + `role="listbox"`) backed by `useCatalogGraphSearch` and render it inline in the `/graph` empty state (replacing the static dead-end prompt) plus via a single `"Switch Root"` dialog button in the active graph header (preserving `iqoqo-ux-auditor` button-density limits and keeping the 9-button canvas toolbar unchanged).
  - Expand `VALID_TYPES` and `RECENTERABLE_TYPES` to include `person`, `contributor`, and `series`, replace the hardcoded `/${rawType}/${rawId}` header link (`page.tsx:63`) with `anchorNode.url` (preventing 404s on `/person/<id>`, `/contributor/<id>`, `/series/<id>`), preserve `?type=&id=&depth=` routing for `CAPACITOR_BUILD=true` static export, and add sentence-case `en.json` / `pl.json` `graph.*` translation keys.
- **OpenAPI 3.1 Contract (`app/api/docs.py`)**:
  - Update `/api/catalog/graph` `entity_type` enum to include `person`, `contributor`, and `series`, and register `/api/catalog/graph/search` query parameters and schemas.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `visual-frbr-relation-graph`: Extend `GET /api/catalog/graph` and `/graph` to accept `person`/`contributor` and `series` roots, enable recentering onto `contributor`/`person` and `series` nodes, add the visibility-safe `GET /api/catalog/graph/search` endpoint, and provide the interactive `/graph` Root Object Picker UI (`C143`).

## Impact

- **Backend**: `app/core/graph_service.py`, `app/api/works.py`, `app/api/docs.py` (zero Alembic DB migrations required).
- **Frontend**: `frontend/app/graph/page.tsx`, `frontend/components/graph/frbr-relation-graph.tsx`, `frontend/components/graph/graph-root-picker.tsx` (new), `frontend/types/frbr.ts`, `frontend/lib/api/hooks/catalog.ts`, `frontend/lib/api/hooks/query-keys.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests**: `tests/test_catalog_graph_api.py`, `tests/test_openapi_contract_completeness.py`, `tests/test_api_admin.py` (regression), `frontend/__tests__/app/graph/page.test.tsx`, `frontend/__tests__/components/graph/graph-root-picker.test.tsx` (new), `frontend/__tests__/e2e/relation_graph.spec.ts`.
