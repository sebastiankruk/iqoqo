## ADDED Requirements

### Requirement: Orthogonal Bilateral Peering Topology Matrix Verification
The multi-instance test suite SHALL verify the full $4 \times 4 = 16$ Cartesian product of instance peering trust states $T_{A \to B} \times T_{B \to A} \in \{\text{unregistered}, \text{untrusted}, \text{trusted}, \text{blocked}\}^2$ across two distinct instances, validating WebFinger discovery, outbound follow initiation, inbox HTTP signature and block-list enforcement, `Accept`/`Reject` round-trip delivery, and FRBR metadata sync disposition (`merged`, `queued_for_review`, or `ignored`).

#### Scenario: Symmetric trusted peering topology (trusted x trusted)
- **WHEN** Instance A has registered Instance B as `trusted` AND Instance B has registered Instance A as `trusted`
- **THEN** outbound `Follow` from User A to User B succeeds, Instance B's inbox accepts the signed activity, `Accept` is delivered back to Instance A transitioning both sides to `accepted`, and incoming federated bibliographic metadata is automatically `merged` into the local FRBR graph

#### Scenario: Symmetric untrusted peering topology (untrusted x untrusted)
- **WHEN** Instance A has registered Instance B as `untrusted` AND Instance B has registered Instance A as `untrusted`
- **THEN** outbound `Follow` from User A to User B is delivered to Instance B's inbox and placed in `pending` state awaiting manual review regardless of User B's `auto_accept_follows` setting, and incoming federated bibliographic metadata is held as `queued_for_review`

#### Scenario: Asymmetric trusted-to-untrusted peering topology (trusted x untrusted)
- **WHEN** Instance A trusts Instance B (`trusted`) while Instance B marks Instance A as `untrusted`
- **THEN** User A's `Follow` to User B is held as `pending` on Instance B (never auto-accepted even if User B enabled `auto_accept_follows=True`), while User B's `Follow` to User A is eligible for auto-acceptance on Instance A if User A enabled `auto_accept_follows=True`

#### Scenario: Asymmetric or bilateral blocked peering topology (* x blocked or blocked x *)
- **WHEN** either Instance A marks Instance B as `blocked` OR Instance B marks Instance A as `blocked`
- **THEN** outbound friend requests initiated on the blocking instance SHALL be rejected locally with HTTP 403 (`Cannot send requests to a blocked federation peer`), and inbound ActivityPub deliveries arriving at the blocking instance's inbox SHALL be rejected or ignored without creating `FederatedFriendship` or `Notification` records

#### Scenario: Unregistered peer auto-discovery topology (unregistered x *)
- **WHEN** Instance B receives a validly signed `Follow` activity from Instance A whose domain is not yet registered in Instance B's `FederationPeer` table
- **THEN** Instance B SHALL treat the sender domain under default untrusted policy (never auto-accepting the follow and never auto-merging FRBR metadata without explicit `trusted` peer status)

### Requirement: Orthogonal Consent, Auto-Accept, and Peer Trust Matrix Verification
The multi-instance test suite SHALL verify the $4 \times 2 \times 3 = 24$ Cartesian product of recipient consent states $C_B = (\text{federated\_profile} \in \{\text{False}, \text{True}\}, \text{federated\_collection} \in \{\text{False}, \text{True}\})$, recipient follow auto-approval $A_B \in \{\text{False}, \text{True}\}$, and inbound peer trust $T_{B \to A} \in \{\text{untrusted}, \text{trusted}, \text{blocked}\}$.

#### Scenario: Recipient with federated_profile disabled (False, *) across all trust and auto-accept states
- **WHEN** User B has `federated_profile=False` (for either `federated_collection=False` or `True`, `auto_accept_follows=False` or `True`, and any peer trust level)
- **THEN** WebFinger (`/.well-known/webfinger`) and Actor lookup (`/ap/users/<username>`) for User B SHALL return HTTP 404, and inbound `Follow` activities targeting User B SHALL be ignored without creating a `FederatedFriendship`

#### Scenario: Recipient with federated_profile enabled and auto_accept_follows enabled on trusted vs untrusted peer
- **WHEN** User B has `federated_profile=True` and `auto_accept_follows=True`
- **THEN** an inbound `Follow` from User A on a `trusted` peer ($T_{B \to A} = \text{trusted}$) SHALL immediately transition the `FederatedFriendship` to `accepted` and dispatch a signed `Accept(Follow)` activity back to Instance A, whereas an identical `Follow` from an `untrusted` peer ($T_{B \to A} = \text{untrusted}$) SHALL remain `pending` and emit a `federation_follow` notification requiring manual action

#### Scenario: Recipient with federated_collection disabled (True, False) vs enabled (True, True)
- **WHEN** User B has `federated_profile=True` and an `accepted` friendship with User A
- **THEN** User B's `outbox` and SPARQL federation snapshot SHALL expose zero collection items when `federated_collection=False`, and SHALL expose eligible shared/public items when `federated_collection=True`

### Requirement: Orthogonal Social State, Item Visibility, and Collection Consent Matrix Verification
The multi-instance test suite SHALL verify the $5 \times 4 \times 2 = 40$ Cartesian product of directional social relationship states $S_{A,B} \in \{\text{none}, \text{pending\_outgoing}, \text{pending\_incoming}, \text{accepted}, \text{rejected\_or\_unfollowed}\}$, item visibility tiers $V_{\text{item}} \in \{\text{private}, \text{friends\_only}, \text{shared}, \text{public}\}$, and owner collection consent $C_{\text{col}} \in \{\text{False}, \text{True}\}$.

#### Scenario: Access gating across all 40 social state x visibility x collection consent combinations
- **WHEN** evaluating whether Viewer A has friend access to Owner B's items and whether Owner B's items are exposed via catalog queries, public RDF export, SPARQL endpoints, and federated loan (`as:Offer`) validation
- **THEN** `private` items SHALL NEVER be exposed to non-owners in any state; `friends_only` items SHALL ONLY be accessible to Viewer A when $S_{A,B} = \text{accepted}$ (returning `False`/hidden for `none`, `pending_outgoing`, `pending_incoming`, `rejected`, and `unfollowed`); `shared` and `public` items SHALL respect their respective authentication and `federated_collection` consent boundaries

### Requirement: Live Dual-Origin Playwright Combinatorial E2E Matrix Workflows
The Playwright E2E suite SHALL execute live browser workflows across two isolated origins (`INSTANCE_A` and `INSTANCE_B`) covering asymmetric peer trust transitions, consent shield toggles, manual Notification Center actions versus zero-click auto-accept, and `friends_only` item visibility gating across friendship establishment and revocation.

#### Scenario: Live browser E2E verification of peer trust, consent, notification actions, and friends_only revocation
- **WHEN** the dual-origin Playwright suite (`federation_matrix_workflows.spec.ts`) runs against the two-instance stack
- **THEN** it SHALL verify through real browser contexts (with zero `page.route()` mocks) that:
  1. Blocking a peer in `/admin/federation` prevents friend requests in the UI, switching to `untrusted` forces manual review even when `auto_accept_follows=True`, and switching to `trusted` restores auto-accept.
  2. Toggling federation consent in `/profile` gates remote WebFinger discovery and automatically enables sender profile federation upon sending an outbound friend request.
  3. Manual `Accept` and `Reject` buttons in the Notification Center popover (maintaining $\le 4$ interactive controls per notification item) and `/profile?tab=incoming#friends` deep-link navigation function deterministically alongside zero-click auto-accept.
  4. Selecting `friends_only` visibility in `/profile` persists without database errors, hides `friends_only` items while `none` or `pending`, reveals them upon `accepted` friendship, and immediately revokes visibility when the friendship is removed (`Undo(Follow)`).
