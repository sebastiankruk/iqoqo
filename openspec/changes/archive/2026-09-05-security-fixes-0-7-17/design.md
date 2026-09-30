## Context

We need to implement patches for four specific vulnerabilities identified in the 0.7.17 security review. See proposal.md for motivation and impact. These vulnerabilities span the backend API, frontend auth handling, and the Docker deployment configuration.

## Goals / Non-Goals

**Goals:**
- Completely eliminate the possibility of unauthorized screenshot access via IDOR or suffix collision.
- Secure the frontend redirect flow against Host Header injection.
- Ensure that no secrets or tokens are compiled into the exported Docker layers.
- Clean up unused docker-compose volume mounts.

**Non-Goals:**
- Redesigning the entire auth flow.
- Changing the storage backend for screenshots.
- Introducing a secret manager (we stick to existing volume mount strategies).

## Decisions

- **Feedback Authorization (Python):** Instead of using `att.endswith(filename)` and `next(...)` to fetch the first matched item, the system will use `os.path.basename` to extract the clean filename. It will then match tickets based on exact filename equality and ensure the current user has access to *at least one* of the matching tickets.
- **Host Validation (TypeScript):** We will introduce a strict domain allowlist (`isAllowedHost`) checking against `localhost`, `127.0.0.1`, `iqoqo.cc`, and its subdomains. If `X-Forwarded-Host` or `Host` headers do not match this allowlist, it will fall back to `url.host` preventing an open redirect to `evil.com`.
- **Nginx Proxy Config:** We will add explicit `proxy_set_header X-Forwarded-Host $http_host;` to the `/api/auth-exchange` location block in `nginx.conf` to sanitize upstream headers.
- **Docker Secrets Elimination:** Removing `COPY rclone.conf*` from `Dockerfile`. Instead, `docker-compose.yml` handles runtime ingestion via `${HOME}/.config/rclone/rclone.conf:/home/appuser/.config/rclone/rclone.conf:ro`. `Dockerfile` will just scaffold an empty directory with strict 0700 permissions.
- **Docker Compose Cleanup:** Remove `.allegro_token.json` mounts as Allegro auth has migrated to Redis/Postgres.

## Risks / Trade-offs

- **[Risk]** The allowlist for `isAllowedHost` might break custom domains in self-hosted environments.
  - **Mitigation:** Self-hosted users should rely on the `NEXT_PUBLIC_FRONTEND_URL` environment variable which bypasses the host header check, so this change primarily protects dynamic preview environments and local dev where the env var is missing.
- **[Risk]** Missing `rclone.conf` at runtime might crash the worker container.
  - **Mitigation:** The application logic handles missing rclone gracefully, treating backups as disabled.
