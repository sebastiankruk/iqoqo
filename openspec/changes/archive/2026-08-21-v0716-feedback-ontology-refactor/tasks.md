## 1. Create FeedbackComment Relational Table

- [x] 1.1 Define `FeedbackComment` model in `app/db/social.py` with columns: `id`, `feedback_item_id` (FK), `user_id` (FK), `comment_text`, `created_at`
- [x] 1.2 Add relationship to `FeedbackItem` model with `cascade="all, delete-orphan"`
- [x] 1.3 Add `__table_args__` with `schema="social"`

## 2. Move feedback_items to Social Schema

- [x] 2.1 Update `FeedbackItem.__table_args__` schema from `inventory` to `social`
- [x] 2.2 Audit all ORM queries referencing `FeedbackItem` for explicit schema qualifiers

## 3. Create Alembic Migration

- [x] 3.1 Generate Alembic migration (revision ID ≤ 32 chars)
- [x] 3.2 Migration step 1: Create `social.feedback_comments` table
- [x] 3.3 Migration step 2: `ALTER TABLE feedback_items SET SCHEMA social`
- [x] 3.4 Migration step 3: Migrate any existing JSONB comment data to new `feedback_comments` rows
- [x] 3.5 Add downgrade path: reverse schema move and recreate JSONB column

## 4. Integrate rclone for Screenshot Storage

- [x] 4.1 Add `RCLONE_FEEDBACK_REMOTE` environment variable to `.env.example`
- [x] 4.2 Create Celery task for uploading feedback screenshots via `rclone copyto`
- [x] 4.3 Update `app/api/feedback.py` to trigger Celery upload task after screenshot save
- [x] 4.4 Add graceful fallback to local storage when `RCLONE_FEEDBACK_REMOTE` is not set
- [x] 4.5 Update screenshot URL resolution to support both local and remote paths

## 5. Update API Layer

- [x] 5.1 Update `app/api/feedback.py` POST endpoint to create `FeedbackComment` records
- [x] 5.2 Update GET endpoint to include comments from `feedback_comments` table
- [x] 5.3 Ensure comment listing is ordered by `created_at` ascending

## 6. Write Tests

- [x] 6.1 Create pytest tests for FeedbackComment CRUD operations
- [x] 6.2 Create pytest test for concurrent comment addition (no race condition)
- [x] 6.3 Create pytest test for schema migration (feedback_items in social schema)
- [x] 6.4 Create pytest test for rclone screenshot upload with mock subprocess
- [x] 6.5 Create pytest test for graceful fallback when rclone remote not configured

## 7. Verification

- [x] 7.1 Verify alembic `upgrade head` succeeds locally
- [x] 7.2 Run backend test suite (`make test-backend`) and verify passing
- [x] 7.3 Use `codegraph impact` on `FeedbackItem` to check if any other imports broke
