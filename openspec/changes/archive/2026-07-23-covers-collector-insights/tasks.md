---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Cover Fallback Enhancement

- [x] 1.1 Upgrade `generate_fallback_cover()` in `app/utils/covers.py` — add "Placeholder — contribute a cover" call-to-action text rendered in a lighter font below the author line, add a subtle "powered by iqoqo" footer at the bottom
- [x] 1.2 Refine gradient color generation to produce more aesthetically muted palettes (shift hue range to avoid harsh neon tones)
- [x] 1.3 Verify center watermark (`add_center_watermark`) continues to apply correctly on top of the enhanced fallback design
- [x] 1.4 Update `add_source_badge()` BADGE_MAP to include missing providers: `api_musicbrainz` → ("M", "teal"), `api_tmdb` → ("T", "red") — currently missing from the mapping

## 2. Cover Provenance Frontend Component

- [x] 2.1 Create `frontend/components/cover/cover-provenance.tsx` — a small badge/label component that translates `cover_source` string to human-readable text + Lucide icon (e.g., `"api_openlibrary"` → "OpenLibrary" with `Globe` icon, `"fallback_pil"` → "Placeholder" with `ImageOff` icon, `"user_photo"` → "User photo" with `Camera` icon, `"llm_gemini"` → "AI-generated" with `Sparkles` icon)
- [x] 2.2 Mount `<CoverProvenance>` on the item detail page near the cover image, reading `cover_source` from `item.manifestation_meta?.cover_source` or `item.meta?.cover_source`
- [x] 2.3 Mount `<CoverProvenance>` on the manifestation detail page near the cover image, reading from `manifestation.meta?.cover_source`
- [x] 2.4 Handle legacy data gracefully: if `cover_source` is undefined/null, either show "Source: Unknown" or hide the provenance indicator
- [x] 2.5 Add i18n translation keys for all provenance labels

## 3. Backend Analytics Endpoints

- [x] 3.1 Add `GET /api/profile/insights/velocity` endpoint to `app/api/profile.py` — `@require_auth`, query items by `owner_id = g.user_id`, GROUP BY `DATE_TRUNC('month', Item.created_at)` for last 12 months, fill missing months with `count: 0`, return JSON array of `{month, count}`
- [x] 3.2 Add `GET /api/profile/insights/distribution` endpoint to `app/api/profile.py` — `@require_auth`, return `by_type` (GROUP BY `Expression.content_type` via Item → Manifestation → Expression join) and `by_format` (GROUP BY `Manifestation.meta['format']` via Item → Manifestation join), return JSON with both arrays
- [x] 3.3 Add aggregate query helpers in `app/core/data_manager.py` (or inline in profile.py): `get_velocity_stats(owner_id)` and `get_distribution_stats(owner_id)`, using SQLAlchemy 2.0 `select()` + `func.date_trunc` + `func.count` with `# pylint: disable=not-callable`

## 4. Backend Tests

- [x] 4.1 Write `tests/test_api_profile_insights.py` — test velocity endpoint returns 12 months of data for authenticated user, 0-count months included, 401 for unauthenticated
- [x] 4.2 Test distribution endpoint returns correct `by_type` and `by_format` groupings, empty arrays for user with no items
- [x] 4.3 Test fallback cover enhancement — verify `generate_fallback_cover()` still produces a valid JPEG, with correct dimensions, and deterministic output for same inputs
- [x] 4.4 Test `add_source_badge()` with new providers (`api_musicbrainz`, `api_tmdb`) renders without errors

## 5. Frontend Dependencies & Types

- [x] 5.1 Install `recharts` in the frontend: `npm install recharts`
- [x] 5.2 Add TypeScript interfaces in `frontend/types/frbr.ts` or new `frontend/types/insights.ts`: `VelocityPoint { month: string; count: number }`, `TypeDistribution { type: string; count: number }`, `FormatDistribution { format: string; count: number }`, `InsightsData { by_type: TypeDistribution[]; by_format: FormatDistribution[] }`
- [x] 5.3 Add API client functions in `frontend/lib/api/profile.ts` (or extend existing): `getVelocityInsights()`, `getDistributionInsights()`
- [x] 5.4 Add React Query hooks: `useVelocityInsights()`, `useDistributionInsights()` in `frontend/lib/api/hooks.ts`

## 6. Dashboard Analytics Components

- [x] 6.1 Create `frontend/components/dashboard/velocity-chart.tsx` — a Recharts `BarChart` (or `AreaChart`) rendering monthly acquisition counts, responsive via `ResponsiveContainer`, with loading skeleton and error state
- [x] 6.2 Create `frontend/components/dashboard/type-distribution-chart.tsx` — a Recharts `PieChart` (donut) or `BarChart` rendering media type distribution, with labels showing type name and count, responsive, with loading skeleton and error state
- [x] 6.3 Create `frontend/components/dashboard/collection-insights.tsx` — a wrapper component that mounts `VelocityChart` and `TypeDistributionChart` side by side (2-column grid on desktop, stacked on mobile)
- [x] 6.4 Mount `<CollectionInsights>` on the dashboard page below the existing `<StatsCards>`, conditionally rendered only for authenticated users
- [x] 6.5 Add i18n translation keys for chart titles, axis labels, and empty-state messages

## 7. Frontend Tests

- [x] 7.1 Write Vitest + RTL test for `<CoverProvenance>` — renders correct label for each known `cover_source` value, renders fallback for unknown/missing
- [x] 7.2 Write Vitest test for `<VelocityChart>` — renders chart with mocked data, shows skeleton during loading, shows error on failure
- [x] 7.3 Write Vitest test for `<TypeDistributionChart>` — renders segments for mocked distribution data, handles empty collection
- [x] 7.4 Write Vitest test for `<CollectionInsights>` — renders both sub-charts, errors in one chart do not break the other

## 8. Lint, Format & QA

- [x] 8.1 Run `make format-python` and `make format-js`
- [x] 8.2 Run `make lint` — ensure zero warnings/errors
- [x] 8.3 Run `make test` — ensure all existing + new tests pass
