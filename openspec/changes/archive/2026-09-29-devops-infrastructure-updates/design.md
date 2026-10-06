## Context

As the iqoqo project progresses through v0.8.x toward federation and production stability, the infrastructure layer requires consolidation. Currently, the production container image built from `deploy/Dockerfile` exceeds 800MB due to build compilers and runtime utilities (notably the `rclone` binary). The existing Nginx configuration serves docker-compose networking but lacks a production-ready reference configuration with modern security headers, TLS termination, and asset caching. Furthermore, remote backups, cover synchronization, and feedback uploads rely on executing `rclone` CLI commands via `subprocess.run()`, requiring host mounts of plaintext `rclone.conf` credentials into container layers. Finally, 17 operational technical debt items (`MOD-OPS-01` through `MOD-OPS-17`) identified in the v0.7.18 architectural review remain open across Docker Compose definitions, operational shell scripts, linter configurations, and operational scripts.

See `proposal.md` for background motivation and `specs/infrastructure/devops-v082/spec.md` for normative requirements.

## Goals / Non-Goals

**Goals:**
- Optimize `deploy/Dockerfile` using multi-stage wheel compilation to achieve a verified image size below 500MB without sacrificing functionality.
- Provide a hardened `deploy/nginx.conf.example` reference template including TLS termination (TLSv1.2/1.3), rate limiting, static asset caching, and security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy).
- Replace external `rclone` CLI subprocess invocations with a unified Python S3 client (`app/core/s3_service.py` using `boto3`) supporting any S3-compatible cloud storage (AWS, MinIO, Cloudflare R2, Wasabi, Backblaze B2, Oracle Cloud Object Storage) configured purely via environment variables.
- Systematically remediate all 17 `MOD-OPS` operational findings across Docker Compose files, operational scripts, linter rules, and data maintenance utilities.

**Non-Goals:**
- Introducing Kubernetes manifests or Helm charts (iqoqo remains standardized on Docker Compose and single-node self-hosting for v0.8.x).
- Refactoring the core FRBR database models or Alembic schema (covered under changes C2 and C18).
- Provisioning remote cloud infrastructure automatically via Terraform/OpenTofu (instance admins supply standard S3 credentials).
- Modifying frontend runtime serving or Next.js build compilation.

## Decisions

### Decision 1: Multi-stage Docker build using isolated wheel compilation

- **Approach**: The build uses `python:3.14-slim` across two distinct stages:
  1. `builder` stage: Installs `build-essential` and system headers, runs `pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt`, compiling pure Python and C-extension wheels into a standalone staging directory.
  2. `runtime` stage: Installs only essential runtime system packages (`tesseract-ocr`), installs wheels from `/wheels` using `pip install --no-cache-dir --no-index --find-links=/wheels`, copies application source, and cleans all package lists.
- **Alternatives Considered**:
  - *Alpine Linux (`python:3.14-alpine`)*: Rejected due to musl libc incompatibility issues with `tesseract-ocr`, Pillow, and C-extensions, leading to fragile builds and compilation overhead. Debian slim with wheel compilation achieves <500MB reliably while maintaining full binary compatibility.
  - *Single-stage build with cleanup*: Rejected because intermediate apt dependencies and compiler libraries leave residual filesystem artifacts in container layers.

### Decision 2: Standalone `deploy/nginx.conf.example` reference configuration

- **Approach**: Keep `deploy/nginx.conf` for internal Docker mesh networking, but introduce `deploy/nginx.conf.example` as the canonical production reference. The reference includes:
  - `server_tokens off;`
  - SSL configuration adhering to Mozilla Modern/Intermediate guidelines (TLSv1.2 and TLSv1.3, ECDHE ciphers, session ticket caching).
  - Port 80 to 443 301 redirection.
  - Strict security headers: HSTS (`max-age=63072000; includeSubDomains; preload`), `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `Referrer-Policy strict-origin-when-cross-origin`, `Permissions-Policy` (disabling unused hardware features), and a Content Security Policy configured for Next.js and API endpoints.
  - Split rate limiting zones: `limit_req_zone` for general `/api/` (20r/s, burst 20) and `/api/scan` (5r/s, burst 5).
  - Static caching rules: `/_next/static/` set to `max-age=31536000, immutable`; `/static/covers/` and `/static/gallery/` set to `max-age=2592000, public, no-transform`.
- **Alternatives Considered**:
  - *Mutating existing `deploy/nginx.conf` in-place with mandatory SSL*: Rejected because local development and testing environments run behind HTTP on port 80 without SSL certificates; forcing SSL in the base compose configuration breaks local workflows.

### Decision 3: Native S3 Object Storage Service (`boto3`) replacing rclone

- **Approach**: Create `app/core/s3_service.py` providing a thread-safe, connection-pooled `S3Service` class encapsulating `boto3.client("s3")`:
  - Configuration parsed via standard environment variables: `S3_ENDPOINT_URL`, `S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_BACKUP`, `S3_BUCKET_COVERS`, `S3_BUCKET_FEEDBACK`.
  - Methods: `upload_file()`, `download_file()`, `upload_bytes()`, `get_bytes()`, and `delete_object()`.
  - Integrate into `BackupManager` (`app/core/tasks.py`), cover sync (`app/utils/images.py`, `app/utils/llm_covers.py`), and feedback screenshots (`app/api/feedback.py`).
  - Update `scripts/cloud_backup.sh` to support direct S3 uploads via AWS CLI or Python S3 runner if `rclone` is absent.
  - Remove `rclone` package installation and `/home/appuser/.config/rclone` directory setup from `deploy/Dockerfile` and `deploy/docker-entrypoint.sh`.
- **Alternatives Considered**:
  - *Keep rclone binary and update subprocess flags*: Rejected because spawning subprocesses is prone to blocking, process leakage, lacks fine-grained error reporting, and adds ~70MB of binary bloat to the container image.
  - *MinIO Python Client*: Rejected because `boto3` is standard across AWS S3, Cloudflare R2, Wasabi, Backblaze B2, MinIO, and Oracle Cloud Object Storage.

### Decision 4: Single dependency source via `pip-compile` (`MOD-OPS-05`)

- **Approach**: Maintain dependencies in `pyproject.toml` as the single canonical source of truth for runtime and development requirements. Use `pip-compile` from `pip-tools` to generate a frozen, reproducible `requirements.txt`.
- **Alternatives Considered**:
  - *Switching to Poetry or uv*: Rejected to minimize disruption to existing CI/CD, Dockerfile, and Makefile scripts during the v0.8.x cycle.

### Decision 5: Systematic Remediation of MOD-OPS Findings

- **Group A: Network & Environment Isolation**:
  - `MOD-OPS-01`: Update `docker-compose.local-ai.yml` port binding to `127.0.0.1:7860:3000`.
  - `MOD-OPS-09`: Document IPv6 limitations in `deploy/sandbox_proxy/proxy.py` HTTP CONNECT validation regex.
  - `MOD-OPS-10`: Remove hardcoded credentials from `scripts/iqoqo-status.sh` line 292; extract from environment.
  - `MOD-OPS-11`: Add `umask 077` at initialization in `scripts/cloud_backup.sh`.
  - `MOD-OPS-15`: Add regex filtering for credentials in `scripts/sync_agy_memory.sh`.
- **Group B: Process Safety & Memory Management**:
  - `MOD-OPS-02`: Increase graceful shutdown wait in `run.sh` from 5s to 15s before SIGKILL.
  - `MOD-OPS-03`: Create `.env.bak.<timestamp>` backup before `update_env_var` in `run.sh`.
  - `MOD-OPS-14`: Add `-P` flag to `df` in `scripts/cloud_backup_check.sh`.
  - `MOD-OPS-16`: Add `.yield_per(1000)` batch streaming in `scripts/archive_orphans.py`.
  - `MOD-OPS-17`: Refactor `scripts/sql_to_json.py` to stream SQL records line-by-line.
- **Group C: Build Tooling & Code Quality**:
  - `MOD-OPS-04`: Move inline `mykg-update` / `mykg-index` shell logic from `Makefile` to `scripts/mykg_sync.sh`.
  - `MOD-OPS-06`: Re-enable `W0511` (fixme/todo) in `.pylintrc`.
  - `MOD-OPS-07`: Incrementally re-enable docstring rules (`C0114, C0115, C0116`) for FRBR models in `.pylintrc`.
  - `MOD-OPS-08`: Lower `max-args` from 10 to 7 in `.pylintrc`; refactor high-argument functions into DTO dataclasses.
  - `MOD-OPS-12`: Replace hardcoded version string in `scripts/refetch_metadata.py` with dynamic version introspection.
  - `MOD-OPS-13`: Centralize role and permission definitions from `scripts/sync_db_permissions.py` into `app.core.permissions`.

## Risks / Trade-offs

- **[Risk] S3 Credentials Unconfigured**: Self-hosted users might not configure remote S3 storage.
  → *Mitigation*: `S3Service` gracefully falls back to local filesystem storage (`/data/backups`, local static directories) and logs an informative notice without raising uncaught exceptions.
- **[Risk] Content Security Policy (CSP) Interruption**: Tight CSP in `nginx.conf.example` could block Next.js server actions or external book cover images.
  → *Mitigation*: The CSP in `nginx.conf.example` explicitly whitelists Next.js inline scripts (`'unsafe-inline'` where necessary for hydration), image CDNs (`img-src 'self' data: https: blob:`), and local API domains.
- **[Risk] Pylint Stricter Checks Fail Existing CI**: Re-enabling docstrings or `max-args` might cause bulk linter failures.
  → *Mitigation*: Refactor affected functions into structured DTOs or apply targeted `# pylint: disable` annotations on legacy methods while enforcing stricter rules on all new code.

## Migration Plan

1. Update `deploy/Dockerfile` and test local build to confirm final size <500MB.
2. Update `deploy/docker-entrypoint.sh` to remove legacy rclone folder validation.
3. Deploy `deploy/nginx.conf.example` and update documentation in `docs/INSTALL.md` and `docs/SECURITY.md`.
4. Introduce `app/core/s3_service.py` with full unit test coverage (`tests/test_s3_service.py`).
5. Wire S3 client into tasks, feedback, and cover modules; update `.env.example`.
6. Apply `MOD-OPS-01` through `MOD-OPS-17` fixes across scripts, Makefiles, and configuration files.
7. Run `make lint && make test` to ensure zero regressions.
