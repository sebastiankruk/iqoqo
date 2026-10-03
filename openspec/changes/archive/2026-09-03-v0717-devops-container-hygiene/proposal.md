## Why

Currently, deploying the application via prebuilt targets (`make prod start prebuilt`, `make preview start prebuilt`) has unintended host dependencies, can result in broken deployments due to naming conflicts, leaves dangling containers, suffers from potential root isolation issues with `rclone.conf`, and lacks resiliency when Redis is down during initialization. This change resolves these issues, ensuring smooth, reproducible, host-independent deployment processes, hardening infrastructure, and improving the developer experience and operational reliability.

## What Changes

- Decouple `make prod start prebuilt` and `make preview start prebuilt` in Makefile. They will now only invoke `docker compose -f docker-compose.prebuilt.yml pull` and `docker compose -f docker-compose.prebuilt.yml up -d`, requiring zero host Python/Node dependencies.
- Add version detection to quickly determine the current project folder version and the version installed via prebuilt make targets.
- Standardize project naming (`COMPOSE_PROJECT_NAME=iqoqo-prod` / `iqoqo-preview`) and enforce explicit image tagging (`iqoqo-backend:preview`, `iqoqo-frontend:preview`).
- Fix `preiqoqo-*` prefixed container images that break deployments.
- Add automated dangling image pruning in Makefile pre-deploy hooks.
- Enforce strict `0600` permissions on mounted `rclone.conf` configuration files in `deploy/Dockerfile`.
- Ensure runtime container user `appuser` (UID 10001) has read permissions on `/home/appuser/.config/rclone` to prevent silent backup task failures.
- Configure explicit fallback mechanisms for Flask-Limiter (`RATELIMIT_STORAGE_URI`) and Flask-Caching (`CACHE_REDIS_URL`) in `app/__init__.py`. If Redis is temporarily unreachable during startup, the WSGI worker gracefully degrades to in-memory fallback without crashing.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. `skip_specs: true` has been set since this is a pure devops/infrastructure change.

## Impact

- **Makefile**: Refactored prebuilt deployment targets, added image pruning hooks and version checks.
- **deploy/Dockerfile**: Modified file permissions for rclone config to enhance container security and non-root execution support.
- **docker-compose.prebuilt.yml & docker-compose.yml**: Updated image naming conventions and project isolation. Added/ensured correct rclone mount permissions.
- **app/__init__.py**: Enhanced fault tolerance for Redis connections to provide in-memory fallbacks for caching and rate limiting.
- **Tests**: Additional automated tests for the `Makefile` and Flask application resilience to guarantee functionality.
