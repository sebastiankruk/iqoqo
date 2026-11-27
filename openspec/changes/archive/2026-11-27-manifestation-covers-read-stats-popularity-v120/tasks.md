## 1. Backend Anonymized Analytics (`app/api/manifestations.py`, `app/core/`)

- [x] 1.1 Implement dialect-aware `GROUP BY` manifestation stats helper (`total_items`, `reader_count`, `completed_count`, `avg_reading_days`, `avg_session_minutes`, `popularity_over_time` monthly buckets) using `func.count()` (`# pylint: disable=not-callable`) with zero N+1 queries and zero PII/note exposure
- [x] 1.2 Add `GET /api/manifestations/<int:manifestation_id>/stats` endpoint and OpenAPI 3.1 schema in `app/api/docs.py`
- [x] 1.3 Verify `GET /api/manifestations/<int:manifestation_id>/images` omits private uploader identities and returns clean `F3` cover provenance

## 2. Frontend Gallery & Stats UI (`frontend/components/manifestation/`)

- [x] 2.1 Add `useManifestationStats` / `useManifestationImages` hooks in `frontend/lib/api/hooks/catalog.ts` and types in `frontend/types/frbr.ts`
- [x] 2.2 Build `ManifestationCoversGallery` component (thumbnail strip, provenance badge, lightbox preview, primary cover deduplication)
- [x] 2.3 Build `ManifestationStatsCard` component (KPI pills + responsive SVG/Tailwind popularity-over-time chart + graceful zero-data empty state) and integrate both into `ManifestationDetailClient`
- [x] 2.4 Add `en.json` and `pl.json` translations

## 3. Tests & Verification

- [x] 3.1 Add Pytest suite (`tests/test_manifestation_stats.py`) covering `GROUP BY` accuracy, private item/note redaction, SQLite & PostgreSQL month-bucketing, and zero-data 200 response
- [x] 3.2 Add Vitest component tests for `ManifestationCoversGallery` and `ManifestationStatsCard` + Playwright E2E manifestation view check
- [x] 3.3 Run `IQOQO_AI_MODE=1 make lint`, `IQOQO_AI_MODE=1 make test-parallel`, and `IQOQO_AI_MODE=1 make secret-scan`
