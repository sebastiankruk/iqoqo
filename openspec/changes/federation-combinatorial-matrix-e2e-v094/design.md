## Context

Federation behavior in iQoQo is governed by six orthogonal state variables across two communicating instances ($A$ and $B$). Previous tests only exercised a single linear happy path (`trusted` bilateral peers + pre-consented users + manual accept + public/shared item loan). During live verification between `preview.iqoqo.cc` and `peer.iqoqo.cc`, five critical production bugs were discovered at state intersections that single-path tests missed:
1. PostgreSQL `check_user_visibility` and `check_user_default_item_visibility` constraints omitted `'friends_only'`, causing `PUT /api/profile` to fail with HTTP 500 `CheckViolation`.
2. Users initiating an outbound federated friend request while `federated_profile=False` caused the remote peer's inbox to fail HTTP Signature verification with 404 when dereferencing the sender's Actor IRI.
3. `list_friends` and `respond_friend_request` checked whether any historical outbound `Follow` activity existed without comparing timestamps against newer inbound `Follow` activities, misclassifying crossover follows as `outgoing` and blocking acceptance with HTTP 400 (`Cannot respond to an outgoing request you initiated`).
4. `respond_friend_request` populated `dummy_follow["object"] = f"local:{user.id}"` instead of `canonical_actor_iri(user.id, base_url)`, triggering false-positive spoofing rejection in `handle_accept`.
5. `get_actor_public_key(user)` returned a stale `user.federation_public_key` DB column when the on-disk private key (`data/federation_keys/user_<id>.pem`) differed, causing HTTP 401 `RSA signature verification failed` on remote inboxes.

See `proposal.md` for full motivation and scope.

## Goals / Non-Goals

**Goals:**
- Formalize the **6-dimensional federation state space** and verify every critical orthogonal intersection through fast, deterministic backend matrix tests (`tests/test_federation_combinatorial_matrix.py`) and zero-mock dual-origin Playwright E2E workflows (`frontend/__tests__/e2e/federation_matrix_workflows.spec.ts`).
- Enforce UX density and navigation standards from `/iqoqo-ux-auditor` across federated notification and friend management surfaces (maximum 4 interactive actions per notification row, keyboard/role-accessible `Accept`/`Reject` buttons, deep-link routing to `/profile?tab=incoming#friends`).
- Maintain strict adherence to `/test-craftsman` rules: zero `page.route()` mocks in multi-instance Playwright E2E tests, realistic RSA-2048 HTTP Signatures, and side-effect assertions on DB rows and outbound activities.

**Non-Goals:**
- Running all 80+ parameter combinations as separate full-browser Playwright loops (which would exceed CI timeouts). Instead, apply the Testing Trophy: run the exhaustive $16 + 24 + 40 + 12 = 92$ combinatorial permutations in the two-instance pytest harness (`tests/test_federation_combinatorial_matrix.py` in `< 15s`), and run the 4 multi-transition stateful journeys in the live dual-origin Playwright suite (`federation_matrix_workflows.spec.ts`).

## Decisions

### Decision 1: Two-Tier Combinatorial Architecture (Pytest Orthogonal Matrices + Playwright Stateful Multi-Origin Workflows)
- **Choice**: Split matrix verification into:
  1. **Backend Two-Instance Combinatorial Matrix (`tests/test_federation_combinatorial_matrix.py`)**: Uses `@pytest.mark.parametrize` and `itertools.product` across four orthogonal matrices:
     - **Matrix 1 ($4 \times 4 = 16$ cases)**: $T_{A \to B} \times T_{B \to A} \in \{\text{unregistered}, \text{untrusted}, \text{trusted}, \text{blocked}\}^2$.
     - **Matrix 2 ($4 \times 2 \times 3 = 24$ cases)**: Recipient consent $C_B \in \{(\text{False},\text{False}), (\text{False},\text{True}), (\text{True},\text{False}), (\text{True},\text{True})\} \times \text{auto\_accept\_follows} \in \{\text{False}, \text{True}\} \times T_{B \to A} \in \{\text{untrusted}, \text{trusted}, \text{blocked}\}$.
     - **Matrix 3 ($5 \times 4 \times 2 = 40$ cases)**: Social state $S_{A,B} \in \{\text{none}, \text{pending\_outgoing}, \text{pending\_incoming}, \text{accepted}, \text{rejected\_or\_unfollowed}\} \times V_{\text{item}} \in \{\text{private}, \text{friends\_only}, \text{shared}, \text{public}\} \times C_{\text{col}} \in \{\text{False}, \text{True}\}$.
     - **Matrix 4 ($12$ lifecycle & cryptographic edge cases)**: Sender auto-consent provisioning, crossover timestamp resolution, outgoing self-accept guard, canonical IRI vs `local:<id>` in `handle_accept`, disk-to-DB RSA key sync, `Undo(Follow)` revocation, and DB check constraint validation.
  2. **Live Dual-Origin Playwright E2E Suite (`frontend/__tests__/e2e/federation_matrix_workflows.spec.ts`)**: Uses two isolated `BrowserContext` instances (`INSTANCE_A_URL` and `INSTANCE_B_URL`) to verify UI state transitions across 4 comprehensive workflows:
     - Workflow 1: Asymmetric & Blocked Peering Gate (`/admin/federation` trust transitions).
     - Workflow 2: Consent & Privacy Shield Toggles (`/profile` consent & auto-provisioning).
     - Workflow 3: Manual Notification Center Inline Actions (`Accept`/`Reject` buttons, $\le 4$ action density, deep-link routing) vs Zero-Click Auto-Accept.
     - Workflow 4: `friends_only` Visibility Barrier & Unfollow Revocation Lifecycle (`none` $\to$ `pending` $\to$ `accepted` $\to$ `Undo(Follow)`).
- **Rationale**: Combinatorial multiplication of 6 dimensions produces $> 1,000$ raw tuples. Factoring into 4 orthogonal sub-matrices covers 100% of pairwise and 3-way interactions in 92 fast pytest cases while keeping E2E browser execution focused on cross-origin UI/UX state transitions.
- **Alternatives Considered**: Running all 92 matrix cases through Playwright browser contexts. Rejected because 92 browser context setups and Celery round-trips would take $> 25$ minutes in CI.

### Decision 2: Disk-Authoritative RSA Key Resolution & Sender Auto-Consent
- **Choice**:
  - In `get_actor_public_key(user)`, always inspect `data/federation_keys/user_<id>.pem` first via `load_private_key(user.id)`. If present, derive the public PEM and update `user.federation_public_key` if out of sync.
  - In `FriendService.send_friend_request`, when dispatching an outbound federated follow, automatically create/update `FederationConsent(federated_profile=True)` and call `ensure_user_keys(requester)` before signing the outbound request.
- **Rationale**: `sign_request` signs outbound HTTP requests using the private key on disk. If the database column `user.federation_public_key` ever drifts (e.g., container rebuild, volume restore, or re-seed) or if `federated_profile` is `False`, the remote peer's inbox either gets 404 on `/ap/users/<username>` or 401 on RSA signature verification.

### Decision 3: Timestamp-Ordered Direction Resolution & Canonical IRI in `Accept`
- **Choice**:
  - Compare `max(created_at)` of `direction="outbound"` vs `direction="inbound"` `Follow` activities in `FederationActivity` for `(user_id, remote_actor_uri)`. A friendship is `outgoing` if and only if an outbound `Follow` exists and is at least as recent as any inbound `Follow`.
  - Construct `dummy_follow["object"] = canonical_actor_iri(user.id, get_federation_base_url())` in `respond_friend_request`, while allowing `handle_accept` to accept either `canonical_actor_iri` or `f"local:{user.id}"` for backward compatibility.
- **Rationale**: Eliminates deadlocked crossover follows where neither peer could accept, and prevents `handle_accept` spoofing checks from rejecting legitimate `Accept` activities.

## Risks / Trade-offs

- **[Risk] Dual-origin Playwright timing sensitivity on async Celery inbox/outbox delivery** $\to$ **Mitigation**: Ensure both `web` and `peer-web` workers subscribe to `-Q celery,federation` in `docker-compose.federation-preview.yml` and `docker-compose.federation-e2e.yml`, and use Playwright `expect.poll()` with bounded timeouts rather than fixed `waitForTimeout` sleeps.
- **[Risk] State leakage between sequential E2E matrix workflows** $\to$ **Mitigation**: Each Playwright workflow resets peer trust state, consent toggles, and any pre-existing friendship state via authenticated API/UI helpers in `beforeEach`/`afterEach` hooks so every workflow starts from a deterministic state.
