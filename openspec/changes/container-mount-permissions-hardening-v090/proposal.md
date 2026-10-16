## Why

In production containers, the backend runs as an unprivileged non-root user (`appuser`, UID 10001). Host bind-mounted volumes (`./app/static/covers`, `./app/static/gallery`, `./app/static/uploads/raw_covers`, `./exports`, and `./data`) are frequently created with host-default UID 1000 ownership or mode 755. This causes silent runtime write failures (`PermissionError: [Errno 13] Permission denied`) during book scans, direct cover downloads, fallback PIL generation, and database exports. Hardening container entrypoint assertions, orchestration startup checks, and offline status diagnostics guarantees that volume mount write permission issues are caught immediately before serving traffic.

## What Changes

- Add pre-start directory writability assertions to `deploy/docker-entrypoint.sh` for critical bind-mount paths (`app/static/covers`, `app/static/gallery`, `exports`, `data`), failing fast with remediation commands if the non-root container user cannot write.
- Add an `ensure-mount-perms` prerequisite to `Makefile` startup targets (`make start`, `make preview-up`, etc.) that automatically creates mounted paths with group/other write permissions (`chmod -R a+rwX` or host-aligned `chown`).
- Extend `scripts/iqoqo-status.sh` to explicitly test inside the web container that mounted directories are writable by `appuser`.
- Update deployment guidelines and operational runbooks to codify container volume ownership invariants.

## Capabilities

### New Capabilities
- `container-mount-permissions-hardening`: Preflight verification and runtime assertion of write permissions for container bind-mounted volumes under unprivileged execution.

## Impact

- Affects `deploy/docker-entrypoint.sh`, `Makefile`, and `scripts/iqoqo-status.sh`.
- Affects host-mounted bind directories: `app/static/covers`, `app/static/gallery`, `app/static/uploads/raw_covers`, `exports`, and `data`.
- Zero database or API contract changes; purely operational resilience and platform hardening.
