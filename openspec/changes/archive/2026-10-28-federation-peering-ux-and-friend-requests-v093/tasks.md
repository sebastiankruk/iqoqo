## 1. Backend Direction Segregation & Guarding in Friend Service

- [x] 1.1 In `app/core/friend_service.py` (`list_friends`), check for an outbound `FederationActivity` (`direction="outbound"`, `activity_type="Follow"`, `actor_uri=canonical_actor_iri(u_uuid)`, target matching remote actor inbox) to place pending federated follows in `outgoing` instead of `incoming`; verify with unit tests in `tests/test_friend_service.py`
- [x] 1.2 In `app/core/friend_service.py` (`respond_friend_request`), reject responding (`accept`/`reject`) to outbound federated follow requests initiated by the caller with HTTP 400 (`Cannot respond to an outgoing request you initiated; use cancel instead`); verify with unit tests in `tests/test_friend_service.py`

## 2. Frontend Peering Guidance & Friends Form Polish

- [x] 2.1 In `frontend/components/admin/federation-instances.tsx`, add an informative Alert banner explaining that ActivityPub peering is unilateral and requires reciprocal peering configuration on the remote instance for mutual trust and follow auto-acceptance; verify with Vitest in `frontend/__tests__/components/admin/instance-settings-federation.test.tsx`
- [x] 2.2 In `frontend/components/profile/friends-card.tsx`, add a helper caption below the identifier input noting that remote recipients must enable "Federated Profile" in instance settings, and ensure localized rendering of federated badges across Accepted, Incoming, and Outgoing tabs; verify with Vitest in `frontend/__tests__/components/profile/friends-card.test.tsx`

## 3. End-to-End & Integration Testing

- [x] 3.1 Author integration test suite in `tests/test_friend_service.py` covering bidirectional friend request segregation, outbound activity linking, self-response rejection, and cancelation
- [x] 3.2 Author Playwright E2E test `frontend/__tests__/e2e/federated_friend_request.spec.ts` validating the user friend request flow, ensuring outbound requests appear strictly under "Outgoing Requests" with a "Cancel" action and do NOT appear under "Incoming Requests"
- [x] 3.3 Run `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, targeted backend `pytest` and frontend `vitest` suites, and `IQOQO_AI_MODE=1 make knowledge-sync`
