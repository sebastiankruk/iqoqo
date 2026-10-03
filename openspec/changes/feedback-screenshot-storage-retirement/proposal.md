## Why

Feedback ticket screenshots are pushed to a dedicated S3 bucket (`S3_BUCKET_FEEDBACK`) by a Celery task, then read back through a signed-request fallback on an authenticated GET route. That second copy buys nothing the nightly backup does not already provide, while adding an async task, a network round-trip on the screenshot-serving hot path, a bucket-permission failure mode, and a credentialed dependency to provision and rotate.

The redundancy is verifiable in the current codebase:

1. **The host backup already ships them offsite.** `scripts/cloud_backup.sh:229` declares `ASSET_PATHS=("app/static/covers" "app/static/gallery" "app/static/uploads/raw_covers")`. `app/static/gallery` is where screenshots land (`app/api/feedback.py:103`), so every nightly archive already contains them.
2. **The local directory is already durable.** `app/static/gallery` is a host bind mount, not container-local. `docker-compose.yml` mounts `./app/static/gallery` into both `web` and `worker` (and read-only into nginx), so the files survive `docker compose down` and container replacement independently of the remote copy. The existing spec's premise — that screenshots are kept "only in container-local `./app/static/gallery/`" — does not describe this deployment.
3. **No external consumer exists.** The only reader of `BUCKET_FEEDBACK` in `app/` is the iqoqo screenshot route itself. Confirmed by the operator: no support workflow, ticketing integration, or manual process pulls them from object storage.

What the remote path actually costs: `get_feedback_screenshot` issues a signed S3 request and proxies the bytes through the application on every cache miss, and it has to special-case bucket-permission failures separately from genuinely absent objects (`app/api/feedback.py:156`) because those are now indistinguishable in the response. That is an operational failure mode created for durability the backup already provides.

## What Changes

- Remove the remote upload path: delete `upload_feedback_screenshot` from `app/core/tasks.py` and its `.apply_async()` call site in the ticket-creation handler
- Remove the remote read-through from `get_feedback_screenshot`, keeping local serving from `GALLERY_DIR` as the only path
- Delete `_fetch_remote_screenshot` and the `s3_service` imports it required from `app/api/feedback.py`
- Drop the `BUCKET_FEEDBACK` role, its `_PREFIXES` entry, and the `RCLONE_FEEDBACK_REMOTE` deprecation mapping from `app/core/s3_service.py`
- Remove `S3_BUCKET_FEEDBACK` from `.env.example` and the module docstring's bucket table
- Restate the `feedback-screenshot-rclone` capability as local-only, correcting the false "container-local" premise
- Update the three test modules that reference the removed surface

**Not removed:** the `BUCKET_BACKUP` role. It looked equally orphaned — C17 deleted the in-container rotation as dead code — but `cloud_backup.sh:286` constructs `S3Service("backup", ...)` for its own upload, so the role is live from the host even though no in-container caller uses it. `S3_BUCKET_BACKUP` is likewise still read by the host script and must stay.

## Capabilities

### New Capabilities

None. This change removes a storage path rather than adding behaviour.

### Modified Capabilities

- `feedback-screenshot-rclone`: Restate as local-only storage on the host bind mount with per-ticket authorisation on read, removing the remote-upload and remote-read requirements. The capability name retains "rclone" for requirement-identifier continuity, matching how `devops-infrastructure-updates` handled it; the current description is replaced.

## Impact

**Backend:**

- `app/core/tasks.py` — remove `upload_feedback_screenshot` (~25 lines)
- `app/api/feedback.py` — remove the `.apply_async()` call, `_fetch_remote_screenshot` (~30 lines), the remote branch in `get_feedback_screenshot`, and four now-unused `s3_service` imports
- `app/core/s3_service.py` — remove `BUCKET_FEEDBACK`, its `_PREFIXES` entry, the `RCLONE_FEEDBACK_REMOTE` deprecation mapping, and the docstring row. `BUCKET_COVERS` is unaffected

**Configuration:**

- `.env.example` — remove the `S3_BUCKET_FEEDBACK` row and narrow the note about which legacy rclone remotes still warn (it currently names both `RCLONE_REMOTE_ARCHIVE` and `RCLONE_FEEDBACK_REMOTE`)

**Tests:** ~31 references across three modules, all updated rather than deleted where they cover behaviour that survives:

- `tests/test_feedback_tickets.py` (8) — the async-upload tests lose their subject; the local-serve and access-control tests stay
- `tests/test_s3_service.py` (8) — bucket-role parametrization drops `BUCKET_FEEDBACK`
- `tests/test_s3_migration.py` (15) — the deprecation-warning matrix drops the `RCLONE_FEEDBACK_REMOTE` row

**Behaviour change:** screenshots uploaded after this lands are no longer copied offsite by the application. Offsite copies continue via the nightly `cloud_backup.sh` archive, on a daily cadence rather than immediately. A screenshot deleted or corrupted between runs is recoverable from the previous night's archive but not from object storage. Accepted: the ticket text is the durable part, and the loss window is bounded by the backup interval.

**No migration is required.** Existing objects in a configured feedback bucket are left untouched; the bucket can be decommissioned independently once its retention window has passed.

**Release:** v0.8.3. Independent of `fix-backup-system-failures` (C44) and touches no backup script.