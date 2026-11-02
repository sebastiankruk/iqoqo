## 1. Mobile Bottom Navigation & UX Audit Fixes

- [x] 1.1 Update mobile bottom navigation in `frontend/components/dashboard/navbar.tsx` (or `mobile-bottom-nav.tsx`) to render 4 primary actions: `Home` (`/`), `Scan` (`/scan`), `Collection` (`/collection`), and `Search` (`/collection?focus=search` / global search trigger), removing `Login` from the bottom bar.
- [x] 1.2 Fix circular loading spinner CSS (`aspect-square shrink-0 animate-spin`) across scanner lookup, auth-exchange, and collection infinite scroll so circles never clip or deform into ovals on mobile viewports.
- [x] 1.3 Update `frontend/components/landing/hero.tsx` so `"Start Your Catalog"` is the single primary solid accent CTA and secondary actions use outline/ghost variants.
- [x] 1.4 Refactor author links in `frontend/components/collection/item-card.tsx` to eliminate overlapping micro-buttons on mobile touchscreens ($\ge 44\text{px}$ tap target).
- [x] 1.5 Add `en.json` and `pl.json` (sentence-case Polish) translation keys for any new navigation labels.

## 2. Zero-URL-Rewrite Conditional Static Export (`CAPACITOR_BUILD=true`)

- [x] 2.1 Configure `frontend/next.config.ts` to use `output: "export"` and `images: { unoptimized: true }` when `process.env.CAPACITOR_BUILD === "true"`.
- [x] 2.2 Implement `useResolvedRouteParam()` in `frontend/lib/capacitor/route-params.ts` to resolve dynamic route IDs from `useParams()` or `window.location.pathname` when served from a static `_placeholder` shell.
- [x] 2.3 Add `generateStaticParams()` placeholder exports to dynamic pages (`/item/[id]`, `/manifestation/[id]`, `/work/[id]`, `/expression/[id]`, `/u/[username]`, `/share/[token]`, `/help/[slug]`) while preserving all `/item/${id}` path links untouched.
- [x] 2.4 Create `frontend/app/admin/layout.tsx` to guard `/admin/*` on native Capacitor platforms and offer a 1-tap redirect to the web admin interface via `@capacitor/browser`.

## 3. Verification & Tests

- [x] 3.1 Author unit tests in `frontend/__tests__/lib/capacitor/route-params.test.ts` and `frontend/__tests__/components/dashboard/mobile-bottom-nav.test.tsx`.
- [x] 3.2 Author Playwright mobile viewport tests in `frontend/__tests__/e2e/mobile_catalog_navigation.spec.ts` (`Pixel 7`, `iPhone 14`) verifying the 4-tab bottom navigation (`Home / Scan / Collection / Search`) and `/item/[id]` navigation.
- [x] 3.3 Verify `CAPACITOR_BUILD=true npm run build` inside `frontend/` succeeds and `IQOQO_AI_MODE=1 make lint` + `IQOQO_AI_MODE=1 make test` pass.
