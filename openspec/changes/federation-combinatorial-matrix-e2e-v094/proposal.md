## Why

Existing multi-instance federation tests in `federation_pair_live.spec.ts` and `test_federation_e2e.py` only exercise a single linear happy path (`trusted` bilateral peers $\to$ opted-in users $\to$ manual follow accept $\to$ loan). In reality, federation behavior is governed by **six independent orthogonal dimensions**—Instance A trust ($T_{A \to B}$), Instance B trust ($T_{B \to A}$), User A & B consent vectors ($\text{federated\_profile} \times \text{federated\_collection}$), recipient follow auto-approval ($\text{auto\_accept\_follows}$), directional social relationship state ($S_{A,B}$), and 4-tier resource/profile visibility ($\text{private} \mid \text{friends\_only} \mid \text{shared} \mid \text{public}$)—whose Cartesian product creates dozens of interacting states where production bugs hide.

## What Changes

- Author an exhaustive parametrized two-instance backend matrix test suite (`tests/test_federation_combinatorial_matrix.py`) systematically verifying the orthogonal intersections of all federation dimensions:
  - **Matrix 1 — $4 \times 4 = 16$ Bilateral & Asymmetric Peering Topologies ($T_{A \to B} \times T_{B \to A}$)**: Test every pairing of `unregistered`, `untrusted`, `trusted`, and `blocked` across WebFinger discovery, outbound follow initiation, inbox HTTP signature & block-list enforcement, `Accept`/`Reject` round-trip delivery, and FRBR metadata sync (`merged` vs `queued_for_review` vs `ignored`).
  - **Matrix 2 — $4 \times 2 \times 3 = 24$ Consent $\times$ Auto-Accept $\times$ Peer Trust Intersections ($C_B \times A_B \times T_{B \to A}$)**: Test all 4 recipient consent states $(\text{federated\_profile} \in \{\text{False}, \text{True}\} \times \text{federated\_collection} \in \{\text{False}, \text{True}\}) \times \text{auto\_accept\_follows} \in \{\text{False}, \text{True}\} \times T_{B \to A} \in \{\text{untrusted}, \text{trusted}, \text{blocked}\}$, plus requester auto-provisioning of `federated_profile=True` and RSA-2048 keys when initiating an outbound follow from an unconsented state $C_A = (\text{False}, \text{False})$.
  - **Matrix 3 — $5 \times 4 \times 2 = 40$ Social State $\times$ Item Visibility $\times$ Collection Consent Intersections ($S_{A,B} \times V_{\text{item}} \times C_{\text{col}}$)**: Test `none`, `pending_outgoing`, `pending_incoming`, `accepted`, and `rejected_or_unfollowed` across `private`, `friends_only`, `shared`, and `public` items with `federated_collection` enabled/disabled across catalog queries, `is_friend_of()`, public RDF (`/api/public/rdf/user/<username>`), SPARQL snapshots (`_get_sparql_items`), and federated `as:Offer` loan requests.
  - **Matrix 4 — 12 Stateful Directional, Cryptographic & Constraint Lifecycle Transitions**: Verify outgoing self-accept/self-reject rejection (`400`), timestamp-aware crossover bidirectional follow resolution (newer inbound `Follow` superseding stale outbound `Follow`), canonical actor IRI matching in `handle_accept`, disk-to-DB public key synchronization in `get_actor_public_key`, `Undo(Follow)` revocation, and PostgreSQL check constraints (`check_user_visibility`, `check_user_default_item_visibility`) across all 4 visibility tiers.
- Author a comprehensive live dual-origin Playwright E2E matrix suite (`frontend/__tests__/e2e/federation_matrix_workflows.spec.ts`) executing zero-mock browser workflows across two live instances (`contextA` & `contextB`):
  - **E2E Matrix Workflow 1 (Asymmetric & Blocked Peering Gate)**: Admin toggles peer trust between `blocked`, `untrusted`, and `trusted` in `/admin/federation`, verifying UI rejection on `blocked`, forced manual review on `untrusted` even when `auto_accept_follows=True`, and full restoration on `trusted`.
  - **E2E Matrix Workflow 2 (Consent & Privacy Shield Toggles)**: Toggle `federated_profile` and `federated_collection` in `/profile` and `POST /api/profile/consent`, verifying 404 actor invisibility when opted out, automatic sender opt-in on outbound friend request, and collection shielding when `federated_collection=False`.
  - **E2E Matrix Workflow 3 (Manual Notification Center Inline Actions vs Zero-Click Auto-Accept)**: Verify manual `Accept` and `Reject` inline actions inside the Notification Center popover (enforcing UX button density $\le 4$ and `/profile?tab=incoming#friends` deep-link routing) alongside zero-click instant friendship when `auto_accept_follows=True` on a `trusted` peer.
  - **E2E Matrix Workflow 4 (`friends_only` Visibility Barrier & Unfollow Revocation Lifecycle)**: Persist `friends_only` user and default item visibility on `/profile`; verify `friends_only` items are hidden before friendship and while `pending`, become visible and lendable once `accepted`, and vanish immediately when friendship is removed (`Undo(Follow)`).
- Register OpenSpec change **C92 (`federation-combinatorial-matrix-e2e-v094`)** in `.context/notes/plan/0.9.x-release-plan.md`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `federation-multi-instance-e2e`: Expand multi-instance verification to require orthogonal combinatorial matrix testing across peering trust states, user consent combinations, auto-accept policies, directional follow states, and visibility tiers in both backend simulation and live dual-origin Playwright E2E suites.
- `federated-friends-and-loans`: Require automatic sender profile consent and RSA key provisioning on outbound federated friend requests, timestamp-ordered directional resolution for crossover follows, canonical actor IRI objects in `Accept` activities, and disk-authoritative public key synchronization.
- `friends-only-visibility-and-social-library`: Require four-tier visibility check constraint parity (`private`, `friends_only`, `shared`, `public`) on `User` and strict dynamic visibility gating across friend lifecycle transitions (`none` $\to$ `pending` $\to$ `accepted` $\to$ `removed`).

## Impact

- **Backend Tests**: New `tests/test_federation_combinatorial_matrix.py` parametrized matrix suite; expanded `tests/test_friend_service.py` and `tests/test_migration.py`.
- **Frontend E2E Tests**: New `frontend/__tests__/e2e/federation_matrix_workflows.spec.ts` and updated `frontend/__tests__/e2e/federation_pair_live.spec.ts`.
- **Backend Core & Migrations**: `app/core/friend_service.py`, `app/core/federation_handlers.py`, `app/core/federation_keys.py`, `app/api/profile.py`, and `migrations/versions/v0_9_4_user_friends_only_checks.py`.
- **Makefile & CI**: Integrated into `make test-e2e-federation` and GitHub Actions `test-federation-pair-e2e` job.
