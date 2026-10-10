## 1. Schema & Backend Modeling

- [ ] 1.1 Create Alembic migration for `work_series_memberships` table (`work_id`, `series_work_id`, `sequence`, `created_at`) with backfill from existing `container_work_id` relations.
- [ ] 1.2 Update SQLAlchemy model `Work` with `series_memberships` relationship.
- [ ] 1.3 Update `/api/works/<id>` endpoints to serialize and accept `series_memberships` payloads.

## 2. Frontend FRBR Editor & Views

- [ ] 2.1 Update FRBR Editor series selector to support multi-select and sequence entry.
- [ ] 2.2 Update `frontend/components/item/item-tabs.tsx` and `components/work/work-detail-client.tsx` to render multi-series badges.

## 3. Verification

- [ ] 3.1 Run pytest tests for multi-series serialization and migration.
- [ ] 3.2 Run Vitest tests for multi-series badge rendering.
