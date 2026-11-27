# MEMORY — iqoqo Dev Server

> **Last updated:** 2026-11-27  
> **Codebase snapshot:** iqoqo v1.2.0 monorepo

---

## 1. Project Identity

**iqoqo** is a self-hosted, local-first personal media catalog for physical collections (books, board games, movies, music, serials, maps, LEGO, puzzles). Built on the FRBR/FRBRoo ontology, it provides:

- A Python **Flask 3.1** backend with JWT/2FA/PAT auth, RBAC, Alembic migrations, ActivityPub federation, and PostgreSQL 18 multi-schema storage
- A **Next.js 16.4** frontend (App Router, shadcn/ui, Tailwind CSS v4) plus Capacitor 7 native Android/iOS dual build
- A **Celery** background worker with **Valkey 8** (`valkey/valkey:8-alpine`) broker/cache
- An isolated Python RDFLib **`sparql-runner`** service and **OpenObserve** telemetry stack
- Multi-tier **Rclone** + native boto3 `S3Service` backups (Daily sync, S3 Glacier cold archiving)
- Docker-based deployment with prebuilt GHCR images (`backend`, `frontend`, `nginx`, `sparql`)

**Owner/Context:** Sebastian Kruk, iqoqo project. Primary user is the developer building and using the system.

---

## 2. Current Codebase Structure

### Top-level Layout

```text
iqoqo/
├── app/                          # Python Flask backend
│   ├── __init__.py               # Flask app factory (create_app)
│   ├── config.py                 # Configuration loading
│   ├── api/                      # Flask blueprints (API routes)
│   │   ├── __init__.py           # api_bp registration
│   │   ├── auth.py               # JWT auth, login/signup, OAuth
│   │   ├── items.py              # /api/items CRUD + bulk operations
│   │   ├── manifestations.py     # /api/manifestations CRUD
│   │   ├── collections.py        # /api/collections CRUD
│   │   ├── works.py              # /api/works CRUD
│   │   ├── lending.py            # /api/lending CRUD
│   │   ├── scanner.py            # Barcode scanner + external API lookups
│   │   ├── admin.py              # /api/admin/* endpoints
│   │   ├── profile.py            # /api/profile endpoints
│   │   ├── public.py             # Public API endpoints
│   │   ├── feedback.py           # User feedback system
│   │   ├── social.py             # Social features
│   │   ├── sharing.py            # Item sharing
│   │   ├── roadmap.py            # Roadmap endpoints
│   │   ├── docs.py               # API documentation
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── decorators.py         # Auth/permission decorators
│   │   ├── filters.py            # Query filters
│   │   ├── core.py               # Core API utilities
│   │   ├── routes.py             # Route registration
│   │   ├── system.py             # System endpoints
│   │   └── taxonomies.py         # Taxonomy endpoints
│   ├── db/                       # Database layer
│   │   ├── __init__.py           # SQLAlchemy db instance
│   │   ├── core.py               # Database initialization
│   │   ├── models.py             # ORM models
│   │   └── schema.py             # DDL creation + seed data
│   ├── core/                     # Core business logic
│   │   ├── celery_app.py         # Celery task queue
│   │   ├── cache.py              # Flask-Caching
│   │   ├── limiter.py            # Rate limiting
│   │   ├── scheduler.py          # Background task scheduler
│   │   ├── telemetry.py          # OpenTelemetry observability
│   │   └── data_manager.py       # Data management
│   ├── strategies/               # Strategy pattern implementations
│   │   └── lookup/               # External API lookup strategies
│   ├── utils/                    # Utility modules
│   └── static/                   # Static assets
├── frontend/                     # Next.js 16 frontend (App Router + Capacitor 7)
│   ├── app/                      # App Router pages
│   │   ├── layout.tsx            # Root layout with providers
│   │   ├── page.tsx              # Home (collection stats)
│   │   ├── login/page.tsx        # Auth pages
│   │   ├── items/page.tsx        # Item catalog
│   │   ├── collections/page.tsx  # Collection list
│   │   └── admin/page.tsx        # Admin panel
│   ├── components/               # Reusable UI components
│   │   ├── ui/                   # shadcn/ui primitives
│   │   ├── layout/               # AppSidebar, header, notifications
│   │   ├── auth/                 # AuthContext, ProtectedRoute
│   │   ├── items/                # ItemForm, ItemCard, BarcodeScanner
│   │   ├── collections/          # CollectionForm, CollectionCard
│   │   ├── admin/                # UsersTable
│   │   ├── import/               # ImportWizard
│   │   ├── dashboard/            # StatsCards, Charts
│   │   ├── scanners/             # scanner components
│   │   ├── cover/                # Cover image components
│   │   ├── social/               # Social features
│   │   └── landing/              # Landing page components
│   ├── lib/                      # Utilities, API client
│   │   └── api/                  # API client (axios-based)
│   │       ├── client.ts         # Browser-side API client
│   │       ├── server-client.ts  # Server-side API client
│   │       └── hooks.ts          # React Query hooks
│   ├── hooks/                    # Custom React hooks
│   ├── types/                    # TypeScript type definitions
│   ├── i18n/                     # Internationalization
│   ├── messages/                 # i18n message files
│   ├── next.config.ts            # Next.js config with rewrites proxy
│   ├── proxy.ts                  # Middleware for auth routing
│   └── package.json
├── tests/                        # pytest test suite
│   ├── conftest.py               # Fixtures (client, db_session, etc.)
│   ├── test_auth.py
│   ├── test_items.py
│   ├── test_items_search.py
│   ├── test_collections.py
│   ├── test_migration.py
│   ├── test_scanner.py
│   ├── test_feedback_tickets.py
│   └── test_wishlist_media.py
├── frontend/__tests__/           # Frontend tests (Vitest + Playwright)
│   ├── vitest.config.ts
│   └── e2e/                      # Playwright E2E suites
├── migrations/                   # Alembic database migrations
├── scripts/                      # Utility and operational scripts
│   ├── build_docker_images.sh    # Decoupled Docker image builder
│   ├── sync_agy_memory.sh        # In-repo AI memory sync
│   └── init_db.py                # Database seed initialization
├── deploy/                       # Docker deployment configurations
│   ├── Dockerfile                # Main app container
│   ├── Dockerfile.nginx          # Standalone reverse proxy container
│   ├── nginx.conf                # Gateway proxy rules
│   └── migrate-postgres-16-to-18.sh
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # Canonical FRBR domain architecture
│   ├── INSTALL.md                # System installation guide
│   ├── CHANGELOG.md              # Versioned release notes
│   ├── RELEASE_PROCESS.md        # Release lifecycle guide
│   └── CONTEXT.md                # Quick architectural snapshot
├── shared/                       # Shared data files
│   ├── taxonomy.yaml             # Media type taxonomy
│   └── format_mappings.yaml      # Barcode format → media type mappings
├── pyproject.toml                # Python project configuration
├── alembic.ini                   # Alembic migration configuration
└── Makefile                      # Development and orchestration commands
```

---

## 3. Configuration System

### Configuration File

**Primary:** Environment variables defined in `.env` (template in `.env.example`).

### What's in the Config

- **Database:** PostgreSQL 18 connection URL (`DATABASE_URL`)
- **Auth:** JWT secrets (`JWT_SECRET_KEY`, `AUTH_SECRET`), Admin credentials (`ADMIN_EMAIL`, `ADMIN_PASSWORD`)
- **RBAC:** Roles: `admin`, `custodian`, `user`, `guest`
- **External APIs:** OpenLibrary, Google Books, MusicBrainz, Discogs, BoardGameGeek, TMDB, Allegro
- **Worker & Queue:** Valkey 8 / Celery (`REDIS_URL`, preserves `redis` service alias)
- **Frontend URL:** `NEXT_PUBLIC_FRONTEND_URL` and `NEXT_PUBLIC_API_URL`
- **AI Covers:** Local SD, Ollama, OpenAI, Gemini
- **Backup:** Rclone remotes (`RCLONE_REMOTE_FAST`, `RCLONE_REMOTE_ARCHIVE`, `RCLONE_COVERS_REMOTE`)
- **Observability:** OpenObserve (`OPENOBSERVE_HOST_PORT`, `OTEL_EXPORTER_OTLP_ENDPOINT`)

---

## 4. External Integrations

### Active

1. **OpenLibrary** — Book metadata (ISBN lookup)
2. **Google Books** — Book metadata (ISBN & title lookup with disambiguation)
3. **MusicBrainz** — Music metadata (barcode / UPC lookup)
4. **Discogs** — Music metadata (barcode / UPC lookup)
5. **BoardGameGeek** — Board game metadata (barcode lookup & taxonomies)
6. **TMDB** — Movie/TV metadata (barcode lookup)
7. **Allegro** — Retail item resolution & device flow OAuth integration
8. **Rclone Backup** — Automated daily sync and AWS S3 Glacier archiving
9. **OpenObserve** — Unified traces, metrics, and logs via OpenTelemetry
10. **Google OAuth** — Social sign-in

---

## 5. User Roles & Access

| Role | Can Do |
| --- | --- |
| **admin** | Full CRUD on all resources, manage users, view debug info, backup/restore, manage roles |
| **user** | CRUD on own items/collections, search, view others' public items, export/import |
| **guest** | Read-only access to public items |

### Key API Routes

| Route | Purpose |
| --- | --- |
| `POST /api/auth/login` | Get JWT token |
| `POST /api/auth/register` | Create account |
| `GET /api/health` | Health check (no auth) |
| `GET /api/db/health` | DB health (no auth) |
| `GET /api/items` | List items (auth required) |
| `POST /api/items` | Create item (user+) |
| `PUT /api/items/{id}` | Update item (owner/admin) |
| `DELETE /api/items/{id}` | Delete item (owner/admin) |
| `POST /api/items/bulk` | Bulk create/import items (user+) |
| `POST /api/items/search` | Full-text search (auth required) |
| `GET /api/items/barcode/{barcode}` | Look up external APIs (auth required) |
| `POST /api/items/{id}/cover-image` | Upload cover image (owner/admin) |
| `DELETE /api/items/{id}/cover-image` | Delete cover image (owner/admin) |
| `GET /api/collections` | List collections (auth required) |
| `POST /api/collections` | Create collection (user+) |
| `GET /api/debug/*` | Debug info (admin only) |
| `POST /api/admin/roles` | Change user role (admin only) |

---

## 6. Database Schema

**Engine:** SQLAlchemy with Flask-SQLAlchemy + Flask-Migrate (Alembic)  
**Migrations:** Alembic  
**Session:** `app/db/__init__.py` — `db` instance

### Schemas & Core Tables

Multi-schema PostgreSQL 18 layout (`auth`, `catalog`, `inventory`, `social`, `federation`, `config`, `public`):

- **`auth`:** `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `token_blocklist`, `user_consents`
- **`catalog`:** `works`, `expressions`, `manifestations`, `contributors`, `work_contributions`, `expression_contributions`, `manifestation_contributions`, `work_parts`, `work_series_memberships`, `work_expansion_links`, `work_relations`, `boardgame_mechanics`, `container_aggregations`, `image_scans`, `reading_roadmaps`, `roadmap_items`, `tags`
- **`inventory`:** `items` (includes `physical_location`), `item_custody_events`, `item_status_logs`, `entity_audit_logs`, `duplicate_candidates`, `escalation_requests`, `loan_requests`, `metadata_refetch_log`, `work_link_candidates`, `shared_collections`, `shared_collection_items`, `llm_telemetry`, `scan_telemetry`
- **`social`:** `feedback_items`, `feedback_comments`, `notifications`
- **`federation`:** `federation_instances`, `federation_actors`, `federation_followers`, `federation_activities`, `federation_consents`
- **`config`:** `instance_settings` (Fernet-encrypted external API secrets)

### Key Relationships

- Work → Expression → Manifestation → Item (FRBR WEMI chain)
- User → Items (`owner_id`) and User → SharedCollections / ReadingRoadmaps (`user_id`)

## 7. Testing Infrastructure

### Backend (pytest)

- **Framework:** pytest + pytest-asyncio
- **Fixtures:** `tests/conftest.py` — `client`, `db_session`, `auth_headers`, `admin_headers`
- **Database:** PostgreSQL test database (`DATABASE_URL_TEST`)
- **Run:** `IQOQO_AI_MODE=1 make test-backend` or `pytest`

### Frontend (Vitest & Playwright)

- **Framework:** Vitest (unit & integration) + Playwright (E2E)
- **Location:** `frontend/__tests__/`
- **Run:** `IQOQO_AI_MODE=1 make test-frontend` and `make test-e2e`

### Shell Scripts (BATS)

- **Framework:** BATS (Bash Automated Testing System)
- **Location:** `tests/bash/`
- **Run:** `IQOQO_AI_MODE=1 make test-scripts`

---

## 8. Common Development Commands

| Command | Purpose |
| --- | --- |
| `make start` | Start full development environment |
| `make test` | Run full test suite across backend, frontend, and scripts |
| `make test-backend` | Run backend pytest suite |
| `make test-frontend` | Run frontend Vitest suite |
| `make test-e2e` | Run Playwright end-to-end tests |
| `make lint` | Run the effective GitHub quality-workflow checks (Ruff, Black, isort, advisory mypy, Markdownlint, license) |
| `make lint-all` | Add stricter local-only Pylint, ESLint, TypeScript, and Stylelint checks |
| `make format` | Format Python and TypeScript codebases |
| `make status` | Check service health and database migrations |
| `make migrate-secrets` | Migrate API secrets from `.env` into encrypted database settings |
| `make knowledge-sync` | Fast AST knowledge sync (<45s, CodeGraph + Graphify) |
| `make knowledge-sync-full` | Full scheduled batch indexing (MemPalace) |
| `make docker-build-preview` | Build local container images for preview testing |

---

## 9. Current Architecture Highlights

- ✅ FRBR four-tier bibliographic model (Work → Expression → Manifestation → Item)
- ✅ Flask 3.1 REST API with Python 3.14+
- ✅ Next.js 16.4 App Router with Tailwind CSS v4, shadcn/ui, and Capacitor 7 multi-server mobile support
- ✅ PostgreSQL 18 across 7 schemas with GIN full-text search, physical item locations (`physical_location`), and Manifestation stats/gallery
- ✅ Valkey 8 (`valkey/valkey:8-alpine`) + Celery background task processing
- ✅ Symmetric Fernet encryption at rest for `InstanceSettings` API credentials
- ✅ Strictly linear Alembic migration DAG (`len(heads) == 1`) through `v1_2_0_item_physical_location`
- ✅ SQL `LIMIT`/`OFFSET` pagination and bounded query memory across endpoints
- ✅ Continuous hands-free batch scanning across 8 formats (`book`, `magazine`, `audiobook`, `music`, `movie`, `board_game`, `puzzle`, `lego`)
- ✅ Nginx gateway routing + isolated RDFLib `sparql-runner` service
- ✅ OpenObserve 8-layer observability stack (traces, metrics, logs, Browser RUM)
- ✅ Multi-tier Rclone + boto3 `S3Service` cloud backups (`data/keys/` + S3 Glacier cold archiving)
- ✅ Bounded 1–4 hop FRBR visual graph (`/graph`, `7` edge categories including cross-media `WorkRelation`, `lod:<digest>` dedup)
- ✅ Polymorphic media support including `vcd` and `cd_dvd_combo` mixed carriers

---

## 10. Known Gotchas & Constraints

1. **FRBR Purity:** Strict four-tier hierarchy must be respected across API and database models.
2. **PostgreSQL Alembic Limits:** Revision identifiers must be <= 32 characters (`len(revision) <= 32`) for `alembic_version.version_num` compatibility.
3. **Pylint & SQLAlchemy:** Append `# pylint: disable=not-callable` on `func.count()`.
4. **Proxy Routing:** External requests go through Nginx: `/api/*` proxies to Flask, other routes to Next.js.
5. **No Heredoc Editing:** Do not author project files using shell heredocs; use designated file tools.
6. **AiOps Terse Output:** Set `IQOQO_AI_MODE=1` for clean, token-efficient test execution.

---

## 11. Docker Architecture

### Standard Services (`docker-compose.yml`)

1. **db** — PostgreSQL 18 database (`5432`)
2. **redis** — Valkey 8 (`valkey/valkey:8-alpine`) broker and cache (`6379`)
3. **migration** — Dedicated one-shot Alembic schema migration runner (completes before web/worker)
4. **web** — Flask / Gunicorn REST API (`5000`)
5. **worker** — Celery background task processor
6. **sparql-runner** — Isolated Python RDFLib SPARQL executor (`5050`)
7. **frontend** — Next.js 16.4 App Router (`3000`)
8. **nginx** — Reverse proxy gateway (`8000`)

### Prebuilt Deployment (`docker-compose.prebuilt.yml`)

- Pulls tagged images from GHCR: `iqoqo-backend`, `iqoqo-frontend`, `iqoqo-nginx`, `iqoqo-sparql`.
- Uses dedicated one-shot `migration` service with isolated volume bindings (`volumes: !reset []`).

---

## 12. Version & Release Context

- **Active Release Version:** `1.2.0`
- **Release Branch:** `release/1.2.0`
- **Changelog:** Documented in [CHANGELOG.md](CHANGELOG.md)
