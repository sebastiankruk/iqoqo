# CONTEXT — iqoqo

> Last updated: 2026-11-27 (`v1.2.0`)

## Overview

**iqoqo** is a self-hosted, local-first personal media catalog application for managing physical collections (books, board games, movies, music, and more). Built on the FRBR (Functional Requirements for Bibliographic Records) ontology, it provides a structured way to catalog, track, and organize media items with full ownership and privacy control.

## Key Links

| Resource | Location |
| --- | --- |
| Python backend | `app/` |
| Next.js frontend | `frontend/` |
| ORM models | `app/db/models.py` |
| API routes | `app/api/` |
| Background tasks & Celery | `app/core/celery_app.py`, `app/core/tasks.py` |
| Alembic migrations | `migrations/versions/` |
| Shared data files | `shared/` |
| Tests | `tests/` + `frontend/__tests__/` |
| OpenSpec specs | `openspec/specs/` |
| Deployment & Docker | `deploy/`, `docker-compose.yml` |

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                       iqoqo System                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Frontend   │    │   Backend   │    │   Worker    │     │
│  │  (Next.js)   │◄──►│   (Flask)   │◄──►│  (Celery)   │     │
│  │  Port 3000   │    │  Port 5000  │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                  │                   │             │
│         │                  │                   │             │
│         ▼                  ▼                   ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │    Nginx    │    │ PostgreSQL  │    │  Valkey 8   │     │
│  │   Gateway   │    │     18      │    │(Redis Comp.)│     │
│  │  Port 8000   │    │  Port 5432  │    │  Port 6379  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                    External Integrations                      │
├──────────────────────────────────────────────────────────────┤
│  OpenLibrary · Google Books · MusicBrainz · Discogs          │
│  BoardGameGeek · TMDB · Allegro (OAuth & Device Flow)         │
│  Rclone Multi-Tier Backup (Daily Sync + S3 Glacier)          │
│  OpenObserve Unified Telemetry (Traces, Metrics, Logs)       │
└──────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16.4 (App Router + Capacitor 7 mobile), React 19.2, TypeScript 5, Tailwind CSS v4, shadcn/ui, Vitest |
| Backend | Python 3.14+, Flask 3.1, SQLAlchemy 2.0, Alembic, Celery, Valkey 8 |
| Database | PostgreSQL 18 (Multi-schema: `auth`, `catalog`, `inventory`, `social`, `federation`, `config`) |
| Auth | JWT (`PyJWT` + `scrypt`), `iqo_` PATs, TOTP 2FA, Google & Apple OAuth |
| Observability | 8-layer OpenTelemetry + OpenObserve (Traces, Metrics, Logs, Browser RUM) |
| Backups | Native boto3 `S3Service` (`S3_BUCKET_ARCHIVE`) & `rclone` multi-tier backup |
| AI Covers | Local SD, Ollama, OpenAI, Gemini + multi-zone Tesseract OCR (`eng+pol`) |
| Deployment | Docker Compose, source-free `DEPLOY_DIR` contract, prebuilt GHCR images |

## Key Files to Reference

| File | Purpose |
| --- | --- |
| `app/__init__.py` | Flask app factory (`create_app`) |
| `app/config.py` | Configuration loading from environment variables |
| `app/db/models.py` | ORM models: User, Work, Expression, Manifestation, Item, Collection |
| `app/api/__init__.py` | Blueprint registration |
| `app/api/items.py` | Items CRUD + bulk operations + external API lookups |
| `app/api/auth.py` | JWT authentication, login/signup |
| `app/api/collections.py` | Collections CRUD |
| `app/api/scanner.py` | Barcode & title scanner with multi-candidate disambiguation |
| `app/api/feedback.py` | In-app feedback tickets with attachments and RBAC |
| `app/core/celery_app.py` | Celery asynchronous worker and task dispatch |
| `frontend/next.config.ts` | Next.js rewrites (API proxy to Flask) |
| `frontend/app/` | Next.js App Router pages |
| `frontend/components/` | Reusable React components (shadcn/ui) |
| `migrations/versions/` | Alembic database migrations |
| `tests/conftest.py` | Pytest fixtures (`client`, `db_session`, `auth_headers`, etc.) |

## Important Notes

- **Reverse Proxy:** Nginx routes external requests: `/api/*` to Flask backend and remaining routes to Next.js frontend.
- **FRBR Ontology:** The data model strictly follows FRBR: Work → Expression → Manifestation → Item.
- **Authentication:** JWT access and refresh tokens. Requests use `Authorization: Bearer <token>` header.
- **PostgreSQL 18:** Uses PostgreSQL 18 with relational JSONB and GIN full-text search indexes.
- **Background Tasks:** Asynchronous tasks (cover fetching, LOD linking, Federation dispatch) run via Celery with Valkey 8 (`redis://redis:6379`).
- **AiOps Standards:** Test runs and linters support terse AI output with `IQOQO_AI_MODE=1`.
