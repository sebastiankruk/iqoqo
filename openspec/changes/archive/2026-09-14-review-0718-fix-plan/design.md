## Context

Following the v0.7.18 code review documented in `.context/notes/review/0.7.18/99-consolidated-findings.md`, 47 critical findings and 203 moderate architectural debt items require systematic remediation. Rather than performing an ad-hoc refactor across 412 files, the fixes are structured into 6 sequential batches ordered strictly by dependency and risk: Security & Secrets → Database Migrations → Backend API Performance → Ingestion & SSRF → Frontend Architecture → Operational Guardrails & Governance.

## Goals / Non-Goals

**Goals:**
- Eliminate all 46 active critical defects across the backend, frontend, database, scripts, and deployment configurations.
- Provide a 100% safe, automated migration bridge for existing production databases at revision `f65648a6aaf4` (clean v0.7.17) when upgrading to the squashed `v0_7_18_baseline`.
- Transparently encrypt all 16 sensitive API keys and live OAuth token data at rest in `InstanceSettings`.
- Decouple Prometheus legacy metrics in favor of OpenObserve + OpenTelemetry.
- Prevent regressions by embedding persistent development rules into `.agent/rules/` and agent skills.

**Non-Goals:**
- Full architectural decomposition of the 1461-line `frontend/components/admin/frbr-editor.tsx` (deferred to the planned v0.8.0 Federation milestone; only unwired controls will be disabled with tooltips in v0.7.18).
- Rewriting FRBR tree refetches into optimistic React Query caches (scheduled for v0.8.0).
- Rewriting working external provider scrapers beyond fixing confirmed bugs (operator precedence in `default.py`, SSRF in `covers.py`, and mechanics unwrap in `boardgame.ts`).

## Decisions

### Decision 1: Centralized Symmetric Fernet Encryption for `InstanceSettings`
- **Choice:** Implement transparent encryption and decryption directly inside `InstanceSettings.get_value()` and `InstanceSettings.set_value()` in `app/db/settings.py` using cryptography's `Fernet` derived from the application `SECRET_KEY`.
- **Alternatives Considered:**
  - *Per-endpoint encryption:* Error-prone; developers could forget to call encryption before saving new settings.
  - *PostgreSQL pgcrypto:* Requires database extensions and ties encryption keys to database storage.
  - *HashiCorp Vault / KMS:* Excessive operational overhead for a local-first/self-hosted deployment.

### Decision 2: Elimination of Prometheus Route in Favor of OpenObserve
- **Choice:** Delete `frontend/app/metrics/route.ts` entirely and drop `prom-client` from `frontend/package.json`.
- **Rationale:** OpenObserve + OpenTelemetry Collector was officially adopted as the system monitoring stack in `docs/CHANGELOG.md:368`. Neither local nor production collectors scrape `/metrics`. Eliminating dead code permanently removes an unauthenticated endpoint rather than maintaining dead security scaffolding.

### Decision 3: Single Baseline Migration with Revision Stamp Bridge
- **Choice:** Squash all 55 historical migrations down to a single `v0_7_18_baseline.py`. In `migrations/env.py` and `run.sh`, implement an automated bridge that inspects `alembic_version.version_num`: if set to `f65648a6aaf4` (the single unified head of clean v0.7.17), execute `alembic_version = 'v0_7_18_baseline'` without executing table creation DDL. Fresh installations execute baseline creation directly.
- **Alternatives Considered:**
  - *Retaining all 55 migrations:* Retains 4 merge conflict heads, duplicate revisions, and risky 500-line downgrade blocks.
  - *Squashing without a bridge:* Existing production deployments would crash with `Can't locate revision identified by 'f65648a6aaf4'`.

### Decision 4: Two-Phase FRBR Editor Stabilization for v0.8.0
- **Choice:** For v0.7.18, disable unwired "Add Child" and "Escalate/Delete" controls in `frontend/components/admin/frbr-editor.tsx` and attach "Coming in v0.8.0" badges. Full file decomposition and optimistic tree state management are formally scheduled for the v0.8.0 milestone.
- **Rationale:** Decomposing 1461 lines right before a scheduled rewrite in the upcoming milestone represents wasteful churn. Disabling dead buttons immediately cures user confusion without risky refactoring.

### Decision 5: Dedicated Migration Service in Docker Compose
- **Choice:** Move `flask db upgrade` out of the application entrypoint `run.sh` into a dedicated `migration` one-shot container in `docker-compose.yml` that exits before the `web` container starts.
- **Rationale:** Prevents race conditions during multi-worker or replica startups and ensures web servers never bind ports against half-migrated schemas.

### Decision 6: Agent Governance Hardening Against Regressions
- **Choice:** Update `.agent/rules/iqoqo-standards.md` and related skills (`implementation-expert`, `security-auditor`, `test-craftsman`) with strict rules: mandatory Fernet encryption for secrets, SQL-level pagination for API lists, prohibition of unwired UI buttons, and single-head Alembic checks.

## Risks / Trade-offs

- **[Risk] Existing non-standard database versions in development** → Mitigation: Bridge checks if table `items` exists in schema `inventory` or `catalog`; if tables exist but revision is an older interim branch, it stamps baseline after running a schema integrity check.
- **[Risk] `SECRET_KEY` rotation invalidates stored encrypted settings** → Mitigation: Document `SECRET_KEY` persistence requirements in `.env.example` and provide a re-keying CLI utility in `scripts/`.
- **[Risk] Large Redis memory usage for taxonomy cache** → Mitigation: Set strict TTL (24 hours) and limit caching to consolidated taxonomy structures.

## Migration Plan

1. **Deploy Batch 1 & 2:** Execute migration bridge, squashing history to `v0_7_18_baseline` and applying transparent Fernet encryption to settings.
2. **Deploy Batch 3 & 4:** Roll out backend performance optimizations and ingestion fixes.
3. **Deploy Batch 5 & 6:** Roll out frontend cache fixes, FRBR button indicators, operational script safety prompts, and governance rule updates.
4. **Rollback Strategy:** Database backups before migration; git rollback to tag `v0.7.17` with preserved `alembic_version` if structural DDL issues arise.
