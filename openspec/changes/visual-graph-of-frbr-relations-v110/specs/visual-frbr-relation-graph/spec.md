## Purpose

Provide a bounded, visibility-enforcing graph API (`GET /api/catalog/graph`) and a dedicated full-screen `/graph` explorer page so users can visually inspect and traverse FRBR hierarchies, series, container parts, expansions, contributors, map supplements, and external LOD links.

## ADDED Requirements

### Requirement: Bounded and Visibility-Safe Catalog Relation Graph Endpoint
The backend SHALL expose `GET /api/catalog/graph` accepting `entity_type` (`work`, `expression`, `manifestation`, `item`), `entity_id`, and `depth` (`1` or `2`, clamped to `2`), returning deterministic `nodes` and `edges` capped at `150` nodes and strictly enforcing three-tier `Item` visibility privacy (`public`, `friends_only`, `private`).

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

### Requirement: Dedicated Full-Screen `/graph` Explorer Page and Entity Entry Buttons
The frontend SHALL provide a dedicated full-screen `/graph` page (reading `?type=<entity_type>&id=<entity_id>&depth=<1|2>` for full `CAPACITOR_BUILD=true` static export compatibility) with interactive pan/zoom/drag, edge-type filtering, node inspection drawer, and `"Explore Graph"` navigation buttons on `/work/[id]`, `/expression/[id]`, `/manifestation/[id]`, and `/item/[id]`.

#### Scenario: Navigating from an entity detail page to `/graph` and recentering on a connected node
- **GIVEN** a user viewing `/work/[id]` (or `/manifestation/[id]`, `/expression/[id]`, `/item/[id]`)
- **WHEN** the user clicks `"Explore Graph"`
- **THEN** the app MUST navigate to `/graph?type=work&id=<id>`, render the centered interactive graph, allow toggling edge-type filter pills (`FRBR`, `Series`, `Parts/Expansions`, `Contributors`, `Maps`, `LOD`), and allow clicking any node to inspect its summary and recenter or open its entity page.
