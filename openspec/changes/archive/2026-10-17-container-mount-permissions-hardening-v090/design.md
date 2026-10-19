## Context

With the container hardening introduced in the v0.8.x release stream, backend application processes in `iqoqo-backend` execute as an unprivileged user (`appuser`, UID 10001, GID 10001). However, docker-compose bind-mounts directories from the host filesystem directly:
- `./app/static/covers` -> `/usr/src/app/app/static/covers`
- `./app/static/gallery` -> `/usr/src/app/app/static/gallery`
- `./app/static/uploads/raw_covers` -> `/usr/src/app/app/static/uploads/raw_covers`
- `./exports` -> `/usr/src/app/exports`
- `./data` -> `/usr/src/app/data`

When developers or server administrators clone the repository or take backups, host permissions are set by default to `1000:1000` with standard umask (`drwxr-xr-x` / 755). Since UID 10001 is neither the owner nor in the primary group, write operations trigger unhandled `PermissionError: [Errno 13] Permission denied`. Because cover generation catches broad exceptions and sets `cover_status='failed'`, the failure is silent at startup and only surfaced when users scan books and notice missing covers in Collections or Fresh Arrivals views.

## Goals / Non-Goals

**Goals:**
- Provide proactive failure detection at container startup: assert directory write permissions in `deploy/docker-entrypoint.sh` and log clear actionable diagnostics before launching application workers.
- Ensure host orchestration scripts (`Makefile` targets `make start`, `make preview-up`) automate directory creation and permission adjustments (`chmod -R a+rwX` or directory group setup).
- Enhance the offline diagnostic suite (`scripts/iqoqo-status.sh`) to verify that the running web container can actually write to static cover, gallery, and export directories.
- Document the ownership invariant in operational runbooks.

**Non-Goals:**
- Modifying the non-root execution policy: we will NOT revert the backend container to run as `root`.
- Managing remote S3 bucket permissions (already handled in `app/core/s3_service.py`).
- Changing the internal layout or storage structure of covers and gallery assets.

## Decisions

### 1. In-Container Entrypoint Writability Assertions
- **Decision:** Check writability of `/usr/src/app/app/static/covers`, `/usr/src/app/app/static/gallery`, `/usr/src/app/exports`, and `/usr/src/app/data` inside `deploy/docker-entrypoint.sh` before executing `gunicorn` or `celery`.
- **Rationale:** The entrypoint executes in every container lifecycle before handing off to the application command. Checking with `[ -w "$dir" ]` or creating/removing a temporary probe file guarantees instant visibility in `docker logs`.
- **Alternatives considered:**
  - Running `chown` inside entrypoint: Rejected because entrypoint runs as non-root `appuser` (10001) and lacks privilege to change ownership of root/other-owned host mounts.
  - Sudo inside container: Rejected for security reasons (adds sudoers complexity and container attack surface).

### 2. Automated Host Target in Makefile (`ensure-mount-perms`)
- **Decision:** Add an `ensure-mount-perms` target in `Makefile` and include it as a prerequisite for `start` and `preview-up`.
- **Rationale:** Running on the host under the operator's shell user, it can safely ensure directories exist and grant group/other write permissions (`chmod -R a+rwX` or appropriate group mode) before launching Docker containers.
- **Alternatives considered:**
  - Requiring manual operator intervention: Error-prone and easily forgotten during upgrades or branch switches.

### 3. Container-Aware Diagnostic Check in `scripts/iqoqo-status.sh`
- **Decision:** In the `Covers` and `Exports` sections of `scripts/iqoqo-status.sh`, add a check via `docker exec "$web_cname" test -w ...` when running against containerized stacks (`STACK=prod` or `STACK=preview`).
- **Rationale:** `make status` is the canonical SRE preflight and post-migration validation gate; catching unwritable volumes here flags permission regressions immediately.

## Risks / Trade-offs

- **[Risk] Host security permissions** → Allowing `a+rwX` on static asset cache directories: In single-host container deployments, cover images and JSON exports are application cache artifacts without sensitive credentials (secrets are stored encrypted in PostgreSQL). Standard permission `a+rwX` on these directories is safe and avoids host/container UID collision.
- **[Risk] Docker volume recreation on remote hosts** → If volumes are mounted with `:ro`: Entrypoint check will fail fast and output explicit error messages pointing directly to `docker-compose.yml`.
