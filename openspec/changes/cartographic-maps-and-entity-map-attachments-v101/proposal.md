## Why
Collectors requested *"support for maps - in books, games, etc #v100"* in `iqoqo development notes.md`. Maps appear in physical collections in two distinct ontological ways: (1) standalone cartographic works (folding tourist/topographic maps, historical maps, atlases), and (2) map supplements/inserts inside Books (e.g., Middle-earth fold-out map), Board Games (board/scenario maps), and Video Games (cloth/poster maps in boxed editions).

## What Changes

- **Standalone Cartographic Media (`docs/ontology/iqoqo.ttl`, `taxonomy.ttl`, `shared/format_mappings.yaml`):** Add `cartographic_map` and `atlas` formats with cartographic properties (`iqoqo:mapScale`, `iqoqo:mapProjection`, `iqoqo:geographicBoundingBox`, and GeoNames `SemanticLink` integration from `v0.8.2`).
- **Entity Map Attachments & Supplements (`iqoqo:hasMapAttachment` / `frbroo:R15_has_part`):** Allow attaching one or more structured map assets (`title`, `image_url`, `map_type`: `"world_map" | "fold_out_insert" | "cloth_map" | "game_board" | "topographic"`, `dimensions`) to any `Work` (F1), `Manifestation` (F3), or `Item` (F5), plus an Item-level physical completeness boolean (`map_insert_present: bool`).
- **API Endpoints for Map Attachments (`app/api/manifestations.py`, `app/api/items.py`):** Support uploading or linking map images (reusing the hardened image upload validation pipeline) and serializing `iqoqo:hasMapAttachment` into RDF/JSON-LD.

## Capabilities

### New Capabilities
- `cartographic-maps-and-supplements`: Standalone cartographic map/atlas formats (`mapScale`, `mapProjection`) and `iqoqo:hasMapAttachment` (`frbroo:R15_has_part`) map supplements on Books, Board Games, and Video Games with Item completeness tracking.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, `docs/ontology/taxonomy.ttl`
- `shared/format_mappings.yaml`, `app/core/format_normalizer.py`, `frontend/types/taxonomy.ts`
- `app/api/manifestations.py`, `app/api/items.py`, `app/core/frbr_service.py`, `app/core/meta_display.py`
- `tests/test_maps_and_attachments.py`
