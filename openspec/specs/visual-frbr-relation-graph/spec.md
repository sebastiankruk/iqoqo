# visual-frbr-relation-graph Specification

## Purpose
Provide a bounded, visibility-enforcing graph API (`GET /api/catalog/graph`) and a dedicated full-screen `/graph` explorer page so users can visually inspect and traverse FRBR hierarchies, series, container parts, expansions, contributors, map supplements, and external LOD links.

## Requirements

### Requirement: Bounded and Visibility-Safe Catalog Relation Graph Endpoint
The backend SHALL expose `GET /api/catalog/graph` accepting `entity_type` (`work`, `expression`, `manifestation`, `item`, `person`, `contributor`, `series`), `entity_id`, and `depth` (`1` or `2`, clamped to `2`), returning deterministic `nodes` and `edges` capped at `150` nodes, strictly enforcing three-tier `Item` visibility privacy (`public`, `friends_only`, `private`), expanding `Contributor` roots (`person` and `organization`) across `WorkContribution`, `ExpressionContribution`, `ManifestationContribution`, and accepted `SemanticLink`s (including hop-2 expansion through connected contributors), resolving `series` roots onto `Work` series containers (`work_kind == "series"` or referenced in `WorkSeriesMembership.series_work_id` / `WorkPart.container_work_id`), and remaining accessible under `FEDERATION_HEAD_MODE=true`.

#### Scenario: Querying a 1-hop or 2-hop FRBR neighborhood around a Work

- **GIVEN** a `Work` with `Expression`s, `Manifestation`s, an `Item` (`private` owned by User A and `public` owned by User B), a `Series`, a `WorkExpansionLink`, and accepted `SemanticLink`s
- **WHEN** an unauthenticated visitor or User C requests `GET /api/catalog/graph?entity_type=work&entity_id=<W>&depth=2`
- **THEN** the response MUST return HTTP `200` with the FRBR tree, series, expansion, and LOD nodes/edges plus User B's `public` `Item`, and MUST omit User A's `private` `Item`.
- **WHEN** User A requests the same endpoint
- **THEN** User A's `private` `Item` MUST be included alongside User B's `public` `Item`.

#### Scenario: Bounding depth and total nodes on dense entities

- **GIVEN** an entity connected to more than 150 nodes or queried with `depth=99`
- **WHEN** `GET /api/catalog/graph` executes
- **THEN** `depth` MUST clamp to `2`, `nodes` MUST NOT exceed `150` entries, and `meta.truncated` MUST indicate when truncation occurred.

#### Scenario: Anchoring the graph on a Person, Contributor, Organization, or Series root

- **GIVEN** a `Contributor` (`type="person"` or `type="organization"`) linked to `Work`, `Expression`, and `Manifestation` contributions plus an accepted `SemanticLink` (`entity_type="contributor"`) and a pending `SemanticLink`, and a `Series` `Work` (`work_kind="series"` or linked via `WorkSeriesMembership.series_work_id`) containing member `Work`s with `public` and `private` `Item`s
- **WHEN** an unauthenticated visitor requests `GET /api/catalog/graph?entity_type=person&entity_id=<C>&depth=1` or `GET /api/catalog/graph?entity_type=contributor&entity_id=<C>&depth=1`
- **THEN** the response MUST return HTTP `200` anchored on `contributor:<C>`, expose `contributor_type` (`"person"` or `"organization"`), include linked `Work`, `Expression`, `Manifestation`, and accepted LOD nodes/edges (omitting pending LOD links and omitting `private` `Item`s at deeper hops), and remain accessible when `FEDERATION_HEAD_MODE=true`.
- **WHEN** a user requests `GET /api/catalog/graph?entity_type=series&entity_id=<S>&depth=1`
- **THEN** the response MUST resolve `<S>` to the series `Work` node (`work:<S>`), traverse `in_series` / `has_part` edges to member `Work`s without duplicating the series node, and return HTTP `404` if `<S>` does not exist or is not a series `Work`.

#### Scenario: Traversing depth-2 connections through a Contributor from a Work anchor

- **GIVEN** `Work A` and `Work B` sharing a `Contributor` `<C>` via `WorkContribution`
- **WHEN** a user requests `GET /api/catalog/graph?entity_type=work&entity_id=<A>&depth=2`
- **THEN** the BFS traversal MUST enqueue `contributor:<C>` at hop 1 and expand `contributor:<C>` at hop 2 so `Work B` appears in the neighborhood within the `150`-node cap.

#### Scenario: Traversing depth 3 and 4 neighborhoods without visibility or LOD leaks

- **GIVEN** a multi-hop graph spanning `Work -> WorkPart -> Expression -> Manifestation -> Item` (up to 4 hops) that includes `friends_only` `Item`s, `private` `Item`s, and `SemanticLink` rows with `status="pending"` or `"rejected"`
- **WHEN** an authenticated accepted friend requests `GET /api/catalog/graph?entity_type=work&entity_id=<W>&depth=4`
- **THEN** the response MUST return `meta.depth == 4`, traverse up to 4 hops without a single high-degree hop-1 hub starving deeper hops ahead of deterministic per-node/per-hop limits, include the accepted friend's `friends_only` `Item`, and strictly omit `private` `Item`s and non-accepted `SemanticLink`s.

#### Scenario: Enforcing FederationConsent exclusion and read-only FEDERATION_HEAD_MODE access

- **GIVEN** User D has `FederationConsent.federated_collection == False` and owns both a `public` `Item` and a `friends_only` `Item` attached to `Work` `W`
- **WHEN** an unauthenticated visitor or non-friend requests `GET /api/catalog/graph?entity_type=work&entity_id=<W>&depth=3` (including when `FEDERATION_HEAD_MODE=true`)
- **THEN** the endpoint MUST return HTTP `200` (not blocked by write guards) and MUST omit User D's non-consented items while preserving User D's own access when User D is the authenticated caller and preserving both User D's `public` and `friends_only` items when the authenticated caller is an accepted friend of User D.

### Requirement: Dedicated Full-Screen `/graph` Explorer Page and Entity Entry Buttons
The frontend SHALL provide a dedicated full-screen `/graph` page (reading `?type=<entity_type>&id=<entity_id>&depth=<1|2>` where `<entity_type>` accepts `work`, `expression`, `manifestation`, `item`, `person`, `contributor`, and `series` for full `CAPACITOR_BUILD=true` static export compatibility) with interactive pan/zoom/drag, edge-type filtering, node inspection drawer (allowing recentering on `work`, `expression`, `manifestation`, `item`, `contributor`, `person`, and `series` nodes), an anchor entity link derived from the anchor node's canonical `url` (preventing broken `/person/<id>`, `/contributor/<id>`, or `/series/<id>` 404 routes), and `"Explore Graph"` navigation buttons on `/work/[id]`, `/expression/[id]`, `/manifestation/[id]`, and `/item/[id]`.

#### Scenario: Navigating from an entity detail page to `/graph` and recentering on a connected node

- **GIVEN** a user viewing `/work/[id]` (or `/manifestation/[id]`, `/expression/[id]`, `/item/[id]`)
- **WHEN** the user clicks `"Explore Graph"`
- **THEN** the app MUST navigate to `/graph?type=work&id=<id>`, render the centered interactive graph, allow toggling edge-type filter pills (`FRBR`, `Series`, `Parts/Expansions`, `Contributors`, `Maps`, `LOD`), and allow clicking any node to inspect its summary and recenter or open its entity page.

#### Scenario: Exploring a Person, Contributor, or Series root and recentering onto a Contributor node

- **GIVEN** a user visiting `/graph?type=person&id=<C>&depth=2` or `/graph?type=series&id=<S>&depth=2` (including in a `CAPACITOR_BUILD=true` static export)
- **WHEN** the graph loads and the user inspects the header `"Open Entity Page"` link or clicks a connected `contributor` node inside an active graph
- **THEN** the header `"Open Entity Page"` link MUST resolve from the anchor node's canonical `url` (e.g., `/collection?q=...` for `person`/`contributor`, `/work/<S>` for `series`) rather than `/${rawType}/${rawId}`, and clicking a non-anchor `contributor` node MUST display `"Recenter Graph"` and navigate via `router.push` to `/graph?type=...&id=<C>&depth=<depth>`.

#### Scenario: Physical item detail page surfaces Explore Graph above the fold on mobile and desktop

- **GIVEN** a user viewing a physical item (`/item/<id>` with `id > 0`) on either a mobile (`390x844`) or desktop (`1280x800`) viewport
- **WHEN** the page renders
- **THEN** the localized `"Explore Graph"` link (`graph.exploreGraph`, pointing to `/graph?type=item&id=<id>`) is visible above the fold without scrolling past sidebar forms or `ItemTabs`
- **AND** when viewing a virtual wishlist item (`id <= 0`), the `"Explore Graph"` link is NOT rendered

#### Scenario: Exploring depth 3 and 4 neighborhoods in the radial SVG layout

- **GIVEN** a user viewing `/graph?type=work&id=42&depth=2`
- **WHEN** the user selects depth `3` or `4`
- **THEN** the URL updates to `depth=3` or `depth=4`, the graph fetches with the corresponding depth parameter, `hop === 3` and `hop === 4` nodes render on distinct outer radial bands without overlapping `{ x: 0, y: 0 }`, and any node/edge cap truncation surfaces both `max_nodes` and `max_edges` context in `graph-truncated-banner`.

#### Scenario: Preserving static export and mobile toolbar density on `/graph`

- **GIVEN** the `/graph` page rendered at a mobile viewport (`390x844`) or desktop viewport in `mode=library` or built with `CAPACITOR_BUILD=true`
- **WHEN** the explorer renders depth controls, mode switcher, and category/entity filters
- **THEN** no dynamic route segments break static export and at most 4 primary FRBR entity-type buttons (`work`, `expression`, `manifestation`, `item`) render inline while the 4 secondary entity types (`series`, `contributor`, `map`, `lod`) are accessible via a compact disclosure toggle.

### Requirement: Full-Library Concept Graph Explorer Endpoint and UI Mode

The system SHALL provide a full-library concept graph explorer mode accessible directly from `/graph` (including top-level navigation discovery and when no single entity anchor is selected) backed by a read-only catalog graph query (`GET /api/catalog/graph?mode=library` or `GET /api/catalog/graph/library`) returning `anchor: null`, `mode: "library"`, bounded `nodes` and `edges` across visible library concepts (`work`, `series`, `contributor`, `expression`, `manifestation`, `item`, `map`, `lod`), and `meta` (`max_nodes`, `max_edges`, `node_count`, `edge_count`, `truncated`). When multiple entity types are requested on a catalog whose `Work` count exceeds `max_nodes` (e.g., `>= 150` works), `build_library_graph()` MUST partition `max_nodes` across the requested entity tiers (`max(1, effective_max_nodes // len(active_tiers))`), mark `meta.truncated = True` whenever any active entity tier has more database rows than its allocated tier quota, prioritize connected child `Expression`, `Manifestation`, `Item`, `Contributor`, `Map`, and `LOD` nodes linked to the selected `Work`/`Series` nodes so non-`Work` tiers and connecting edges are never starved, push `Work.work_kind != "series"` into the SQL `WHERE` clause before `LIMIT` when `work` is requested without `series`, and emit `WorkPart`, `WorkExpansionLink`, `ContainerAggregation`, `ExpressionContribution`, and `ManifestationContribution` edges whenever their endpoint nodes and relationship families (`parts_expansions`, `contributions`) are active. The explorer MUST support filtering by entity types and edge categories, preserve isolated matching nodes when edges are filtered out, arrange disconnected components deterministically without overlapping at `(0, 0)`, enforce three-tier `Item` visibility, `FederationConsent.federated_collection` (exempting accepted friends), `SemanticLink.status == "accepted"`, rate limits, and remain functional in read-only `FEDERATION_HEAD_MODE=true`.

#### Scenario: Opening the full-library concept graph without a single entity anchor

- **GIVEN** an authenticated collector or anonymous visitor navigating to `/graph` or `/graph?mode=library`
- **WHEN** the full-library explorer loads without `?type=` and `?id=` anchor parameters
- **THEN** `/graph` MUST render the full-library concept graph explorer (instead of a dead-end missing-parameter error), display disconnected concept clusters in distinct non-overlapping layout regions, and provide `"Fit to View"` and node inspection controls.

#### Scenario: Opening the full-library concept graph on a >150-work catalog returns connected multi-tier nodes and edges

- **GIVEN** a catalog containing more than 150 `Work` rows along with connected `Expression`, `Manifestation`, `Item`, `Contributor`, `WorkPart`, and `WorkExpansionLink` records
- **WHEN** a caller requests `GET /api/catalog/graph?mode=library&max_nodes=150` with default entity types and relationship families enabled
- **THEN** the response MUST include nodes from multiple active entity tiers (`work`, `expression`, `manifestation`, `item`, `contributor`) as well as connecting FRBR, contribution, and `parts_expansions` edges, and MUST report `meta.truncated == True` because the `Work` tier exceeded its per-tier quota.

#### Scenario: Filtering the full-library concept graph by entity type and edge category

- **GIVEN** a full-library concept graph containing `Work`, `Contributor` (`Person`), `Series`, `Manifestation`, and `Item` nodes
- **WHEN** the user filters to `Work` (excluding `Series`) and `Contributor` entity types or toggles off an edge category
- **THEN** SQL filtering excludes `Work.work_kind == "series"` prior to `LIMIT`, only matching entity types and active edge categories remain visible, matching isolated nodes with zero visible edges remain rendered on the canvas, and `meta.truncated` warns if results hit `max_nodes` or `max_edges`.

#### Scenario: Enforcing privacy, FederationConsent, and FEDERATION_HEAD_MODE in full-library mode

- **GIVEN** a catalog containing `private` `Item`s, `friends_only` `Item`s, `public` `Item`s owned by a user with `FederationConsent.federated_collection == False`, and `"pending"` `SemanticLink`s
- **WHEN** an anonymous visitor queries the full-library concept graph (including when `FEDERATION_HEAD_MODE=true`)
- **THEN** the response MUST return HTTP `200` and MUST exclude `private` items, `friends_only` items, non-consented users' items (unless the caller is the owner or an accepted friend), and non-accepted `SemanticLink`s, while never elevating a virtual wishlist `UserWorkIntent` entry into a physical `Item` node.

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

### Requirement: Consistent Above-the-Fold Localized Graph Entry Across Work, Expression, and Manifestation Pages

The frontend SHALL provide a consistent, `iqoqo-ux-auditor`-compliant top utility bar on `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]` containing the `[← Back]` navigation control on the left and the secondary `"Explore Graph"` entry link (`data-testid="explore-graph-link"`, `variant="outline"`, `size="sm"`, linking to `/graph?type=work&id=<id>`, `/graph?type=expression&id=<id>`, or `/graph?type=manifestation&id=<id>`) on the right alongside the optional FRBR tier badge (`hidden sm:inline-flex` on narrow mobile viewports). Every `"Explore Graph"` entry button across `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]` MUST render using the localized `graph.exploreGraph` translation key (`"Explore Graph"` in `en.json`, sentence-case `"Eksploruj graf"` in `pl.json`), MUST remain visible above the fold on both mobile (`390x844`) and desktop (`1280x800`) viewports without being pushed below cover artwork, MUST keep its bar at `<= 4` visible buttons, and MUST preserve query-parameter routing compatible with `CAPACITOR_BUILD=true` static export.

#### Scenario: Work, Expression, and Manifestation pages surface localized Explore Graph above the fold

- **GIVEN** a user viewing `/work/<id>`, `/expression/<id>`, or `/manifestation/<id>` on a mobile (`390x844`) or desktop (`1280x800`) viewport
- **WHEN** the page renders
- **THEN** the top utility bar displays `[← Back]` and the localized `"Explore Graph"` link (`data-testid="explore-graph-link"`, text from `graph.exploreGraph`) above the fold prior to cover artwork and metadata sections
- **AND** the utility bar contains `<= 4` visible buttons with zero horizontal clipping on `390px` viewports

#### Scenario: Polish locale renders sentence-case graph entry label across entity pages

- **GIVEN** a user browsing `/work/<id>`, `/expression/<id>`, or `/manifestation/<id>` with the Polish (`pl`) locale active
- **WHEN** the entity detail page renders
- **THEN** `data-testid="explore-graph-link"` displays `"Eksploruj graf"` (never a hardcoded English `"Explore Graph"` string) and navigates to `/graph?type=<work|expression|manifestation>&id=<id>`

#### Scenario: Work hero action cluster stays focused on Work CTAs without graph crowding

- **GIVEN** an authenticated user viewing a serial `Work` (`/work/<id>` with `work_kind === "serial"`)
- **WHEN** the hero metadata section renders
- **THEN** `"Explore Graph"` resides in the top utility bar rather than between `"Add Issue"` and `"Add to Wishlist"`, keeping the hero action cluster uncluttered with a single clear primary CTA (`"Add Issue"`)

### Requirement: Accepted Cross-Media Derivative Edges in Catalog Graph and `/graph` Explorer

`GET /api/catalog/graph` and the `/graph` explorer UI SHALL traverse and display confirmed (`accepted`) cross-media `Work -> Work` derivative/adaptation relations (`WorkRelation`) when expanding `Work` neighborhoods, allowing users to filter those edges in `/graph` while strictly omitting `pending`/`suggested` and `dismissed` reconciliation candidates and preserving the `150`-node cap and `Item` three-tier visibility rules.

#### Scenario: Connected cross-media Works appear in `/api/catalog/graph` only when accepted

- **GIVEN** a novel `Work` (`W_book`) with an accepted cross-media link from a film `Work` (`W_film`, `is_adaptation_of`), plus an unaccepted `pending` candidate to a game `Work` (`W_game`) and a `dismissed` candidate to a soundtrack `Work` (`W_music`)
- **WHEN** a visitor queries `GET /api/catalog/graph?entity_type=work&entity_id=<W_book>&depth=1`
- **THEN** the response MUST return HTTP `200` including `W_film` and the directed derivative edge (`W_film -> W_book`), and MUST omit `W_game` and `W_music` candidates while enforcing `Item` visibility privacy and `MAX_GRAPH_NODES = 150`.

#### Scenario: User filters cross-media derivative edges on `/graph`

- **GIVEN** a user viewing `/graph?type=work&id=<W_book>` with connected cross-media derivative `Work` nodes
- **WHEN** the user toggles the cross-media/derivative edge filter pill in the `/graph` explorer
- **THEN** the canvas MUST show or hide the cross-media derivative edges cleanly and allow clicking the connected `Work` node to recenter or open its entity detail page.

### Requirement: Visibility-Safe Graph Root Object Picker Search Endpoint
The backend SHALL expose a dedicated `GET /api/catalog/graph/search` endpoint decorated with `@optional_auth` and `@limiter.limit("60 per minute")` (registered in OpenAPI 3.1 alongside the expanded `entity_type` enum on `/api/catalog/graph`) that accepts `q`, optional `types` (comma-separated subset of `person`, `contributor`, `series`, `work`, `expression`, `manifestation`, `item`), and `limit` (SQL `LIMIT` clamped to `1..25`), performs diacritic-insensitive search without N+1 queries, enforces three-tier `Item` visibility (`public` with `is_hidden=false`, `owner_id == viewer`, `friends_only`/`shared` for accepted friends) in SQL before `LIMIT`, and remains functional under `FEDERATION_HEAD_MODE=true`.

#### Scenario: Searching diacritic-insensitively across Person, Series, and FRBR catalog roots

- **GIVEN** a `Contributor` `"Stanisław Lem"` (`type="person"`), a `Contributor` `"Wydawnictwo Literackie"` (`type="organization"`), a `Series` `Work` (`work_kind="series"`), and matching `Work`, `Expression`, and `Manifestation` rows
- **WHEN** an anonymous or authenticated user requests `GET /api/catalog/graph/search?q=Stanislaw&types=person,series,work`
- **THEN** the response MUST return HTTP `200` with typed candidate entries (`entity_type`, `entity_id`, `label`, `subtitle`, and optional `contributor_type`/`work_kind`/`issn`/`url`) matching `"Stanisław Lem"` diacritic-insensitively, using bounded SQL `LIMIT` queries.

#### Scenario: Enforcing three-tier Item visibility in SQL before LIMIT during picker search

- **GIVEN** `User A` owns a `private` `Item`, a `friends_only` `Item`, and a `public` (`is_hidden=false`) `Item` all matching `"SecretChronicleCopy"`
- **WHEN** an anonymous visitor or stranger `User C` requests `GET /api/catalog/graph/search?q=SecretChronicleCopy&types=item`
- **THEN** ONLY the `public` `Item` MUST be returned, and `private` and `friends_only` `Item`s MUST be excluded in the SQL predicate before applying `LIMIT`.
- **WHEN** an accepted friend `User B` requests the same endpoint
- **THEN** `public` and `friends_only` `Item`s MUST be returned while `private` `Item`s remain excluded.
- **WHEN** owner `User A` requests the same endpoint
- **THEN** all three matching `Item`s (`public`, `friends_only`, `private`) MUST be returned.

#### Scenario: Bounding limit, rejecting invalid types, and preserving FEDERATION_HEAD_MODE read access

- **GIVEN** `FEDERATION_HEAD_MODE=true` or `false`
- **WHEN** a caller requests `GET /api/catalog/graph/search?q=Lem&limit=500`
- **THEN** the endpoint MUST clamp `limit` to `25` and return HTTP `200` (without returning `403` in `FEDERATION_HEAD_MODE`).
- **WHEN** a caller requests `GET /api/catalog/graph/search?q=%20%20%20` (blank query)
- **THEN** the endpoint MUST return HTTP `200` with an empty result list.
- **WHEN** a caller requests `GET /api/catalog/graph/search?q=Lem&types=invalid_type`
- **THEN** the endpoint MUST return HTTP `400` with a JSON error payload.

### Requirement: Interactive Root Object Picker UI on `/graph`
The frontend SHALL provide an interactive, keyboard-accessible Root Object Picker component (`role="combobox"` with `role="listbox"` / `role="option"`, debounced query input requiring at least 2 characters, entity-type filter selector, and localized `en.json` / sentence-case `pl.json` labels) rendered inline in the `/graph` empty state (replacing the static missing-parameters dead end) and accessible from active graph views via a single `"Switch Root"` header button that opens a dialog without adding buttons to the 9-button canvas filter/zoom toolbar.

#### Scenario: Selecting a Person root from the `/graph` empty-state picker

- **GIVEN** a user visits `/graph` with no `type` or `id` query parameters
- **WHEN** the user optionally filters by `Person`, types at least 2 characters into the inline Root Object Picker combobox, and selects a matching `Person` candidate via click or `ArrowDown` + `Enter`
- **THEN** the frontend MUST navigate via `router.push` to `/graph?type=person&id=<entity_id>&depth=2` and render the person-centered FRBR neighborhood graph.

#### Scenario: Switching roots from an active graph via the Switch Root dialog

- **GIVEN** a user viewing an active `/graph?type=work&id=<W>&depth=2` page
- **WHEN** the user clicks the `"Switch Root"` header button, searches for a `Series` or `Manifestation` in the dialog picker, and selects it
- **THEN** the dialog MUST close and navigate via `router.push` to `/graph?type=<selected_type>&id=<selected_id>&depth=2` while preserving browser Back history and keeping the canvas filter/zoom toolbar free of extra buttons.

#### Scenario: Keyboard navigation, minimum-character guard, and error states in the Root Object Picker

- **GIVEN** a user typing into the Root Object Picker combobox
- **WHEN** the trimmed query has fewer than 2 characters
- **THEN** the picker MUST display a localized minimum-character hint and MUST NOT issue a search request.
- **WHEN** the user presses `Escape` while the listbox is open or when the search API returns an error
- **THEN** `Escape` MUST dismiss the listbox and an API failure MUST render a localized error message without crashing `/graph`.

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

### Requirement: Order-Independent Series/Work Deduplication in Graph Root Search and 7-Category Blueprint Documentation

When `GET /api/catalog/graph/search` is invoked with both `work` and `series` included in `types` in any order (for example `types=work,series` or `types=series,work`), `GraphService.search_root_candidates()` SHALL emit any matching series `Work` at most once (under `entity_type="series"`), never duplicating the same `Work.id` in the `work` bucket. Architecture Blueprint 8 (`docs/images/architecture/08-frbr-visual-relation-graph.svg` and `frontend/public/images/help/08-frbr-visual-relation-graph.svg`) SHALL accurately document all 7 cross-schema edge categories (including `"derivatives"`).

#### Scenario: Requesting types=work,series emits a matching Series Work only once

- **GIVEN** a `Work` with `work_kind="series"` titled `"Dune Chronicles"` and a regular `Work` titled `"Dune"`
- **WHEN** a caller requests `GET /api/catalog/graph/search?q=Dune&types=work,series&limit=10`
- **THEN** `"Dune Chronicles"` appears once with `entity_type="series"` and does NOT appear again under `entity_type="work"`, while `"Dune"` appears under `entity_type="work"`
