## 1. Self-Contained Nginx Packaging & Compose Decoupling

- [x] 1.1 Update `deploy/Dockerfile.nginx` to copy `deploy/nginx.conf` into `/etc/nginx/conf.d/default.conf` and verify container build succeeds.
- [x] 1.2 Update `docker-compose.prebuilt.yml` to define `nginx` service pulling `iqoqo-nginx:${APP_VERSION:-preview}` without requiring host config bind-mounts.
- [x] 1.3 Override `web` and `worker` volume mounts in `docker-compose.prebuilt.yml` to remove the `./scripts:/usr/src/app/scripts` mount, and verify compose config with `docker compose -f docker-compose.prebuilt.yml config`.

## 2. Unified Local Multi-Image Build Tooling

- [x] 2.1 Create `scripts/build_docker_images.sh` supporting `--tag`, `--prefix`, and building `backend`, `frontend`, and `nginx` images.
- [x] 2.2 Update `scripts/test_docker_builds.sh` and Bats tests in `tests/bash/test_docker_builds.bats` to validate building all three images.
- [x] 2.3 Add `docker-build` and `docker-build-preview` targets to `Makefile` and verify with `make -n docker-build-preview`.

## 3. CI/CD Publishing & Pipeline Automation

- [x] 3.1 Update `.github/workflows/deploy.yml` to build and push `iqoqo-nginx` to GitHub Container Registry.
- [x] 3.2 Update `.github/workflows/release.yml` to build and push `iqoqo-nginx` for tagged releases, and verify YAML syntax with `tests/bash/validate_yaml.bats`.

## 4. Documentation & Verification

- [x] 4.1 Update `docs/RELEASE_PROCESS.md` with detailed instructions on building local images, testing in `/opt/pre.iqoqo`, and cloning production DB and assets with `make clone`.
- [x] 4.2 Test local image build and execute prebuilt stack verification in `/opt/pre.iqoqo` to confirm `web` and `nginx` start cleanly without restart loops.
