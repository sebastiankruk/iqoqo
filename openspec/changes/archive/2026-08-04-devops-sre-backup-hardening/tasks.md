## 1. Automated Backup Retention

- [x] 1.1 Add `boto3` to dependencies for AWS S3 interactions if not present
- [x] 1.2 Implement the daily rotation logic in `app/core/tasks.py` to count and manage local/Dropbox backups (7 daily, 5 weekly)
- [x] 1.3 Implement the archival logic in `app/core/tasks.py` to upload older backups to AWS S3 Glacier and delete them from Dropbox
- [x] 1.4 Write unit tests for the retention logic (mocking Dropbox and AWS APIs)

## 2. DEPLOY_TOKEN Cleanup

- [x] 2.1 Audit the `Makefile` and identify where `DEPLOY_TOKEN` is referenced during `make stats`
- [x] 2.2 If strictly unused, remove all references to `DEPLOY_TOKEN` in the `Makefile` and environment templates
- [x] 2.3 If optional, add conditional checks in the `Makefile` so `make stats` passes without it

## 3. Container Hardening

- [x] 3.1 Update `Dockerfile` to create an `appuser` and switch to it via `USER appuser`
- [x] 3.2 Adjust directory permissions (`chown`) during the Docker build so `appuser` can write to log and tmp directories
- [x] 3.3 Test container startup and verify no permission denied errors occur in standard workflows
