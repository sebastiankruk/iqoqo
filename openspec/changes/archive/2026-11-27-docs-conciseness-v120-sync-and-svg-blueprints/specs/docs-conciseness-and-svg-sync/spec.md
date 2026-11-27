# docs-conciseness-v120-sync-and-svg-blueprints Specification

## Purpose

Make iqoqo project documentation, in-product help, and architecture diagram blueprints concise, deduplicated, free of stale pre-`v1.2.0` claims, and synchronized with `v1.2.0` code and `data/keys/` paths.

## ADDED Requirements

### Requirement: Single-Source-of-Truth Documentation and Formatting Integrity

Project Markdown documentation (`README.md`, `docs/*.md`, `frontend/lib/help-articles.ts`) MUST eliminate duplicate runbooks across core files and contain zero broken Markdown escapes, split table headers, or truncated procedural sections.

#### Scenario: Auditing documentation quality and conciseness

- **GIVEN** `README.md`, `docs/*.md`, and `frontend/lib/help-articles.ts`
- **WHEN** `make lint-markdown` and documentation checks run
- **THEN** `docs/COVERS_SETUP.md` & `docs/auth-setup.md` MUST have clean code fences/inline code (no ``\`\`` escapes or truncated Section 6), `docs/INSTALL.md` & `docs/item_statuses.md` MUST have valid table headers, historical `0.8.0`/`PG18` upgrade docs MUST move to `docs/archive/`, and duplicated setup/backup/API/AI blocks MUST be consolidated with canonical cross-links

### Requirement: v1.2.0 Code-to-Docs Accuracy and Key-Path Reconciliation

All technical specifications (`Valkey 8`, `federation`/`config` schemas, `19 FKs / 13 tables`, Tailwind v4, RDFLib `sparql-runner`, `C154`–`C158`, `C163`–`C164`, and `data/keys/` backup path) MUST match the running `v1.2.0` codebase.

#### Scenario: Verifying backup key path and v1.2.0 feature docs

- **GIVEN** `scripts/cloud_backup.sh`, `scripts/restore.sh`, `docs/BACKUPS.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/MOBILE_*.md`, and `frontend/lib/help-articles.ts`
- **WHEN** compared against `v1.2.0` source code (`federation_keys.py`, `frbr_merge.py`, `graph_service.py`, `items.py`, `manifestations.py`, `storage.ts`)
- **THEN** backup/restore scripts and `BACKUPS.md` MUST handle `data/keys/` cleanly alongside `S3_BUCKET_ARCHIVE` / `--archive`, and docs + EN/PL help articles MUST accurately state `Valkey 8`, `depth 1..4`, `7` graph edge categories, `physical_location`, Manifestation stats/gallery, multi-server mobile switching, and canonical LOD dedupe

### Requirement: Architecture Blueprint Spec Alignment and SVG Parity Gate

`.context/notes/docs/docs-iqoqo-architecture-blueprints.md` MUST document all `v1.2.0` deltas for the 10 drifted SVGs (`01`–`08`, `10`, `12`), and synced SVGs in `docs/images/architecture/` and `frontend/public/images/help/` MUST maintain byte-parity and valid AGPL XML license headers.

#### Scenario: Preparing and syncing regenerated architecture SVGs

- **GIVEN** the updated `.context/notes/docs/docs-iqoqo-architecture-blueprints.md` and human-supplied regenerated SVGs (`01`–`08`, `10`, `12`)
- **WHEN** synced into `docs/images/architecture/` and `frontend/public/images/help/`
- **THEN** shared SVGs (`02`, `04`, `05`, `06`, `07`, `08`, `09`) MUST be byte-identical across both directories and `./scripts/check_license.sh` + `make lint-markdown` MUST pass
