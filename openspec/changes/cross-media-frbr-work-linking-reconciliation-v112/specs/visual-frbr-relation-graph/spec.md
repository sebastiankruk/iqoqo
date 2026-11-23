## ADDED Requirements

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
