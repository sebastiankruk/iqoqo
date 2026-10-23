## Why

The `v0.9.2` pre-release code review (PR #366, documented in `.context/notes/review/0.9.2/principal-review-pr-366.md`) identified several non-blocking moderate and low-severity enhancements that do not block the `v0.9.2` release once `C83d` (`v092-pre-release-critical-fixes`) is applied, and should be delivered at the start of the `v0.9.3` stream:

1. **Friends-Scoped Facet Counts in `/collection` (`frontend/app/collection/page.tsx`, `app/api/items.py`)**: When toggling to the `Friends` scope in `/collection`, the item grid filters to friends' holdings, but `useFacetStats` (`/api/stats/facets`) is not passed `scope="friends"`, leaving sidebar facet counts on personal/global totals.
2. **Localization (`next-intl`) Completeness for Social & Notification Surfaces**: `FriendsCard` (`frontend/components/profile/friends-card.tsx`), `NotificationCenter` (`frontend/components/dashboard/notification-center.tsx`), and the consolidated Requests tabs in `FeedbackPage` (`frontend/app/feedback/page.tsx`) contain fallback/hardcoded English labels that should be extracted into `frontend/messages/en.json` and `pl.json`.
3. **Graceful Disabled-Federation State on `/federation/directory` (`app/api/federation.py`, `frontend/app/federation/directory/page.tsx`)**: `GET /api/federation/directory` is decorated with `@federation_required`, causing `/federation/directory` (linked in the global Footer) to display a destructive error card when `FEDERATION_ENABLED=False` instead of rendering the local library summary with an informational disabled badge.
4. **Social & Custody RDF Triples in User Data Export (`app/core/export_service.py`) & Notification Rate Limiting (`app/api/notifications.py`)**: Extend user collection exports in `export_service.py` to include authorized social/custody triples (`C80` carry-over), remove dead JSONB `cast(..., String)` fallback code in `federation_sync.py`, and add `@limiter.limit("60 per minute")` decorators to `notifications_bp`.

## What Changes

- **Scope-Aware Facet Statistics (`app/api/items.py`, `app/core/data_manager.py`, `frontend/lib/api/hooks/catalog.ts`, `frontend/app/collection/page.tsx`)**:
  - Pass `scope` (`personal` | `friends` | `global`) to `useFacetStats` and `/api/stats/facets` so sidebar facet counts match the active `Friends` scope in `/collection`.
- **Frontend i18n Extraction (`frontend/messages/en.json`, `frontend/messages/pl.json`, `frontend/components/profile/friends-card.tsx`, `frontend/components/dashboard/notification-center.tsx`, `frontend/app/feedback/page.tsx`)**:
  - Move all remaining hardcoded English strings in `FriendsCard`, `NotificationCenter`, and `FeedbackPage` tabs into `en.json` and `pl.json` under `ProfilePage`, `Notifications`, and `FeedbackPage` namespaces.
- **Graceful Federation Directory Fallback (`app/api/federation.py`, `frontend/app/federation/directory/page.tsx`)**:
  - Allow `GET /api/federation/directory` to return `local_instance` metadata with `federation_enabled: False` and `peers: []` when federation is disabled, and display a subtle status badge in `FederationDirectoryPage`.
- **Export Service Social Triples, Rate Limits & Cleanup (`app/core/export_service.py`, `app/api/notifications.py`, `app/core/federation_sync.py`)**:
  - Include user's own `ItemCustodyEvent` and `UserFriendship` (`foaf:knows`) triples in `ExportService` RDF exports.
  - Add `@limiter.limit("60 per minute")` to `notifications_bp` endpoints and remove redundant `cast(Manifestation.meta[...], String)` fallback branches in `resolve_local_manifestation`.

## Capabilities

### Modified Capabilities
- `faceted-navigation`: Support `scope=friends` in `/api/stats/facets` and `useFacetStats` on the `/collection` page.
- `in-app-notifications`: Localize `NotificationCenter` and `FeedbackPage` tab strings in `en.json` and `pl.json`, and add rate limiting to `/api/v1/notifications*`.
- `federation-index-and-docs`: Return graceful `federation_enabled: false` local summary on `GET /api/federation/directory` when federation is disabled.
- `social-activitystreams-ontology`: Include owner custody and friendship triples in `ExportService` RDF exports.

## Impact

- `frontend/app/collection/page.tsx`, `frontend/lib/api/hooks/catalog.ts`, `app/api/items.py`, `app/core/data_manager.py`
- `frontend/components/profile/friends-card.tsx`, `frontend/components/dashboard/notification-center.tsx`, `frontend/app/feedback/page.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`
- `app/api/federation.py`, `frontend/app/federation/directory/page.tsx`
- `app/core/export_service.py`, `app/api/notifications.py`, `app/core/federation_sync.py`
