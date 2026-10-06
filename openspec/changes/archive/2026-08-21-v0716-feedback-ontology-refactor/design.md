## Context

The feedback subsystem (`FeedbackItem` model in `app/db/social.py`) stores comments as JSONB, lives incorrectly in the `inventory` schema, and saves screenshots to ephemeral container-local storage. These issues block horizontal scaling, create race conditions under concurrent edits, and violate domain boundaries (feedback is a social/admin construct, not an inventory asset).

## Goals / Non-Goals

**Goals:**

- Create a dedicated `FeedbackComment` relational table in the `social` schema with proper foreign keys to `FeedbackItem`, `User`, timestamps, and comment text
- Migrate `feedback_items` table from `inventory` schema to `social` schema via `ALTER TABLE SET SCHEMA`
- Introduce a new rclone remote target for feedback screenshot storage, replacing `./app/static/gallery/`
- Write Alembic migration (revision ID ≤ 32 chars) for schema changes
- Add pytest tests for comment CRUD and rclone upload

**Non-Goals:**

- ActivityPub federation of feedback threads (deferred to v0.8.0)
- Refactoring the entire feedback API
- Migrating existing screenshot files (handled in deployment runbook)

## Decisions

### Decision 1: Separate `FeedbackComment` table
**Choice:** Create `social.feedback_comments` table with `id`, `feedback_item_id` (FK), `user_id` (FK), `comment_text`, `created_at` columns.
**Rationale:** Relational table eliminates JSONB read-modify-write races, enables proper indexing, and aligns with ActivityPub `sioc:Thread` model for future federation.

### Decision 2: rclone integration for screenshots
**Choice:** Introduce `RCLONE_FEEDBACK_REMOTE` environment variable and upload screenshots via `rclone copyto` in a Celery background task.
**Rationale:** User specified rclone integration (not simple volume mount) for consistency with existing backup infrastructure. Background upload prevents blocking the API response.

### Decision 3: Schema migration order
**Choice:** Single Alembic migration: (1) create `feedback_comments` table in `social`, (2) move `feedback_items` from `inventory` to `social`, (3) migrate existing JSONB comments to new table.
**Rationale:** Single migration ensures atomicity of the schema restructuring.

## Risks / Trade-offs

- **Risk:** Moving table across schemas breaks existing queries with explicit schema qualifiers → **Mitigation:** Audit all SQL/ORM queries referencing `feedback_items`
- **Risk:** JSONB → relational migration loses comment ordering → **Mitigation:** Add `created_at` timestamp and `order` column during migration
- **Risk:** rclone remote not configured on all instances → **Mitigation:** Graceful fallback to local storage if `RCLONE_FEEDBACK_REMOTE` not set

## Migration Plan

1. **Pre-deploy:** Back up `feedback_items` table
2. **Deploy:** Run Alembic migration (creates comment table, moves schema, migrates JSONB data)
3. **Post-deploy:** Configure `RCLONE_FEEDBACK_REMOTE` environment variable
4. **Rollback:** Reverse migration recreates JSONB column and moves table back to `inventory`
