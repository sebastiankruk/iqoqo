## Why

The `/manifestation/[id]` page currently surfaces only the primary cover and basic ownership counts, hiding community-contributed edition covers and anonymized reading/popularity insights that help collectors evaluate editions and discover active titles.

Target release: scheduled for **v1.2.0** (`C158`).

## What Changes

- Render a contributed covers gallery on `/manifestation/[id]` (`ManifestationDetailClient`) backed by `GET /api/manifestations/<id>/images`, surfacing `F3_Manifestation_Product_Type` cover provenance without exposing private uploader identities.
- Add an anonymized, visibility-safe `GROUP BY` analytics projection on `GET /api/manifestations/<id>/stats` (and summary fields in `GET /api/manifestations/<id>`) computing reader counts, completion counts, average reading duration, and monthly popularity-over-time buckets from `Item`, `ReadingTransition`, and `reading_sessions` with zero N+1 queries.
- Render an interactive Read Stats & Popularity Over Time card on `/manifestation/[id]` with graceful zero-data empty states.

## Capabilities

### New Capabilities

- `manifestation-covers-and-popularity-analytics`: Contributed covers gallery and anonymized, visibility-safe `GROUP BY` read stats & popularity-over-time analytics on `Manifestation` (`F3`).

### Modified Capabilities

<!-- None -->

## Impact

- Backend: `app/api/manifestations.py`, `app/core/data_manager.py` (or dedicated stats query helper), `app/api/docs.py`
- Frontend: `frontend/components/manifestation/manifestation-detail-client.tsx`, new `ManifestationCoversGallery` and `ManifestationStatsCard` components, `frontend/lib/api/hooks/catalog.ts`, `frontend/types/frbr.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`
- Tests: Pytest (`tests/test_manifestation_stats.py`), Vitest (`frontend/__tests__/components/manifestation/`), Playwright E2E
