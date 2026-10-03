## Context

See `proposal.md` for the motivation of these DevOps and application resilience changes. This design details how we implement decoupling in our Makefile, correct Docker image naming, non-root execution support, and Redis failovers in Flask.

## Goals / Non-Goals

**Goals:**
- Completely remove host dependencies (Python/Node) from `make prod start prebuilt` and `make preview start prebuilt`.
- Provide a simple version check mechanism in the Makefile.
- Enforce explicit project names and image tags for Docker Compose to prevent orphans and conflicts.
- Ensure the container user `appuser` (10001) can read `rclone.conf` securely.
- Ensure the WSGI worker gracefully falls back to in-memory caching and rate-limiting if Redis is unavailable at startup.

**Non-Goals:**
- Do not change how non-prebuilt deploy targets build local code.
- Do not implement a complex high-availability Redis setup (just a simple degradation fallback).

## Decisions

**1. Makefile Prebuilt Targets**
- **Decision**: Refactor `start prebuilt` to strictly use `docker compose -f docker-compose.prebuilt.yml pull` and `up -d`.
- **Decision**: Add a `make version` or similar target/logic to check the current package version (e.g. from `package.json` or `pyproject.toml`) versus the image tag.

**2. Docker Image Tagging & Orphan Prevention**
- **Decision**: Set `COMPOSE_PROJECT_NAME=iqoqo-prod` or `iqoqo-preview` via environment variables or `.env` files loaded in Makefile targets. Update `docker-compose.prebuilt.yml` to use `image: iqoqo-backend:preview` and `image: iqoqo-frontend:preview` explicitly, avoiding implicit `preiqoqo-*` builds.
- **Decision**: Add `docker image prune -f` in pre-deploy hooks to clear dangling images and prevent host storage bloat.

**3. Rclone Permissions**
- **Decision**: In `deploy/Dockerfile`, use `COPY --chown=appuser:appuser rclone.conf /home/appuser/.config/rclone/rclone.conf`. Apply `RUN chmod 0600 /home/appuser/.config/rclone/rclone.conf`.
- **Rationale**: Strict permissions (`0600`) ensure secrets aren't exposed, and explicit chown ensures `appuser` (UID 10001) can read it without root access.

**4. Redis Fallback Initialization**
- **Decision**: In `app/__init__.py`, wrap the Redis connection check in a `try...except` block using `redis.Redis(..).ping()`. If it fails (e.g., `redis.exceptions.ConnectionError`), override `app.config['RATELIMIT_STORAGE_URI']` to `'memory://'` and `app.config['CACHE_TYPE']` to `'SimpleCache'`.
- **Rationale**: This is a robust way to degrade gracefully without crashing the Flask worker process.

## Risks / Trade-offs

- **Risk**: In-memory caching/rate-limiting fallback works per-process and won't sync across multiple workers.
  - **Mitigation**: This is acceptable as a temporary degradation state to keep the application running.
- **Risk**: Pruning dangling images might remove layers needed by other projects on the same host.
  - **Mitigation**: Standard behavior for `docker image prune` without `-a` is safe; it only removes untagged images with no containers.
