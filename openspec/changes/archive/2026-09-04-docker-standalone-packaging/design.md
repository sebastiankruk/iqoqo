## Context

Deployments in `/opt/pre.iqoqo` or clean server environments without a git checkout currently fail because `docker-compose.prebuilt.yml` inherits development-oriented bind mounts from `docker-compose.yml`. Missing files (such as `deploy/nginx.conf`) trigger Docker to create empty directories on the host, causing mount errors in runc, while empty host directories (such as `./scripts`) shadow pre-baked code inside the backend container.

Existing production (`/opt/iqoqo.cc`), disaster recovery backups (`scripts/cloud_backup.sh`), and environment cloning (`scripts/clone.sh`) rely on host directory paths for media assets (`app/static/covers`, `app/static/gallery`, `exports`). Database data is already isolated within the Docker named volume `postgres_data` and cloned via container streaming (`docker exec`).

## Goals / Non-Goals

**Goals:**
- Package a 100% self-contained `iqoqo-nginx` container image with virtual host routing built-in.
- Decouple `docker-compose.prebuilt.yml` so that prebuilt stacks run cleanly without host repository files or destructive `./scripts` shadowing.
- Provide a unified local image build script (`scripts/build_docker_images.sh`) and Makefile targets to build and tag all three images (`backend`, `frontend`, `nginx`) locally for pre-release validation.
- Publish `iqoqo-nginx` to GitHub Container Registry via GitHub Actions alongside backend and frontend images.
- Document the end-to-end workflow in `docs/RELEASE_PROCESS.md` for building local images, running in `/opt/pre.iqoqo`, and cloning DB and assets with `make clone`.

**Non-Goals:**
- Converting static media assets (`covers`, `gallery`) to Docker named volumes. Host directory paths are explicitly preserved to maintain zero production risk and 100% compatibility with `scripts/clone.sh`.
- Altering development workflow in `docker-compose.yml` (local developers still benefit from hot-reloading scripts and configs when running from source).

## Decisions

### 1. Bake Nginx Configuration into Dockerfile
- **Decision**: Add `COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf` to `deploy/Dockerfile.nginx`.
- **Rationale**: Eliminates the need to mount `deploy/nginx.conf` at runtime. The image is immediately functional upon pull or local build. Custom overrides remain possible via optional volume mounting.
- **Alternatives Considered**: Using runtime environment variable substitution (`envsubst`) or keeping the host bind mount. Rejected because host file mounts fail when the repository is not present.

### 2. Preserve Host Asset Paths for Production & Clone Safety
- **Decision**: Keep `./app/static/covers`, `./app/static/gallery`, and `./exports` as host paths.
- **Rationale**: Existing production stores media directly on host storage. `scripts/clone.sh` synchronizes covers between hosts using `rsync` across these host paths. `scripts/cloud_backup.sh` archives them directly. Switching to named volumes would require complex data migration and rewriting operational scripts.
- **Alternatives Considered**: Docker named volumes (`covers_data`, `gallery_data`). Rejected based on architectural review and risk to production data.

### 3. Decouple Prebuilt Compose Specification
- **Decision**: In `docker-compose.prebuilt.yml`, explicitly define `nginx` with `image: ${IMAGE_PREFIX:-}iqoqo-nginx:${APP_VERSION:-preview}` and override `web`/`worker` volumes to exclude `./scripts:/usr/src/app/scripts`.
- **Rationale**: The backend image (`deploy/Dockerfile`) already bakes `scripts/` into `/usr/src/app/scripts`. Omitting the bind mount in prebuilt mode ensures migration scripts (`fix_alembic.py`, `flask db upgrade`) execute reliably from the container image.
- **Alternatives Considered**: Requiring users to copy `scripts/` to the host. Rejected because it breaks standalone container encapsulation.

### 4. Parameterized Local Multi-Image Build Tooling
- **Decision**: Create `scripts/build_docker_images.sh` with `--tag <tag>` (defaulting to version from `pyproject.toml` or `preview`) and `--prefix <prefix>`. Add Makefile targets `make docker-build [TAG=...]` and `make docker-build-preview`.
- **Rationale**: Provides developers and SREs a repeatable, single-command method to build and tag `backend`, `frontend`, and `nginx` before merging PRs, matching what GitHub Actions produces during official releases.
- **Alternatives Considered**: Running three separate manual `docker build` commands. Rejected due to error-proneness and tag inconsistencies.

### 5. Publish `iqoqo-nginx` in GitHub Actions
- **Decision**: Update `.github/workflows/deploy.yml` and `release.yml` with metadata and build-push steps for `iqoqo-nginx`.
- **Rationale**: Completes the container suite on GHCR so downstream environments (`prod`, `preview`, standalone self-hosters) can pull complete stacks with zero build dependencies.

## Risks / Trade-offs

- **[Risk] Nginx routing drift between development and production** → Mitigation: Development and production use the exact same file (`deploy/nginx.conf`), with production baking it into the image and development bind-mounting it for live updates.
- **[Risk] Host directories created with root ownership by Docker** → Mitigation: `scripts/clone.sh` and deploy entrypoint verify and ensure non-root access permissions for UID 10001 (`appuser`).
- **[Risk] Missing `rclone.conf` or `.allegro_token.json`** → Mitigation: Ensure prebuilt compose mounts directories or gracefully handles absent optional configuration files without failing container startup.
