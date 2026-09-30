## Why

Following the comprehensive pre-release code review of v0.7.18 documented in `99-consolidated-findings.md`, 47 critical defects (46 confirmed active defects + 1 dead code cleanup) and 203 moderate architectural debt items were identified across the codebase. Addressing these defects is essential before commencing the v0.8.0 Federation & Semantic Web milestone to guarantee data integrity, eliminate high-risk credential exposures, prevent memory exhaustion, ensure reliable production database migrations, stabilize frontend state synchronization, and establish preventative governance rules.

## What Changes

This change implements the 6 sequential execution batches defined in Section 4 of `99-consolidated-findings.md` and establishes persistent AI agent guardrails:

- **Batch 1 (Security & Secret Protection):** Encrypt all 16 secret keys and live tokens in `catalog.instance_settings` using symmetric Fernet encryption; mask secrets in admin endpoints; enforce strict rate limits on `/login`, `/register`, and `/settings/reveal`; switch sensitive GET routes to POST; use `hmac.compare_digest` for token comparisons; and eliminate vestigial Prometheus code (`metrics/route.ts` and `prom-client`).
- **Batch 2 (Database Schema & Migration Squashing):** Squash historical Alembic migrations down to a unified `v0_7_18_baseline`; implement an automated migration bridge in `migrations/env.py` and `run.sh` to safely stamp existing clean 0.7.17 databases (at head `f65648a6aaf4`) to the baseline without DDL failure; extract heavy unbatched data migrations to standalone operational scripts; isolate `instance_settings` into a dedicated `config` schema; and add missing check constraints and cascading delete rules.
- **Batch 3 (Backend API Performance & Memory Limits):** Replace Python-level list slicing in `get_items()` and `fetch_global_fresh_arrivals` with database-level SQL `LIMIT`/`OFFSET` and `DISTINCT ON`; eliminate N+1 query storms in `get_virtual_items` using eager loading (`selectinload`/`joinedload`); implement Redis caching for heavy FRBR taxonomy queries; replace O(N) roadmap reordering with LexoRank / differential SQL updates; and extract QR code SVG generation into `app/utils/qrcode.py`.
- **Batch 4 (Ingestion, SSRF & External Integrations):** Fix operator precedence bug in barcode ISBN fallback heuristic (`default.py:30`); route all external cover image downloads through SSRF-safe `safe_get`; and fix board game mechanics double-unwrap bug in `boardgame.ts`.
- **Batch 5 (Frontend Architecture & 0.8.0 Alignment):** Synchronize TanStack React Query invalidation keys across hooks and components; prune dead `getRecentManifestations` code; align FRBR Editor with the v0.8.0 roadmap by disabling unwired "Add Child" and "Escalate/Delete" controls with "Coming in v0.8.0" tooltips (deferring component split to v0.8.0); replace manual `setInterval` polling with React Query `refetchInterval`; and eliminate duplicate select options in bulk-add UI.
- **Batch 6 (Operational Guardrails, Test Reliability & Governance Protection):** Add interactive confirmation prompts and environment safeguards to destructive operational scripts (`clone.sh`, `init_db.py --reset`, `migrate_legacy.py --clear`); isolate database migrations into a dedicated Docker Compose service; remove hardcoded monitoring passwords; fix frontend test race conditions; and update project rules (`iqoqo-standards.md`) and agent skills (`implementation-expert`, `security-auditor`, `test-craftsman`) to permanently prevent regressions of these critical patterns.

## Capabilities

### New Capabilities
- `security-and-secrets`: Symmetric encryption for at-rest credentials in `InstanceSettings`, API key masking, rate limiting on authentication and secret reveal endpoints, POST-based token transport, constant-time token comparison, and elimination of dead Prometheus metrics routes.
- `database-schema-migrations`: Squashing 55 historical migrations to `v0_7_18_baseline`, backwards-compatible production upgrade bridge for clean 0.7.17 head `f65648a6aaf4`, extraction of data backfills into standalone CLI scripts, schema isolation for settings, and foreign key integrity.
- `backend-query-performance`: SQL-level pagination and deduplication for items and arrivals, eager loading to prevent N+1 query storms in virtual items, Redis caching for taxonomies, LexoRank differential roadmap reordering, and modular QR code utility extraction.
- `ingestion-and-integrations`: Operator precedence fix in scanner ISBN detection, SSRF prevention in cover image fetching, and correct API response unwrapping for board game taxonomies.
- `frontend-architecture`: TanStack Query cache key normalization, dead API client code pruning, FRBR Editor interim UX stabilization (disabling dead buttons with v0.8.0 tooltips), declarative query polling, and deduplication of bulk-add UI options.
- `operational-guardrails`: Interactive confirmation guards on destructive scripts, Zip Slip prevention, Docker Compose migration lifecycle separation, monitoring credential enforcement, test suite isolation, and agent governance rule hardening against regression.

### Modified Capabilities

None.

## Impact

- **Security Posture:** Eliminates plaintext secret storage in database, secures token exposure vectors, and removes unused public attack surfaces.
- **Database Operations:** Simplifies migration DAG from 55 files down to 1 baseline with automated migration bridging for zero-downtime upgrades from 0.7.17.
- **System Performance:** Resolves out-of-memory risks from unbounded pagination and N+1 query patterns.
- **Frontend Usability:** Prevents stale UI views and eliminates dead button clicks in FRBR Editor.
- **Agent Governance:** Strengthens project rules and agent skills to prevent recurring anti-patterns in future features.
