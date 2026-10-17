## 1. Container Entrypoint Hardening

- [x] 1.1 Add volume writability verification loop in `deploy/docker-entrypoint.sh` for `app/static/covers`, `app/static/gallery`, `exports`, and `data`
- [x] 1.2 Format clear diagnostic failure output in `deploy/docker-entrypoint.sh` displaying failing paths, current effective UID/GID, and remediation command (`chmod -R a+rwX <dirs>`)
- [x] 1.3 Add test coverage for entrypoint writability validation under writable and unwritable mock environments

## 2. Orchestration Automation

- [x] 2.1 Add `ensure-mount-perms` target to `Makefile` ensuring host bind-mount paths exist and have `chmod -R a+rwX`
- [x] 2.2 Wire `ensure-mount-perms` as a prerequisite for `start`, `preview-up`, and other container lifecycle targets
- [x] 2.3 Verify `make ensure-mount-perms` behaves idempotently across local and CI execution environments

## 3. Status Diagnostics & Observability

- [x] 3.1 Extend `scripts/iqoqo-status.sh` to test container write permissions for static cover, gallery, and export volumes via `docker exec test -w`
- [x] 3.2 Add clear error diagnostics and remediation recommendations in status reports when container mounts are unwritable
- [x] 3.3 Update `tests/scripts/test_iqoqo_status.py` or script test suite to cover container mount writability assertions

## 4. Documentation & Operational Runbooks

- [x] 4.1 Document container non-root UID (10001) storage invariants and volume mount permissions in `docs/DEPLOYMENT.md`
- [x] 4.2 Add troubleshooting guide for resolving `PermissionError: [Errno 13]` during covers/exports in operational runbooks
