## 1. Federated Friend Service & Dual-Table Disambiguation

- [x] 1.1 In `app/core/friend_service.py`, fix `FederationActor` attribute lookups in `get_friends_list` and `get_pending_friend_requests` to use `.username`, `.actor_uri`, and `.display_name` instead of `.preferred_username`, `.uri`, and `.name`.
- [x] 1.2 In `app/core/friend_service.py` and `app/api/friends.py`, prefix federated friendship IDs with `fed:<id>` (or accept `source="federated"` / `fed:` prefix in `respond_friend_request` and `remove_friend`) so `FederationFollower` rows are updated/deleted in `federation_followers` rather than colliding with `UserFriendship.id` integer primary keys.
- [x] 1.3 In `app/core/friend_service.py` (`send_friend_request`), parse `@user@domain` handles into `(username, domain)`, filter `FederationActor.domain == domain`, resolve remote actors via `WebFingerService` + `ActivityPubClient.fetch_actor` when not yet cached, and create outbound `FederationFollower` rows with `status=FollowStatus.PENDING` while dispatching an outbound ActivityPub `Follow` activity via `FederationDispatcher`.
- [x] 1.4 Update `frontend/lib/api.ts` and `frontend/components/profile/friends-card.tsx` to support string/prefixed friendship IDs (`string | number`) when accepting, rejecting, or removing local and federated friends.

## 2. Lending API, Shadow Users & Federated Loan Handlers

- [x] 2.1 In `app/api/lending.py` (`request_loan`) and `app/core/federation_handlers.py` (`handle_offer`), replace `item.user_id` with `item.owner_id` and change notification `target_iri` from `/items/{item.id}` to `/item/{item.id}`.
- [x] 2.2 In `app/api/lending.py` (`request_loan`) and `app/core/federation_handlers.py` (`handle_offer`), verify borrower access rights before creating a `LoanRequest` (`public`/`shared` item visibility, or `friends_only` with confirmed mutual `UserFriendship` / accepted `FederationFollower`), returning `403` / rejecting unauthorized requests.
- [x] 2.3 In `app/core/federation_handlers.py` (`handle_offer`), set a non-loginable sentinel `password_hash` (e.g., `"!federated-shadow-account"`) when creating `@federated.local` shadow `User` rows so `check_user_auth_method` is satisfied.
- [x] 2.4 In `app/api/lending.py` (`resolve_loan_request`), guard federated ActivityPub `Accept`/`Reject` dispatch by verifying `loan_req.requester.email.endswith("@federated.local")` in addition to checking the `[Federated request from ...]` notes prefix.
- [x] 2.5 In `app/core/federation_handlers.py` (`handle_accept` and `handle_reject`), detect when an incoming `Accept` or `Reject` activity targets a loan `Offer` and emit an in-app `Notification` (`loan_approved` / `loan_rejected` with `target_iri="/item/{item_id}"`) for the local requester.

## 3. SPARQL Federated Visibility, N+1 Elimination & Graph Serialization

- [x] 3.1 In `app/api/sparql.py` (`_get_sparql_items`), include `get_friend_user_ids(user.id)` in `allowed_owner_ids`, remove integer `FederationFollower.remote_actor_id` values from the `Item.owner_id` (`UUID`) comparison, restrict friends' items to `Item.is_hidden.is_(False)` and `Item.visibility.in_(["public", "friends_only", "shared"])`, and replace the Python-level `is_item_publicly_visible` loop with SQL-level joins/subqueries on `User` and `Collection`.
- [x] 3.2 In `app/core/sparql_service.py` (`build_graph`), pass `viewer_user_id` (and precomputed friend owner IDs) into `_add_item_triples` so that `friends_only` items belonging to accepted friends are serialized into the RDFLib graph rather than skipped by `is_item_publicly_visible(item)`.

## 4. Thread-Safe Federation Probing

- [x] 4.1 In `app/core/federation_discovery.py` (`probe_registered_instances`), extract plain data tuples/dataclasses `(id, domain, actor_uri)` from `FederationInstance` ORM objects before submitting tasks to `ThreadPoolExecutor`, perform only pure HTTP requests inside `_probe_single_instance`, and apply status/timestamp updates + `db.session.commit()` on the main thread after `as_completed()`.

## 5. Item Visibility Synchronization & Scoped Search

- [x] 5.1 In `app/db/core.py` (`Item`), add a SQLAlchemy `@validates("is_hidden", "visibility")` hook or before-flush listener so constructing or updating `Item(is_hidden=True)` without an explicit restricted visibility automatically sets `visibility = "private"`, and setting `visibility = "private"` sets `is_hidden = True`.
- [x] 5.2 In `app/api/items.py` (`get_items`) and `app/core/data_manager.py` (`search_items`), pass `scope` (`"own"`, `"friends"`, `"all"`) and `friend_ids` into `data_manager.search_items` so search queries (`?q=...`) filter across friends' visible items (`public`, `friends_only`, `shared`, `is_hidden=False`).

## 6. Public Endpoints Hardening, Notification Deep-Links & Release Docs

- [x] 6.1 In `app/api/public_profile.py` (`check_inventory`), require `@jwt_required(optional=True)` and only permit `include_friends=True` when the authenticated caller is `user.id` or a confirmed friend of `user.id`, capping remote friend federation checks to a bounded fan-out.
- [x] 6.2 In `app/api/public_items.py` (`get_public_items`), move the `if rdf_format:` branch after `user.visibility` and `is_friend` authorization checks; in `app/api/public_rdf.py` (`serialize_user_collection_to_rdf`), filter items using `is_item_visible_to_viewer(item, viewer_id)` so hidden/private items are never serialized; in `app/api/public_profile.py` (`get_public_user_followers`), populate local mutual friends alongside federated followers.
- [x] 6.3 In `frontend/app/feedback/page.tsx`, read `useSearchParams().get("tab")` (`"my-escalations"` / `"escalations"` / `"my-reports"`) to initialize the active tab so escalation notification links open the escalations view directly.
- [x] 6.4 In `docs/CHANGELOG.md`, replace `## [0.9.2] - TBD` with the release date and add the `C83c` (`friends-only-visibility-and-social-library-v092`) feature summary.

## 7. Verification & Regression Test Suite

- [x] 7.1 Add backend unit and integration tests covering `friend_service.py` (`FederationActor` attributes, `fed:` ID disambiguation, `@user@domain` parsing and `PENDING` status), `lending.py` & `federation_handlers.py` (`item.owner_id`, `/item/<id>`, visibility checks, shadow user creation, federated `Accept`/`Reject` notifications), `sparql.py` & `sparql_service.py` (authenticated friend `friends_only` SPARQL queries), `federation_discovery.py` (multi-instance thread-safe probing), `Item(is_hidden=True)` visibility sync, `get_items(scope="friends", q=...)`, and `public_profile.py` / `public_items.py` / `public_rdf.py` guards.
- [x] 7.2 Add frontend unit tests in `frontend/__tests__/` covering `FeedbackPage` `?tab=my-escalations` deep-linking and string/prefixed friendship IDs in `FriendsCard`.
- [x] 7.3 Run `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and full backend/frontend test suites to verify green status.
