## Context

Board game expansions are currently modeled inconsistently — some are aggregated into base game F16 Container Works, violating FRBR ontological purity. The `mechanics` field uses free-text, causing data inconsistency. The custodian escalation review screen at `app/api/social.py` (`_handle_type_change_acceptance`) accepts approval payloads without displaying target entity details, creating a blind IDOR vulnerability.

## Goals / Non-Goals

**Goals:**

- Define OWL/SHACL constraints preventing expansion aggregation into F16 Container Works
- Create `work_expansion_links` association table linking expansions to base games via `iqoqo:is_expansion_of`
- Create `boardgame_mechanics` vocabulary table with BGG taxonomy data as a local copy
- Enrich custodian escalation API to return target entity details (title, type, ID) in the response payload
- Update escalation review frontend to display entity details before approval
- Add pytest tests for SHACL constraints and mechanics vocabulary

**Non-Goals:**

- Migrating existing incorrectly-aggregated expansions (requires separate data cleanup migration)
- Real-time BGG taxonomy sync (periodic manual updates suffice)
- Refactoring the entire custodian workflow

## Decisions

### Decision 1: Association table for expansion links
**Choice:** Create `work_expansion_links` table with `base_work_id` (FK → Work), `expansion_work_id` (FK → Work), and `link_type` columns.
**Rationale:** Association table is the standard relational pattern for many-to-many Work relationships. `link_type` enables distinguishing `is_expansion_of` from future relationship types like `is_sequel_to`.
**Alternative considered:** JSONB array on Work — rejected because it violates relational normalization and blocks efficient querying.

### Decision 2: OWL/SHACL constraint location and form
**Choice:**

- Vocabulary terms (`iqoqo:is_expansion_of`, `iqoqo:WorkExpansionLink`, supporting properties) live in `docs/ontology/iqoqo.ttl`.
- The actual SHACL shape preventing expansion Works from being aggregated into F16 Container Works lives in a new file, `docs/ontology/iqoqo-shapes.ttl`.
- API-layer enforcement is implemented in Python via a new `app/core/ontology_validation.py` helper that queries `work_expansion_links` and `container_aggregations`, and is called from `app/core/frbr_service.py::add_container_component` and from the expansion-link creation path.

**Rationale:** Separating OWL vocabulary from SHACL shapes keeps the ontology file readable and mirrors the pattern of separating taxonomy data (`taxonomy.ttl`) from the ontology. The SHACL file is declarative documentation and a machine-checkable contract; the Python guard provides immediate SQL-level enforcement without requiring a SHACL engine on every write.

**Alternative considered:** Pure SHACL runtime validation with pyshacl on every API call — rejected for performance and because the association table does not yet exist as RDF triples at write time.

### Decision 3: Local BGG mechanics taxonomy copy
**Choice:** Maintain `data/bgg_mechanics.json` file and seed into `boardgame_mechanics` database table via migration.
**Rationale:** User specified local copy approach. Periodic updates via `scripts/update_bgg_mechanics.py`.
**Alternative considered:** Dynamic fetch from BGG API — rejected due to reliability concerns and API rate limits.

### Decision 4: Backend enrichment for escalation review
**Choice:** Modify the escalation detail endpoint in `app/api/social.py` to include `target_entity` dict with `title`, `type`, `id`, and `current_state` fields.
**Rationale:** User specified backend API enrichment. Frontend can then render entity context without additional API calls.

## Risks / Trade-offs

- **Risk:** SHACL constraints may be too strict for edge cases (e.g., standalone expansion without base game) → **Mitigation:** Allow `is_expansion_of` to be optional; constraint only prevents F16 aggregation
- **Risk:** BGG mechanics taxonomy changes over time → **Mitigation:** Version the local copy; add `last_updated` timestamp to table
- **Risk:** Escalation enrichment increases API response size → **Mitigation:** Include only essential entity fields, not full FRBR tree
