# Change Proposal: v094-pre-merge-bug-hardening-v094

## Why
During the final multi-agent code review sweep of release v0.9.4 prior to v1.0.0 branching, 6 Moderate and 4 Low priority bugs and hardening gaps were identified across federation friend scoping, ActivityPub protocol lifecycle (missing Reject/Undo dispatch), WebFinger SQL wildcards and domain resolution, actor IRI boundary verification, E2E placeholder synchronization, key generation idempotency, transaction rollback on key sync, migration downgrade data normalization, and disaster recovery script robustness. Resolving these issues ensures that release v0.9.4 achieves complete protocol correctness and rock-solid cross-instance federation.

## What Changes
1. **[M1] Scoped Inbound Follow Resolution**: In `friend_service.py`, filter inbound `Follow` activities strictly by `FederationActivity.actor_uri.in_(pending_actor_uris)` and ensure `target_uri` or `object` matches the local user's actor IRI or UUID, preventing cross-user inbound follow theft.
2. **[M2] ActivityPub Reject & Undo Dispatch**: In `friend_service.py`, dispatch an outbound `Reject(Follow)` activity when a user rejects an inbound federated follow request (`fed:<id>`), and dispatch an outbound `Undo(Follow)` activity when a user cancels or removes an active federated friend.
3. **[M3] WebFinger SQL Safety & Domain Fallback Resolution**: In `federation.py`, replace wildcard-injectable `ilike(f"{username}@%")` with structured matching, prioritize `public_username`, and append `@peer_domain` in fallback discovery queries to prevent 404 resource domain mismatches.
4. **[M4] Actor IRI Boundary Checks & Auto-Accept Notification Cleanliness**: In `federation_handlers.py`, ensure actor IRI matching uses anchored suffix/pattern verification (`actor_uri.rstrip("/").endswith(f"/u/{target_id}")`) rather than loose substring checks. Hide inline action buttons in `notification-center.tsx` for notifications where `status === "accepted"`.
5. **[M5] E2E Instance Placeholder Synchronization**: Update dual-origin E2E Playwright tests to expect localized/updated placeholders `library.example.org` and `biblioteka.example.org`.
6. **[M6] OpenSpec Changes Workspace Cleanliness**: Confirm all obsolete or duplicated change directories in `openspec/changes/` are pruned.
7. **[L1] Domain Normalization & Keypair Idempotency**: Normalize target domain before checking instance block status; check for existing RSA keypair before generating new keys in `send_friend_request()` and `update_consent()`; preserve `federated_collection` consent when updating federation profile consent.
8. **[L2] Transaction Rollback on Key Synchronization Failure**: Add `db.session.rollback()` in `federation_keys.py` when database synchronization encounters an exception.
9. **[L3] Migration Downgrade Normalization & Script Robustness**: In `v0_9_4_user_friends_only_checks.py`, normalize rows prior to re-imposing narrower check constraints. In `restore.sh`, use null-delimited find loops and `--no-same-owner` tar extraction.
10. **[L4] Documentation & Changelog Release Stamping**: Update `docs/FEDERATION.md` peering behavior description and finalize the release date header in `docs/CHANGELOG.md`.

## Capabilities
- Secure and isolated federated friend request handling without crosstalk between different local users.
- Full two-way ActivityPub state convergence on follow rejection and cancellation.
- Robust WebFinger identity discovery against external ActivityPub instances.
- Zero-drift database migration downgrades and hardened restore tooling.

## Impact
- Backend: `app/core/friend_service.py`, `app/api/federation.py`, `app/core/federation_handlers.py`, `app/api/profile.py`, `app/core/federation_keys.py`, `migrations/versions/v0_9_4_user_friends_only_checks.py`.
- Frontend: `frontend/components/dashboard/notification-center.tsx`, `frontend/__tests__/e2e/federation_pair_live.spec.ts`, `frontend/__tests__/e2e/federation_matrix_workflows.spec.ts`.
- Scripts & Docs: `scripts/restore.sh`, `docs/FEDERATION.md`, `docs/CHANGELOG.md`.
