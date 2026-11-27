## Context

`GraphService` (`app/core/graph_service.py`) serves both bounded BFS neighborhood graphs (anchored on `person`/`contributor`, `work`, `series`, `manifestation`, `item`) and full-library graphs (`?mode=library`). Both paths serialize accepted `SemanticLink` records via `_lod_node_dict(link, hop=...)`.

## Goals / Non-Goals

- **Goals:**
  - Ensure any external LOD resource URI renders as at most one canonical `lod:*` node per graph response, regardless of how many `SemanticLink` rows or `http`/`https`/trailing-slash variants reference it.
  - Ensure `Contributor`/`Person` LOD links are included in full-library `anchor_filters` alongside `Work`, `Expression`, and `Manifestation`.
  - Deduplicate identical `(source, target, relation)` edges so collapsed LOD nodes never receive duplicate `same_as` edges from the same source node.
- **Non-Goals:**
  - Running a destructive database migration to delete historical `SemanticLink` rows (graph-level canonicalization fixes display immediately and non-destructively; optional DB cleanup remains independent).
  - Changing the frontend graph UI contract or `SemanticLink` admin moderation flows.

## Decisions

1. **Deterministic Canonical LOD Key (`_canonical_lod_uri` + `_canonical_lod_node_key`):**
   - Normalize `external_uri` by trimming whitespace, treating `http://` and `https://` equivalently (`https`), lowercasing scheme + netloc, and stripping trailing `/` on non-root paths.
   - Hash the normalized URI (`hashlib.sha256(canonical_uri.encode("utf-8")).hexdigest()[:16]`) to form `lod:<digest>` so IDs are URL-safe, deterministic across requests, and strictly 1-to-1 with the canonical URI.
   - When multiple `SemanticLink` rows collide onto the same `lod:<digest>`, keep the first node inserted and enrich `label` if the existing label was a fallback slug and the later row provides a `pref_label`.
2. **Full-Library Contributor Anchor Order:**
   - Compute `present_person_ids` before constructing `anchor_filters` in full-library mode and append `and_(SemanticLink.entity_type == "contributor", SemanticLink.entity_id.in_(present_person_ids))`.
3. **Edge Set Deduplication:**
   - Track `(source, target, relation)` in `add_edge` (both bounded and full-library builders) so collapsing multiple `SemanticLink` rows into one canonical LOD node never emits duplicate `same_as` edges between the same source entity and canonical LOD node.

## Risks / Trade-offs

- **Node ID shape change (`lod:<row_id>` -> `lod:<hash16>`):** Frontend graph components treat node `id` as an opaque string key starting with `"lod:"`; verifying existing frontend graph tests and adding a regression test ensures full compatibility.
