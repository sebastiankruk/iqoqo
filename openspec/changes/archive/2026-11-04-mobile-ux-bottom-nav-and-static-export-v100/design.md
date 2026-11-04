## Context

In the archived `origin/feat/1.0.0/mobile-capacitor` branch (commits `a735ba3` and `2990292`), dynamic routes (`/item/[id]` and `/manifestation/[id]`) were rewritten to query parameters (`/item?id=...`) across 40+ files using `migrate_links.js` to appease Next.js `output: "export"`. That URL rewrite breaks canonical FRBRoo Linked Open Data IRIs (`app/core/iri.py`), ActivityPub object URLs, and clean RESTful routing.

## Goals / Non-Goals

**Goals:**
- Export the Next.js user-facing app to `frontend/out/` when `CAPACITOR_BUILD=true` with **zero changes to `/item/[id]`, `/manifestation/[id]`, `/work/[id]`, or `/expression/[id]` link schemas**.
- Replace the `Home / Scan / Collection / Login` mobile bottom bar with `Home / Scan / Collection / Search`.
- Fix the circular loading spinner distortion and `ItemCard` author touch-target overlap on mobile screens.
- Exclude `/admin/*` workflows from the native app experience by redirecting to the external system browser.

**Non-Goals:**
- Rewriting any `<Link href="/item/${id}">` or canonical IRI paths to query parameters.

## Decisions

### Zero-URL-Rewrite Static Export via Placeholder Shell + Runtime Path Extraction
* **Decision:** Keep all `[id]`, `[username]`, `[token]`, and `[slug]` directory routes intact. Export `generateStaticParams()` returning a single placeholder entry (e.g., `[{ id: "_placeholder" }]`) so `CAPACITOR_BUILD=true npm run build` emits `out/item/_placeholder/index.html`. Provide `useResolvedRouteParam(paramName)` in `frontend/lib/capacitor/route-params.ts` which returns `useParams()[paramName]` unless it equals `"_placeholder"`, in which case it extracts the segment directly from `window.location.pathname`.
* **Rationale:** Preserves 100% URL compatibility across SSR web mode, Linked Open Data IRIs, ActivityPub objects, and Capacitor native WebViews without touching link callers.

## Risks / Trade-offs

- **Risk:** Server-only API route handlers (`frontend/app/api/*` and `frontend/app/auth/exchange/route.ts`) fail Next.js static export if they lack static export compatibility or build-time exclusion.
  - **Mitigation:** Pre-build script / conditional route handling during `CAPACITOR_BUILD=true` swaps or skips BFF cookie routes since native mode uses `/auth-exchange` client page (`C97`) and direct `apiClient` Bearer requests (`C96`).
