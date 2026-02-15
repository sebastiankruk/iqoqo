# Migration Quick-Start Checklist

This checklist provides a step-by-step guide to begin the migration based on the full [Migration Plan](./MIGRATION_PLAN.md).

**Migration Strategy:** Direct replacement - build new frontend completely, then deploy and remove old Flask web code.

## Pre-Flight Check

- [ ] Read full migration plan: [MIGRATION_PLAN.md](./MIGRATION_PLAN.md)
- [ ] Review v0 design files in `.github/context/private-designs/v0/`
- [ ] Ensure current system is working and tested
- [ ] Create backup of current database: `pg_dump iqoqo > backup_$(date +%Y%m%d).sql`
- [ ] Create new git branch: `git checkout -b feature/react-migration`
- [ ] Tag current working version: `git tag -a v1.0-pre-migration -m "Before React migration"`

---

## Phase 1: Foundation (Start Here!)

### Step 1: Create Frontend Directory Structure

```bash
# From project root
mkdir -p frontend
cd frontend

# Initialize Next.js with TypeScript and Tailwind
npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*"

# Install additional dependencies
npm install @tanstack/react-query zustand axios zod react-hook-form @hookform/resolvers
npm install lucide-react date-fns clsx tailwind-merge class-variance-authority

# Install dev dependencies
npm install -D prettier eslint-config-prettier @types/node
```

### Step 2: Set Up shadcn/ui

```bash
cd frontend

# Initialize shadcn/ui
npx shadcn@latest init

# Add required components
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add input
npx shadcn@latest add badge
npx shadcn@latest add avatar
npx shadcn@latest add tabs
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
npx shadcn@latest add toast
npx shadcn@latest add progress
```

### Step 3: Configure Theme

Create/update these files:

**`frontend/tailwind.config.ts`:**

```typescript
import type { Config } from "tailwindcss"

const config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
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
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config

export default config
```

**`frontend/.env.local`:**

```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Step 4: Update Docker Compose

Add frontend service to `docker-compose.yml`:

```yaml
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:5000
    command: npm run dev
```

Create `frontend/Dockerfile.dev`:

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy source
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

### Step 5: Test Dual Stack

```bash
# Terminal 1: Start backend
cd /Users/sebastiankruk/Development/iQoQo/iqoqo
source .venv/bin/activate
flask run --port 5000

# Terminal 2: Start frontend
cd /Users/sebastiankruk/Development/iQoQo/iqoqo/frontend
npm run dev

# Verify:
# - Backend: [http://localhost:5000/api/health](http://localhost:5000/api/health)
# - Frontend: [http://localhost:3000](http://localhost:3000)
```

**Checkpoint:** ✅ Both services running without errors

**Note:** The old Flask web interface at [http://localhost:5000/](http://localhost:5000/) still works - keep it for reference during development. We'll remove it after deployment.

---

## Phase 2: API Enhancement

### Step 6: Install CORS and API Tools

```bash
# Activate venv
source .venv/bin/activate

# Install packages
pip install flask-cors flask-restx pydantic

# Update requirements
pip freeze > requirements.txt
```

### Step 7: Add CORS Configuration

Edit `app/__init__.py`:

```python
from flask_cors import CORS

def create_app(config_class=Config, config_override=None):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Add CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # ... rest of setup
```

### Step 8: Create API v1 Structure

```bash
mkdir -p app/api/v1
touch app/api/v1/__init__.py
touch app/api/v1/items.py
touch app/api/v1/manifestations.py
touch app/api/v1/lookup.py
touch app/api/v1/stats.py
```

### Step 9: Test API Endpoints

```bash
# Test ISBN lookup
curl http://localhost:5000/api/isbn/9780547928227

# Test items list
curl http://localhost:5000/api/items

# Verify CORS headers
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:5000/api/items
```

**Checkpoint:** ✅ API accessible from frontend origin

---

## Build the Complete Frontend

From this point, follow the [Full Migration Plan](./MIGRATION_PLAN.md) Phase 2 to build all pages and components.

### Quick Reference: Key Pages to Build

1. **Dashboard** (`app/page.tsx`) - Stats, current context, fresh arrivals
2. **Scanner** (`app/scan/page.tsx`) - Camera interface
3. **Collection** (`app/collection/page.tsx`) - Browse/search
4. **Item Detail** (`app/item/[id]/page.tsx`) - Full item info
5. **Add/Edit** - Manual entry form

---

## Testing Before Deployment

### Step 10: Create API Client

**`frontend/lib/api/client.ts`:**

```typescript
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);
```

**`frontend/lib/api/hooks.ts`:**

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export function useItems() {
  return useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/items');
      return data;
    }
  });
}

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      const { data } = await apiClient.get('/api/stats');
      return data;
    }
  });
}
```

### Step 11: Set Up React Query Provider

**`frontend/app/providers.tsx`:**

```typescript
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

**Update `frontend/app/layout.tsx`:**

```typescript
import { Providers } from './providers';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
```

### Step 12: Create Simple Dashboard

**`frontend/app/page.tsx`:**

```typescript
'use client';

import { useItems, useStats } from '@/lib/api/hooks';

export default function Dashboard() {
  const { data: items, isLoading: itemsLoading } = useItems();
  const { data: stats, isLoading: statsLoading } = useStats();

  if (itemsLoading || statsLoading) {
    return <div className="p-8">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-warm-paper p-8">
      <h1 className="font-serif text-4xl font-bold text-deep-indigo mb-8">
        iqoqo Dashboard
      </h1>

      <div className="grid gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold">Stats</h2>
          <pre>{JSON.stringify(stats, null, 2)}</pre>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold">Items</h2>
          <pre>{JSON.stringify(items, null, 2)}</pre>
        </div>
      </div>
    </div>
  );
}
```

```bash
# Run all tests
source .venv/bin/activate && pytest
cd frontend && npm test

# Run E2E tests
cd frontend && npm run test:e2e

# Test critical flows manually:
# 1. Scan a barcode
# 2. Add an item manually
# 3. View item details
# 4. Edit an item
# 5. Browse collection
# 6. Search

# Performance check
cd frontend && npm run build
# Check bundle size, run Lighthouse
```

**Checkpoint:** ✅ All features working, all tests passing

---

## Deployment

### Build Production

```bash
# Build frontend for production
cd frontend
npm run build
npm run start  # Test production build locally
```

### Deploy

```bash
# Create database backup
pg_dump iqoqo > backup_pre_migration_$(date +%Y%m%d).sql

# Deploy via Docker Compose
docker-compose down
docker-compose up --build -d

# Monitor logs
docker-compose logs -f
```

### Cleanup Old Code

Only after verifying everything works in production:

```bash
# Remove old Flask web code
rm -rf app/web/

# Update app/__init__.py to remove web blueprint
# (Remove the web_bp import and registration)

# Commit changes
git add .
git commit -m "Remove old Flask web interface"
git tag -a v2.0.0 -m "React migration complete"
git push origin main --tags
```

**Checkpoint:** ✅ New system deployed, old code removed

---

## Rollback Plan (If Needed)

If something goes wrong:

```bash
# Restore old version
git checkout v1.0-pre-migration

# If database issues, restore backup
psql iqoqo < backup_pre_migration_YYYYMMDD.sql

# Rebuild and redeploy
docker-compose up --build -d
```

---

## Post-Migration

Once deployed successfully:

- ✅ New React frontend live
- ✅ Old Flask web code removed
- ✅ Database intact and working
- ✅ All features functional
- ✅ Clean codebase

**Next steps:**

1. Monitor performance and errors
2. Gather user feedback
3. Plan new features (PWA, enhanced scanner, etc.)
4. Update documentation

Refer to the full [Migration Plan](./MIGRATION_PLAN.md) for more details!

---

## Common Issues & Troubleshooting

### CORS Errors

```text
Access to XMLHttpRequest blocked by CORS policy
```

**Fix:** Verify CORS is properly configured in Flask with correct origins

### Port Conflicts

```text
Port 3000 already in use
```

**Fix:** `lsof -ti:3000 | xargs kill -9`

### Module Not Found (Frontend)

```text
Cannot find module '@/lib/api/client'
```

**Fix:** Check `tsconfig.json` has correct `paths` configuration:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### API Connection Refused

```text
Error: connect ECONNREFUSED 127.0.0.1:5000
```

**Fix:** Ensure Flask backend is running and accessible

---

## Verification Commands

```bash
# Check Flask is running
curl http://localhost:5000/api/health

# Check Next.js is running
curl http://localhost:3000

# Check CORS headers
curl -I -H "Origin: http://localhost:3000" http://localhost:5000/api/items

# Check frontend build
cd frontend && npm run build

# Run tests
cd .. && source .venv/bin/activate && pytest
cd frontend && npm test
```

---

Good luck with the migration! 🚀

Remember: Take it one phase at a time, test thoroughly, and don't hesitate to refer back to the detailed migration plan.
