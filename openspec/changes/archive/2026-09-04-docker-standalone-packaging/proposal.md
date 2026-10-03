## Why

Deploying or testing iqoqo using Docker Compose outside a full git checkout (such as in `/opt/pre.iqoqo` or on clean standalone servers) currently fails because container definitions depend directly on host repository files. Specifically, `deploy/Dockerfile.nginx` does not bundle `deploy/nginx.conf` into the image, GitHub Actions does not build or publish an `iqoqo-nginx` image to GHCR, and `docker-compose.yml` mounts host paths (such as `./scripts` and `./deploy/nginx.conf`) that create empty host directories and shadow container code or fail file mounts. Furthermore, developers lack a unified local image-building script and documentation to build and test the full multi-image stack locally before merging pull requests and triggering official GitHub releases.

Addressing this now enables seamless pre-release testing of Docker images in preview environments and allows iqoqo to be distributed as a standalone Docker stack requiring only a compose specification and `.env` file.

## What Changes

- **Self-Contained Nginx Container**: Bundle `deploy/nginx.conf` into `/etc/nginx/conf.d/default.conf` in `deploy/Dockerfile.nginx` so the image runs out-of-the-box without requiring host config bind-mounts.
- **CI/CD Publishing of `iqoqo-nginx`**: Update `.github/workflows/deploy.yml` and `.github/workflows/release.yml` to build and publish `iqoqo-nginx` to GitHub Container Registry alongside `iqoqo-backend` and `iqoqo-frontend`.
- **Prebuilt Compose Decoupling**: Update `docker-compose.prebuilt.yml` to reference `${IMAGE_PREFIX:-}iqoqo-nginx:${APP_VERSION:-preview}` without requiring `./deploy/nginx.conf` on the host, and override `web` and `worker` to drop the destructive `./scripts:/usr/src/app/scripts` bind-mount.
- **Preserve Production Host Paths**: Retain `./app/static/covers`, `./app/static/gallery`, and `./exports` as host paths to ensure zero migration risk for production and maintain full compatibility with `scripts/clone.sh` and `scripts/cloud_backup.sh`.
- **Unified Local Multi-Image Build Script**: Introduce `scripts/build_docker_images.sh` and Makefile targets (`make docker-build [TAG=...]`) to build all three images (`backend`, `frontend`, `nginx`) locally with arbitrary tags (such as `preview` or specific release versions).
- **Pre-Release Testing Documentation**: Update `docs/RELEASE_PROCESS.md` to guide developers and operators through building local images, launching the prebuilt stack in test directories like `/opt/pre.iqoqo`, and cloning database and assets from production before merging PRs.

## Capabilities

### New Capabilities
- `docker-standalone-packaging`: Covers self-contained Nginx image packaging, prebuilt Docker Compose decoupling, unified multi-image local build tooling, and pre-release testing procedures.

### Modified Capabilities
*(None - existing spec requirements are unchanged)*

## Impact

- **Docker Images**: New image `iqoqo-nginx` published to GHCR. `deploy/Dockerfile.nginx` updated.
- **Compose Files**: `docker-compose.prebuilt.yml` updated to define `nginx` service and remove `./scripts` mount.
- **Tooling**: New script `scripts/build_docker_images.sh`, updated `scripts/test_docker_builds.sh`, and new Makefile targets.
- **CI/CD Workflows**: `.github/workflows/deploy.yml` and `.github/workflows/release.yml` now build and push `iqoqo-nginx`.
- **Documentation**: `docs/RELEASE_PROCESS.md` updated with local image build and pre-release testing instructions.
- **Backward Compatibility**: Completely preserves existing host data paths and `scripts/clone.sh` compatibility.
