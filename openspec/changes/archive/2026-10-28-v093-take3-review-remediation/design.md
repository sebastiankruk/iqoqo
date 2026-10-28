## Context

`release/0.9.3` (`main..ac85446`) integrates asynchronous SSE/Celery transitions (`C84`), Personal Access Tokens and TOTP 2FA (`C85`), BoardGameGeek2/IGDB diagnostics (`C86`), 100% OpenAPI 3.1 contract generation (`C87`), and Federation Trust/Key hardening (`C87d`). The Take 3 Principal Code Review (`release-0.9.3-principal-review-take-3.md`) audited all 158 changed files across runtime Docker/Gunicorn topology, Next.js BFF origin headers, SQLAlchemy 2.0 ORM definitions, and ActivityPub handlers, identifying 7 immediate release blockers plus 40 moderate/low issues that must be remediated before cutting the `v0.9.3` tag (see `proposal.md`).

## Goals / Non-Goals

**Goals:**
- Eliminate Gunicorn synchronous worker starvation and 30s `SIGABRT` worker kills caused by SSE connections while keeping container memory within Oracle Free Tier / local Docker budgets.
- Close all security bypasses uncovered in Take 3: `/api/auth-exchange` `X-Forwarded-Host` open redirects, 6 port-stripping `urlparse(...).hostname` ActivityPub lookups, `handle_follow` `or` auto-accept bypass and state overwrites, `?token=` SSE query-string credential leakage, TOTP 90s replay, cross-origin NodeInfo `instance_actor` pollution, and `optional_auth` missing PAT scope checks.
- Make `batch_fts_reindex` perform genuine PostgreSQL `Work.search_vector` (`to_tsvector`) updates with Redis `NX EX` task coalescing, pooled Redis connections, and owner-scoped `fts_reindexed` SSE invalidations.
- Achieve 1:1 parity across `InstanceSettings` atomic updates, DER key fingerprints, OpenAPI 3.1 schemas, `docs/API.md`, bilingual (`en`/`pl`) `/profile` PAT/TOTP UI, and automated regression suites without introducing any new Alembic schema migration.

**Non-Goals:**
- Introducing ASGI/Uvicorn/Hypercorn or rewriting Flask into async views (Gunicorn `gthread` solves SSE concurrency cleanly within WSGI).
- Adding new database columns or Alembic migrations on top of `v0_9_3_pats` (all fixes—including Redis/cache-backed TOTP replay tracking—operate against the existing linear migration head).
- Re-architecting `peer-frontend` into a separate Nginx container (deferrable to `C89` domain/proxy consolidation; binding `127.0.0.1` closes the immediate exposure).

## Decisions

### 1. Gunicorn `gthread` Workers + `< GUNICORN_TIMEOUT` SSE Stream Window + Authenticated Client Gate
- **Decision**: Configure Gunicorn in `docker-compose.yml` with `--workers ${GUNICORN_WORKERS:-2} --worker-class gthread --threads ${GUNICORN_THREADS:-8} --timeout ${GUNICORN_TIMEOUT:-30}` (16 concurrent request threads across 2 processes), clamp `GET /api/v1/events/stream` `timeout` to `[1.0, 20.0]` seconds (default `20.0s`, heartbeat every `10.0s`), and gate `TransitionEventsListener` in `frontend/components/providers.tsx` on authenticated user state (`useProfile` / non-public pathname).
- **Rationale**: Under Gunicorn `sync` (`--threads 1`), `worker.notify()` only executes *between* requests, so a 30s generator kills the worker with `SIGABRT` and 2 open tabs block 100% of API traffic. `gthread` shares the loaded Python interpreter memory across 8 threads per worker while handling I/O-bound Redis Pub/Sub waits concurrently, and capping SSE stream duration at `20.0s` ensures every generator exits cleanly 10 seconds before Gunicorn's 30s timeout (browser `EventSource` reconnects seamlessly).
- **Alternatives considered**: `gevent` monkey-patching (risks subtle interactions with `psycopg` v3 / `cryptography` C extensions and OpenTelemetry contextvars).

### 2. Real PostgreSQL `Work.search_vector` Recomputation, Redis Debounce Lock & Scoped `fts_reindexed`
- **Decision**:
  1. Reuse a module-level thread-safe `redis.ConnectionPool` in `app/core/events.py` (shared with `app/core/tasks.py`) so `publish_transition_event`, `enqueue_fts_reindex`, and `batch_fts_reindex` do not leak TCP sockets on every call.
  2. In `enqueue_fts_reindex(entity_type, entity_id, user_id=None)`, guard `_in_memory_fts_queue` with a `threading.Lock()` and gate `batch_fts_reindex.apply_async(countdown=5)` on `client.set("iqoqo:fts_reindex_scheduled", "1", nx=True, ex=10)`, clearing the lock key at the start of `batch_fts_reindex` when atomically draining `iqoqo:fts_reindex_queue`.
  3. In `batch_fts_reindex`, resolve queued `work:<id>`, `manifestation:<id>` (`mani.expression.work_id`), and `item:<id>` (`item.manifestation.expression.work_id`) entries to deduplicated `Work` IDs (plus affected `Item.owner_id` UUIDs for item entries). On PostgreSQL, execute a bulk SQL `UPDATE works SET search_vector = to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(original_title, '') || ' ' || coalesce(description, '')) WHERE id IN (...)` (matching `Work` FTS indexing); on SQLite test dialects, recompute/serialize deterministic text into `Work.search_vector` or verify via dialect-aware update so unit tests observe real state transitions.
  4. Include `"fts_reindexed"` in owner-scoped delivery when triggered solely by private/user `item` mutations (attaching `user_id` per affected owner, or omitting global broadcast when only private items changed) so User A's private item edit never stampedes User B's TanStack Query caches.
- **Rationale**: `Manifestation.fts_simple` is already `GENERATED ALWAYS AS (...) STORED` in PostgreSQL, whereas `Work.search_vector` is a regular `TSVECTOR` column requiring explicit SQL maintenance.

### 3. Strict WHATWG `URL` Parsing in `/api/auth-exchange`
- **Decision**: Replace string-splitting in `frontend/app/api/auth-exchange/route.ts` with a parser that trims the first comma-delimited hop only if no commas exist (rejecting multi-value `X-Forwarded-Host` outright), rejects any input containing `/`, `\`, `@`, `?`, `#`, or whitespace, parses `new URL(\`https://${candidate}\`)`, verifies `parsed.username === ""`, `parsed.password === ""`, `parsed.pathname === "/"`, `parsed.search === ""`, `parsed.hash === ""`, validates `parsed.hostname` against strict hostname rules (`localhost`, `127.0.0.1`, `iqoqo.cc`, `*.iqoqo.cc`, or the configured `NEXT_PUBLIC_FRONTEND_URL` hostname), and returns `parsed.host`.
- **Rationale**: Eliminates RFC 3986 authority userinfo (`iqoqo.cc:80@evil.com`) and path-suffix (`evil.com/.iqoqo.cc`) confusion by never interpolating unparsed header text into a URL origin.

### 4. Uniform `clean_instance_domain`, Conjunctional Follow Consent & DER Key Fingerprints
- **Decision**:
  - Replace all 6 remaining `urlparse(...).hostname` calls (`receive_inbox`, `handle_create`, `handle_update`, `handle_delete`, `handle_announce`, `reconcile_activity`) with `clean_instance_domain(...)`.
  - Change `handle_follow` to `should_accept = bool(auto_accept and instance and instance.trust_level == TrustLevel.TRUSTED)`, and short-circuit when `existing` already has `FollowStatus.REJECTED` (return without mutating/notifying) or `FollowStatus.ACCEPTED` (re-send `Accept` idempotently without downgrading to `PENDING`).
  - Update `compute_pem_fingerprint` to parse the PEM via `cryptography.hazmat.primitives.serialization.load_pem_public_key` and hash `pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)`.
  - Filter peer `FederationActor` fingerprint queries in `app/api/admin.py` strictly to `FederationActor.actor_uri.like("%/api/federation/actor")` (verifying `actor.actor_uri.rstrip("/").endswith("/api/federation/actor")`), and verify `clean_instance_domain(instance_actor_url) == instance.domain` in `probe_instance_health` and `probe_registered_instances`.
- **Rationale**: Guarantees 1:1 alignment between runtime code, `C87d`'s canonical specifications, and `docs/SECURITY.md`.

### 5. Migration-Free RFC 6238 TOTP Replay Guard & PAT Scope Alignment
- **Decision**: Track accepted TOTP codes in `Flask-Caching` / Redis (`cache.get` / `cache.set` keyed by `f"totp_used:{user.id}:{time_step}:{code_digest}"` with `timeout=120`, backed by an in-process bounded TTL dict fallback if cache backend is null in isolated unit tests) inside `User.verify_totp` or the login/verify handler. Remove `?token=` query-string parsing from `_extract_token` in `app/api/decorators.py`, add 60s `last_used_at` throttling + `read:` scope enforcement to `optional_auth`, and align `"curator"`, `"sparql:query"`, and `"write:inventory"` across `create_token`, `require_auth`, `require_permission`, and `PatManagement`.
- **Rationale**: Prevents RFC 6238 TOTP replay within the `valid_window=1` (90s) window immediately in `v0.9.3` without adding a new Alembic migration before release freeze.

### 6. Two-Phase Atomic `_put_settings` & Bounded `ExportService` / OpenAPI Zero-Drift
- **Decision**: Refactor `_put_settings` in `app/api/admin.py` to validate every `(key, val)` pair first, then stage mutations via `InstanceSettings(..., commit=False)` (or flush without intermediate commits) alongside `EntityAuditLog` rows, followed by a single `db.session.commit()`. In `ExportService.export_rdf`, add `joinedload(Item.borrower)` and iterate with `.yield_per(500)` / bounded batching so large collections do not trigger N+1 queries or unconstrained ORM heap spikes. In `app/api/docs.py`, stamp `decorated._requires_auth = True` inside `@require_auth`, `@admin_required`, and `@admin_or_custodian_required` and inspect Flask's `rule._converters` to distinguish `UUIDConverter` / `UnicodeConverter` from `IntegerConverter`.

## Risks / Trade-offs

- **[Risk] Removing `?token=` on `/api/v1/events/stream` could break tests or clients passing tokens in URLs** -> **Mitigation**: Browser `EventSource` in `providers.tsx` already uses `withCredentials: true` (`HttpOnly` `iqoqo_session` cookie), and programmatic clients use `Authorization: Bearer`. Update `tests/test_sse_events.py` to pass `Authorization: Bearer` headers (and add an explicit regression test asserting `?token=` returns `401`).
- **[Risk] Changing `compute_pem_fingerprint` from raw PEM bytes to DER `SubjectPublicKeyInfo` bytes changes displayed `SHA256:...` values** -> **Mitigation**: `C87d` has not been released yet (`0.9.3` is still on the release branch), `FederationInstance` does not persist static fingerprints in DB columns (it computes them dynamically from cached `public_key_pem`), and DER hashing matches `docs/SECURITY.md` and `openssl pkey -pubin -outform DER | sha256sum`.
- **[Risk] `boardgamegeek` vs `boardgamegeek2` package coexistence in `.venv`** -> **Mitigation**: Both packages expose the `boardgamegeek` top-level module; `.venv` already has `boardgamegeek2==1.0.1` installed, so updating `requirements.txt` and `pyproject.toml` to `boardgamegeek2>=1.0.1` aligns fresh installs with `C86` without breaking imports.

## Migration Plan

1. No database schema migration is required (`alembic_version` remains at single head `v0_9_3_pats`).
2. Recreate `web` container (`docker compose up -d web`) when deploying `v0.9.3` so the updated Gunicorn `--worker-class gthread --threads 8` command takes effect.
3. Rollback is a clean `git revert` with zero database downgrade steps.
