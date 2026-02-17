# Architecture Comparison: Current vs. Target

This document provides a visual comparison of the current and target architectures for the iqoqo project.

---

## Current Architecture (Flask Monolith)

```text
┌─────────────────────────────────────────────────────────────┐
│                         Browser                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  HTML Pages (Jinja2)                                  │  │
│  │  + Bootstrap CSS + jQuery                             │  │
│  │  + Custom JS (scanner.js, isbn.js, etc.)              │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↕ HTTP                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Flask Application                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Web Blueprint (web_bp)                               │  │
│  │  ├── routes.py → Renders Jinja2 Templates             │  │
│  │  ├── static/ → CSS, JS, Images                        │  │
│  │  └── templates/ → HTML with Jinja2                    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  API Blueprint (api_bp)                               │  │
│  │  └── routes.py → JSON Endpoints                       │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Core Services                                        │  │
│  │  ├── data_manager.py                                  │  │
│  │  ├── frbr_service.py                                  │  │
│  │  └── ingest.py                                        │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Database Models (SQLAlchemy)                         │  │
│  │  └── models.py → Work, Expression, Manifestation,     │  │
│  │                  Item                                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Tables: work, expression, manifestation, item        │  │
│  │  + JSONB columns for flexible metadata                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

CHARACTERISTICS:
✓ Simple deployment (single container)
✓ Server-side rendering
✓ Tight coupling between UI and backend
✗ Limited interactivity
✗ No mobile PWA support
✗ Harder to scale frontend independently
✗ jQuery-based interactions (legacy)
```

---

## Target Architecture (Decoupled React + Flask API)

```text
┌─────────────────────────────────────────────────────────────┐
│                    Browser / Mobile                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  React Application (Next.js)                          │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Pages (App Router)                             │  │  │
│  │  │  ├── Dashboard (/)                              │  │  │
│  │  │  ├── Scanner (/scan)                            │  │  │
│  │  │  ├── Collection (/collection)                   │  │  │
│  │  │  └── Item Detail (/item/[id])                   │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Components (shadcn/ui + Radix)                 │  │  │
│  │  │  ├── Navbar, Footer                             │  │  │
│  │  │  ├── StatsCards, ItemCard                       │  │  │
│  │  │  └── Scanner, QRCode                            │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  State Management                               │  │  │
│  │  │  ├── React Query (server state)                 │  │  │
│  │  │  └── Zustand (client state)                     │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  Styling                                        │  │  │
│  │  │  ├── Tailwind CSS                               │  │  │
│  │  │  └── Custom Theme (Modern Athenaeum)            │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                      ↕ REST API (JSON)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────────────────────┐
            │    API Gateway (nginx)        │
            │  ┌─────────────────────────┐  │
            │  │  /api/* → Flask         │  │
            │  │  /* → Next.js           │  │
            │  └─────────────────────────┘  │
            └───────────────────────────────┘
                  ↓                    ↓
┌──────────────────────────────┐   ┌──────────────────────┐
│   Flask API Backend          │   │  Next.js Frontend    │
│  ┌────────────────────────┐  │   │  (Static Server)     │
│  │  API v1 (/api/v1/)     │  │   └──────────────────────┘
│  │  ├── /auth             │  │
│  │  ├── /items            │  │   Port: 3000
│  │  ├── /manifestations   │  │   Built with: Vite/Turbo
│  │  ├── /lookup           │  │   Deployed: Docker
│  │  └── /stats            │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  Core Services         │  │
│  │  ├── data_manager.py   │  │
│  │  ├── frbr_service.py   │  │
│  │  └── ingest.py         │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  Database Layer        │  │
│  │  └── models.py (ORM)   │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │  Background Workers    │  │
│  │  └── Celery + Redis    │  │
│  │     (Future: AI, Sync) │  │
│  └────────────────────────┘  │
│                              │
│  Port: 5000                  │
│  CORS: Enabled               │
│  Auth: JWT + Sessions        │
└──────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Tables: work, expression, manifestation, item        │  │
│  │  + JSONB columns for flexible metadata                │  │
│  │  + Full-text search indexes                           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

CHARACTERISTICS:
✓ Decoupled frontend and backend
✓ Modern React with TypeScript
✓ Mobile-first design (PWA capable)
✓ Independent scaling
✓ Better developer experience (hot reload)
✓ API-first design (supports future mobile apps)
✓ Better performance (client-side routing)
✓ Modern UI/UX (Tailwind + shadcn/ui)
```

---

## Data Flow Comparison

### Current: Server-Side Rendering

```text
User Action → Flask Route → Database Query → Jinja2 Template
    ↓                                               ↓
HTML Page ←────────────────────────────────── Full Page Render
```

#### Example: View Item

1. User clicks item link
2. Browser navigates to `/item/123`
3. Flask renders entire HTML page with data
4. Browser displays page (full reload)

### Target: Client-Side Rendering

```text
User Action → React Component → API Call → Flask Endpoint → Database
    ↓              ↓                ↓
React Router   Update State   JSON Response
    ↓              ↓
Component Re-render (No full page reload)
```

#### Example: View Item

1. User clicks item link
2. React Router updates URL (no reload)
3. React component makes API call to `/api/v1/items/123`
4. Flask returns JSON
5. React updates component (smooth transition)

---

## Technology Stack Changes

| Layer                  | Current                  | Target                | Reason                                      |
| ---------------------- | ------------------------ | --------------------- | ------------------------------------------- |
| **Frontend Framework** | Jinja2 Templates         | Next.js 16 (React)    | Modern, component-based, better DX          |
| **Styling**            | Bootstrap 5 + Custom CSS | Tailwind CSS 3        | Utility-first, smaller bundle, customizable |
| **UI Components**      | Bootstrap Components     | Radix UI (shadcn/ui)  | Accessible, headless, fully customizable    |
| **JavaScript**         | jQuery 3.6               | TypeScript            | Type safety, better tooling, modern         |
| **State Management**   | DOM manipulation         | React Query + Zustand | Declarative, optimistic updates, caching    |
| **Build Tool**         | None (static files)      | Vite/Turbo            | Fast HMR, optimized builds                  |
| **Routing**            | Flask routes             | Next.js App Router    | Client-side navigation, prefetching         |
| **Backend**            | Flask (Web + API)        | Flask (API only)      | Focus on API, remove template rendering     |
| **API Style**          | Mixed endpoints          | RESTful JSON API      | Consistent, versioned, documented           |
| **Authentication**     | Sessions only            | JWT + Sessions        | Supports mobile apps, stateless             |
| **Database**           | PostgreSQL               | PostgreSQL            | ✓ No change                                 |
| **ORM**                | SQLAlchemy               | SQLAlchemy            | ✓ No change                                 |

---

## Deployment Architecture

### Current Deployment

```text
┌─────────────────────────┐
│   Docker Container      │
│  ┌──────────────────┐   │
│  │   Flask App      │   │
│  │  (Web + API)     │   │
│  │   Port 5000      │   │
│  └──────────────────┘   │
│          ↓              │
│  ┌──────────────────┐   │
│  │   PostgreSQL     │   │
│  │   Port 5432      │   │
│  └──────────────────┘   │
└─────────────────────────┘
         ↓
    Port 80/443
```

### Target Deployment

```text
┌───────────────────────────────────────────────┐
│              Load Balancer / CDN              │
│                 (Cloudflare)                  │
└───────────────────────────────────────────────┘
                      ↓
┌───────────────────────────────────────────────┐
│               Reverse Proxy (nginx)           │
│  /api/* → Backend  |  /* → Frontend           │
└───────────────────────────────────────────────┘
         ↓                          ↓
┌─────────────────────┐    ┌─────────────────────┐
│  Docker Container   │    │  Docker Container   │
│  ┌───────────────┐  │    │  ┌───────────────┐  │
│  │  Flask API    │  │    │  │  Next.js      │  │
│  │  Port 5000    │  │    │  │  Port 3000    │  │
│  └───────────────┘  │    │  └───────────────┘  │
│         ↓           │    └─────────────────────┘
│  ┌───────────────┐  │
│  │  Celery       │  │    Benefits:
│  │  Workers      │  │    - Independent scaling
│  └───────────────┘  │    - CDN caching for frontend
│         ↓           │    - Better separation of concerns
│  ┌───────────────┐  │    - API can serve mobile apps
│  │  Redis        │  │
│  │  (Queue)      │  │
│  └───────────────┘  │
└─────────────────────┘
         ↓
┌─────────────────────┐
│    PostgreSQL       │
│    Port 5432        │
└─────────────────────┘
```

---

## File Structure Comparison

### Current Structure

```text
iqoqo/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── api/
│   │   └── routes.py          # API endpoints (mixed with web)
│   ├── core/
│   │   ├── data_manager.py
│   │   └── frbr_service.py
│   ├── db/
│   │   └── models.py
│   └── web/
│       ├── routes.py          # Web UI routes
│       ├── static/            # CSS, JS, images
│       │   ├── css/
│       │   │   └── bootstrap.min.css
│       │   └── js/
│       │       ├── jquery-3.6.0.min.js
│       │       └── scanner.js
│       └── templates/         # Jinja2 HTML
│           ├── index.html
│           ├── scan.html
│           └── item.html
├── requirements.txt
└── run.py
```

### Target Structure

```text
iqoqo/
├── backend/  (or keep as app/)
│   ├── __init__.py
│   ├── config.py
│   ├── api/
│   │   └── v1/                # Versioned API
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── items.py
│   │       ├── manifestations.py
│   │       ├── lookup.py
│   │       └── stats.py
│   ├── core/
│   │   ├── data_manager.py
│   │   ├── frbr_service.py
│   │   └── auth_service.py    # New
│   ├── db/
│   │   └── models.py
│   └── workers/               # New (for background tasks)
│       └── tasks.py
├── frontend/                  # New Next.js app
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Dashboard
│   │   ├── scan/
│   │   │   └── page.tsx
│   │   ├── collection/
│   │   │   └── page.tsx
│   │   └── item/
│   │       └── [id]/
│   │           └── page.tsx
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   ├── layout/
│   │   │   ├── navbar.tsx
│   │   │   └── footer.tsx
│   │   ├── dashboard/
│   │   │   ├── stats-cards.tsx
│   │   │   └── fresh-arrivals.tsx
│   │   └── scanner/
│   │       └── camera-view.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── hooks.ts       # React Query hooks
│   │   └── utils.ts
│   ├── types/
│   │   └── frbr.ts            # TypeScript types
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
├── deploy/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docker-compose.yml
└── requirements.txt
```

---

## Migration Path Visualization

```text
┌──────────────┐
│  Phase 0     │  Foundation Setup
│  (2 weeks)   │  ✓ Create frontend/ directory
└──────┬───────┘  ✓ Next.js + Tailwind installed
       │          ✓ Both stacks running
       ↓
┌──────────────┐
│  Phase 1     │  API Stabilization
│  (2 weeks)   │  ✓ CORS enabled
└──────┬───────┘  ✓ RESTful API at /api/v1/
       │          ✓ Flask serves JSON only
       ↓
┌──────────────┐
│  Phase 2     │  Frontend Scaffolding
│  (2 weeks)   │  ✓ Design system implemented
└──────┬───────┘  ✓ Components from v0 ported
       │          ✓ API client + React Query
       ↓
┌──────────────┐
│  Phase 3     │  Feature Parity
│  (4 weeks)   │  ✓ Dashboard working
└──────┬───────┘  ✓ Scanner implemented
       │          ✓ All CRUD operations
       │          ✓ Old features replicated
       ↓
┌──────────────┐
│  Phase 4     │  New Features
│  (3 weeks)   │  ✓ Enhanced UX
└──────┬───────┘  ✓ PWA support
       │          ✓ Performance optimizations
       ↓
┌──────────────┐
│  Phase 5     │  Production Cutover
│  (1 week)    │  ✓ Deploy new architecture
└──────────────┘  ✓ Remove old web blueprint
                  ✓ Update documentation
```

---

## Benefits Summary

### Migration Strategy Benefits

- ✅ Faster timeline (8 weeks vs 14 weeks with parallel approach)
- ✅ Simpler during development (no dual maintenance)
- ✅ Cleaner git history (one directional change)
- ✅ Database remains completely unchanged
- ✅ Single cutover reduces complexity

### Developer Experience

- ✅ Hot module replacement (instant feedback)
- ✅ TypeScript (catch errors early)
- ✅ Component-based architecture (reusable)
- ✅ Modern tooling (ESLint, Prettier, Vitest)
- ✅ Better debugging tools (React DevTools)

### User Experience

- ✅ Faster page transitions (no full reloads)
- ✅ Better mobile experience
- ✅ Offline support (PWA)
- ✅ Smoother animations
- ✅ Modern, beautiful UI

### Technical

- ✅ API-first (supports future mobile apps)
- ✅ Independent scaling (frontend/backend)
- ✅ Better caching strategies
- ✅ Easier to test
- ✅ Cleaner separation of concerns

### Business

- ✅ Faster feature development
- ✅ Easier to onboard new developers
- ✅ Better mobile app foundation
- ✅ More maintainable codebase

---

## Risk Mitigation

| Risk                   | Mitigation                                                   |
| ---------------------- | ------------------------------------------------------------ |
| Breaking changes       | Thorough testing before deployment, feature parity checklist |
| Performance regression | Load testing in staging environment                          |
| Data loss              | Full database backup before deployment                       |
| User disruption        | Clear communication, plan for quick rollback                 |
| Missing features       | Complete feature comparison checklist                        |

---

## Conclusion

The migration from a Flask monolith to a decoupled React + Flask API architecture will modernize the iqoqo application while maintaining the existing database intact. The **direct replacement strategy** ensures a faster migration with less complexity.

**Key Success Factors:**

1. Database schema remains unchanged (zero risk to data)
2. Build complete frontend before switching over
3. Modern UI/UX from v0 designs
4. Comprehensive testing before deployment
5. Simple rollback via git if needed
6. Clean separation: Frontend development independent of backend

**Timeline:** 8 weeks full-time (vs 14 weeks with parallel approach)

For detailed implementation steps, see:

- [Full Migration Plan](./MIGRATION_PLAN.md)
- [Quick-Start Checklist](./MIGRATION_CHECKLIST.md)
