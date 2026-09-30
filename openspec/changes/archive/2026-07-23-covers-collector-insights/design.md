---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

The cover pipeline in `app/utils/covers.py` follows a 5-tier waterfall: (1) User photo → (1.5) Direct URL hotlinks → (2) External APIs (OpenLibrary, Google Books, Allegro) → (2.5) Non-ISBN providers (MusicBrainz, TMDb, IGDB) → (3/4) LLM generation → (5) PIL fallback. Each tier stores the origin in `manifestation.meta['cover_source']` (e.g., `"fallback_pil"`, `"llm_gemini"`, `"api_openlibrary"`). The existing `add_source_badge()` function draws a tiny colored letter in the bottom-right corner of the cover image itself, but this badge is visually cryptic (a single letter on a 30×30 box) and never explained in the UI.

The dashboard currently renders five `StatsCards` showing aggregated counts from `/api/stats` (total items, reading, wishlist, lent, borrowed). The underlying `DashboardStats` type has additional fields but no temporal or distributional analytics.

## Goals / Non-Goals

**Goals:**

- Produce visually polished fallback covers that clearly communicate they are placeholders and invite user contribution
- Surface cover provenance in the UI (not buried in DB metadata) so collectors understand where their cover came from
- Provide read-only analytics: item acquisition velocity over time and media type/format distribution
- Keep analytics queries performant with GROUP BY aggregates (no N+1 patterns)

**Non-Goals:**

- Interactive editing of covers (existing "Upload Cover" / "Regenerate Cover" actions handle this)
- Geo-spatial analytics (deferred — requires location data collection which is not yet in the schema)
- Real-time streaming analytics or WebSocket updates
- Third-party analytics integration (Google Analytics, Plausible, etc.)
- Modifying the cover pipeline tier ordering or adding new external providers

## Decisions

### D1: Enhance `generate_fallback_cover()` in-place, not replace

**Decision**: Upgrade the existing `generate_fallback_cover()` function to render a more polished gradient with an iqoqo logo watermark, a "Placeholder — contribute a cover" call-to-action text, and a "powered by iqoqo" provenance footer.

**Rationale**: The function already produces deterministic gradient covers. Keeping it in-place preserves the same file-naming convention (`{identifier}_generated.jpg`) and the existing callers in `process_cover_pipeline`. The center watermark (`add_center_watermark`) is already applied to fallback covers — we refine its visual output rather than creating a parallel path.

**Alternative considered**: A template-image-based approach (pre-designed SVG templates per format). Rejected because it adds asset management complexity and the procedural PIL approach is already proven and deterministic.

### D2: Frontend provenance indicator as a lightweight badge component

**Decision**: Create a `<CoverProvenance>` component that reads `cover_source` from the manifestation/item metadata and renders a human-readable label with an icon (e.g., "AI-generated", "OpenLibrary", "User photo", "Placeholder"). Place it near the cover image on detail pages.

**Rationale**: This is a read-only display concern — no API changes needed. The `cover_source` is already returned in the manifestation/item API responses via the `meta` JSONB field.

**Alternative considered**: Modifying the cover image itself to embed a permanent visible label. Rejected because it degrades image quality and makes provenance information un-removable.

### D3: Analytics endpoints on `profile_bp` with GROUP BY aggregates

**Decision**: Add two new endpoints to the existing `profile_bp` blueprint:

- `GET /api/profile/insights/velocity` — returns item counts grouped by month (last 12 months)
- `GET /api/profile/insights/distribution` — returns item counts grouped by `Expression.content_type` and `Manifestation.meta.format`

**Rationale**: Analytics are per-user (the authenticated collector), so they belong in the profile module. Using `GROUP BY` with `DATE_TRUNC` (for velocity) and JSON field extraction (for distribution) avoids N+1 queries. Both endpoints are `@require_auth` (no admin permission needed — users view their own data).

**Alternative considered**: Adding to `system.py` under `/api/stats/`. Rejected because these are personal analytics, not instance-wide stats. The existing `/api/stats` endpoint already serves the admin dashboard.

### D4: Recharts for frontend chart rendering

**Decision**: Add `recharts` as the charting library for the analytics components.

**Rationale**: Recharts is React-native, declarative, SSR-compatible, and the most widely adopted charting library in the Next.js ecosystem. It renders SVG (no canvas), which aligns with the existing Tailwind/Shadcn design system. The bundle size impact is ~40KB gzipped.

**Alternative considered**: Chart.js (canvas-based, less React-idiomatic), D3 (too low-level for simple bar/donut charts), Nivo (heavier, overlapping with Recharts). Shadcn has chart primitives based on Recharts, confirming ecosystem alignment.

### D5: No new database columns or migrations

**Decision**: All analytics are computed on-the-fly from existing schema fields: `Item.created_at` (velocity), `Expression.content_type` and `Manifestation.meta['format']` (distribution). Cover provenance uses the existing `Manifestation.meta['cover_source']`.

**Rationale**: Avoids migration churn. The analytics queries are read-only aggregates that run efficiently with proper indexes (which already exist on `Item.owner_id` and `Item.created_at`).

## Risks / Trade-offs

- **[Velocity query performance on large collections]** → Mitigation: Query is bounded to last 12 months with a WHERE clause on `Item.created_at`; GROUP BY on `DATE_TRUNC('month', ...)` uses the existing index.
- **[Recharts bundle size]** → Trade-off accepted: ~40KB gzipped is acceptable. Tree-shaking limits it to imported components only.
- **[Geospatial analytics deferred]** → Trade-off accepted: The roadmap mentions geospatial data, but no location fields exist in the schema today. Adding location collection is a separate feature. The insights framework can be extended when location data is available.
- **[Fallback cover re-generation]** → Existing covers produced by the old fallback generator will not automatically update. New and re-generated covers will use the enhanced design. This is acceptable — the improvement is forward-looking.

## Open Questions

- Should the velocity chart default to 12 months or show all-time data? (Recommendation: 12 months, with optional "all time" toggle — keep scope minimal for v0.7.12.)
