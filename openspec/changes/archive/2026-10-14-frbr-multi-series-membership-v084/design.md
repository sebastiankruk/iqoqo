## Context

See `proposal.md` for motivation. In the current relational schema, a Work can point to a single `container_work_id` in `catalog.works`. This prevents a single Work from being part of both an overarching franchise/universe and a specific sub-series.

## Goals / Non-Goals

**Goals:**
- Provide a clean relational join table `catalog.work_series_memberships` linking `work_id` and `series_work_id` with an integer `sequence` column.
- Update Work CRUD APIs to accept and return an array of series memberships (`series: [{ id, title, sequence }]`).
- Update the FRBR Editor UI to allow custodians to search and attach multiple series containers.
- Render multi-series chips on Work and Item pages.

**Non-Goals:**
- Changing hierarchical Work->Expression relationships.
- Infinite recursive series nesting UI.

## Decisions

- **Decision 1: Relational join table over JSON metadata array**
  - *Rationale*: A dedicated table with foreign keys enforces referential integrity, supports fast indexed joins, and prevents orphaned series IDs upon Work deletion.
  - *Alternatives considered*: Storing series lists in `work.meta['series']` (rejected: lacks referential integrity, leads to denormalization drift).

## Risks / Trade-offs

- **[Risk]** Migration of existing single `container_work_id` entries.
  - **Mitigation**: Alembic migration will backfill rows from existing `container_work_id` relationships into `work_series_memberships`.
