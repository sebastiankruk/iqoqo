## 1. Board Game Expansion Association Table

- [x] 1.1 Create `work_expansion_links` association table in `app/db/core.py` with `base_work_id` (FK → Work), `expansion_work_id` (FK → Work), `link_type` columns
- [x] 1.2 Add SQLAlchemy relationships on `Work` model for `expansions` and `base_game`
- [x] 1.3 Create Alembic migration for `work_expansion_links` table (revision ID ≤ 32 chars)

## 2. OWL/SHACL Constraints

- [x] 2.1 Define OWL vocabulary in `docs/ontology/iqoqo.ttl`: `iqoqo:is_expansion_of`, `iqoqo:WorkExpansionLink`, `iqoqo:baseWork`, `iqoqo:expansionWork`, `iqoqo:link_type`, plus `iqoqo:containerWork` / `iqoqo:aggregatedWork` / `iqoqo:aggregatedItem` for F16 aggregation
- [x] 2.2 Add SHACL shape in new `docs/ontology/iqoqo-shapes.ttl` preventing an F1_Work with `iqoqo:is_expansion_of` from being the target of `iqoqo:aggregatedWork` in an `iqoqo:ContainerAggregation`
- [x] 2.3 Add Python validation logic in `app/core/ontology_validation.py` enforcing the constraint at the API layer; call it from `app/core/frbr_service.py::add_container_component` and from the expansion-link creation path
- [x] 2.4 Add constants `WORK_LINK_TYPES` and `WORK_LINK_TYPE_IS_EXPANSION_OF` in `app/db/core.py`
- [x] 2.5 Update `app/core/format_normalizer.py` expansion handling to use new association table

## 3. Board Game Mechanics Vocabulary

- [x] 3.1 Create `data/bgg_mechanics.json` file with BGG mechanics taxonomy data
- [x] 3.2 Create `boardgame_mechanics` database table with `id`, `name`, `description`, `bgg_id` columns
- [x] 3.3 Create Alembic migration for mechanics vocabulary table and seed data
- [x] 3.4 Create `scripts/update_bgg_mechanics.py` for periodic taxonomy updates
- [x] 3.5 Update board game metadata editor to use mechanics vocabulary selector

## 4. Custodian Escalation API Enrichment

- [x] 4.1 Modify escalation detail endpoint in `app/api/social.py` to include `target_entity` dict in response
- [x] 4.2 Include `title`, `type` (FRBR level), `id`, and `current_state` in `target_entity`
- [x] 4.3 Add server-side validation: entity ID in approval MUST match escalation request entity ID
- [x] 4.4 Update frontend escalation review component to display entity details prominently

## 5. Write Tests

- [x] 5.1 Create pytest test: expansion created as F1_Work with association link to base game
- [x] 5.2 Create pytest test: SHACL constraint prevents F16 aggregation of expansions (data graph + `pyshacl` against `docs/ontology/iqoqo-shapes.ttl`)
- [x] 5.3 Create pytest test: Python `ontology_validation.py` guard rejects adding an expansion to a container and vice versa
- [x] 5.4 Create pytest test: mechanics vocabulary CRUD and seeding
- [x] 5.5 Create pytest test: escalation detail API returns target_entity with correct fields
- [x] 5.6 Create pytest test: approval with mismatched entity ID is rejected
- [x] 5.7 Create Playwright E2E test: custodian review screen displays entity details

## 6. Verification

- [x] 6.1 Run `make format-python && make format-js`
- [x] 6.2 Run `make lint-python && make lint-js` — verify no errors
- [x] 6.3 Run `flask db upgrade` in test environment
- [x] 6.4 Run `make test-backend && make test-frontend` — verify all tests pass
- [x] 6.5 Manual verification: create expansion, verify it appears as separate F1_Work
