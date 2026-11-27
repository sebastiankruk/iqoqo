## 1. Backend Graph Canonicalization (`app/core/graph_service.py`)

- [x] 1.1 Add `_canonical_lod_uri(uri: str)` and `_canonical_lod_node_key(link: SemanticLink)` in `app/core/graph_service.py` normalizing `http`/`https`, host casing, and trailing slashes into deterministic `lod:<digest>` node IDs
- [x] 1.2 Update `_lod_node_dict` / `try_add_node` so colliding `SemanticLink` rows merge onto one canonical LOD node (preserving richest `pref_label`) and deduplicate `(source, target, relation)` in `add_edge`
- [x] 1.3 Compute `present_person_ids` before `anchor_filters` in full-library mode so `SemanticLink.entity_type == "contributor"` links are anchored alongside `work`/`expression`/`manifestation`

## 2. Tests & Verification

- [x] 2.1 Add Pytest regression tests in `tests/test_catalog_graph_api.py` covering Person (`Stephen King`) duplicate `http`/`https`/trailing-slash `SemanticLink` rows, shared Work/Person LOD links, edge deduplication, and full-library contributor LOD inclusion
- [x] 2.2 Verify frontend graph tests pass with canonical `lod:*` node IDs
- [x] 2.3 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test-parallel`, and `IQOQO_AI_MODE=1 make secret-scan`
