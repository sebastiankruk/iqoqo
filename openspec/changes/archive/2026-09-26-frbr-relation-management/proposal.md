## Why

Catalog ingestion from external sources (Google Books, Discogs, IGDB, Allegro) frequently generates fragmented FRBR entity graphs—such as duplicate Works created under minor title variations, Expressions separated across different Works, or Manifestations incorrectly linked to arbitrary Expressions. Currently, administrators cannot restructure these relationships without manual database interventions, risking hierarchy corruption and dangling references. Furthermore, `RoadmapItem` models allow ambiguous simultaneous links to multiple FRBR levels (`work_id` and `manifestation_id`), violating strict FRBR normalization.

This change delivers milestone C11: FRBR Relation Management for v0.8.1, introducing full backend services, RESTful admin APIs, and an interactive admin UI to safely reassign, merge, and split FRBR hierarchy nodes while strictly enforcing single-level FRBR bindings on roadmap items.

## What Changes

- **Backend FRBR Reassignment, Merge, and Split Services**:
  - Implement atomic hierarchy re-parenting in `app/core/frbr_service.py` to move Manifestations between Expressions and Expressions between Works.
  - Implement merge operations for duplicate Works, Expressions, and Manifestations with child re-linking, metadata consolidation, and clean deletion of orphaned sources.
  - Implement entity split operations allowing administrators to extract selected children into newly created Works, Expressions, or Manifestations.
  - Enforce FRBR hierarchy integrity: prevent circular hierarchies, ensure ISBN-13 remains strictly on Manifestations, and log all relational structural changes to `EntityAuditLog`.
- **Admin Relation Management API**:
  - Expose dedicated endpoints under `/api/v1/admin/frbr/relations/` for reassigning parents, merging duplicate nodes, and splitting entities.
  - Secure endpoints with `@require_auth` and `@require_permission(PermissionName.WRITE_METADATA)`.
- **Roadmap Item FRBR Normalization**:
  - Add `expression_id` FK to `catalog.roadmap_items` and enforce an explicit database check constraint ensuring each roadmap item links to strictly ONE FRBR entity level (Work, Expression, or Manifestation).
  - Provide an Alembic migration to apply the schema constraint and backfill/clean legacy ambiguous rows.
  - Update `app/db/roadmap.py` and `app/api/roadmap.py` to serialize and validate single-level FRBR targets.
- **Admin Relation Management UI**:
  - Enhance `frontend/components/admin/frbr-editor.tsx` with dedicated interactive actions for Reassign, Merge, and Split.
  - Provide entity picker search modals (`searchFrbrEntities`) with impact previews showing affected child nodes before confirming destructive or structural changes.
  - Wire UI state with TanStack Query invalidation to immediately refresh the entity tree and catalog views.

## Capabilities

### New Capabilities
- `editor/relation-management`: Interactive administrative UI and backend services to reassign, merge, and split FRBR hierarchy nodes (Work -> Expression -> Manifestation -> Item) while enforcing single-FRBR-level foreign key normalization on roadmap items.

### Modified Capabilities
<!-- None: existing FRBR ontology boundary specifications remain invariant; this capability provides relation editing and schema normalization adhering to those boundaries -->

## Impact

- **Database**:
  - Schema migration on `catalog.roadmap_items` adding `expression_id` foreign key and a strict mutual exclusivity `CHECK` constraint across `(work_id, expression_id, manifestation_id)`.
- **Backend Services & API**:
  - `app/core/frbr_service.py`: Add `reassign_parent()`, `merge_entities()`, and `split_entity()` transactional operations.
  - `app/api/admin.py`: Add `/api/v1/admin/frbr/relations/*` endpoints.
  - `app/db/roadmap.py` & `app/api/roadmap.py`: Normalize FRBR linkage and serialization.
- **Frontend**:
  - `frontend/components/admin/frbr-editor.tsx`: Add node action menus and relation management dialogs.
  - `frontend/lib/api/admin.ts`: Add API client methods for FRBR reassign, merge, and split actions.
  - `frontend/types/frbr.ts`: Add relation mutation payload and response interfaces.
