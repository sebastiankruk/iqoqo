## Context

See `proposal.md` for motivation. The iqoqo system models bibliographic entities using the four-tier FRBR standard hierarchy:
- `Work` (F1, conceptual creation, title, authors)
- `Expression` (F2, realization, content type, language, kind)
- `Manifestation` (F3, embodiment, format, publisher, isbn13, barcode)
- `Item` (F5, single owned copy, condition, owner, shelf status)

Currently, `app/core/frbr_service.py` provides scalar field updates for entities, but lacks transactional operations to modify the structural hierarchy: reassigning an entity to a different parent, merging duplicate entities while reparenting child branches, or splitting an entity's children into a new sibling. Furthermore, `RoadmapItem` in `app/db/roadmap.py` currently defines nullable `work_id` and `manifestation_id` columns without mutual exclusivity constraints or an `expression_id` foreign key, allowing invalid multi-level or zero-level bindings.

## Goals / Non-Goals

**Goals:**
- Provide atomic, transactional backend operations in `app/core/frbr_service.py` for `reassign_frbr_parent`, `merge_frbr_entities`, and `split_frbr_entity`.
- Expose RESTful admin endpoints under `/api/v1/admin/frbr/relations/` secured by `write:metadata` permissions.
- Introduce an Alembic migration adding `expression_id` to `catalog.roadmap_items` and enforcing a strict single-FRBR-level check constraint.
- Provide an intuitive admin UI in `frontend/components/admin/` with search autocomplete, child impact preview, and confirmation dialogs.
- Record detailed audit logs in `EntityAuditLog` for all relation mutations.

**Non-Goals:**
- Automated AI or algorithmic duplicate detection (handled by separate operational ETL scripts and future LLM tasks).
- Modifying end-user reading roadmap ordering or status tracking workflows.
- Permitting non-adjacent FRBR hierarchy links (e.g., attaching Manifestation directly to Work without an Expression).

## Decisions

### Decision 1: Explicit Level-Specific Transactional Service Operations
We implement explicit service functions in `app/core/frbr_service.py`:
- `reassign_frbr_parent(entity_type, entity_id, new_parent_id, user_id=None)`
- `merge_frbr_entities(entity_type, source_id, target_id, user_id=None)`
- `split_frbr_entity(entity_type, source_id, child_ids_to_split, new_entity_attrs, user_id=None)`

*Rationale*: Generic or dynamic graph re-parenting easily bypasses level-specific validation (such as ensuring an Expression is only reparented to a Work, or reconciling ISBN-13 and format metadata when merging Manifestations). Explicit functions enforce ontological validation, handle level-specific child migrations, deduplicate metadata, and emit audit logs inside a single database transaction.

*Alternatives considered*:
- *Generic PATCH endpoint*: Rejected because each FRBR tier has distinct relational children, metadata schemas, and event contribution bindings.
- *Client-orchestrated multi-step updates*: Rejected due to risk of partial failure leaving orphaned entities or broken hierarchies.

### Decision 2: Schema Normalization for Roadmap Items
We add `expression_id` to `catalog.roadmap_items` and enforce mutual exclusivity via a database check constraint:
```sql
ALTER TABLE catalog.roadmap_items
  ADD COLUMN expression_id INTEGER REFERENCES catalog.expressions(id) ON DELETE SET NULL;

ALTER TABLE catalog.roadmap_items
  ADD CONSTRAINT check_roadmap_item_single_frbr_level
  CHECK (
    (CASE WHEN work_id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN expression_id IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN manifestation_id IS NOT NULL THEN 1 ELSE 0 END) = 1
  );
```

*Rationale*: Normalizes `RoadmapItem` so that every item represents an exact, unambiguous point in the FRBR hierarchy (e.g., queuing an entire conceptual Work, a specific translation Expression, or a physical Manifestation edition). Enforcing this at the database level guarantees integrity regardless of ingestion or client source.

*Alternatives considered*:
- *Polymorphic `target_type` string + `target_id` integer*: Rejected because it eliminates foreign key relational integrity, cascade cleanup, and indexed JOIN performance in PostgreSQL.
- *Application-only validation*: Rejected because direct SQL updates or concurrent requests could still create invalid states.

### Decision 3: Child Entity Cascade and Metadata Consolidation during Merge
When merging two entities (e.g., `source` into `target`):
1. All direct children of `source` are updated to point to `target` (e.g., Expressions of source Work reparent to target Work; Manifestations of source Expression reparent to target Expression; Items of source Manifestation reparent to target Manifestation).
2. For Works and Expressions, event contributions (`WorkContribution`, `ExpressionContribution`) are re-linked to `target`, avoiding duplicates.
3. Metadata dictionaries are consolidated: target keys are preserved; missing keys from source are copied over; list values (e.g., authors, genres) are merged and deduplicated.
4. An `EntityAuditLog` record is written capturing `action='merge'`, source ID, target ID, and count of migrated children.
5. The source entity is deleted within the transaction.

*Rationale*: Guarantees clean catalog reconciliation without orphaned entities, dangling references, or lost children.

*Alternatives considered*:
- *Tombstone marking (`is_deleted=True`)*: Rejected because unique constraints (such as `isbn13` on `manifestations`) would conflict if source records are retained.

### Decision 4: Admin UI Impact Preview & Modal Workflow
We build `RelationManagementDialog` within `frontend/components/admin/frbr-editor.tsx`:
- Offers three operational modes: "Reassign Parent", "Merge into Existing", "Split to New".
- Reuses `searchFrbrEntities` to provide real-time search and selection of target parent/merge destination.
- Displays an "Impact Summary" card prior to submission showing:
  - Selected entity and its current hierarchy path.
  - Target entity and its hierarchy path.
  - Count of child records that will be moved.
- Requires explicit confirmation click ("Confirm Merge" / "Confirm Reassign").
- On success, triggers TanStack Query invalidation (`["frbr-tree", manifestationId]`, `["items"]`, `["manifestations"]`) and displays Sonner toast notifications.

## Risks / Trade-offs

- **[Risk] Migration failure on existing ambiguous roadmap items** → *Mitigation*: The migration script includes a pre-migration cleanup step: for rows with multiple IDs set, it retains the most granular reference (`manifestation_id` > `work_id`) and nullifies the other; for rows with neither set, it assigns them or removes orphaned rows before adding the check constraint.
- **[Risk] Accidental destruction during entity merge** → *Mitigation*: Merge operations strictly require `write:metadata` permission, provide an impact preview in the UI, execute atomically in a transaction, and record an audit entry.
- **[Risk] Cache desynchronization after structural reparenting** → *Mitigation*: The backend invalidates relevant Redis catalog caches upon relation mutation, and the frontend invalidates TanStack Query keys across catalog, tree, and roadmap endpoints.

## Migration Plan

1. Create a linear Alembic migration in `migrations/versions/` chained after current head.
2. In `upgrade()`:
   - Add column `expression_id` to `catalog.roadmap_items`.
   - Run SQL cleanup to normalize existing `roadmap_items` rows to exactly one entity reference.
   - Add check constraint `check_roadmap_item_single_frbr_level`.
3. In `downgrade()`:
   - Drop check constraint `check_roadmap_item_single_frbr_level`.
   - Drop column `expression_id`.
