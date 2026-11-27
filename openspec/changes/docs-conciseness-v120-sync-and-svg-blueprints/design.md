## Context

Over rapid releases from `v0.8.0` through `v1.2.0`, documentation accumulated duplicated sections across core files while key operational contracts (`Valkey 8`, `federation`/`config` schemas, `preview-reconcile`, native S3/Glacier `S3_BUCKET_ARCHIVE`, `Item.physical_location`, Manifestation gallery/stats, mobile multi-server switching, 4-hop `7`-category `/graph` with canonical `lod:<digest>`) drifted out of sync. Additionally, `scripts/cloud_backup.sh` and `scripts/restore.sh` still archive `data/federation_keys` even though `app/core/federation_keys.py`, `.env.example`, and `Makefile` store keys in `data/keys`.

## Goals / Non-Goals

- **Goals:**
  - Make each doc file the Single Source of Truth (SSoT) for its domain, cutting redundant duplicated prose by ~30% across `ARCHITECTURE.md`, `INSTALL.md`, `API.md`, `OPERATIONS.md`, and `COVERS_SETUP.md`.
  - Fix every stale version, technology reference (`Redis` -> `Valkey 8`, `Oxigraph` -> `RDFLib`), broken Markdown formatting, and missing `v1.1.2`–`v1.2.0` capability.
  - Reconcile `data/keys/` vs `data/federation_keys/` cleanly in backup/restore scripts (supporting legacy `data/federation_keys` fallback if present while prioritizing canonical `data/keys`).
  - Update `.context/notes/docs/docs-iqoqo-architecture-blueprints.md` so the human can regenerate all 10 drifted SVG diagrams cleanly, then verify byte-parity and AGPL XML headers.
- **Non-Goals:**
  - Never hand-edit `.svg` XML diagram paths directly from an AI agent (prose blueprint update + human SVG regeneration + byte-sync script check only).

## Decisions

1. **Single-Source-of-Truth Documentation Map:**
   - `INSTALL.md`: First-time install, `.env`, migrations, troubleshooting.
   - `DEPLOYMENT.md`: Production/preview Compose, `preview-reconcile`, container hardening.
   - `BACKUPS.md`: Unified daily + cold archive (`S3Service` & `rclone`), health checks, DR restore.
   - `API.md`: Auth, endpoints, OpenAPI 3.1 contract pointer (`GET /api/docs/openapi.json`), errors (linking verbose Semantic Web curls to `SEMANTIC_WEB.md`).
   - `ARCHITECTURE.md`: High-level FRBRoo + multi-schema DB (`19 FKs / 13 tables`), service topology, visual blueprints.
   - `docs/archive/`: Historical migration runbooks (`UPGRADE_0.8.0.md`, `UPGRADE_POSTGRES_18.md`).
2. **Safe Federation Key Path Reconciliation:**
   - Update `scripts/cloud_backup.sh` to archive `data/keys` (and also preserve `data/federation_keys` if present for backward compatibility), matching `app/core/federation_keys.py` and `SVG 12`.
3. **Human-in-the-Loop SVG Synchronization:**
   - Task completion for SVGs produces updated `docs-iqoqo-architecture-blueprints.md`, pauses for human SVG regeneration of `01`–`08`, `10`, `12`, then copies updated files to `docs/images/architecture/` and `frontend/public/images/help/` and runs `make lint-markdown` + `./scripts/check_license.sh`.
