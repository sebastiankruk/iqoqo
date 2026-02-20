# Migration Plan: Flask/jQuery → React/Tailwind Architecture

**Project:** iqoqo - Library of Everything
**Created:** February 15, 2026
**Version:** 1.0

---

## Executive Summary

This document outlines the migration strategy from the current Flask-based monolithic architecture with server-side rendering (Jinja2 templates + Bootstrap + jQuery) to a modern decoupled architecture using React, Next.js, Tailwind CSS, and Vite, while retaining Flask as a robust API backend.

**Migration Approach:** Direct replacement ("rip and replace") - build the new frontend completely, then switch over in one deployment. The database schema remains intact throughout.

### Key Objectives

1. **Decouple frontend from backend** - Enable independent development and deployment
2. **Modernize UI/UX** - Implement "Modern Athenaeum" design system from v0 prototypes
3. **Improve developer experience** - Hot reload, TypeScript, component-based architecture
4. **Maintain database integrity** - Zero changes to existing database schema required
5. **Enable mobile-first features** - Better scanner UX, responsive design, PWA capabilities

---

## Current State Analysis

### Technology Stack (As-Is)

**Backend:**

- Python 3.11+ / Flask
- SQLAlchemy ORM with PostgreSQL
- Alembic for migrations
- Flask blueprints: `web_bp` (UI routes), `api_bp` (API endpoints)
- Server-side rendering with Jinja2 templates

**Frontend:**

- Bootstrap 5.x for UI framework
- jQuery 3.6.0 for JavaScript interactions
- Static assets served from Flask (`app/web/static/`)
- HTML5 QR Code scanner library
- Custom JavaScript modules: `scanner.js`, `isbn.js`, `metaform.js`

**Data Model:**

- FRBR-compliant 4-tier hierarchy: Work → Expression → Manifestation → Item
- PostgreSQL with JSONB for flexible metadata
- Full-text search capability

### Current Routes & Features

| Route              | Type | Description               |
| ------------------ | ---- | ------------------------- |
| `/`                | Web  | Dashboard with stats      |
| `/scan`            | Web  | Barcode scanner interface |
| `/add`             | Web  | Manual add/edit form      |
| `/item/<id>`       | Web  | Item detail view          |
| `/list`            | Web  | Collection browser        |
| `/api/isbn/<isbn>` | API  | ISBN metadata lookup      |
| `/api/items`       | API  | CRUD operations           |
| `/api/qrcode/<id>` | API  | Generate QR codes         |

---

## Target Architecture (To-Be)

### Technology Stack

#### Backend (Flask API)

- Flask as RESTful API server only (no HTML rendering)
- Retain SQLAlchemy, Alembic, PostgreSQL
- Add CORS support for frontend
- JWT/session authentication
- OpenAPI/Swagger documentation
- Background workers (Celery/Redis) for async tasks

#### Frontend (React + Next.js)

- **Framework:** Next.js 16 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS 3.x
- **UI Components:** Radix UI (shadcn/ui)
- **State Management:** React Query (TanStack Query) + Zustand
- **Forms:** React Hook Form + Zod validation
- **Build Tool:** Vite/Turbo
- **Testing:** Vitest, React Testing Library

#### Design System: "Modern Athenaeum"

- **Colors:**
  - Primary: Deep Indigo (`#2C3E50`)
  - Background: Warm Paper (`#FDFBF7`)
  - Accent: Library Clay (`#D35400`)
- **Typography:**
  - Headings: Merriweather (serif)
  - UI: Inter (sans-serif)

---

## Migration Strategy: Direct Replacement

### Overview

We'll use a **Direct Replacement Strategy** - build the complete new frontend, then switch over in a single deployment. The old Flask web blueprint will be removed once the new frontend is tested and ready.

**Key Advantage:** No need to maintain two systems simultaneously, simpler codebase during migration.

```text
Phase 1: API Enhancement (1.5 weeks)
Phase 2: Frontend Build (4 weeks)
Phase 3: Testing & Polish (1.5 weeks)
Phase 4: Deployment & Cleanup (1 week)
```

**Total Duration:** ~8 weeks (~2 months)

**Database:** The existing PostgreSQL database and schema remain completely unchanged. All Work, Expression, Manifestation, and Item tables stay as-is.

---

## Phase 1: API Enhancement & Frontend Foundation

**Duration:** 1.5 weeks
**Goal:** Prepare Flask to serve as API-only backend and initialize frontend

### Tasks

#### 1.1 Repository Structure

```text
iqoqo/
├── app/                 # Keep existing Flask app structure
│   ├── api/             # API blueprints (enhanced)
│   ├── core/            # Business logic
│   ├── db/              # Models & migrations (UNCHANGED)
│   ├── web/             # Will be REMOVED after migration
│   └── config.py
├── frontend/            # New Next.js application
│   ├── app/             # Next.js App Router pages
│   ├── components/      # React components
│   ├── lib/             # Utilities
│   ├── hooks/           # Custom hooks
│   └── types/           # TypeScript types
├── docker-compose.yml
├── docs/
└── tests/
```

**Action Items:**

- [x] Create `frontend/` directory structure
- [x] Initialize Next.js project: `npx create-next-app@latest frontend --typescript --tailwind --app`
- [x] Update Docker Compose to include frontend service

#### 1.2 Backend API Enhancement

**Goal:** Enhance existing API endpoints and add CORS support. The Flask web blueprint stays functional during development for reference.

- [x] Install Flask-CORS: `pip install flask-cors`
- [x] Add CORS configuration (allow `localhost:3000` during development)
- [x] Review and enhance existing API endpoints in `app/api/routes.py`
- [x] Add any missing endpoints needed for frontend
- [x] Keep `app/web/` intact for now (reference only, will delete later)

#### 1.3 Development Environment

- [x] Update `.venv` requirements with CORS
- [x] Create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:5000`
- [x] Test that API endpoints work and return proper JSON

**Deliverables:**

- ✅ Flask API with CORS enabled
- ✅ Next.js initialized (skeleton only)
- ✅ Both can run simultaneously for development
- ✅ Database schema untouched

**Status:** ✅ **COMPLETE** (February 15, 2026)

---

## Phase 2: Frontend Build

**Duration:** 4 weeks
**Goal:** Build complete React frontend with feature parity

### Tasks

#### 2.1 API Route Enhancement
Ensure existing API endpoints are properly structured for frontend consumption.

**Current API Audit:**

- `/api/isbn/<isbn>` - ISBN lookup
- `/api/items` - Get all items
- `/api/manifestation` - CRUD operations
- `/api/qrcode/<id>` - QR code generation

**New API Structure:**

```text
/api/v1/
├── /auth
│   ├── POST /login
│   ├── POST /logout
│   └── GET /me
├── /works
│   ├── GET / (list)
│   ├── GET /:id (details)
│   └── GET /:id/manifestations
├── /manifestations
│   ├── GET / (list with filters)
│   ├── GET /:id
│   ├── POST / (create)
│   ├── PUT /:id
│   └── DELETE /:id
├── /items
│   ├── GET / (list)
│   ├── GET /:id
│   ├── POST /
│   ├── PUT /:id
│   ├── DELETE /:id
│   └── GET /:id/qrcode
├── /lookup
│   ├── GET /isbn/:isbn
│   └── GET /barcode/:barcode
└── /stats
    └── GET / (dashboard stats)
```

**Action Items:**

- [ ] Review existing endpoints in `app/api/routes.py`
- [ ] Add any missing endpoints (stats dashboard, etc.)
- [ ] Ensure standardized response format:

  ```python
  {
    "success": true,
    "data": {...},
    "meta": {
      "page": 1,
      "total": 100
    },
    "error": null
  }
  ```

- [ ] Add pagination support with query params: `?page=1&limit=20`
- [ ] Add filtering/sorting: `?status=reading&sort=-added_at`
- [ ] Implement proper HTTP status codes (200, 201, 400, 404, 500)

#### 2.2 CORS Configuration (Already Done in Phase 1)

Verify CORS is working:

```bash
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:5000/api/items
```

#### 2.3 Next.js Project Setup

```bash
cd frontend
npm install  # or pnpm install
npm install @tanstack/react-query zustand axios zod react-hook-form
npm install -D @types/node prettier eslint-config-next
```

#### 2.4 Design System Implementation

**Install shadcn/ui:**

```bash
npx shadcn@latest init
npx shadcn@latest add button card input badge avatar tabs progress
npx shadcn@latest add dialog dropdown-menu popover toast
```

**Create theme configuration:**

```typescript
// frontend/lib/theme.ts
export const theme = {
  colors: {
    primary: '#2C3E50',      // Deep Indigo
    background: '#FDFBF7',    // Warm Paper
    accent: '#D35400',        // Library Clay
    // ... other semantic colors
  },
  fonts: {
    serif: 'var(--font-merriweather)',
    sans: 'var(--font-inter)',
  }
}
```

**Update Tailwind config:**

```javascript
// frontend/tailwind.config.ts
module.exports = {
  theme: {
    extend: {
      colors: {
        'deep-indigo': '#2C3E50',
        'warm-paper': '#FDFBF7',
        'library-clay': '#D35400',
      },
      fontFamily: {
        serif: ['var(--font-merriweather)'],
        sans: ['var(--font-inter)'],
      }
    }
  }
}
```

#### 2.5 Component Migration from v0 Designs

Port components from `.github/context/private-designs/v0/`:

**Core Layout Components:**

- [ ] `components/layout/navbar.tsx` - Main navigation
- [ ] `components/layout/footer.tsx` - Footer
- [ ] `components/layout/sidebar.tsx` - Sidebar navigation

**Dashboard Components:**

- [ ] `components/dashboard/stats-cards.tsx` - Statistics display
- [ ] `components/dashboard/current-context.tsx` - Currently reading/playing
- [ ] `components/dashboard/fresh-arrivals.tsx` - Recently added items

**Scanner Components:**

- [ ] `components/scanner/camera-view.tsx` - Camera overlay
- [ ] `components/scanner/scan-result.tsx` - Result display
- [ ] `components/scanner/manual-search.tsx` - Manual entry fallback

**Item Components:**

- [ ] `components/item/detail-view.tsx` - Item detail page
- [ ] `components/item/card.tsx` - Grid/list item card
- [ ] `components/item/qr-code.tsx` - QR code display

#### 2.6 API Client Setup

```typescript
// frontend/lib/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // For session cookies
});

// Add interceptors for error handling, auth tokens, etc.
```

```typescript
// frontend/lib/api/hooks.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from './client';

export function useItems() {
  return useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/v1/items');
      return data.data;
    }
  });
}

export function useLookupISBN() {
  return useMutation({
    mutationFn: async (isbn: string) => {
      const { data } = await apiClient.get(`/api/v1/lookup/isbn/${isbn}`);
      return data.data;
    }
  });
}
```

#### 2.7 TypeScript Types

```typescript
// frontend/types/frbr.ts
export interface Work {
  id: number;
  title: string;
  creators: Array<{
    name: string;
    role: string;
  }>;
  meta: Record<string, any>;
}

export interface Expression {
  id: number;
  work_id: number;
  work?: Work;
  language?: string;
  format?: string;
}

export interface Manifestation {
  id: number;
  expression_id: number;
  expression?: Expression;
  title: string;
  publisher?: string;
  publication_date?: string;
  isbn13?: string;
  isbn10?: string;
  identifiers: Record<string, string>;
  meta: Record<string, any>;
}

export interface Item {
  id: number;
  manifestation_id: number;
  manifestation?: Manifestation;
  owner_id: string;
  status: 'available' | 'reading' | 'lent' | 'lost';
  added_at: string;
}
```

#### 2.8 Core Pages Implementation

### Week 1-2: Essential Pages

**Dashboard (Home Page):**

- [ ] Implement main dashboard layout
- [ ] Connect to `/api/v1/stats` endpoint
- [ ] Display stats cards (total items, lent out, to read)
- [ ] Show "Current Context" (currently reading/playing)
- [ ] Display "Fresh Arrivals" (recently added items)
- [ ] Add loading states and error handling

**Collection Browser (List Page):**

- [ ] Implement filtering UI (format, status, tags)
- [ ] Add sorting controls
- [ ] Create responsive grid/list view toggle
- [ ] Implement pagination
- [ ] Add search functionality
- [ ] Connect to `/api/v1/manifestations` endpoint

**Item Detail Page:**

- [ ] Create item detail layout
- [ ] Implement FRBR data display (Work → Expression → Manifestation → Item)
- [ ] Add tabbed interface (Details, My Copy, Federation, Shop)
- [ ] Display cover image with fallback
- [ ] Show QR code
- [ ] Add action buttons (Edit, Lend, Delete)

### Week 3: Scanner & Add Functionality

**Scanner Interface:**

- [ ] Port HTML5 QR Code scanner to React
- [ ] Create camera permission handling
- [ ] Implement viewfinder overlay (matching v0 design)
- [ ] Add tab interface (Barcode, Cover Match, Manual)
- [ ] Connect to `/api/v1/lookup/isbn/:isbn`
- [ ] Handle scan success/failure states
- [ ] Add "Add to Library" action

**Manual Add/Edit Form:**

- [ ] Create form with React Hook Form
- [ ] Add Zod validation schema
- [ ] Implement autocomplete for existing Works
- [ ] Add cover image upload
- [ ] Connect to `/api/v1/manifestations` POST/PUT
- [ ] Add success/error toast notifications

### Week 4: Polish & Integration

**Navigation & Routing:**

- [ ] Implement Next.js App Router structure
- [ ] Add navigation menu with active states
- [ ] Create mobile hamburger menu
- [ ] Add breadcrumbs
- [ ] Implement deep linking

**User Experience Enhancements:**

- [ ] Add loading skeletons
- [ ] Implement optimistic updates
- [ ] Add toast notifications system
- [ ] Create empty states
- [ ] Add confirmation dialogs for destructive actions

**Testing:**

- [ ] Write component tests (React Testing Library)
- [ ] Add E2E tests (Playwright)
- [ ] Test responsive design on multiple devices
- [ ] Perform accessibility audit (WCAG 2.1 AA)

**Deliverables:**

- ✅ Complete frontend with all features (Dashboard, Collection, Item detail, Scanner)
- ✅ Design system fully implemented (Modern Athenaeum – Tailwind v4 CSS @theme)
- ✅ All components built and connected to live Flask API
- ✅ Mobile-responsive design
- ✅ React Query hooks + Sonner toasts
- ✅ TypeScript types matching FRBR data model
- ✅ Barcode scanner (html5-qrcode) wired to `/api/isbn/<isbn>`
- ✅ API error states in all components (no silent blank screens)
- ✅ Phase 2 backend test suite (`tests/test_phase2_frontend.py`, 24 tests)

**Status:** ✅ **COMPLETE** (February 20, 2026)

---

## Phase 3: Testing & Polish

**Duration:** 1.5 weeks
**Goal:** Comprehensive testing and refinement

### 3.1 Testing Suite

- [ ] Unit tests for all components
- [ ] Integration tests for API calls
- [ ] E2E tests for critical flows (scan, add, view, edit)
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Mobile device testing (iOS, Android)
- [ ] Accessibility testing (WCAG 2.1 AA)

### 3.2 Performance Optimization

- [ ] Run Lighthouse audit (target score > 90)
- [ ] Optimize bundle size
- [ ] Implement code splitting
- [ ] Add image lazy loading
- [ ] Test load times on slow connections

### 3.3 Bug Fixes & Polish

- [ ] Fix any UI inconsistencies
- [ ] Improve error messages
- [ ] Add loading states where missing
- [ ] Refine animations and transitions
- [ ] Test edge cases

**Deliverables:**

- ✅ 80%+ test coverage
- ✅ All critical bugs fixed
- ✅ Performance optimized
- ✅ Production-ready frontend

---

## Phase 4: Deployment & Cleanup

**Duration:** 1 week
**Goal:** Deploy new system and remove old code

### 4.1 Pre-Deployment Checklist

- [ ] Configure production environment variables
- [ ] Set up CDN for static assets
- [ ] Configure production database connection pooling
- [ ] Set up monitoring (Sentry, logging)
- [ ] Create backup and rollback procedures

### 4.2 Deployment Configuration

```nginx
# nginx.conf - Simple routing
server {
    server_name iqoqo.com;

    location /api/ {
        proxy_pass http://flask:5000;
    }

    location / {
        proxy_pass http://nextjs:3000;
    }
}
```

### 4.3 Deployment Steps

- [ ] Create database backup
- [ ] Deploy Flask API (with CORS enabled)
- [ ] Deploy Next.js frontend
- [ ] Update nginx routing
- [ ] Test all critical paths in production
- [ ] Monitor error rates and performance for 24 hours

### 4.4 Code Cleanup

- [ ] Remove `app/web/` directory entirely
- [ ] Remove Flask templates: `app/web/templates/`
- [ ] Remove old static files: `app/web/static/`
- [ ] Remove web blueprint registration from `app/__init__.py`
- [ ] Clean up old CSS/JS libraries
- [ ] Tag release: `git tag -a v2.0.0 -m "React migration complete"`
- [ ] Update README and CONTRIBUTING guides
- [ ] Archive old code: `git branch archive/flask-web`
- [ ] Celebrate! 🎉

**Deliverables:**

- ✅ Production deployment successful
- ✅ Old Flask web code removed
- ✅ Clean codebase with frontend/backend separation
- ✅ Documentation updated

---

## Risk Management

### Technical Risks

| Risk                         | Probability | Impact   | Mitigation                                     |
| ---------------------------- | ----------- | -------- | ---------------------------------------------- |
| API breaking changes         | Low         | High     | Test thoroughly, keep API endpoints compatible |
| Data loss during migration   | Low         | Critical | Database backups before deployment             |
| Performance regression       | Medium      | Medium   | Load testing, monitoring, rollback plan        |
| Frontend bundle size bloat   | Medium      | Low      | Bundle analysis, code splitting, tree shaking  |
| Browser compatibility issues | Low         | Medium   | Polyfills, progressive enhancement, testing    |
| Downtime during switch       | Low         | Medium   | Quick deployment process, test staging first   |

### User Experience Risks

| Risk                           | Probability | Impact | Mitigation                                      |
| ------------------------------ | ----------- | ------ | ----------------------------------------------- |
| User confusion with new UI     | High        | Medium | Clear changelog, in-app onboarding if needed    |
| Feature missing in new version | Low         | High   | Thorough feature parity checklist before launch |
| Mobile scanner not working     | Low         | High   | Extensive mobile testing, fallback methods      |

### Mitigation Strategies

1. **Testing** - Comprehensive testing before deployment
2. **Staging Environment** - Test the exact deployment on staging first
3. **Database Backup** - Full backup before any deployment
4. **Rollback Plan** - Git tag old version, can revert within 5 minutes
5. **Monitoring** - Real-time error tracking and performance monitoring

---

## Rollback Strategy

If critical issues arise after deployment:

1. **Immediate (< 5 min):**

   ```bash
   git checkout archive/flask-web
   git cherry-pick <web-blueprint-commit>
   docker-compose up --build
   ```

2. **API Issues (< 10 min):** Rollback Flask to previous tagged version
3. **Data Issues (< 30 min):** Restore database from pre-deployment backup
4. **Frontend Only Issues:** Fix forward - backend still works, just deploy frontend fix

**Rollback Triggers:**

- Error rate > 10% for critical endpoints after 15 minutes
- Complete inability to scan or add items
- Data corruption detected
- Security vulnerability discovered

**Rollback Triggers:**

- Error rate > 10% for critical endpoints after 15 minutes
- Complete inability to scan or add items
- Data corruption detected
- Security vulnerability discovered

---

## Success Metrics

### Technical KPIs

- **Performance:**
  - First Contentful Paint < 1.5s
  - Time to Interactive < 3s
  - Lighthouse Score > 90

- **Reliability:**
  - API uptime > 99.9%
  - Error rate < 1%
  - Zero data loss events

- **Code Quality:**
  - Test coverage > 80%
  - No critical security vulnerabilities
  - TypeScript strict mode enabled

### User Experience KPIs

- Page load feels faster (subjective + metrics)
- Mobile scanner easier to use
- Reduced clicks to common actions
- Positive user feedback (if public)

---

## Development Workflow During Migration

### Git Strategy

```text
main                    [Protected - production]
├── feature/api-v1      [API enhancements]
├── feature/frontend-dashboard
├── feature/frontend-scanner
└── feature/deployment  [Infrastructure updates]
```

**Branch Protection:**

- `main` requires PR reviews
- All tests must pass
- No direct commits to `main`

### Testing Strategy

```bash
# Backend tests
cd backend
source .venv/bin/activate
pytest tests/

# Frontend tests
cd frontend
pnpm test
pnpm test:e2e

# Integration tests (both running)
docker-compose up -d
pytest tests/integration/
```

### Local Development

```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate
flask run --port 5000

# Terminal 2: Frontend
cd frontend
pnpm dev

# Terminal 3: Database
docker-compose up postgres
```

---

## Timeline Summary

```text
Week 1-1.5: Phase 1 - API Enhancement & Frontend Init
Week 2-5:   Phase 2 - Frontend Build (Complete)
Week 6-7:   Phase 3 - Testing & Polish
Week 8:     Phase 4 - Deployment & Cleanup
```

**Estimated Effort:**

- Full-time: 8 weeks (~2 months)
- Part-time: 16 weeks (~4 months)

**Advantages of Direct Replacement:**

- Faster overall timeline (8 weeks vs 14 weeks)
- Simpler codebase during development
- No need to maintain two systems
- Cleaner git history
- Less deployment complexity

---

## Resources & References

### Documentation

- [Next.js App Router Docs](https://nextjs.org/docs/app)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Radix UI Components](https://www.radix-ui.com/primitives)
- [React Query Docs](https://tanstack.com/query/latest)
- [Flask-CORS](https://flask-cors.readthedocs.io/)

### Design References

- v0 design prototypes: `.github/context/private-designs/v0/`
- Architecture notes: `.github/context/private-notes/⚒️ Building New iqoqo Project Architecture.md`
- UI/UX design doc: `.github/context/private-notes/⚒️ Designing a Resource Management UI.md`

### Code Examples

- v0 dashboard: `.github/context/private-designs/v0/app/page.tsx`
- v0 scanner: `.github/context/private-designs/v0/app/scan/page.tsx`
- v0 item detail: `.github/context/private-designs/v0/app/item/page.tsx`

---

## Appendices

### A. Environment Variables

#### Backend (.env)

```bash
FLASK_APP=run.py
FLASK_ENV=development
DATABASE_URL=postgresql://user:pass@localhost:5432/iqoqo
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000
```

#### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### B. Docker Compose Updates

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: iqoqo
      POSTGRES_USER: iqoqo
      POSTGRES_PASSWORD: iqoqo

  backend:
    build:
      context: .
      dockerfile: deploy/Dockerfile
    volumes:
      - ./app:/app/app
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://iqoqo:iqoqo@postgres:5432/iqoqo
    depends_on:
      - postgres

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:5000

  nginx:
    image: nginx:alpine
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
```

### C. nginx Configuration

```nginx
# deploy/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:5000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;

        # API routes to Flask
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Everything else to Next.js
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support for Next.js HMR
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

---

## Conclusion

This migration plan provides a structured approach to modernizing the iqoqo application while maintaining operational continuity. The phased strategy allows for incremental progress, continuous user access, and the ability to roll back if issues arise.

Key success factors:

1. **Incremental delivery** - Each phase delivers working functionality
2. **Parallel operation** - Both systems run during transition
3. **Testing rigor** - Comprehensive testing at each stage
4. **Risk mitigation** - Clear rollback procedures
5. **Documentation** - Detailed guides for developers and users

By following this plan, the iqoqo project will transition to a modern, maintainable, and user-friendly architecture that supports future growth and feature development.

---

**Plan Status:** Draft v1.0
**Next Review:** After Phase 0 completion
**Updates:** Document will be updated after each phase retrospective
