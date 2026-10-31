## 1. Compose Environment Hardening

- [x] 1.1 Add `ADMIN_EMAIL` and `ADMIN_PASSWORD` to `peer-worker` in `docker-compose.federation-preview.yml` and verify `docker compose -f docker-compose.yml -f docker-compose.federation-preview.yml config --quiet` succeeds without errors

## 2. Backend Notification Enrichment

- [x] 2.1 Update `handle_follow` in `app/core/federation_handlers.py` to set `target_iri="/profile?tab=incoming#friends"`, attach `friendship_id: f"fed:{follower.id}"`, and format requester identity into the notification message
- [x] 2.2 Add unit test coverage in `tests/test_federation_inbox.py` and `tests/test_notifications_api.py` and verify with `pytest tests/test_federation_inbox.py tests/test_notifications_api.py`

## 3. Frontend Notification Center Actions & Deep Links

- [x] 3.1 Update `getNotificationTargetUrl` in `frontend/components/dashboard/notification-center.tsx` to route `follow_request` to `/profile?tab=incoming#friends`
- [x] 3.2 Add inline Accept and Reject action controls for pending friend and follow request items in `NotificationCenter` calling `/api/profile/friends/<id>/respond`
- [x] 3.3 Add translation keys for inline notification actions in `frontend/messages/en.json` and `frontend/messages/pl.json`
- [x] 3.4 Update and run frontend test suite in `frontend/__tests__/components/dashboard/notification-center.test.tsx` and verify with `pnpm --prefix frontend test -- notification-center`

## 4. Verification and Quality Gates

- [x] 4.1 Run full formatters and linters (`make format-python`, `make format-js`, `make lint`) and verify clean exit
- [x] 4.2 Run test suites (`make test-backend`, `make test-frontend`) and verify all tests pass
