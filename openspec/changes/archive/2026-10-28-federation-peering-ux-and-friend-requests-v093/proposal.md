## Why

Multi-instance testing between `preview.iqoqo.cc` and `peer.iqoqo.cc` revealed a critical bug where outbound federated friend requests appear in the sender's own "Incoming Requests" tab with Accept/Reject actions instead of "Outgoing Requests", while the recipient instance drops requests with 404 when default federated profile consent is disabled. Additionally, administrators experience confusion because adding a remote peer in `/admin/federation` is unilateral and does not establish reciprocal trust on the remote peer, causing follow auto-acceptance and trust settings to appear disconnected.

## What Changes

- **Fix Federated Follow Request Direction**: In `app/core/friend_service.py`, determine follow direction for pending `FederationFollower` records by checking outbound `FederationActivity` logs (`direction="outbound"`, `activity_type="Follow"`), properly placing outbound requests into `outgoing` with a "Cancel" action and inbound requests into `incoming` with "Accept"/"Reject" actions.
- **Guard Respond Endpoint**: Prevent callers from accepting or rejecting outbound follow requests they initiated themselves in `respond_friend_request`.
- **Informative Peering UX in Admin Federation**: Add explanatory callouts and badges to `frontend/components/admin/federation-instances.tsx` informing administrators that ActivityPub peering is unilateral and requires reciprocal configuration on the remote instance for mutual trust and follow auto-acceptance.
- **Federated Follow Pre-Flight & Consent Feedback**: Provide user-facing hints on the `/profile` friends addition form about recipient federated profile consent and surface clearer feedback when remote discovery fails or returns unconsented actors.
- **Comprehensive Unit & E2E Testing**: Add backend unit test coverage for bidirectional friend requests in `test_friend_service.py`, frontend component tests for incoming vs outgoing tabs in `friends-card.test.tsx`, and a dual-instance end-to-end Playwright test simulating friend request dispatch and acceptance across two instances.

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `activitypub-inbox-outbox`: Differentiate outbound vs inbound ActivityPub Follow tracking in local friend status queries and guard respond endpoints against inverted state mutations.
- `admin-federation-dashboard`: Present reciprocal peering guidance and unilateral Trust Graph explanations in the Federation admin dashboard.
- `social-activitystreams-ontology`: Ensure federated friend listings correctly separate outgoing pending follows from incoming pending follow requests.

## Impact

- **Backend**: `app/core/friend_service.py` (`list_friends`, `respond_friend_request`), `app/core/federation_handlers.py`.
- **Frontend**: `frontend/components/profile/friends-card.tsx`, `frontend/components/admin/federation-instances.tsx`.
- **Tests**: `tests/test_friend_service.py`, `tests/test_federation_inbox_outbox.py`, `frontend/__tests__/components/profile/friends-card.test.tsx`, and `frontend/__tests__/e2e/federated_friend_request.spec.ts`.
