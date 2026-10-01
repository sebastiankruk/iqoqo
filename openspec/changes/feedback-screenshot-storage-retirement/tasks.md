## 1. Remove the Remote Write Path

- [ ] 1.1 Delete `upload_feedback_screenshot` from `app/core/tasks.py` (~25 lines), and remove its Celery registration if it is named explicitly in any task list
- [ ] 1.2 Remove the `upload_feedback_screenshot.apply_async(...)` call and the `local_path` construction it depends on from the ticket-creation handler in `app/api/feedback.py`
- [ ] 1.3 Remove the now-unused `from app.core.tasks import upload_feedback_screenshot` import
- [ ] 1.4 Confirm `os.path` remains imported for other uses in the module (it is also used by `_validate_screenshot_access` and the local read) — do not remove it

## 2. Remove the Remote Read Path

- [ ] 2.1 Delete `_fetch_remote_screenshot` from `app/api/feedback.py` (~30 lines)
- [ ] 2.2 In `get_feedback_screenshot`, replace the remote fallback branch with a plain 404 when the file is absent from `GALLERY_DIR`, removing the `get_s3_service`/`BUCKET_FEEDBACK` call and the `warn_if_legacy_rclone_configured` invocation
- [ ] 2.3 Remove the `S3DownloadError` import and the now-unused `boto3`-adjacent s3_service imports, keeping the module's remaining imports intact
- [ ] 2.4 Update the route docstring, which currently reads "from local storage, or from remote object storage"
- [ ] 2.5 Verify the `get_s3_service is None` → 404 branch that distinguished "no remote configured" is gone; a single 404 now covers absence regardless of cause

## 3. Drop the Feedback Bucket Role

- [ ] 3.1 Remove `BUCKET_FEEDBACK`, its `_PREFIXES` entry, and its membership in `_VALID_BUCKETS` from `app/core/s3_service.py`
- [ ] 3.2 Remove the `RCLONE_FEEDBACK_REMOTE` → `(BUCKET_FEEDBACK, "S3_BUCKET_FEEDBACK")` deprecation mapping, keeping the `RCLONE_REMOTE_ARCHIVE` and `RCLONE_REMOTE_FAST` entries
- [ ] 3.3 Remove the `S3_BUCKET_FEEDBACK` row from the module docstring's bucket table
- [ ] 3.4 ⚠️ **Leave `BUCKET_BACKUP` in place.** It looks orphaned — C17 removed the in-container rotation as dead code — but `cloud_backup.sh:286` constructs `S3Service("backup", ...)` for its own upload. Verify with a grep that no removal of `BUCKET_BACKUP` is proposed before touching `_VALID_BUCKETS`
- [ ] 3.5 Remove the `S3_BUCKET_FEEDBACK` row from `.env.example`, and narrow the note about which legacy rclone remotes still warn so it names only `RCLONE_REMOTE_ARCHIVE`
- [ ] 3.6 Confirm the S3 credential set is still required by `BUCKET_COVERS` and the host backup upload, so no credential is dropped from `.env.example` as a side effect

## 4. Update Tests

Baseline: `tests/test_feedback_tickets.py` (8 references), `tests/test_s3_service.py` (8), `tests/test_s3_migration.py` (15).

- [ ] 4.1 In `test_feedback_tickets.py`, remove the async-upload tests that mock `apply_async` — they have no subject once the task is gone — and **keep** every local-serve, access-control and validation test, which cover surviving behaviour
- [ ] 4.2 In `test_feedback_tickets.py`, add a test asserting an absent screenshot returns 404 with no remote call attempted
- [ ] 4.3 In `test_s3_service.py`, drop `BUCKET_FEEDBACK` from the bucket-role parametrizations and env-var matrices
- [ ] 4.4 In `test_s3_migration.py`, drop the `RCLONE_FEEDBACK_REMOTE` deprecation row from the warning matrix and keep the `RCLONE_REMOTE_ARCHIVE` coverage
- [ ] 4.5 Add a test asserting `BUCKET_BACKUP` and `BUCKET_COVERS` remain valid roles, so a later cleanup cannot silently remove the host script's upload path
- [ ] 4.6 Run the three modules and confirm the remaining tests pass; then run the full backend suite

## 5. Verification

- [ ] 5.1 Confirm no remaining reference to `BUCKET_FEEDBACK`, `S3_BUCKET_FEEDBACK`, `RCLONE_FEEDBACK_REMOTE` or `upload_feedback_screenshot` in `app/`, `tests/`, `deploy/`, `.env.example` or the docs
- [ ] 5.2 Confirm a feedback ticket can be created with a screenshot and the image served back, with no object-storage configuration present in the environment
- [ ] 5.3 Confirm `app/static/gallery` is still bind-mounted for `web` and `worker` in `docker-compose.yml`, and that the nightly backup's `ASSET_PATHS` still contains it — the change must not have removed either
- [ ] 5.4 Run `make lint && make test` with no new failures

## 6. Documentation

- [ ] 6.1 Update `docs/BACKUPS.md` §4 (feedback screenshot remote) to state that screenshots are stored locally and shipped off-site by the nightly backup, and remove the `RCLONE_FEEDBACK_REMOTE` setup instructions
- [ ] 6.2 Leave §1 (fast backups), §2 (archive) and §3 (covers) unchanged — §3 is the shared cover cache, which is retained and still boto3-backed
- [ ] 6.3 Note in the operational docs that no bucket needs to be provisioned for feedback screenshots