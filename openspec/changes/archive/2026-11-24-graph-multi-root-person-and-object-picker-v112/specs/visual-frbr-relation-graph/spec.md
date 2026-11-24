## MODIFIED Requirements

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

## ADDED Requirements

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
- **WHEN** a caller requests `GET /api/catalog/graph/search?q=   ` (blank query)
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
