## 1. Key Directory Alignment & Markdown Syntax Repairs

- [x] 1.1 Reconcile `data/keys/` vs `data/federation_keys/` across `scripts/cloud_backup.sh`, `scripts/restore.sh`, `docs/BACKUPS.md`, and `tests/bash/cloud_backup.bats` (archiving `data/keys` primarily with legacy fallback)
- [x] 1.2 Fix broken ``\`\`` escapes in `docs/COVERS_SETUP.md` & `docs/auth-setup.md`, complete truncated Section 6 of `docs/COVERS_SETUP.md`, and fix split table headers in `docs/INSTALL.md` & `docs/item_statuses.md`

## 2. Consolidate Bloat & Refresh Prose to v1.2.0

- [x] 2.1 Trim & deduplicate `docs/ARCHITECTURE.md`, `docs/INSTALL.md`, `docs/API.md`, `docs/OPERATIONS.md`, `docs/SEMANTIC_WEB.md`, `docs/MONITORING.md`, and `docs/COVERS_SETUP.md` + `docs/AI_COVERS.md`; archive `docs/UPGRADE_0.8.0.md` & `docs/UPGRADE_POSTGRES_18.md` under `docs/archive/`; refresh/prune `docs/MEMORY.md` & `docs/CONTEXT.md`
- [x] 2.2 Replace all stale `Redis 8` references with `Valkey 8`, fix `ARCHITECTURE.md` DB schema tables (`federation`, `config`) + Work merge counts (`19 FKs / 13 tables / 20 total`), fix `CONTRIBUTING.md` (`Tailwind CSS v4 + shadcn/ui`, `:8000`, SQLAlchemy 2.0), and fix `API.md` / `SECURITY.md` / `BACKUPS.md` / `TESTING.md` / `MOBILE_*.md` / `README.md` for `v1.1.1`–`v1.2.0` (`C154`–`C158`, `C163`–`C164`)
- [x] 2.3 Update `frontend/lib/help-articles.ts` (EN & PL) to remove stale `Oxigraph` / `TRUSTED-LIMITED-BLOCKED` / `depth 1..2` / `6` edge-category claims and document `physical_location`, Manifestation gallery/stats, multi-server mobile switching, and canonical LOD graph dedupe

## 3. Architecture Blueprint Spec & SVG Sync

- [x] 3.1 Update `.context/notes/docs/docs-iqoqo-architecture-blueprints.md` with exact `v1.2.0` deltas for the 10 drifted SVGs (`01`–`08`, `10`, `12`, prioritizing `03`, `08`, `10`, `12`)
- [x] 3.2 Prompt human to regenerate drifted `.svg` files; once supplied, sync byte-identical AGPL-headered SVGs across `docs/images/architecture/` and `frontend/public/images/help/`
- [x] 3.3 Run `IQOQO_AI_MODE=1 make lint-markdown`, `./scripts/check_license.sh`, and `IQOQO_AI_MODE=1 make test-scripts-bash`
