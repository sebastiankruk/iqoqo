# CONTEXT — iqoqo

> Last updated: 2026-08-28

## Overview

**iqoqo** is a self-hosted, local-first personal media catalog application for managing physical collections (books, board games, movies, music, and more). Built on the FRBR (Functional Requirements for Bibliographic Records) ontology, it provides a structured way to catalog, track, and organize media items with full ownership and privacy control.

## Key Links

| Resource | Location |
| --- | --- |
| Python backend | `app/` |
| Next.js 15 frontend | `frontend/` |
| Database schema | `app/db/schema.py` |
| ORM models | `app/db/models.py` |
| API routes | `app/api/` |
| Alembic migrations | `migrations/versions/` |
| Watchdog daemon | `watchdog/` |
| iCal server | `ical_server/` |
| OpenCode integration | `opencode.json` |
| Shared data files | `shared/` |
| Tests | `tests/` + `frontend/__tests__/` |
| Memory & context | `docs/MEMORY.md`, `docs/CONTEXT.md` |
| Architecture decisions | `docs/ADR/` |
| Deployment | `deploy/` |

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                       iqoqo System                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Frontend   │    │   Backend   │    │  Watchdog   │     │
│  │  (Next.js)   │◄──►│  (Flask)    │◄──►│  (Daemon)   │     │
│  │  Port 3000   │    │  Port 5000  │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                  │                   │             │
│         │                  │                   │             │
│         ▼                  ▼                   ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Next.js    │    │   SQLite    │    │  Filesystem  │     │
│  │  Rewrites   │    │  Database   │    │  Watch Dir   │     │
│  │  (Proxy)    │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                    External Integrations                      │
├──────────────────────────────────────────────────────────────┤
│  OpenLibrary · Google Books · MusicBrainz · Discogs          │
│  BoardGameGeek · TMDB · OAuth (Google/Facebook)              │
│  S3 Backup · WebDAV Backup · CalDAV Sync                     │
│  ComfyUI (AI Covers) · OpenCode (AI Agent)                  │
└──────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Zustand, React Query, Vitest |
| Backend | Python 3.12+, Flask, SQLAlchemy (sync), Pydantic, Alembic |
| Database | SQLite (default) or PostgreSQL |
| Auth | JWT (PyJWT + bcrypt), Google OAuth, Facebook OAuth |
| File Monitoring | watchdog (Python) |
| Calendar | Quart (async Flask) for iCal server |
| AI Covers | ComfyUI + Flux/SDXL models |
| Deployment | Docker Compose (multi-service), GitHub Actions CI/CD |

## Key Files to Reference

| File | Purpose |
| --- | --- |
| `app/__init__.py` | Flask app factory (create_app) |
| `app/config.py` | Configuration loading from environment variables |
| `app/db/__init__.py` | SQLAlchemy db instance |
| `app/db/models.py` | ORM models: User, Work, Expression, Manifestation, Item, Collection |
| `app/db/schema.py` | SQLite DDL creation + seed data |
| `app/api/__init__.py` | Blueprint registration |
| `app/api/items.py` | Items CRUD + bulk operations + external API lookups |
| `app/api/auth.py` | JWT authentication, login/signup |
| `app/api/collections.py` | Collections CRUD |
| `app/api/scanner.py` | Barcode scanner + external API lookups |
| `app/api/schemas.py` | Pydantic request/response schemas |
| `frontend/next.config.ts` | Next.js rewrites (API proxy to Flask) |
| `frontend/proxy.ts` | Middleware for auth routing |
| `frontend/lib/api/client.ts` | Browser-side API client (axios) |
| `frontend/lib/api/hooks.ts` | React Query hooks |
| `frontend/components/auth/AuthContext.tsx` | React auth context with JWT management |
| `watchdog/monitor.py` | File system observer |
| `ical_server/app.py` | Quart async Flask app for iCal |
| `opencode.json` | OpenCode configuration (agents, MCP, servers) |
| `migrations/versions/` | Alembic database migrations |
| `tests/conftest.py` | Pytest fixtures (db_client, auth_headers, etc.) |

## Important Notes

- **Single Proxy:** The frontend uses Next.js rewrites in `next.config.ts` to proxy ALL `/api/*` requests to the Flask backend. There are no Next.js API routes for business logic.
- **No TOML Config:** The project uses `opencode.json` for configuration, not TOML files.
- **Sync Database:** Database operations are synchronous (Flask-SQLAlchemy).
- **FRBR Ontology:** The data model follows FRBR: Work → Expression → Manifestation → Item.
- **Authentication:** JWT tokens with refresh support. Include `Authorization: Bearer <token>` header for authenticated requests.
- **Roles:** Three roles (admin, user, guest) with RBAC.
- **Bulk Import:** Use `POST /api/items/bulk` for importing multiple items at once.
- **Cover Images:** Stored in `~/.local/share/iqoqo/covers/{item_id}/`.
