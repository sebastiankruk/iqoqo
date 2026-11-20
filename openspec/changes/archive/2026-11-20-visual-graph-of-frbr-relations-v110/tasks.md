## 1. Backend Graph Service & API

- [x] 1.1 Implement `GraphService.build_neighborhood()` in `app/core/graph_service.py` traversing FRBR (`Work ↔ Expression ↔ Manifestation ↔ Item`), `Series` (`WorkSeriesMembership`), `WorkPart`, `WorkExpansionLink`, `WorkContribution` / `Contributor`, attached maps, and accepted `SemanticLink`s with `depth` clamped to `1..2`, node cap `<= 150` (`truncated` flag), and strict `Item` visibility enforcement (`public`, `friends_only` for friends, `private` for owner only)
- [x] 1.2 Expose `GET /api/catalog/graph` with `@optional_auth` and query validation (`entity_type`, `entity_id`, `depth`), document in `app/api/docs.py`, and add backend tests in `tests/test_catalog_graph_api.py` covering all relation types, depth/node clamping, and private-item isolation; verify via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_catalog_graph_api.py tests/test_openapi_spec.py`

## 2. Dedicated `/graph` Explorer & Entity Entry Buttons (Frontend)

- [x] 2.1 Add `useCatalogGraph(entityType, entityId, depth)` hook and TypeScript types (`GraphNode`, `GraphEdge`, `CatalogGraphResponse`) in `frontend/lib/api/hooks/catalog.ts` and `frontend/types/frbr.ts`
- [x] 2.2 Build `FRBRRelationGraph` interactive SVG pan/zoom/drag visualizer (`frontend/components/graph/frbr-relation-graph.tsx`) and dedicated full-screen `frontend/app/graph/page.tsx` (`<Suspense>` + `useSearchParams()` compatible with `CAPACITOR_BUILD=true`), with edge-type filter pills, depth toggle (`1` / `2` hops), node inspection side drawer (`"Recenter"` & `"Open Entity"`), truncation notice, and EN/PL strings in `frontend/messages/en.json` and `frontend/messages/pl.json`
- [x] 2.3 Add `"Explore Graph"` navigation buttons linking to `/graph?type=<type>&id=<id>` on `frontend/components/work/work-detail-client.tsx`, `frontend/components/expression/expression-detail-client.tsx`, `frontend/components/manifestation/manifestation-detail-client.tsx`, and `frontend/components/item/item-header.tsx`

## 3. Frontend & E2E Verification

- [x] 3.1 Add Vitest tests in `frontend/__tests__/app/graph/page.test.tsx` covering `/graph` rendering, edge filter toggles, node drawer inspection, and `"Explore Graph"` links, plus Playwright E2E navigation test (`/work/[id]` → `/graph`); verify via `cd frontend && npx vitest run __tests__/app/graph/` and `IQOQO_AI_MODE=1 make test-parallel`
