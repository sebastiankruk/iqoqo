## Context

See `proposal.md` for motivation. During the `/grill-me` interview (`2026-11-18`), a **dedicated full-screen `/graph` explorer page** (reached via an `"Explore Graph"` button on entity detail pages) was selected over embedding inline mini-graphs on every entity tab. Because iqoqo supports `CAPACITOR_BUILD=true` static export (`next.config.ts`), using a query-parameter route `/graph?type=work&id=123` avoids adding another dynamic `[id]` route segment and works seamlessly on web, Android, and iOS.

## Goals / Non-Goals

**Goals:**
- Keep graph responses bounded (`depth <= 2`, `max_nodes <= 150`) with `selectinload`/batched SQL queries and zero N+1 lookups.
- Enforce three-tier visibility (`public`, `friends_only`, `private`) strictly on `Item` nodes and never leak unowned private items or unapproved (`status != "accepted"`) LOD candidate links.
- Deliver an intuitive, responsive pan/zoom/drag graph explorer (`frontend/app/graph/page.tsx`) with zero server-side rendering dependency on native mobile builds.

**Non-Goals:**
- Editing or mutating FRBR relations directly by dragging edges on the graph (read-only exploration + navigation to existing FRBR Relation / Custodian editors).
- Full-library global hairball dump without an anchor entity (`entity_type` + `entity_id` required).

## Decisions

1. **Deterministic radial/force SVG renderer with pointer pan/zoom (`frontend/components/graph/frbr-relation-graph.tsx`):** Zero external WebGL dependency and full accessibility (`aria-label` on nodes, keyboard focus traversal, crisp dark/light Tailwind theme tokens matching `app/globals.css`), plus smooth touch pan/pinch support on Capacitor mobile viewports.
2. **Backend `GraphService.build_neighborhood()` (`app/core/graph_service.py`):** Performs breadth-first expansion up to `depth` (`1` or `2`, capped at `150` nodes) across:
   - FRBR backbone: `Work ↔ Expression ↔ Manifestation ↔ Item` (filtering `Item` via caller visibility rules)
   - `Series` / `WorkSeriesMembership`
   - `WorkPart` (complex works / box sets / serial containers) & `WorkExpansionLink`
   - `WorkContribution` / `Contributor`
   - Attached map supplements (`iqoqo:hasMapAttachment`)
   - `SemanticLink` (`status == "accepted"`)
3. **Strict Capacitor-compatible route `/graph` (`frontend/app/graph/page.tsx`):** Wraps `useSearchParams()` in `<Suspense>` and reads `?type=...&id=...&depth=...`.

## Risks / Trade-offs

- **Serial works with 100+ issues or prolific authors overflowing the graph** → Deterministic priority ordering during BFS (`FRBR anchor path` -> `Series/Expansions/Parts` -> `Contributors/Maps/LOD` -> sibling issues/items up to `max_nodes=150`) with a visible `"Graph truncated to 150 nodes — click a node to recenter"` banner when `meta.truncated === true`.
- **Static export `Suspense` build failure in Next.js 16** → Wrap `useSearchParams()` client child in `<Suspense>` inside `frontend/app/graph/page.tsx` and validate with `CAPACITOR_BUILD=true` build check.
