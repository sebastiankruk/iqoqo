## Context

See `proposal.md` for motivation and scope. Current codebase inspection establishes several concrete structural and operational constraints across the graph explorer, SPARQL stack, and frontend visualization:

1. **Graph Traversal & Bounds (`app/core/graph_service.py`, `app/api/works.py`, `app/api/docs.py`):**
   - `GET /api/catalog/graph` (`@limiter.limit("60 per minute")`, `@optional_auth`) currently anchors exclusively on `VALID_GRAPH_ENTITY_TYPES = ("work", "expression", "manifestation", "item")` and delegates to `GraphService.build_neighborhood()`.
   - `MAX_GRAPH_DEPTH = 2` and `MAX_GRAPH_NODES = 150` are enforced; there is **no `MAX_GRAPH_EDGES` cap** (`add_edge()` deduplicates only on `(source, target, relation)`).
   - `build_neighborhood()` executes per-node SQL queries inside a Python `deque` BFS loop (up to **12 SQL queries per `Work`**, 5 per `Expression`, 5 per `Manifestation`, 3 per `Item`). At `depth = 3` or `4`, sequential roundtrips grow $O(V)$, and greedy FIFO `try_add_node()` exhaustion can fill all 150 slots on a single prolific serial `Work` or large `Series` at hop 1–2, starving hops 3–4.
   - `GraphService.is_item_visible_to_viewer()` checks `public`, `friends_only`, legacy `shared`, and `private`/`is_hidden`, and `_add_semantic_links()` filters `SemanticLink.status == "accepted"`. However, `GraphService` does **not** yet check `FederationConsent.federated_collection == False` for public non-owner/non-friend queries (unlike `_get_sparql_items()` and `is_item_publicly_visible()`).

2. **RDF / SPARQL Infrastructure & Constraints (`app/core/sparql_service.py`, `app/api/sparql.py`, `app/services/sparql/*`, `app/core/frbr_service.py`):**
   - `/api/sparql` requires `@require_auth`, `READ_METADATA`, and `@limiter.limit("10 per minute")`.
   - `sparql_service.py` enforces `MAX_QUERY_LENGTH = 10240` (10 KB), `QUERY_TIMEOUT = 15s`, `MAX_RESULT_ROWS = 1000`, `MAX_GRAPH_ITEMS = 5000`, `MAX_GRAPH_WORKS = 10000`, `MAX_GRAPH_TRIPLES = 200000`, `MAX_CONCURRENT_QUERIES = 4`, and `MAX_SERIALIZED_BYTES = 10 MB`.
   - `sparql-runner` (`app/services/sparql/protocol.py`, `server.py`, `worker.py`, `docs/SPARQL_EXECUTION_SERVICE.md`) runs with `MAX_SNAPSHOT_BYTES = 10 MB`, `DEFAULT_MAX_CONCURRENCY = 4`, `DEFAULT_MAX_QUEUE_DEPTH = 16`, `RLIMIT_AS = 2 GB` inside the worker, and container cgroup limits of **`1.0 CPU`, `512 MB RAM`, `64 PIDs`** (following the prior Fuseki ADR rejecting JVM triplestores due to Oracle Cloud Free Tier memory limits).
   - **Verified N+1 Defect:** `sparql_service.build_graph()` currently loops over `items` calling `is_friend_of()` and `is_item_publicly_visible()` per item (causing up to `5,000–10,000` extra SQL queries), and `build_graph(items=None)` omits `friends_only` and `FederationConsent` filters.
   - **Verified RDF Parity Gaps:** `frbr_service._enrich_graph_from_db()` emits `WorkContribution`, `ExpressionContribution`, `ManifestationContribution`, `WorkPart`, `WorkSeriesMembership`, and `SemanticLink` (`work`, `manifestation` with `status == "accepted"`), but **omits** `WorkExpansionLink`, `ContainerAggregation`, `Expression`-scoped `SemanticLink`s, and stable addressable `MapAttachment` IRIs (currently `BNode()`).

3. **Frontend & Capacitor Static Export (`frontend/app/graph/page.tsx`, `frontend/components/graph/frbr-relation-graph.tsx`, `frontend/next.config.ts`):**
   - `page.tsx` clamps `depth` to `1 | 2` and shows a `missingParamsTitle` empty state when `type`/`id` are omitted.
   - `computeRadialLayout()` handles `hop = 0, 1, 2` only; any `hop >= 3` node falls back to `{ x: 0, y: 0 }` and collapses onto the anchor.
   - `FRBRRelationGraph` assumes a non-null `graph.anchor.node_id` and filters `visibleNodes` by edge connectivity from the anchor, dropping isolated matching nodes.
   - `CAPACITOR_BUILD=true` triggers `output: "export"`, prohibiting un-prerenderable dynamic path segments.

## Goals / Non-Goals

**Goals:**
- Support bounded `depth` `1..4` neighborhood traversal and a filterable full-library concept graph explorer mode behind a clean, backend-agnostic `GraphService` contract.
- Enforce explicit `max_nodes` and `max_edges` caps, per-hop fairness/prioritization, rate limits, and query timeouts across all query paths.
- Keep the query backend choice (**Option A: Bounded SQL / Batched Frontier BFS / Recursive CTE** vs. **Option B: RDF/SPARQL** vs. **Option C: Hybrid**) explicitly **OPEN** until empirical benchmarking on the cloned preview PostgreSQL database completes.
- Guarantee strict FRBR 4-tier purity, three-tier `Item` visibility, `FederationConsent` parity, `SemanticLink.status == "accepted"` filtering, and `FEDERATION_HEAD_MODE=true` read-only compatibility.
- Deliver a `hop >= 3` radial layout, multi-component full-library packing, auto-fit zoom, compact toolbar density (`<= 4` visible buttons per control group), and Capacitor static-export safety.

**Non-Goals:**
- Committing upfront to SQL vs. RDF/SPARQL before running the preview-DB benchmark gate.
- Decluttering `/item/[id]` or relocating item-page buttons (`C142`).
- Adding `person`/`contributor` or `series` as anchored neighborhood root `entity_type`s or building the multi-root autocomplete object picker (`C143`).
- Creating or reconciling new cross-media `Work -> Work` adaptation links (`C144`).

## Decisions

### Decision 1: Query Backend Architecture (EXPLICITLY OPEN Pending Preview-DB Benchmark)

All candidate backends MUST implement a shared `GraphQueryBackend` / `GraphService` interface returning the canonical `{ anchor, mode, nodes, edges, meta }` payload with identical FRBR semantics, visibility/`FederationConsent` filtering, `SemanticLink.status == "accepted"`, `max_nodes`/`max_edges` bounds, and `429`/`503`/`504` safety. **No backend option is pre-selected in this design; selection is gated by Task 1 (Preview-DB Performance Benchmark).**

- **Option A — Bounded SQL / Batched Frontier BFS / PostgreSQL Recursive CTE:**
  - *How it works:* Refactor `GraphService.build_neighborhood()` from per-node queries to batched frontier `IN (...)` queries per hop (plus optional `WITH RECURSIVE` CTEs for transitive `WorkPart`/`WorkSeriesMembership`/`WorkExpansionLink` chains) with per-hop node/edge quotas, and add a batched SQL overview query for `mode=library` pushing visibility (`public`, `friends_only`, `private`), `FederationConsent`, and `SemanticLink.status == "accepted"` directly into SQL `WHERE` clauses.
  - *Pros:* Lowest baseline latency and memory overhead; avoids serializing/re-parsing `rdflib.Graph` and `10 MB` N-Triples IPC; naturally supports `@optional_auth` (`60/min`) and SQL `LIMIT`/`OFFSET`/keyset ranking without hitting `200k` triple ceilings or the `512 MB` `sparql-runner` cgroup cap.
  - *Cons:* Requires procedural batching logic per SQLAlchemy relationship table and careful dialect parity between PostgreSQL (preview/prod) and SQLite (unit tests).

- **Option B — N+1-Fixed, Parity-Completed RDF / SPARQL Projection (`sparql_service` / `sparql-runner`):**
  - *How it works:* Fix the per-item `is_friend_of` / `is_item_publicly_visible` N+1 loop in `sparql_service.build_graph()`, close RDF emission gaps in `frbr_service._enrich_graph_from_db()` (`WorkExpansionLink`, `ContainerAggregation`, `Expression`-scoped `SemanticLink`s, stable map IDs), and execute SPARQL `CONSTRUCT`/`SELECT` property-path queries (depth `1..4` and full-library filtered concept queries) via `sparql-runner` (or scoped/cached RDF graphs), projecting bindings back to graph JSON.
  - *Pros:* Declarative semantic traversal aligned with FRBRoo/RDF/LOD; property paths (`{1,4}`) express heterogeneous multi-hop relations concisely as new predicates (such as `C144` links) are added.
  - *Cons:* High per-request cost if rebuilding `rdflib.Graph` (up to `5,000` items / `10,000` works / `200,000` triples), N-Triples serialization (`<= 10 MB`), and re-parsing inside the `512 MB` `sparql-runner` container (`MAX_CONCURRENT_QUERIES = 4`, `QUERY_TIMEOUT = 15s`). Caching snapshots introduces complex invalidation keys across `(viewer_user_id, friend_ids, FederationConsent, Item.visibility)`. Also `/api/sparql` currently enforces `@require_auth` + `READ_METADATA` + `10/min`, whereas `/graph` supports `@optional_auth` + `60/min`.

- **Option C — Hybrid (Batched SQL / CTE Explorer + Scoped RDF/SPARQL):**
  - *How it works:* Use Option A's batched SQL / frontier-capped BFS for latency-sensitive interactive `/api/catalog/graph` (depth `1..4` and full-library concept explorer under `@optional_auth` / `60/min`), while fixing `build_graph()` N+1 and `_enrich_graph_from_db()` relation parity so `sparql_service`/`sparql-runner` (or SQL-pre-scoped subgraphs) serves declarative SPARQL exploration, LOD export, and optional `"View as SPARQL"` / RDF projections cleanly.
  - *Pros:* Delivers sub-second interactive UI performance within strict `512 MB` `sparql-runner` bounds while resolving the SPARQL N+1 and RDF parity debt cleanly.
  - *Cons:* Maintains two query projections (SQL graph JSON and RDF graph builder), requiring automated parity tests to ensure zero divergence in nodes, edges, visibility, or `FederationConsent`.

- **Benchmark Selection Rule (Task 1 Gate — RECORDED 2026-11-22):**
  - Ran `scripts/benchmark_graph_backends.py --scale-seed --iterations 3` (`400` works, `400` expressions, `800` manifestations, `800` items, `40` contributors, `90` series memberships, `40` work parts, `30` semantic links):
    - **Option B (RDF/SPARQL `build_graph()` + `rdflib`):** `11,600` triples (`1.32 MB` N-Triples); `depth=1 p95=1626.36 ms`, `depth=2 p95=2061.06 ms`, `depth=3 p95=3741.62 ms`, `depth=4 p95=15053.89 ms` (breaches `<= 300 ms` / `<= 800 ms` gates and hits `15s` `QUERY_TIMEOUT` at depth 4). **Rejected for interactive `/api/catalog/graph`.**
    - **Baseline unbatched SQL `GraphService`:** `depth=1 p95=111.04 ms (58 SQL)`, `depth=2 p95=966.38 ms (1,779 SQL)`, proving per-node queries must be replaced with **batched frontier `IN (...)` BFS**.
  - **LOCKED DECISION: Option C (Hybrid) Selected** — Use **Batched SQL Frontier BFS** in `GraphService` for interactive `/api/catalog/graph` (`depth 1..4` and `mode=library` with calibrated defaults `MAX_GRAPH_DEPTH=4`, `MAX_GRAPH_NODES=150`, `MAX_GRAPH_EDGES=400`), while fixing `sparql_service.build_graph()` N+1 and `frbr_service._enrich_graph_from_db()` RDF relation parity for `/api/sparql` and LOD exports.

### Decision 2: Bounding Caps, Edge Limits, and Non-Starving Hop Fairness

- **Choice:** Introduce `MAX_GRAPH_DEPTH = 4` and an explicit `MAX_GRAPH_EDGES` cap (calibrated during Task 1, targeting e.g. `max_nodes <= 150..250`, `max_edges <= 400..600` configurable via query params clamped to server ceilings). Replace greedy FIFO exhaustion with **level-by-level frontier expansion** and per-parent fan-out / priority ordering (prioritizing core FRBR chain & higher-signal links before tail siblings) so a single prolific serial or series at hop 1–2 cannot silently consume the entire budget without leaving room for hop 3–4 or marking `meta.truncated = true` with `meta.truncated_reason` (`"node_cap" | "edge_cap" | "both"`).
- **Alternative Considered:** Raising `MAX_GRAPH_NODES` unboundedly (e.g., `2000+`). Rejected because dense subgraphs produce $O(N^2)$ SVG edges, degrading browser SVG layout FPS on mobile Capacitor webviews and amplifying backend memory/query cost.

### Decision 3: Full-Library Concept Explorer Contract & FRBR Concept Mapping

- **Choice:** Extend `GET /api/catalog/graph` with `mode=library` (or companion `GET /api/catalog/graph/library`, finalized cleanly in OpenAPI) returning `anchor: null`, `mode: "library"`, `nodes`, `edges`, and `meta`. Map collector concept filter chips strictly to canonical FRBR/domain entities without flattening tiers:
  - `work`: `Work` (`F1_Work`, excluding `work_kind == "series"` when filtered separately, or tagged with `work_kind` for `"series"` / `"serial"`).
  - `series`: `Work` with `work_kind == "series"` (linked via `WorkSeriesMembership`).
  - `contributor` (UI label `"Person / Contributor"`): `Contributor` (`F10` / `F11`, supporting `type="person"` vs `"organization"`).
  - `expression`: `Expression` (`F2_Expression`).
  - `manifestation`: `Manifestation` (`F3_Manifestation_Product_Type`).
  - `item`: `Item` (`F5_Item`, physical owned copies only — never virtual `UserWorkIntent` wishlist entries with `id < 0`).
  - `map` / `lod`: `MapAttachment` and accepted `SemanticLink` (`status == "accepted"`).
- **Alternative Considered:** Adding a separate Next.js route `/graph/library` or `/library-graph/[filter]`. Rejected to keep `/graph` unified and guarantee `CAPACITOR_BUILD=true` static export safety via query params (`?mode=library&entities=...`) inside `<Suspense>`.

### Decision 4: Frontend Layout (`hop >= 3`, Multi-Component Packing) & UX Density

- **Choice:**
  1. Extend `computeRadialLayout()` in `frontend/components/graph/frbr-relation-graph.tsx` to support arbitrary `hop >= 1` concentric bands (e.g. `hop = 1: r ~ 235`, `hop = 2: r ~ 445`, `hop = 3: r ~ 670` staggered `640/740` when dense, `hop = 4: r ~ 910` staggered `880/980` when dense) with parent-angle grouping to minimize edge crossings.
  2. When `anchor === null` (`mode === "library"`) or multiple disconnected components exist, partition `visibleNodes` by connected components over `visibleEdges`, compute a local radial/clustered layout per component, and pack components on a deterministic grid with bounding-box padding—keeping isolated matching nodes visible when edges are filtered out.
  3. Compute the graph bounding box to support a `"Fit to View"` action (and auto-fit initial `zoom`/`pan` for `depth >= 3` or `mode === "library"`).
  4. Enforce `iqoqo-ux-auditor` density (`<= 4` visible buttons per control group): keep Mode switch + compact Depth selector (`1`–`4`) in the header, and consolidate Edge Categories + Entity Types into a compact Shadcn `Popover` / `DropdownMenu` filter control with active count badge alongside search and compact zoom/fit controls (`Zoom In`, `Zoom Out`, `Fit to View`, `Reset`). Add a discoverable link to `/graph?mode=library` in `Navbar` (`frontend/components/dashboard/navbar.tsx`) and on the `/graph` missing-anchor view. All new `pl.json` keys use sentence case.
- **Alternative Considered:** Introducing a heavy force-directed physics library (`d3-force`) or WebGL canvas. Rejected for initial scope to avoid breaking existing deterministic SVG `data-testid` node selectors (`graph-node-*`), accessibility attributes, and bundle size on Capacitor unless preview benchmarks prove pure SVG insufficient.

### Decision 5: Visibility, `FederationConsent`, `FEDERATION_HEAD_MODE`, and Rate-Limit Parity

- **Choice:**
  - Unify `FederationConsent.federated_collection == False` exclusion in `GraphService` (for public non-owner/non-friend callers) alongside `_get_sparql_items()` and `build_graph()`.
  - Fix `build_graph()` in `app/core/sparql_service.py` to resolve `friend_ids` and `opted_out_user_ids` once in bulk/SQL rather than calling `is_friend_of()` and `is_item_publicly_visible()` inside the per-item loop.
  - Keep read-only graph & SPARQL queries allowed under `FEDERATION_HEAD_MODE=true` (exempt from `reject_if_federation_head_item_write`), preserve `SemanticLink.status == "accepted"` strictly, and preserve `@limiter.limit("60 per minute")` on `/api/catalog/graph` (and `"10 per minute"` on `/api/sparql`) backed by Valkey/Redis.

## Risks / Trade-offs

- **High Cardinality / Edge Explosion at Depth 3–4 or Full-Library Mode** → Mitigation: Enforce strict server-side `max_nodes` and `max_edges` ceilings, per-hop fairness quotas, and deterministic ranking; surface `meta.truncated` and `truncated_reason` clearly in the UI.
- **`sparql-runner` 512 MB Cgroup OOM / 10 MB Snapshot Overflow under Option B** → Mitigation: Keep Option B gated behind Task 1 preview-DB benchmarks measuring `sparql-runner` RSS, `snapshot_bytes`, and `MAX_GRAPH_TRIPLES` under `concurrency=4`; reject Option B if it breaches any hard gate.
- **SQL vs. RDF Semantic Drift (if Option C Hybrid is chosen)** → Mitigation: Add automated parity tests (`tests/test_sparql_service_parity.py` / `tests/test_catalog_graph_api.py`) asserting identical node/edge/visibility/consent outcomes across SQL and RDF projections.
- **SVG DOM Rendering Lag on Large Subgraphs (Mobile WebView)** → Mitigation: Cap default visible nodes/edges conservatively (`<= 150–250` nodes, `<= 400–600` edges), auto-fit viewport on load, and simplify label rendering when zoomed out.
- **Cross-Milestone Spec Collisions (`C142`, `C143`, `C144`)** → Mitigation: Keep anchored `VALID_GRAPH_ENTITY_TYPES` at `("work", "expression", "manifestation", "item")` (leaving `person`/`series` root anchoring to `C143`), leave `/item/[id]` layout to `C142`, and leave `Work -> Work` cross-media adaptation links to `C144`.

## Open Questions

1. **Primary Query Backend (Decision 1 — Gated by Task 1 Preview-DB Benchmark):** Should `GraphService` execute depth `1..4` and full-library explorer queries via **Option A (Batched SQL / Recursive CTE)**, **Option B (N+1-fixed, parity-completed RDF/SPARQL via `sparql_service`/`sparql-runner`)**, or **Option C (Hybrid)**? *Cannot be finalized until Task 1 measures p50/p95 latency, RSS, SQL count, triple count, snapshot bytes, and truncation rates on the cloned preview PostgreSQL database.*
2. **Exact Calibrated Production Caps (`MAX_GRAPH_NODES`, `MAX_GRAPH_EDGES`, Default Depth):** What exact numeric ceilings (e.g., `max_nodes` `150` vs `250`, `max_edges` `400` vs `600`, full-library default `max_nodes`) keep p95 latency within budget (`<= 800 ms` depth 4, `<= 1500 ms` library overview) and SVG interaction smooth on mobile? *To be calibrated from Task 1 benchmark telemetry.*
3. **Full-Library Default Scope & Endpoint Shape:** Should full-library mode default to `GET /api/catalog/graph?mode=library` (single unified endpoint) or a companion route `GET /api/catalog/graph/library`, and should authenticated collectors default to `my+friends+public` vs `public` scope toggle? *To be finalized immediately following Task 1 benchmark and OpenAPI review.*
