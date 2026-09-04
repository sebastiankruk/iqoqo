# docker-standalone-packaging Specification

## Purpose
Provides standalone container packaging, prebuilt Docker Compose decoupling, unified multi-image local build tooling, and release verification workflows for iqoqo.

## Requirements

### Requirement: Self-Contained Nginx Reverse Proxy Container
The Nginx container image SHALL package all virtual host routing rules, upstream resolvers, and rate-limiting directives internally so that it can start and route traffic without requiring a host configuration file bind-mount.

#### Scenario: Running Nginx container standalone
- **WHEN** the `iqoqo-nginx` container starts without `/etc/nginx/conf.d/default.conf` mounted from the host
- **THEN** Nginx loads its internal virtual host configuration
- **THEN** requests to `/api/` are forwarded to the API upstream and requests to `/` are forwarded to the frontend upstream
- **THEN** container initialization succeeds without missing-file or invalid mount errors

### Requirement: Decoupled Prebuilt Docker Compose Specification
The prebuilt Docker Compose specification (`docker-compose.prebuilt.yml`) SHALL define prebuilt images for all core services (backend, frontend, worker, and nginx) and SHALL NOT mount host application scripts over container-internal directories.

#### Scenario: Launching prebuilt stack from an empty directory
- **WHEN** `docker compose -f docker-compose.prebuilt.yml up -d` is executed in a directory containing only `.env`
- **THEN** all container images (`iqoqo-backend`, `iqoqo-frontend`, `iqoqo-nginx`, `db`, `redis`) start successfully
- **THEN** backend initialization scripts (`scripts/fix_alembic.py`, `flask db upgrade`) execute from within the container image without being shadowed by empty host directories
- **THEN** media assets and database dumps use host directory paths without breaking existing production filesystem structure

### Requirement: Multi-Image Local Build Tooling
The codebase SHALL provide a unified build script and Makefile targets that build all three custom container images (`iqoqo-backend`, `iqoqo-frontend`, and `iqoqo-nginx`) locally with configurable version tags.

#### Scenario: Building unreleased images locally
- **WHEN** an operator runs `./scripts/build_docker_images.sh --tag preview` or `make docker-build-preview`
- **THEN** the script builds `iqoqo-backend:preview`, `iqoqo-frontend:preview`, and `iqoqo-nginx:preview`
- **THEN** the resulting images are registered in the local Docker daemon and ready for pre-release validation

### Requirement: Automated Container Registry Publishing
GitHub Actions release and deployment workflows SHALL build and push the `iqoqo-nginx` container image to GitHub Container Registry alongside `iqoqo-backend` and `iqoqo-frontend`.

#### Scenario: Publishing release containers on merge to main
- **WHEN** a release PR is merged into `main` or a version tag is pushed
- **THEN** GitHub Actions builds and publishes `ghcr.io/<owner>/iqoqo-nginx:<version>` and `:latest`
- **THEN** the prebuilt container image is publicly pullable for standalone deployments
