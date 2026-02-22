# Phase 4 Ubuntu Cutover Runbook

This runbook upgrades an existing Ubuntu-hosted iqoqo installation from old Flask-rendered UI to the new split architecture:

- Flask API (internal)
- Next.js frontend (internal)
- Nginx reverse proxy (public)

## Scope and assumptions

- You already have a running iqoqo instance on Ubuntu.
- PostgreSQL data should be preserved.
- You will deploy branch `dev/skruk/v0.0.2-phase4` (or a newer branch containing Phase 4 files).
- Docker Engine + Docker Compose plugin are installed.
- Cloudflare is configured to route `(www.)iqoqo.cc` to origin `http://localhost:8000`.

## 1) Prepare and backup

```bash
cd /opt/iqoqo

git fetch --all --tags

# Ensure you are on the version currently running in production (tag or commit)
git checkout <your-current-production-version>

git pull

cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

mkdir -p backups

docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backups/pre_phase4_$(date +%Y%m%d_%H%M%S).sql
```

If the current stack is not running yet, start only DB first and retry dump:

```bash
docker compose up -d db
```

## 2) Update environment for cutover

Edit `.env` and ensure these values exist:

```text
APP_PORT=8000
NEXT_PUBLIC_API_URL=/api
CORS_ENABLED=false
```

Notes:

- Keep your existing `DATABASE_URL`, `POSTGRES_*`, and `SECRET_KEY` values.
- CORS can stay disabled when frontend and API are served through the same origin via nginx.
- Keep `APP_PORT=8000` to match the Cloudflare origin expectation (`localhost:8000`).

## 3) Build and start Phase 4 stack

```bash
cd /opt/iqoqo

docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

Run migrations (safe/idempotent):

```bash
docker compose -f docker-compose.prod.yml --env-file .env exec web flask db upgrade
```

## 4) Smoke tests

```bash
# root should render frontend
curl -I http://localhost:${APP_PORT:-80}/

# API should be available behind nginx
curl -s http://localhost:${APP_PORT:-80}/api/health

# Containers should be healthy/running
docker compose -f docker-compose.prod.yml --env-file .env ps
```

Manual checks:

- Open `http://<your-server-ip-or-domain>/`
- Open scanner and collection pages.
- Add one test item and verify it appears in collection.

## 5) Rollback (if needed)

Stop Phase 4 stack:

```bash
docker compose -f docker-compose.prod.yml --env-file .env down
```

Return to previous stack:

```bash
git checkout <your-previous-stable-tag-or-commit>
docker compose --env-file .env up -d --build
```

If database restore is required:

```bash
# WARNING: destructive; run only if you must restore
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backups/pre_phase4_YYYYMMDD_HHMMSS.sql
```

## 6) Post-cutover cleanup (after 24h stable)

- Tag deployment commit (example: `v2.0.0`).
- Remove old web blueprint and static Flask UI code in a dedicated cleanup PR.
- Update docs and operational notes with any environment-specific tweaks.
