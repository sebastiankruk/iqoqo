## Why

Shared collection links currently hardcode `Item.visibility == "public"` and `Item.is_hidden == False`, preventing collectors from sharing curated subsets that include `friends_only` or `private` (hidden) items when intentionally sending a capability link to trusted family, friends, or personal AI assistants, and denying logged-in friends access to `friends_only` items inside default share links.

## What Changes

- Add an explicit `visibility_scope` setting inside `SharedCollection.filters["visibility_scope"]` (`"public_only"` [default], `"friends_and_public"`, `"all"`), validated on `POST /api/sharing/` (`app/api/sharing.py`) and returned by `SharedCollection.to_dict()`.
- Implement the **Token Scope + Friend Bonus** access model consistently across `fetch_shared_collection_by_token`, `public_shared_collection` (`app/api/public_items.py`), `/api/public/rdf/share/<token>` (`app/api/public_rdf.py`), `/share/<token>/jsonld/<page>`, and RSS feeds:
  - **`"public_only"` (default):** Exposes `visibility == "public"` items to anonymous visitors; if the caller is authenticated on the instance and is an accepted friend of the owner (or is the owner), also exposes `visibility == "friends_only"` items (with `Cache-Control: private, no-store`).
  - **`"friends_and_public"`:** The 256-bit `share_token` grants read access to both `public` and `friends_only` items to anyone holding the link, while keeping `private` items excluded.
  - **`"all"`:** The 256-bit `share_token` grants read access to all matching items (`public`, `friends_only`, and `private`) owned by the link creator.
- Pass matching `include_hidden` / visibility criteria into PostgreSQL `SearchService.search_items()` when a shared collection also carries a saved `query` filter.
- Update `ShareCollectionDialog` (`frontend/components/collection/share-collection-dialog.tsx`) with a localized 3-option scope selector (`Public only (Recommended)`, `Friends & Public`, `All items including Private/Hidden`) and a clear privacy warning for non-public scopes.

## Capabilities

### New Capabilities
- `shared-collection-visibility-scope`: Configurable `visibility_scope` (`public_only`, `friends_and_public`, `all`) with logged-in friend bonus across share link creation, JSON/SSR views, RDF/JSON-LD exports, and RSS feeds.

### Modified Capabilities
- `shared-collection-ai-feed`: Update share endpoint visibility filtering from unconditionally excluding `is_hidden == True` / non-public items to honoring each `SharedCollection`'s configured `visibility_scope` (`public_only` default with friend bonus, `friends_and_public`, or `all`).

## Impact

- **Backend (`app/`)**: `app/api/sharing.py`, `app/api/public_items.py`, `app/api/public_rdf.py`, `app/core/search_service.py`, `app/api/schemas.py`, `app/api/docs.py`.
- **Frontend (`frontend/`)**: `frontend/components/collection/share-collection-dialog.tsx`, `frontend/app/share/[token]/page.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests (`tests/`, `frontend/__tests__/`)**: `tests/test_shared_collection_ai_feed.py`, `tests/test_public_feeds.py`, `tests/test_openapi_spec.py`, Vitest `ShareCollectionDialog` tests.
