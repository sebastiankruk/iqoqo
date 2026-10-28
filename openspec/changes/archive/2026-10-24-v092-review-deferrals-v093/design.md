## Context

During the `v0.9.2` Principal Code Review of PR #366 (`release/0.9.2`), non-blocking polish, i18n, and performance/consistency improvements were separated from critical release blockers (`C83d`) and scheduled for `v0.9.3` (`C83e`).

## Goals / Non-Goals

**Goals:**
- Pass `scope` (`"own"` / `"friends"` / `"all"`) through `useFacetStats` to `GET /api/stats/facets` so sidebar facet counts accurately reflect the "Friends' Items" view.
- Complete bilingual (`en` / `pl`) localization for `FriendsCard`, `NotificationCenter`, and `/feedback` (`Requests`) tabs.
- Ensure `/federation/directory` renders the local instance overview card even when `FEDERATION_ENABLED=False`.
- Extend `ExportService.export_rdf()` to include authorized `foaf:knows` and `iqoqo:custodyHolder` triples, add `@limiter.limit` to `notifications_bp`, and remove the dead JSONB string-cast fallback in `federation_sync.py`.

**Non-Goals:**
- Modifying core database schemas or introducing new Alembic migrations.

## Decisions

### 1. Friend-Scoped Facet Aggregation in `app/api/stats.py`
- **Decision:** Accept `scope = request.args.get("scope", "own")` on `/api/stats/facets`. When `scope == "friends"` and a user is authenticated, resolve `friend_ids = get_friend_user_ids(user.id)` and filter `Item.owner_id.in_(friend_ids)`, `Item.is_hidden.is_(False)`, and `Item.visibility.in_(["public", "friends_only", "shared"])` across all `GROUP BY` facet queries. In `frontend/app/collection/page.tsx` and `frontend/lib/hooks/use-library.ts`, include `scope` in the `useFacetStats` query key and request parameters.

### 2. Complete i18n Extraction for Social & Notification UI
- **Decision:** Move all hardcoded strings in `frontend/components/profile/friends-card.tsx`, `frontend/components/notification-center.tsx`, and `frontend/app/feedback/page.tsx` into `frontend/messages/en.json` and `frontend/messages/pl.json` under `Profile.friends`, `Notifications`, and `Feedback` namespaces, and add a translation parity check in Vitest.

### 3. Graceful Federation Directory Degradation
- **Decision:** Allow `GET /api/v1/public/federation/instance-info` to return local instance metadata with `"federation_enabled": False` even when S2S federation is disabled, and update `frontend/app/federation/directory/page.tsx` to display a friendly informational badge instead of an error state when peer directory discovery is disabled.

### 4. RDF Export Social/Custody Triples & Notification Rate Limiting
- **Decision:** Reuse `serialize_social_graph_to_rdf` / `iqoqo:custodyHolder` helpers inside `ExportService.export_rdf()` when exporting a user's collection, apply `@limiter.limit("60 per minute")` to `notifications_bp` endpoints, and replace the dead `cast(Manifestation.meta["isbns"], String).contains(isbn)` fallback in `app/core/federation_sync.py` with dialect-aware JSON containment or clean column lookup.

## Risks / Trade-offs

- **[Risk] Facet aggregation query complexity for users with many friends** -> **Mitigation:** `get_friend_user_ids` returns a compact set of UUIDs indexed by `ix_items_owner_id`, keeping `GROUP BY` facet queries fast.
