## Context

See `proposal.md` for motivation. Currently `SharedCollection` stores `filters` as JSON (`app/db/social.py`), and `app/api/public_items.py` (`fetch_shared_collection_by_token` and `public_shared_collection`) unconditionally applies `Item.is_hidden.is_(False), Item.visibility == "public"` alongside `SearchService.search_items(..., include_hidden=False)`.

## Goals / Non-Goals

**Goals:**
- Support `"public_only"` (default + friend bonus), `"friends_and_public"`, and `"all"` share scopes without requiring a destructive table migration.
- Guarantee consistent visibility enforcement across JSON, Next.js SSR `/share/[token]`, `/share/[token]/jsonld/[page]`, `/api/public/rdf/share/<token>`, RSS, and PostgreSQL FTS search branches.
- Prevent shared HTTP/CDN caches from caching authenticated friend-bonus or non-public share responses.

**Non-Goals:**
- Changing per-item visibility ownership rules or enabling cross-user collection shares (a share link always scopes exclusively to `collection.user_id`'s items).

## Decisions

1. **Store `visibility_scope` inside `SharedCollection.filters["visibility_scope"]`:** Avoids an extra Alembic DDL migration on `shared_collections` while ensuring `to_dict()`, existing links (`filters.get("visibility_scope", "public_only")`), and `filters` schema stay backward-compatible.
2. **Centralize visibility predicate helper `_resolve_allowed_visibilities(collection, viewer_user_id)` in `app/api/public_items.py`:** Both `fetch_shared_collection_by_token()` (used by RSS/RDF) and `public_shared_collection()` (used by `/share/[token]`) call this single helper so logic never drifts:
   - `"all"` → `("public", "friends_only", "shared", "private")` (bypassing `is_hidden` filter).
   - `"friends_and_public"` → `("public", "friends_only", "shared")`.
   - `"public_only"` → check optional JWT/cookie auth (never failing anonymous calls) via `get_friend_user_ids` / owner equality; if owner or accepted friend, return `("public", "friends_only", "shared")` and mark response uncacheable (`Cache-Control: private, no-store`); otherwise return `("public",)`.
3. **Pass `visibility` / `include_hidden` into `SearchService.search_items()`:** When `filters["query"]` is present on PostgreSQL, `SearchService.search_items()` receives the resolved allowed visibilities and `include_hidden=(scope == "all")` so FTS results match the SQL branch identically.

## Risks / Trade-offs

- **CDN/Browser caching leaking friend-bonus items across users** → Set `Cache-Control: private, no-store` and `Vary: Authorization, Cookie` whenever `visibility_scope != "public_only"` OR when an authenticated viewer triggers friend bonus on a `"public_only"` share.
- **Next.js SSR cookie forwarding on `/share/[token]`** → Forward `cookie` header in `frontend/app/share/[token]/page.tsx` (matching `/u/[username]` pattern from `v0.9.2`) so logged-in friends immediately see `friends_only` items on initial SSR load.
