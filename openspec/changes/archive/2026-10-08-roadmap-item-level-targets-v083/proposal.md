## Why

Reading roadmaps currently let a user target a Work, Expression, or Manifestation, but cannot name the particular physical copy they own and intend to read. For v0.8.3, add Item as a fourth exclusive target so users can distinguish a specific copy from its edition or intellectual realization without weakening the existing one-target integrity rule.

## What Changes

- **Target release: v0.8.3.** Extend roadmap target semantics to exactly one of Work (title-level), Expression (realization/translation), Manifestation (edition, often ISBN), or Item (an actual individual copy).
- Add `item_id` to roadmap storage, with a schema-aware foreign key, migration, and a database constraint requiring exactly one of the four target references. Preserve existing Work/Expression/Manifestation bindings without converting them.
- Extend roadmap API validation, serialization, and entry create/read/update/delete behavior to support all four targets. Item targets must resolve to a real Item owned by the authenticated roadmap user; missing, borrowed-only, or otherwise non-owned Items are not selectable.
- Provide a four-level target selector in the roadmap UI, including search/selection of the user's owned physical Items and clear level/copy distinctions in the roadmap display.
- Define catalog-deletion behavior that preserves the four-way integrity constraint and roadmap progress: a referenced target cannot be deleted until its roadmap entry is removed; deletion APIs return a conflict instead of nulling a target or silently deleting roadmap data.
- Do not create placeholder Item rows for purchase intentions. An intended title or edition remains a Work or Manifestation target (or belongs in wishlist intent); Item means an existing individual copy.
- This is a dedicated v0.8.3 change. It does **not** modify or expand the existing `security-hardening-v081` change, including its explicit deferral of Item-level roadmap targets.

## Capabilities

### New Capabilities
- `reading-roadmaps/item-level-targets`: Four-level exclusive FRBR targets for roadmap entries, including persistence, API behavior, owned-Item selection, display, deletion semantics, and integrity testing.

### Modified Capabilities

None. No existing OpenSpec capability currently specifies reading-roadmap target behavior; the new capability defines it without editing the v0.8.1 security-hardening spec or change.

## Impact

- **Database:** `RoadmapItem` model and a new Alembic migration for `item_id`, its inventory-schema FK/index, the exactly-one-of-four constraint, and restrictive target-delete handling.
- **API:** `/api/v1/roadmaps` serialization and roadmap-item mutations in `app/api/roadmap.py`; target ownership and existence validation; frontend API DTOs/hooks.
- **Frontend:** `frontend/components/collection/roadmap-view.tsx` target selector and display; owned physical Item candidates sourced from the authenticated collection API.
- **Tests:** Roadmap model/migration and API tests, frontend component/hook tests, and roadmap E2E coverage for each target level and owned Item selection.
- **Release planning:** Add a concise v0.8.3 roadmap-plan entry linking this change and its scope.
