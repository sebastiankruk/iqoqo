# federation-multi-instance-e2e Specification

## Purpose
Defines automated multi-instance end-to-end integration testing and orchestration capabilities for iqoqo federation, validating ActivityPub WebFinger discovery, dual-context identity isolation, signed Follow activity delivery, and reproducible local multi-instance preview environments.

## Requirements

### Requirement: Multi-Instance E2E Playwright Federation Suite
The testing pipeline MUST support executing Playwright E2E tests simulating interactions across two distinct iqoqo instance configurations (Instance A and Instance B) with isolated databases, domain origins, and cryptographic identities.

#### Scenario: Cross-instance Actor discovery and Follow interaction in E2E

- **GIVEN** two local test instances running at distinct origins (e.g. `http://localhost:3000` and `http://localhost:3001`)
- **WHEN** a user on Instance A searches for `@alice@localhost:3001`
- **THEN** Instance A resolves WebFinger and fetches Alice's Actor JSON-LD representation
- **WHEN** the user on Instance A clicks "Follow"
- **THEN** a signed ActivityPub `Follow` activity is delivered to Instance B's inbox and processed

### Requirement: Manual Federation Preview Staging Option
The deployment orchestration scripts MUST provide an option to initialize a dual-instance federation preview stack for manual validation that preserves peer cryptographic keys across restarts, enforces secure production-parity defaults (`FEDERATION_AUTO_ACCEPT_FOLLOWS=false`), cleans up synthetic internal smoke-test trust records after preflight checks, and documents full administrative peering and key-pinning procedures.

#### Scenario: Operator boots dual-instance preview stack

- **WHEN** an operator runs `make preview-up FEDERATION_PAIR=1` or triggers the federation preview profile in `iqopretest`
- **THEN** two isolated application stacks (primary and peer) are provisioned with interconnected internal networking, persistent cryptographic key volumes, and mutual seed credentials
- **THEN** the operator can open both instances in a browser to inspect federation activity logs and UI reactions in real time

#### Scenario: Preflight verification script leaves zero synthetic internal trusted peers behind

- **WHEN** `scripts/verify_federation_preview.sh` executes internal container-to-container discovery smoke checks (`web:5000` and `peer-web:5000`)
- **THEN** a `try ... finally` cleanup block restores prior state and removes synthetic `web:5000` / `peer-web:5000` records before exiting so persistent preview databases are never polluted with pre-trusted internal hostnames

#### Scenario: Manual federation walkthrough documents settings, defaults, and SHA-256 fingerprint verification

- **WHEN** an operator or QA engineer follows `.context/notes/tests/federation-manual-testing-walkthrough.md`
- **THEN** the guide documents `Auto-Accept Follow Requests` (default `Disabled`), `Default Peer Trust` (`untrusted` / `pending`), `Instance Actor Key Fingerprint` out-of-band SHA-256 verification, and clean public-domain peering (`preview.iqoqo.cc` <-> `peer.iqoqo.cc`)

### Requirement: Automated Dual-Origin Live Federation Click-Through Suite
The Playwright E2E testing framework MUST execute a multi-instance federation test suite against two concurrently running live application origins without mock route interceptions, asserting full cross-instance user journeys through accessible UI interactions.

#### Scenario: Cross-instance trust peering and user consent via UI

- **WHEN** an administrator opens the Trust Graph dashboard on Instance A and registers Instance B as a trusted peer
- **AND** a user on Instance B toggles federation consent on their profile page
- **THEN** both instances record mutual peering state and permit cross-instance ActivityPub discovery

#### Scenario: Dual-origin social follow and notification handshake

- **WHEN** a user on Instance A navigates to the social discovery interface and submits a follow request targeting a user on Instance B
- **THEN** a signed ActivityPub `as:Follow` activity is delivered across the network boundary to Instance B
- **AND** the user on Instance B observes an incoming notification badge and follow request in the Notification Center
- **AND** approving or auto-accepting the follow returns a signed `as:Accept` activity, rendering both users as accepted friends

#### Scenario: Cross-instance physical loan request and custody transfer

- **WHEN** an accepted friend on Instance A browses the connected library directory to view Instance B's public holdings
- **AND** submits an in-app loan request for a lendable item owned by Instance B
- **THEN** Instance B receives a pending loan request with federated origin metadata
- **WHEN** the item owner on Instance B approves the request in the lending administration interface
- **THEN** the item collection status updates to `lent`
- **AND** an immutable `ItemCustodyEvent` (`crm:E10_Transfer_of_Custody`) is recorded in Instance B's custody ledger
- **AND** Instance A receives an ActivityPub `as:Accept` activity and displays an approval notification to the borrower

#### Scenario: Cross-instance item return and custody reconciliation

- **WHEN** the item owner on Instance B marks the lent item as returned in the lending interface
- **THEN** the item collection status resets to `available`
- **AND** a return custody event is recorded in the immutable custody ledger

#### Scenario: In-app Help Hub navigation and bilingual article display

- **WHEN** a user navigates to `/help`
- **THEN** topic cards and quick-start guides render with accessible links
- **AND** navigating to `/help/[slug]` renders the localized article content in the user's active locale

### Requirement: Standardized Federation Pair CI Test Runner
The build and test orchestration system MUST provide automated Makefile and continuous integration targets that boot an isolated dual-instance paired stack, perform automated preflight connectivity probes, execute the dual-origin Playwright suite, and cleanly tear down resources, covered by a dedicated BATS test suite for preflight runner reliability.

#### Scenario: Preflight runner argument and health verification

- **WHEN** `tests/bash/verify_federation_preview.bats` executes
- **THEN** it validates CLI argument parsing, health check timeouts, fixture seeding, and non-zero exit codes on unresponsive instances.

#### Scenario: Automated CI execution of federation pair tests

- **WHEN** the continuous integration runner triggers `make test-e2e-federation`
- **THEN** the system boots isolated primary and secondary container stacks with distinct databases and ports
- **AND** verifies HTTP health and WebFinger endpoints before running Playwright
- **AND** executes the dual-origin live federation suite
- **AND** terminates all test containers upon completion, archiving logs and test traces on failure

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

#### Scenario: Asymmetric or bilateral blocked peering topology (*x blocked or blocked x*)

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
