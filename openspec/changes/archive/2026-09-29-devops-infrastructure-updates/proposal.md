## Why

As part of milestone v0.8.2 (Linked Data Extensions & Performance, deliverable C17), iqoqo requires critical operational hardening and infrastructure modernization. The current deployment stack suffers from container image bloat (>800MB), lacks an enterprise-ready production Nginx reference configuration with security headers and caching, relies on fragile CLI subprocess invocations of `rclone` requiring plaintext configuration mounts, and carries 17 unaddressed moderate operational findings (`MOD-OPS-01` through `MOD-OPS-17`) identified in the v0.7.18 architectural review. Resolving these items stabilizes instance deployments, reduces attack surfaces, optimizes resource utilization, and establishes production readiness.

## What Changes

- **Multi-Stage Docker Build Optimization**:
  - Optimize `deploy/Dockerfile` multi-stage build pipeline, compiling wheels and binary dependencies exclusively in the builder stage.
  - Remove extraneous runtime utilities (such as `rclone` CLI, build compilers, and header packages).
  - Clean package manager caches, bytecode (`.pyc`), and optimize `.dockerignore` context exclusions to guarantee a final image size under 500MB.
- **Production `deploy/nginx.conf.example`**:
  - Provide a production-grade Nginx configuration template implementing modern TLS termination (TLSv1.2/TLSv1.3, strong ciphers) and HTTP-to-HTTPS redirection.
  - Enforce comprehensive HTTP security headers: `server_tokens off;`, `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `Referrer-Policy strict-origin-when-cross-origin`, `Permissions-Policy`, and a tight `Content-Security-Policy`.
  - Configure rate limiting zones for general API traffic (`20r/s`) and resource-heavy scanner/OCR uploads (`5r/s`).
  - Configure optimized static asset caching policies: immutable long-term caching for `/_next/static/` (1 year) and 30-day caching with revalidation for cover art and gallery images.
- **Migration from rclone to Native S3 SDK (`boto3`)**:
  - Deprecate shell subprocess invocations (`subprocess.run(["rclone", ...])`) across the application runtime (`app/core/tasks.py`, `app/api/feedback.py`, `app/utils/images.py`, `app/utils/llm_covers.py`).
  - Introduce `app/core/s3_service.py` wrapping `boto3` to manage object storage operations (backup archiving, cover caching, feedback uploads).
  - Support any S3-compatible backend (AWS S3, MinIO, Cloudflare R2, Wasabi, Backblaze B2, Oracle Cloud Object Storage) using standard environment variables (`S3_ENDPOINT_URL`, `S3_REGION_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_BACKUP`, `S3_BUCKET_COVERS`, `S3_BUCKET_FEEDBACK`).
  - Eliminate the requirement to mount plaintext `rclone.conf` files into container filesystems (`/home/appuser/.config/rclone`).
- **17 Operational & Infrastructure Findings (`MOD-OPS-01` – `MOD-OPS-17`)**:
  - `MOD-OPS-01`: Restrict `docker-compose.local-ai.yml` port binding to `127.0.0.1:7860:3000` to prevent exposure on public network interfaces.
  - `MOD-OPS-02`: Increase graceful shutdown timeout in `run.sh` before issuing SIGKILL from 5s to 15s.
  - `MOD-OPS-03`: Create automatic `.env.bak` timestamped backups in `run.sh` prior to `update_env_var` file mutations.
  - `MOD-OPS-04`: Extract inline shell scripts for `mykg-update` and `mykg-index` in `Makefile` into dedicated scripts under `scripts/`.
  - `MOD-OPS-05`: Consolidate `pyproject.toml` and `requirements.txt` into a single deterministic dependency lockfile via `pip-compile`.
  - `MOD-OPS-06`: Re-enable `W0511` (fixme/todo) in `.pylintrc` to surface technical debt during CI runs.
  - `MOD-OPS-07`: Incrementally re-enable docstring rules (`C0114`, `C0115`, `C0116`) in `.pylintrc` for core FRBR models.
  - `MOD-OPS-08`: Lower `max-args` threshold from 10 to 7 in `.pylintrc` and refactor high-argument functions into DTO dataclasses.
  - `MOD-OPS-09`: Document IPv6 limitations in `deploy/sandbox_proxy/proxy.py` HTTP CONNECT validation regex.
  - `MOD-OPS-10`: Remove hardcoded OpenObserve default credentials in `scripts/iqoqo-status.sh` line 292, sourcing from environment variables.
  - `MOD-OPS-11`: Enforce `umask 077` at initialization in `scripts/cloud_backup.sh` to protect generated archives and temporary dumps.
  - `MOD-OPS-12`: Replace hardcoded version string in `scripts/refetch_metadata.py` line 41 with dynamic version introspection.
  - `MOD-OPS-13`: Centralize role and permission definitions from `scripts/sync_db_permissions.py` into `app.core.permissions`.
  - `MOD-OPS-14`: Add `-P` POSIX flag to `df` invocation in `scripts/cloud_backup_check.sh` to ensure stable single-line parsing across operating systems.
  - `MOD-OPS-15`: Add secret masking/filtering to `scripts/sync_agy_memory.sh` to prevent credential exposure in synced files.
  - `MOD-OPS-16`: Add `.yield_per(1000)` batch streaming in `scripts/archive_orphans.py` to prevent memory exhaustion during bulk orphan cleanup.
  - `MOD-OPS-17`: Stream SQL record conversion line-by-line in `scripts/sql_to_json.py` to prevent unbounded memory usage on large database dumps.

## Capabilities

### New Capabilities
- `infrastructure/devops-v082`: Comprehensive DevOps and operational infrastructure modernization for v0.8.2, encompassing multi-stage Docker build optimizations (<500MB target), production Nginx configuration with security headers and static caching, migration from rclone CLI subprocesses to native S3 SDK (`boto3`), and systematic remediation of 17 MOD-OPS operational findings.

### Modified Capabilities

## Impact

- **Containerization**: `deploy/Dockerfile`, `deploy/docker-entrypoint.sh`, `.dockerignore`, `docker-compose.yml`, `docker-compose.local-ai.yml`. Image size reduced by ~40% (under 500MB target) and container secret mounting eliminated.
- **Web Server & Reverse Proxy**: New `deploy/nginx.conf.example` reference configuration providing TLS termination, security headers, rate limiting, and asset caching for production self-hosting.
- **Storage Subsystem**: Deprecates `rclone` binary dependency; introduces `app/core/s3_service.py` using `boto3`. Replaces subprocess calls in `app/core/tasks.py`, `app/api/feedback.py`, `app/utils/images.py`, and `app/utils/llm_covers.py`.
- **Developer Experience & Tooling**: `Makefile`, `.pylintrc`, `requirements.txt`, `pyproject.toml`, and scripts in `scripts/` (`run.sh`, `cloud_backup.sh`, `cloud_backup_check.sh`, `sync_agy_memory.sh`, `archive_orphans.py`, `sql_to_json.py`, `iqoqo-status.sh`, `refetch_metadata.py`, `sync_db_permissions.py`).
- **Dependencies**: Adds `boto3` / `botocore` to backend requirements; removes system package dependency on `rclone`.
