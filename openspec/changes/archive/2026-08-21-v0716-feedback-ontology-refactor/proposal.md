## Why

The feedback subsystem has three structural issues blocking scalability and federation readiness: (1) `FeedbackComment` data stored as JSONB causes read-modify-write race conditions under concurrent admin edits; (2) the `feedback_items` table incorrectly lives in the `inventory` schema when it's a platform admin construct belonging in `social`; (3) feedback screenshots saved to container-local `./app/static/gallery/` create ephemeral storage that doesn't survive container restarts, blocking horizontal scaling and disaster recovery.

## What Changes

- **Normalize** `FeedbackComment` from JSONB blob into a dedicated relational table with proper foreign keys, timestamps, and user attribution — aligned with future ActivityPub `sioc:Thread` federation pattern
- **Move** `feedback_items` table from `inventory` schema to `social` schema via Alembic migration with `ALTER TABLE SET SCHEMA`
- **Integrate rclone** for feedback screenshot storage — introduce a new rclone remote target for feedback attachments, replacing container-local `./app/static/gallery/` path
- **Add comprehensive tests** covering comment normalization, schema migration, and rclone screenshot upload/retrieval

## Capabilities

### New Capabilities

- `feedback-comment-normalization`: Relational FeedbackComment table replacing JSONB storage
- `feedback-screenshot-rclone`: rclone integration for feedback screenshot persistent storage

### Modified Capabilities

- `feedback-mechanism`: Moving feedback_items to social schema and normalizing comment storage

## Impact

- **Files:** `app/db/social.py`, `app/api/feedback.py`, new Alembic migration, `app/core/tasks.py` (rclone target)
- **Tests:** pytest for comment CRUD, schema location, rclone upload
- **Risk:** High — database schema migration with data transformation
- **FRBR Constraint:** Feedback is a platform/social construct, not an inventory asset
