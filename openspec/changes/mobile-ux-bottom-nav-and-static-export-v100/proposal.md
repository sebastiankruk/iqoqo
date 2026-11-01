## Why
To ship native Android and iOS apps in `v1.0.0`, the Next.js frontend must support static export (`CAPACITOR_BUILD=true`) without rewriting our canonical path-parameterized URLs (`/item/[id]`, `/manifestation/[id]`, `/work/[id]`, `/expression/[id]`) to query strings (`/item?id=...`), and must resolve the mobile bottom navigation dead-end (`Login` tab shown to logged-in users), circular loading spinner clipping, and mobile touch-target density findings from the UX audit.

## What Changes

- **4-Action Mobile Bottom Navigation (`Home / Scan / Collection / Search`):** Refactor mobile bottom navigation (`frontend/components/dashboard/navbar.tsx` / `mobile-bottom-nav.tsx`) to expose `Home` (`/`), `Scan` (`/scan`), `Collection` (`/collection`), and `Search` (`/collection?focus=search` or search sheet), removing the dead `Login` tab from the bottom bar and keeping auth/profile/server switching in the top header avatar menu.
- **Circular Loading Spinner & UX Audit Polish:** Fix circular loading icon aspect-ratio/border clipping across scanner, auth-exchange, and collection views; fix Landing Hero CTA hierarchy (`frontend/components/landing/hero.tsx`); and refactor clustered author micro-buttons in `frontend/components/collection/item-card.tsx` into touch-safe targets ($\ge 44\text{px}$).
- **Zero-URL-Rewrite Conditional Static Export (`CAPACITOR_BUILD=true`):** Configure `frontend/next.config.ts` to enable `output: "export"` and `images: { unoptimized: true }` when `CAPACITOR_BUILD=true`. Add `generateStaticParams() { return [{ id: "_placeholder" }]; }` to dynamic routes (`/item/[id]`, `/manifestation/[id]`, `/work/[id]`, `/expression/[id]`, `/u/[username]`, `/share/[token]`, `/help/[slug]`) and a `useResolvedRouteParam()` hook that reads the live ID from `useParams()` or `window.location.pathname` when served via the static shell.
- **Admin Route Exclusion Guard:** Add `frontend/app/admin/layout.tsx` to intercept `/admin/*` on native Capacitor builds and offer a 1-tap redirect to the web admin UI via `@capacitor/browser`.

## Capabilities

### New Capabilities
- `mobile-ux-and-static-export`: 4-tab mobile bottom navigation (`Home / Scan / Collection / Search`), spinner & tap-target UX polish, admin native exclusion guard, and zero-URL-rewrite Next.js static export for Capacitor.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `frontend/next.config.ts`
- `frontend/components/dashboard/navbar.tsx`
- `frontend/components/landing/hero.tsx`
- `frontend/components/collection/item-card.tsx`
- `frontend/lib/capacitor/route-params.ts`
- `frontend/app/{item,manifestation,work,expression}/[id]/page.tsx`, `frontend/app/u/[username]/page.tsx`, `frontend/app/share/[token]/page.tsx`, `frontend/app/help/[slug]/page.tsx`, `frontend/app/admin/layout.tsx`
