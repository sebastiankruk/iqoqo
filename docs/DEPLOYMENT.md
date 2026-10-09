# iQoQo Deployment Directory Contract & Guide

Starting in **v0.8.3**, iQoQo establishes a formal, self-contained contract for source-free deployment directories (such as `/opt/pre.iqoqo` or `/opt/iqoqo`).

---

## 1. The Deployment Directory Contract

A deployment directory is an isolated host directory that contains runtime configuration, Docker Compose specifications, and mounted data volumes. **It contains no application source code checkouts** (`app/`, `frontend/`, `tests/`, etc.).

### Contract Rules

1. **Self-Contained Runtime Files**:
   - Runtime assets executed or mounted into containers (`scripts/`, `shared/`, `deploy/nginx.conf`, and `docs/ontology/`) **MUST** exist as real files inside the deployment directory.
   - They **MUST NOT** be symlinks resolving outside the deployment directory.
   - Symlinks resolving *within* the deployment directory are permitted.

2. **Single Source of Truth for Environment Configuration**:
   - Exactly one `.env` file describes a deployment (`<DEPLOY_DIR>/.env`).
   - All tools, diagnostics (`make status`), backups, and Compose operations read this file directly. Diagnostics never fall back to an unrelated checkout's `.env`.

3. **Pre-Flight Mount Guards**:
   - File-target bind mount sources (`.allegro_token.json`, `deploy/nginx.conf`) **MUST** be regular files, never directories.
   - Directory-target bind mount sources (`data/`, `exports/`, `app/static/covers/`, `gallery/`, `uploads/`, `shared/`, `scripts/`, `docs/ontology/`) are created with the application user's ownership and explicit permissions (`0755`) prior to `docker compose up`, preventing Docker from silently creating them as root-owned directories.
   - Sensitive environment files (`.env`) are tightened to `0600`.

4. **Ontology Validation**:
   - Canonical OWL and SHACL schemas (`docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl`) are mounted read-only into running service containers (`web`, `migration`), allowing operational validation scripts (`scripts/sync_ontology.py`) to run against live files.

5. **Lifecycle & Maintenance**:
   - Application data directories are strictly protected from accidental deletion.
   - Debris (unrecognized files) is reported.
   - Secret backup snapshots (`.env.bak.*`) are pruned beyond a retention threshold (default: 5) after explicit operator confirmation.

---

## 2. Directory Layout Reference

| Path | Type | Role | Lifecycle |
| ---- | ---- | ---- | --------- |
| `.env` | File (`0600`) | Instance configuration & secrets | Managed by operator / key rotation |
| `.deploy_manifest.json` | File | Manifest of synced runtime files & SHA-256 hashes | Managed by `deploy-sync` |
| `.allegro_token.json` | File (`0600`) | Allegro OAuth credentials | Created by pre-flight / managed by app |
| `docker-compose.yml` | File | Base compose specification | Synced by `deploy-sync` |
| `docker-compose.prebuilt.yml` | File | Prebuilt container images override | Synced by `deploy-sync` |
| `docker-compose.monitoring.yml` | File | OpenObserve & OTel Collector specification | Synced by `deploy-sync` |
| `scripts/` | Directory | Operational CLI scripts & migrations | Synced by `deploy-sync` |
| `shared/` | Directory | Permissions YAML, taxonomies, mappings | Synced by `deploy-sync` |
| `deploy/nginx.conf` | File | Nginx reverse proxy configuration | Synced by `deploy-sync` |
| `deploy/otel-collector-local.yaml` | File | OTel Collector dev/preview configuration | Synced by `deploy-sync` |
| `deploy/otel-collector-prod.yaml` | File | OTel Collector production configuration | Synced by `deploy-sync` |
| `docs/ontology/` | Directory | Canonical OWL ontology & SHACL shapes | Synced by `deploy-sync` |
| `data/` | Directory | SQLite DBs (e.g. GeoNames gazetteer) | **Application Data** (Preserved) |
| `exports/` | Directory | Data dumps & exported records | **Application Data** (Preserved) |
| `app/static/covers/` | Directory | Media cover assets | **Application Data** (Preserved) |
| `app/static/gallery/` | Directory | Gallery photos & scans | **Application Data** (Preserved) |
| `app/static/uploads/` | Directory | Uploaded attachments | **Application Data** (Preserved) |

---

## 3. Operational Makefile Targets

Manage deployment directories directly via `make`:

```bash
# 1. Validate layout against the contract
make deploy-validate [DIR=/opt/pre.iqoqo]

# 2. Materialise / sync runtime files and generate manifest
make deploy-sync [DIR=/opt/pre.iqoqo]

# 3. Check for drift against manifest
make deploy-verify [DIR=/opt/pre.iqoqo]

# 4. Report debris and prune .env snapshots (default: dry run report)
make deploy-maintain [DIR=/opt/pre.iqoqo]
# With pruning enabled:
make deploy-maintain [DIR=/opt/pre.iqoqo] ARGS="--prune"

# 5. Start preview environment in DEPLOY_DIR (runs sync & mount pre-flight)
make preview-up

# 6. Stop preview environment cleanly
make preview-down

# 7. Check health of preview stack reading DEPLOY_DIR/.env
make status preview
```

---

## 4. Deploy Paths & Shared Guards

iQoQo supports two deployment workflows:

1. **Host Checkout Dev / Direct Path (`./run.sh dev|prod`)**:
   - Runs directly out of a developer or server repository checkout.
   - Executes pre-deploy mount preparation (`scripts/pre_deploy_mounts.py .`).
   - Tightens `.env` to `0600`.
   - Generates and verifies secrets with `scripts/ensure_env_secrets.py`.
   - Provisions OpenObserve RUM token.

2. **Source-Free Deployment Directory Path (`make preview-up` or `make deploy-sync`)**:
   - Deploys into an isolated `DEPLOY_DIR` (default: `/opt/pre.iqoqo`).
   - Copies runtime files, removing external symlinks.
   - Executes pre-deploy mount preparation (`scripts/pre_deploy_mounts.py $(DEPLOY_DIR)`).
   - Tightens `$(DEPLOY_DIR)/.env` to `0600`.
   - Generates secrets and provisions RUM token in `$(DEPLOY_DIR)/.env`.
   - Launches stack via `docker compose --project-directory $(DEPLOY_DIR)`.

Both paths share identical mount validation and secrets hardening guards.

---

## 5. Observability Gotchas (OpenObserve)

When deploying OpenObserve in `docker-compose.monitoring.yml`:

- **Password Policy**: `ZO_ROOT_USER_PASSWORD` requires minimum 8 characters with at least one uppercase letter, one lowercase letter, one digit, and one special character (e.g. `!@#$%^&*()`). Passwords violating this policy cause OpenObserve to crash-loop on initialisation.
- **Initialisation-Only**: `ZO_ROOT_USER_PASSWORD` is evaluated only during the initial volume bootstrap. Changing `OPENOBSERVE_ROOT_PASSWORD` in `.env` afterwards will not update an existing database. If resetting credentials, reset via OpenObserve UI or recreate the `openobserve_data` volume.
