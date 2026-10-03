## Purpose

Provides comprehensive DevOps, operational infrastructure, containerization, and reverse-proxy specifications for the iqoqo v0.8.2 milestone, ensuring production-hardened deployments, optimized container footprints, native cloud storage integration, and defensive operational scripts.

## ADDED Requirements

### Requirement: Multi-stage Docker Build Isolating Compilers from the Runtime
The production container image build process MUST employ multi-stage compilation to isolate build-time compilers and development headers, stripping bytecode and unused caches, so the runtime image carries no build toolchain.

#### Scenario: Building optimized production container
- **WHEN** the production Docker image is built using `deploy/Dockerfile`
- **THEN** compiler toolchains and build dependencies are isolated to the builder stage
- **THEN** the final runtime image excludes build tools, development packages, and unused binaries
- **THEN** the runtime installs pre-built wheels without a package index, so it cannot silently compile a source distribution
- **THEN** the build artifacts are transferred to the runtime stage without entering an image layer

The numeric size target is deliberately not stated here. C17 measured 826.7 MB against its own `<500MB` requirement, because `ImageHash` pulls in `scipy` and `numpy` (167 MB, 20% of the image) for a single function. Publishing an unmet figure as a requirement would make the specification actively wrong; the target and the work required to meet it are tracked by the `container-image-size-target` change.

### Requirement: Hardened Production Nginx Configuration Template
The deployment assets MUST provide a production-ready `deploy/nginx.conf.example` reverse-proxy configuration incorporating strict security headers, modern TLS termination, and request rate limiting.

#### Scenario: Deploying behind production Nginx reverse proxy
- **WHEN** an HTTP client requests the application through the production Nginx configuration
- **THEN** `server_tokens` is disabled to prevent server fingerprinting
- **THEN** response headers enforce `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `Referrer-Policy strict-origin-when-cross-origin`, and `Content-Security-Policy`
- **THEN** non-TLS HTTP requests to port 80 are redirected to HTTPS on port 443 with a 301 status code

#### Scenario: Rate limiting abuse protection
- **WHEN** client requests to `/api/` exceed 20 requests per second or requests to `/api/scan` exceed 5 requests per second
- **THEN** Nginx throttles or rejects excessive requests according to configured zone bursts

### Requirement: Static Asset Reverse Proxy Caching
The Nginx configuration MUST define explicit, performant caching directives for static web assets, distinguishing immutable assets from dynamic routes.

#### Scenario: Serving immutable Next.js static bundles
- **WHEN** a client requests assets under `/_next/static/`
- **THEN** Nginx responds with `Cache-Control: public, max-age=31536000, immutable`

#### Scenario: Serving media covers and gallery images
- **WHEN** a client requests files under `/static/covers/` or `/static/gallery/`
- **THEN** Nginx serves files directly from local storage with `Cache-Control: public, max-age=2592000, no-transform`

### Requirement: Native S3 Object Storage Service
The storage subsystem MUST use native S3 API protocols (`boto3`) for remote backup archive replication, cover image caching, and user feedback uploads, eliminating external CLI subprocess invocations and container credential file mounts.

#### Scenario: Uploading backup archive to S3 storage
- **WHEN** a backup archive upload is initiated with S3 credentials configured
- **THEN** the upload is executed natively via authenticated S3 PUT object API calls without invoking external `rclone` subprocesses
- **THEN** failure to connect or upload logs a descriptive error and raises an exception without crashing the host process

#### Scenario: Running container without mounted config files
- **WHEN** the backend application container starts up
- **THEN** S3 access is configured entirely through environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_BUCKET_BACKUP`)
- **THEN** no local configuration file in `/home/appuser/.config/rclone` is required or mounted

### Requirement: Local AI Service Network Interface Binding (MOD-OPS-01)
Auxiliary AI service definitions in `docker-compose.local-ai.yml` MUST bind exposed ports exclusively to the loopback interface (`127.0.0.1`) rather than public interfaces (`0.0.0.0`).

#### Scenario: Starting local AI container stack
- **WHEN** `docker compose -f docker-compose.local-ai.yml up` is executed
- **THEN** service port 7860 is bound exclusively to `127.0.0.1:7860` and is unreachable from external network interfaces

### Requirement: Process Signal Handling and Environment Safety (MOD-OPS-02, MOD-OPS-03)
Operational runtime scripts MUST allow sufficient graceful shutdown time before force-killing background tasks and MUST create backup snapshots before mutating environment configuration files.

#### Scenario: Gracefully stopping running instance via run.sh
- **WHEN** a stop signal is issued to the application processes via `run.sh`
- **THEN** the script sends SIGTERM and waits at least 15 seconds for clean termination before escalating to SIGKILL

#### Scenario: Mutating environment variable via run.sh
- **WHEN** `update_env_var` is invoked in `run.sh`
- **THEN** a backup of `.env` is created with a timestamped extension prior to in-place file modification

### Requirement: Operational Script Safety and Memory Streaming (MOD-OPS-04 to MOD-OPS-17)
Administrative and operational scripts MUST enforce strict file permissions, avoid hardcoded credentials, stream large dataset queries, and maintain clean build tooling.

#### Scenario: Executing cloud backup script
- **WHEN** `scripts/cloud_backup.sh` is executed
- **THEN** the script initializes with `umask 077` so that created archive files are restricted to owner read/write permissions only

#### Scenario: Checking cloud backup disk space
- **WHEN** `scripts/cloud_backup_check.sh` inspects available disk storage
- **THEN** `df -P` is executed to guarantee standard single-line POSIX output parsing regardless of filesystem mount name length

#### Scenario: Archiving orphan catalog records
- **WHEN** `scripts/archive_orphans.py` queries candidate records for archiving
- **THEN** database queries stream results using `.yield_per(1000)` chunks without buffering the full recordset in memory

#### Scenario: Exporting SQL records to JSON
- **WHEN** `scripts/sql_to_json.py` converts database dumps
- **THEN** data is processed and written line-by-line avoiding full-table memory accumulation
