## Context

See `proposal.md` and `.context/notes/review/0.9.2/principal-review-pr-366.md` for full code review context across PR #366 (`release/0.9.2 -> main`).

## Goals / Non-Goals

**Goals:**
- Eliminate all 6 critical runtime crash vectors and privacy/authorization leaks identified in the `v0.9.2` release review.
- Ensure 100% of notification deep-links (`/item/<id>`, `/feedback?tab=escalations`, `/profile?tab=...#friends`) resolve to active UI views.
- Guarantee thread-safe SQLAlchemy session handling in `probe_registered_instances` and eliminate the N+1 query storm in `_get_sparql_items`.
- Finalize `docs/CHANGELOG.md` and archive `friends-only-visibility-and-social-library-v092` (`C83c`).

**Non-Goals:**
- Scope-aware sidebar facet counts (`useFacetStats`), remaining hardcoded i18n string extraction, and `export_service.py` social triples (deferred to `C83e: v092-review-deferrals-v093`).

## Decisions

1. **Disambiguating Local vs. Federated Friend Actions (`friend_service.py`, `profile.py`, `friends-card.tsx`)**:
   - `list_friends` returns `"is_federated": True` for `FederationFollower` rows and `"is_federated": False` for `UserFriendship` rows.
   - `DELETE /api/v1/profile/friends/<int:friendship_id>` and `remove_friend()` will accept an optional `is_federated: bool = False` query parameter (and `FriendsCard.handleRemove` will pass `?is_federated=true` when removing a federated friend) so `remove_friend` deletes the `FederationFollower` row owned by `local_user_id == u_uuid` without touching `UserFriendship`. Similarly, `respond_friend_request` will support `is_federated` (or `FederationFollower` fallback when `addressee` is local).
2. **Stateless Worker Probing in `federation_discovery.py`**:
   - Separate `_probe_domain_http(domain: str, trust_level: str) -> dict[str, Any]` from ORM mutation. `probe_instance_health(instance)` calls `_probe_domain_http` and commits on the current thread; `probe_registered_instances` runs `_probe_domain_http` inside `ThreadPoolExecutor` workers and applies ORM updates + `db.session.commit()` on the main thread after futures complete.
3. **SQL Predicate Pushdown & Pre-Authorized Set in SPARQL (`sparql.py`, `sparql_service.py`, `item_access.py`)**:
   - In `_get_sparql_items(user)`, compute `friend_ids = get_friend_user_ids(user.id)` (UUIDs) and filter `Item` in SQL: own items (`Item.owner_id == user.id`), friend items (`and_(Item.owner_id.in_(friend_ids), or_(Item.is_hidden.is_(False), Item.visibility.in_(["friends_only", "shared"])))`), or public items (`and_(Item.is_hidden.is_(False), Item.visibility == "public")`) whose owners do not have `FederationConsent.federated_collection == False`.
   - Pass `friend_owner_ids` into `build_graph` so `friends_only` items belonging to accepted friends are retained without per-item DB queries.
4. **`Item.__init__` Visibility/Hidden Invariant (`app/db/core.py`)**:
   - Implement `__init__` on `Item`: if `visibility` is explicitly provided without `is_hidden`, set `is_hidden = (visibility != "public")`; if `is_hidden` is explicitly provided without `visibility`, set `visibility = ("private" if is_hidden else "public")`.

## Risks / Trade-offs

- **[Risk] Existing unit tests instantiating `Item(is_hidden=True)` without `visibility`** -> Mitigation: Synchronizing `visibility = "private"` in `Item.__init__` when `is_hidden=True` is passed preserves backwards compatibility while closing the friend-visibility leak.
