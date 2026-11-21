## MODIFIED Requirements

### Requirement: Bounded and Visibility-Safe Catalog Relation Graph Endpoint
The backend SHALL expose `GET /api/catalog/graph` accepting `entity_type` (`work`, `expression`, `manifestation`, `item`), `entity_id`, `depth` (`1` through `4`, clamped to `4`), `max_nodes` (bounded integer ceiling, default `150`), `max_edges` (bounded integer ceiling), and optional `edge_types` (`frbr`, `series`, `parts_expansions`, `contributors`, `maps`, `lod`), returning deterministic `nodes`, `edges`, and `meta` (`depth`, `requested_depth`, `max_nodes`, `max_edges`, `node_count`, `edge_count`, `truncated`, `truncated_reason`) within configured rate-limit (`60 per minute`) and execution timeout budgets. The endpoint MUST strictly respect the four-tier FRBR ontology (`Work -> Expression -> Manifestation -> Item`), enforce three-tier `Item` visibility privacy (`public`, `friends_only`, `private`, plus legacy `shared` compatibility), exclude items owned by users with `FederationConsent.federated_collection == False` for public/non-owner/non-friend callers, emit only `SemanticLink` nodes with `status == "accepted"`, and remain available in read-only mode when `FEDERATION_HEAD_MODE=true`.

#### Scenario: Querying a 1-hop or 2-hop FRBR neighborhood around a Work

- **GIVEN** a `Work` with `Expression`s, `Manifestation`s, an `Item` (`private` owned by User A and `public` owned by User B), a `Series`, a `WorkExpansionLink`, and accepted `SemanticLink`s
- **WHEN** an unauthenticated visitor or User C requests `GET /api/catalog/graph?entity_type=work&entity_id=<W>&depth=2`
- **THEN** the response MUST return HTTP `200` with the FRBR tree, series, expansion, and LOD nodes/edges plus User B's `public` `Item`, and MUST omit User A's `private` `Item`.
- **WHEN** User A requests the same endpoint
- **THEN** User A's `private` `Item` MUST be included alongside User B's `public` `Item`.

#### Scenario: Bounding depth and total nodes on dense entities

- **GIVEN** an entity connected to more than the allowed `max_nodes` or `max_edges` bounds or queried with `depth=99`
- **WHEN** `GET /api/catalog/graph` executes
- **THEN** `depth` MUST clamp to `4`, `nodes` MUST NOT exceed `meta.max_nodes`, `edges` MUST NOT exceed `meta.max_edges`, and `meta.truncated` MUST indicate when node or edge truncation occurred.

#### Scenario: Traversing depth 3 and 4 neighborhoods without visibility or LOD leaks

- **GIVEN** a multi-hop graph spanning `Work -> WorkPart -> Expression -> Manifestation -> Item` (up to 4 hops) that includes `friends_only` `Item`s, `private` `Item`s, and `SemanticLink` rows with `status="pending"` or `"rejected"`
- **WHEN** an authenticated accepted friend requests `GET /api/catalog/graph?entity_type=work&entity_id=<W>&depth=4`
- **THEN** the response MUST return `meta.depth == 4`, traverse up to 4 hops without starving deeper hops unfairly ahead of deterministic per-hop limits, include the accepted friend's `friends_only` `Item`, and strictly omit `private` `Item`s and non-accepted `SemanticLink`s.

#### Scenario: Enforcing FederationConsent exclusion and read-only FEDERATION_HEAD_MODE access

- **GIVEN** User D has `FederationConsent.federated_collection == False` and owns a `public` `Item` attached to `Work` `W`
- **WHEN** an unauthenticated visitor or non-friend requests `GET /api/catalog/graph?entity_type=work&entity_id=<W>&depth=3` (including when `FEDERATION_HEAD_MODE=true`)
- **THEN** the endpoint MUST return HTTP `200` (not blocked by write guards) and MUST omit User D's non-consented `Item` while preserving User D's own access when User D is the authenticated caller.

### Requirement: Dedicated Full-Screen `/graph` Explorer Page and Entity Entry Buttons
The frontend SHALL provide a dedicated full-screen `/graph` page reading URL query parameters (`?type=<entity_type>&id=<entity_id>&depth=<1|2|3|4>` for anchored neighborhood mode, and `?mode=library` with optional type/edge filters for full-library mode) inside a `<Suspense>` boundary for full `CAPACITOR_BUILD=true` static export compatibility. The page SHALL provide interactive pan/zoom/drag, a `"Fit to View"` action with auto-fit framing, depth selection for `1` through `4` hops, radial concentric positioning for `hop >= 3` (`3` and `4`) that prevents nodes from collapsing onto the origin `(0, 0)`, node inspection drawer, edge-category and entity-type filtering that keeps toolbar button density bounded (`<= 4` visible buttons per control group via compact menus/popovers on mobile and desktop), node/edge truncation alerts, sentence-case non-English (`pl.json`) localizations, and `"Explore Graph"` navigation buttons on `/work/[id]`, `/expression/[id]`, `/manifestation/[id]`, and `/item/[id]`.

#### Scenario: Navigating from an entity detail page to `/graph` and recentering on a connected node

- **GIVEN** a user viewing `/work/[id]` (or `/manifestation/[id]`, `/expression/[id]`, `/item/[id]`)
- **WHEN** the user clicks `"Explore Graph"`
- **THEN** the app MUST navigate to `/graph?type=work&id=<id>`, render the centered interactive graph, allow toggling edge-type filter pills (`FRBR`, `Series`, `Parts/Expansions`, `Contributors`, `Maps`, `LOD`), and allow clicking any node to inspect its summary and recenter or open its entity page.

#### Scenario: Exploring depth 3 and 4 neighborhoods in the radial SVG layout

- **GIVEN** a user viewing `/graph?type=work&id=42&depth=2`
- **WHEN** the user selects depth `3` or `4`
- **THEN** the URL updates to `depth=3` or `depth=4`, the graph fetches with the corresponding depth parameter, `hop === 3` and `hop === 4` nodes render on distinct outer radial bands without overlapping `{ x: 0, y: 0 }`, and any node/edge cap truncation surfaces both `max_nodes` and `max_edges` context in `graph-truncated-banner`.

#### Scenario: Preserving static export and mobile toolbar density on `/graph`

- **GIVEN** the `/graph` page rendered at a mobile viewport (`390x844`) or built with `CAPACITOR_BUILD=true`
- **WHEN** the explorer renders depth controls, mode switcher, and category/entity filters
- **THEN** no dynamic route segments break static export and secondary filter controls collapse into compact dropdown/popover menus so no single action bar exceeds 4 visible inline buttons.

## ADDED Requirements

### Requirement: Full-Library Concept Graph Explorer Endpoint and UI Mode
The system SHALL provide a full-library concept graph explorer mode accessible directly from `/graph` (including top-level navigation discovery and when no single entity anchor is selected) backed by a read-only catalog graph query (`GET /api/catalog/graph?mode=library` or `GET /api/catalog/graph/library`) returning `anchor: null`, `mode: "library"`, bounded `nodes` and `edges` across visible library concepts (`work`, `series`, `contributor`, `expression`, `manifestation`, `item`, `map`, `lod`), and `meta` (`max_nodes`, `max_edges`, `node_count`, `edge_count`, `truncated`). The explorer MUST support filtering by entity types and edge categories, preserve isolated matching nodes when edges are filtered out, arrange disconnected components deterministically without overlapping at `(0, 0)`, enforce three-tier `Item` visibility, `FederationConsent.federated_collection`, `SemanticLink.status == "accepted"`, rate limits, and remain functional in read-only `FEDERATION_HEAD_MODE=true`.

#### Scenario: Opening the full-library concept graph without a single entity anchor

- **GIVEN** an authenticated collector or anonymous visitor navigating to `/graph` or `/graph?mode=library`
- **WHEN** the full-library explorer loads without `?type=` and `?id=` anchor parameters
- **THEN** `/graph` MUST render the full-library concept graph explorer (instead of a dead-end missing-parameter error), display disconnected concept clusters in distinct non-overlapping layout regions, and provide `"Fit to View"` and node inspection controls.

#### Scenario: Filtering the full-library concept graph by entity type and edge category

- **GIVEN** a full-library concept graph containing `Work`, `Contributor` (`Person`), `Series`, `Manifestation`, and `Item` nodes
- **WHEN** the user filters to `Work` and `Contributor` entity types or toggles off an edge category
- **THEN** only matching entity types and active edge categories remain visible, matching isolated nodes with zero visible edges remain rendered on the canvas, and `meta.truncated` warns if results hit `max_nodes` or `max_edges`.

#### Scenario: Enforcing privacy, FederationConsent, and FEDERATION_HEAD_MODE in full-library mode

- **GIVEN** a catalog containing `private` `Item`s, `friends_only` `Item`s, `public` `Item`s owned by a user with `FederationConsent.federated_collection == False`, and `"pending"` `SemanticLink`s
- **WHEN** an anonymous visitor queries the full-library concept graph (including when `FEDERATION_HEAD_MODE=true`)
- **THEN** the response MUST return HTTP `200` and MUST exclude `private` items, `friends_only` items, non-consented users' items, and non-accepted `SemanticLink`s, while never elevating a virtual wishlist `UserWorkIntent` entry into a physical `Item` node.

### Requirement: Benchmark-Gated Pluggable Graph Query Backend with Parity Guarantees
The backend graph query execution layer SHALL expose a backend-agnostic contract capable of running over bounded SQL/recursive CTE, RDF/SPARQL (`sparql_service`/`sparql-runner`), or a hybrid projection, while mandating a preview-database performance benchmark gate (measuring p50/p95 latency, web and `sparql-runner` peak RSS, SQL query counts, RDF triple/snapshot bytes, and truncation behavior across depth `1..4` and full-library mode under concurrency `1` and `4`) before committing the production backend choice. Regardless of the selected backend, the API MUST uphold identical node/edge schemas, FRBR four-tier purity, three-tier `Item` visibility, `FederationConsent`, `SemanticLink.status == "accepted"`, `max_nodes`/`max_edges` bounds, rate limits, and timeout protection (`429` / `503` / `504` graceful handling).

#### Scenario: Maintaining semantic and privacy parity across query backends

- **GIVEN** identical catalog fixtures containing four-tier FRBR entities, `WorkPart`, `WorkSeriesMembership`, `WorkExpansionLink`, `ContainerAggregation`, `Contributor`s, `MapAttachment`s, accepted/pending `SemanticLink`s, and mixed-visibility `Item`s
- **WHEN** evaluated by any candidate query backend (bounded SQL/CTE, RDF/SPARQL, or hybrid)
- **THEN** every backend MUST produce identical visibility exclusions, `SemanticLink.status == "accepted"` enforcement, FRBR tier separation, and bounded node/edge caps.

#### Scenario: Enforcing timeout and memory budgets under concurrent depth-4 and library queries

- **GIVEN** concurrent depth-4 and full-library explorer requests executed against a large catalog dataset
- **WHEN** execution approaches configured query timeout or resource limits (`MAX_GRAPH_NODES`, `MAX_GRAPH_EDGES`, `MAX_GRAPH_TRIPLES`, `MAX_SNAPSHOT_BYTES`, or worker memory ceiling)
- **THEN** the system MUST bound execution or return a structured non-500 error (`429`, `503`, or `504`) without triggering OOM kills or leaking partial private records.
