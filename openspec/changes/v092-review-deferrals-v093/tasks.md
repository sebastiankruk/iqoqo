## 1. Friend-Scoped Facet Counts (`faceted-navigation`)

- [x] 1.1 Update `GET /api/stats/facets` in `app/api/stats.py` to accept `scope` (`"own"`, `"friends"`, `"all"`) and filter `GROUP BY` facet counts across confirmed friends' visible items (`public`, `friends_only`, `shared`, `is_hidden=False`) when `scope="friends"`.
- [x] 1.2 Update `useFacetStats` in `frontend/lib/hooks/use-library.ts` and `frontend/app/collection/page.tsx` to pass `scope` to `/api/stats/facets` and include `scope` in the React Query cache key.

## 2. Social & Notification Localization and Rate Limiting (`in-app-notifications`)

- [x] 2.1 Extract all hardcoded English strings in `frontend/components/profile/friends-card.tsx`, `frontend/components/notification-center.tsx`, and `frontend/app/feedback/page.tsx` into `frontend/messages/en.json` and `frontend/messages/pl.json`.
- [x] 2.2 Add `@limiter.limit` decorators to `app/api/notifications.py` (`GET /api/v1/notifications`, `PATCH /api/v1/notifications/<id>/read`, `POST /api/v1/notifications/read-all`).

## 3. Graceful Federation Directory Degradation (`federation-index-and-docs`)

- [x] 3.1 Update `GET /api/v1/public/federation/instance-info` and `frontend/app/federation/directory/page.tsx` so `/federation/directory` renders the local instance summary card and an informational "Federation disabled on this instance" banner when `FEDERATION_ENABLED=False`.

## 4. RDF Export Social/Custody Triples & Sync Cleanup (`social-activitystreams-ontology`)

- [x] 4.1 Update `ExportService.export_rdf()` in `app/core/export_service.py` to emit `foaf:knows` triples for confirmed mutual friends and `iqoqo:custodyHolder` triples for active public loans when permitted by user privacy settings.
- [x] 4.2 Remove the dead `cast(Manifestation.meta["isbns"], String).contains(isbn)` fallback in `app/core/federation_sync.py`.

## 5. Verification & Tests

- [x] 5.1 Add backend pytest and frontend Vitest coverage for `scope="friends"` facet counts, `en`/`pl` translation parity on `FriendsCard`/`NotificationCenter`/`FeedbackPage`, `/federation/directory` disabled-mode rendering, and `ExportService.export_rdf()` social triples.
