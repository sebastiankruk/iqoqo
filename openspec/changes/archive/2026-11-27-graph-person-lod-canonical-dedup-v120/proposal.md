## Why

When exploring the concept graph for a Person (e.g., `"Stephen King"`), the graph renders multiple duplicate `"Stephen King"` LOD nodes instead of a single canonical LOD node. Investigation of `app/core/graph_service.py` revealed three causes:

1. `_lod_node_dict(link, hop=...)` keys every LOD node by database row primary key (`lod:<SemanticLink.id>`). Multiple `SemanticLink` rows pointing to the same external resource (e.g., `http://dbpedia.org/resource/Stephen_King` vs `https://dbpedia.org/resource/Stephen_King`, trailing-slash differences, or duplicate links across a `Contributor` and `Work`s) therefore produce separate LOD nodes in the graph.
2. In full-library mode (`GraphService._build_full_library_graph`), `anchor_filters` queries `SemanticLink` rows for `work`, `expression`, and `manifestation` IDs, omitting `SemanticLink.entity_type == "contributor"` because `present_person_ids` is computed after LOD collection.
3. `add_edge` and `_add_semantic_links` do not deduplicate identical `(source, target, relation)` pairs when multiple rows map to the same canonical URI.

## What Changes

- **Canonical LOD URI & Node Key (`app/core/graph_service.py`):**
  - Add `_canonical_lod_uri(uri: str) -> str` normalizing scheme (`http`/`https`), lowercasing host, stripping trailing slashes/fragments where appropriate, and producing a deterministic canonical node key (e.g., `lod:<sha256_16>`).
  - Merge duplicate `SemanticLink` hits onto the single canonical LOD node (keeping the richest `pref_label` and earliest canonical `external_uri`) rather than spawning one node per DB row.
- **Full-Library Contributor LOD Anchors & Edge Deduplication (`app/core/graph_service.py`):**
  - Compute `present_person_ids` before full-library `anchor_filters` so `SemanticLink.entity_type == "contributor"` links are prioritized alongside `work`/`expression`/`manifestation` links.
  - Deduplicate `(source, target, relation)` edges in `add_edge` so multiple DB rows pointing to the same canonical LOD node produce a single `same_as` edge.

## Impact

- Affected files: `app/core/graph_service.py`, `tests/test_catalog_graph_api.py`, `frontend/__tests__/` (graph rendering check if needed).
- No database migrations; keeps `entity_type: "lod"` and existing graph payload contract (`id`, `entity_type`, `label`, `subtitle`, `authority`, `external_uri`, `url`) intact.
