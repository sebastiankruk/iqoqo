## Why

Board game expansions are incorrectly aggregated into base game F16 Container Works, violating FRBR ontological purity. The `mechanics` field uses free-text input instead of a controlled vocabulary, leading to inconsistent data. Additionally, the custodian escalation review screen doesn't display target entity details (title, type, ID), enabling blind IDOR approval of `_handle_type_change_acceptance` payloads.

## What Changes

- **Define OWL/SHACL constraints** preventing board game expansion items from aggregating directly into base game F16 Container Works — expansions must be modeled as separate `frbroo:F1_Work` entities
- **Model board game expansions** as distinct `F1_Work` entities linked to base games via `frbroo:R15_has_part` / `iqoqo:is_expansion_of` association table
- **Introduce controlled vocabulary** for the board game `mechanics` field referencing BGG mechanics taxonomy, maintained as a local copy with periodic update capability
- **Enrich custodian escalation API** to include target entity details (title, type, ID) in the escalation payload, and update the frontend review screen to clearly display these details — preventing blind IDOR approval
- **Add backend API enrichment** for the escalation review endpoint to return full entity context

## Capabilities

### New Capabilities

- `boardgame-expansion-modeling`: FRBR-compliant expansion modeling as distinct F1_Work entities with association table
- `boardgame-mechanics-vocabulary`: Controlled vocabulary for board game mechanics using local BGG taxonomy copy
- `custodian-escalation-enrichment`: Backend API enrichment and frontend display of target entity details in escalation review

### Modified Capabilities

- `board-game-container-aggregation`: Adding OWL/SHACL constraints to prevent incorrect expansion aggregation
- `custodian-escalation`: Adding entity detail display to prevent blind IDOR approval

## Impact

- **Backend Files:** `app/db/core.py` or `app/db/social.py` (association table), `app/core/format_normalizer.py` (expansion handling), `app/api/social.py` (escalation enrichment)
- **Frontend Files:** Custodian escalation review component
- **Data:** New `boardgame_mechanics` vocabulary table, `work_expansion_links` association table
- **Tests:** pytest for SHACL validation, expansion modeling, mechanics vocabulary; E2E for custodian review screen
- **Risk:** Medium — new data model tables but no migration of existing data required initially
- **FRBR Constraint:** Expansions MUST be `F1_Work`, NEVER aggregated into F16 Container Works
