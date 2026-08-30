# MEMORY — iqoqo Dev Server

> **Last updated:** 2026-08-28  
> **Codebase snapshot:** iqoqo-internal monorepo

---

## 1. Project Identity

**iqoqo** is a self-hosted, local-first personal media catalog for physical collections (books, board games, movies, music, etc.). Built on the FRBR (Functional Requirements for Bibliographic Records) ontology, it provides:

- A Python **Flask** backend with JWT auth, RBAC, Alembic migrations, and SQLite/PostgreSQL support
- A **Next.js 15** frontend with server-side rendering, shadcn/ui, Zustand state management
- A **watchdog** daemon for background file monitoring
- An **iCal server** for lending deadline calendar feeds
- An **opencode** integration for AI-assisted catalog management
- Docker-based deployment with one-click setup

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
├── frontend/                     # Next.js 15 frontend
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
├── watchdog/                     # Background file monitoring daemon
│   ├── __init__.py
│   ├── __main__.py               # CLI entry point
│   ├── monitor.py                # Watchdog file system observer
│   ├── queue.py                  # Asyncio task queue
│   ├── processors.py             # File change processors
│   ├── state.py                  # Checkpoint persistence
│   └── config.py                 # Watchdog-specific config
├── ical_server/                  # iCal server for lending deadlines
│   ├── __init__.py
│   ├── __main__.py               # CLI entry point
│   ├── app.py                    # Quart async Flask app
│   ├── feed.py                   # ICS feed generation
│   └── feed_storage.py           # SQLite feed storage
├── tests/                        # pytest test suite
│   ├── conftest.py               # Fixtures (db_client, auth_headers, etc.)
│   ├── test_auth.py
│   ├── test_items.py
│   ├── test_items_bulk.py
│   ├── test_items_search.py
│   ├── test_collections.py
│   ├── test_health.py
│   ├── test_manifest.py
│   ├── test_debug.py
│   ├── test_watchdog.py
│   ├── test_ical_server.py
│   └── test_password_reset.py
├── frontend/__tests__/           # Frontend tests
│   └── vitest.config.ts
├── migrations/                   # Alembic database migrations
├── scripts/                      # Utility scripts
│   ├── start_dev.py              # Dev server with auto-restart
│   ├── launch.py                 # Dashboard launcher
│   └── diagnose.py               # System diagnostics
├── deploy/                       # Docker deployment
│   ├── Dockerfile                # Main app container
│   ├── Dockerfile.watchdog       # Watchdog daemon container
│   ├── docker-compose.yml        # Production compose (4 services)
│   └── docker-compose.dev.yml    # Dev compose with hot reload
├── docs/                         # Documentation
│   ├── MEMORY.md                 # This file — project context memory
│   ├── CONTEXT.md                # Project overview and architecture
│   ├── ADR/                      # Architecture Decision Records
│   └── handover/                 # Handover documentation
├── shared/                       # Shared data files
│   ├── taxonomy.yaml             # Media type taxonomy
│   ├── prompt_spec.yaml          # AI cover generation prompts
│   └── format_mappings.yaml      # Barcode format → media type mappings
├── opencode.json                 # OpenCode config (agents, servers, MCP)
├── pyproject.toml                # Python project config
├── alembic.ini                   # Alembic migration config
├── Makefile                      # Development commands
└── shell.nix                     # Nix development environment
```

---

## 3. Configuration System

### Configuration File

**Primary:** `/home/sebastiankruk/Development/iqoqo/opencode.json` (JSON)

### What's in the Config

- **App name:** "iqoqo"
- **Database:** SQLite at `/home/sebastiankruk/.local/share/iqoqo/iqoqo.db`
- **Auth:** JWT with bcrypt passwords
- **RBAC:** Three roles: admin, user, guest
- **External APIs:** OpenLibrary, Google Books, MusicBrainz, Discogs, BoardGameGeek, TMDB
- **iCal Server:** localhost:5001
- **Watchdog:** File monitoring with debounced queue
- **Frontend:** Next.js 15 on port 3000
- **AI Covers:** Flux + SDXL via ComfyUI (disabled by default)
- **Backup:** S3 + WebDAV targets

### Environment Variables

- `IQOQO_DB_URL` — Database URL override
- `IQOQO_JWT_SECRET_KEY` — JWT secret
- `IQOQO_ENV` — Environment (dev/prod)
- `OPENAI_API_KEY` — OpenAI key (for AI features)
- `COMFYUI_URL` — ComfyUI server URL
- `WEBDAV_URL`, `WEBDAV_USERNAME`, `WEBDAV_PASSWORD` — WebDAV backup

---

## 4. External Integrations

### Active

1. **OpenLibrary** — Book metadata (ISBN lookup)
2. **Google Books** — Book metadata (ISBN lookup)
3. **MusicBrainz** — Music metadata (barcode/ UPC lookup)
4. **Discogs** — Music metadata (barcode/ UPC lookup)
5. **BoardGameGeek** — Board game metadata (barcode lookup)
6. **TMDB** — Movie/TV metadata (barcode lookup)
7. **OpenCode** — AI-assisted catalog management (MCP tools, custom agents)
8. **S3 Backup** — AWS S3 bucket backup
9. **WebDAV Backup** — Nextcloud/ownCloud backup
10. **CalDAV Sync** — Contact and calendar synchronization
11. **OAuth** — Google and Facebook login

### Planned/Partially Built

- **ComfyUI** — AI cover generation (Flux + SDXL models)
- **Casdoor** — External identity provider integration

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

### Tables

- **users** — id, email, password_hash, is_active, role
- **works** — id, title, abstract, entity_type, created_at, updated_at
- **expressions** — id, work_id (FK→works), name, language, created_at, updated_at
- **manifestations** — id, expression_id (FK→expressions), name, publisher, publication_date, media_type, meta (JSON), created_at, updated_at
- **items** — id, manifestation_id (FK→manifestations), user_id (FK→users), barcode, status, notes, condition, meta (JSON), collection_status, available, created_at, updated_at
- **collections** — id, user_id (FK→users), name, description, media_type, is_smart, smart_rules (JSON), created_at, updated_at
- **item_collections** — item_id, collection_id (many-to-many join table)
- **lending_records** — id, item_id (FK→items), user_id (FK→users), borrower_name, borrower_contact, loan_date, due_date, return_date, status, notes, created_at, updated_at
- **cover_images** — id, item_id (FK→items), filename, original_filename, file_size, mime_type, width, height, created_at

### Key Relationships

- Work → Expression → Manifestation → Item (FRBR chain)
- User → Items (ownership)
- User → Collections (ownership)
- Item ↔ Collections (many-to-many via item_collections)
- Item → CoverImages (one-to-many)
- Item → LendingRecords (one-to-many)

---

## 7. Testing Infrastructure

### Backend (pytest)

- **Framework:** pytest + pytest-asyncio + httpx
- **Fixtures:** `tests/conftest.py` — `db_client`, `db_session`, `auth_headers`, `admin_headers`, `sample_item`, `sample_collection`
- **Database:** Each test gets a fresh SQLite DB in `tmp_path` (schema + seed data)
- **Run:** `make test` or `uv run python -m pytest`

### Frontend (vitest)

- **Framework:** Vitest
- **Location:** `frontend/__tests__/`
- **Run:** `make frontend-test` or `cd frontend && npx vitest run`

---

## 8. Common Development Commands

| Command | Purpose |
| --- | --- |
| `make dev` | Start dev server (auto-restarts on changes) |
| `make test` | Run full pytest suite |
| `make test-fast` | Run tests excluding slow ones |
| `make frontend-install` | Install frontend dependencies |
| `make frontend-dev` | Start frontend dev server |
| `make frontend-test` | Run frontend tests |
| `make frontend-lint` | Lint frontend code |
| `make frontend-typecheck` | Type-check frontend code |
| `make frontend-build` | Build frontend for production |
| `make build` | Build all Docker containers |
| `make up` | Start production containers |
| `make down` | Stop production containers |
| `make backup` | Trigger backup (DB + optional S3/WebDAV) |
| `make restore BACKUP=xxx` | Restore from backup |
| `make backup-status` | Check backup status |

---

## 9. Current State

### What Works

- ✅ Flask backend with full CRUD for items, collections, users, manifests
- ✅ JWT authentication with refresh tokens and session management
- ✅ RBAC with admin/user/guest roles
- ✅ Next.js 15 frontend with full UI (items, collections, admin, import, dashboard, scanners)
- ✅ API proxy: Next.js rewrites `/api/*` → Flask backend (next.config.ts rewrites)
- ✅ External API integration: OpenLibrary, Google Books, MusicBrainz, Discogs, BoardGameGeek, TMDB
- ✅ Barcode scanner integration (web + desktop)
- ✅ Full-text search with FTS5 (SQLite) or GIN indexes (PostgreSQL)
- ✅ Bulk import/export (JSON)
- ✅ Watchdog file monitoring daemon
- ✅ iCal server for lending deadlines
- ✅ Docker deployment (multi-service with hot reload)
- ✅ AI cover generation pipeline (ComfyUI + Flux/SDXL)
- ✅ Backup system (S3 + WebDAV)
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Tests: backend (pytest) + frontend (vitest)
- ✅ Authentication pages: login, signup, forgot-password, reset-password
- ✅ Dark mode support
- ✅ PWA (Progressive Web App) support

### What's Not Working / Missing

- ❌ Some Next.js pages may have minor issues (mostly cosmetic)
- ❌ No WIP tracking system
- ❌ No CI/CD for frontend changes
- ❌ No backup verification/restore testing

---

## 10. Known Gotchas

1. **Proxy:** Frontend API calls go through Next.js rewrites in `frontend/next.config.ts` — all `/api/*` requests are proxied to the Flask backend.
2. **No `/config/default.toml`:** The project uses `opencode.json` for configuration, not TOML files.
3. **Database sessions:** Use Flask's application context pattern with `db.session`.
4. **Auth tokens:** Include `Authorization: Bearer <token>` header for authenticated requests.
5. **Bulk import:** Use `POST /api/items/bulk` for importing multiple items at once.
6. **File uploads:** Cover images are stored in `~/.local/share/iqoqo/covers/{item_id}/`.
7. **Config:** The `Config` class in `app/config.py` loads from environment variables and `opencode.json`.
8. **Alembic migrations:** Run `alembic upgrade head` to apply database migrations.
9. **Watchdog:** The watchdog daemon monitors `~/.local/share/iqoqo/watch/` for file changes.
10. **iCal server:** Runs on port 5001, serves ICS feeds for lending deadlines.

---

## 11. Navigation Guide

### To modify a route

1. Check `app/api/` — find the appropriate blueprint file
2. Look at `app/api/__init__.py` to see how blueprints are registered
3. Check `app/api/schemas.py` for request/response schemas
4. Check `app/db/models.py` for ORM models

### To modify the database

1. Check `app/db/models.py` for ORM definitions
2. Check `migrations/versions/` for existing migrations
3. Create new migration: `alembic revision --autogenerate -m "description"`
4. Apply: `alembic upgrade head`

### To modify the frontend

1. Check `frontend/app/` for pages (App Router)
2. Check `frontend/components/` for reusable components
3. Check `frontend/next.config.ts` for API proxy rewrites
4. Check `frontend/lib/api/` for API client and hooks

### To modify external API integrations

1. Check `app/api/scanner.py` — `barcode_lookup` and `_fetch_*` functions
2. Check `app/strategies/lookup/` — Strategy pattern implementations

### To modify tests

1. Backend: `tests/` directory with `conftest.py` for fixtures
2. Frontend: `frontend/__tests__/` directory

---

## 12. Docker Setup

### Services

1. **iqoqo** — Main Flask app (port 8000)
2. **frontend** — Next.js frontend (port 3000)
3. **iqoqo-watchdog** — File monitoring daemon
4. **iqoqo-ical** — iCal server (port 5001)

### Volumes

- `iqoqo-data` — SQLite database
- `iqoqo-watch` — Watchdog monitoring directory
- `iqoqo-covers` — Cover images

---

## 13. Git Branch

- **Current:** `main`
- **Recent activity:** Added reset-password endpoint, Next.js auth pages (login, signup, forgot-password, reset-password), added NPM_TOKEN to Dockerfile, added Vitest testing infrastructure, added badges to README, fixed npm cache bug, added PWA support
