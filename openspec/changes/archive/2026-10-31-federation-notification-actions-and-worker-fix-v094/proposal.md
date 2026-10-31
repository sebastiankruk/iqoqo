## Why

Federated friend requests (ActivityPub `Follow` activities) correctly reach the peer node and persist `follow_request` notifications, but the user experience in the notification center is degraded:
1. `follow_request` notifications lack actionable deep links, rendering as non-interactive list items that do not take the user to `/profile?tab=incoming#friends`.
2. Notification payloads omit the remote actor's display name or username, displaying only generic text like `"New follower from preview.iqoqo.cc"` rather than identifying who sent the request.
3. The notification dropdown does not provide inline call-to-actions (Accept / Reject) or an intuitive link to respond directly without manually navigating to the Profile page.
4. In preview deployments (`docker-compose.federation-preview.yml`), the `peer-worker` container continuously crash-loops because `ADMIN_PASSWORD` is absent from its environment, preventing Celery from dispatching outbound `Accept` activities back across the federation wire.

## What Changes

- **Backend Notification Enhancements**:
  - Update `handle_follow` in `app/core/federation_handlers.py` to populate `target_iri="/profile?tab=incoming#friends"` and include the requester's name/handle in the notification payload message (e.g., `"New friend request from skruk (preview.iqoqo.cc)"`).
  - Provide helper endpoints or structured payload fields (`friendship_id` / `actor_uri`) enabling client-side quick actions.
- **Frontend Notification Center Deep Links & Actionability**:
  - Update `getNotificationTargetUrl` in `frontend/components/dashboard/notification-center.tsx` to route `follow_request` to `/profile?tab=incoming#friends`.
  - Add quick action buttons (Accept / Reject) or an explicit "Review" action directly within incoming friend/follow notification rows in `NotificationCenter`.
  - Ensure all labels are properly localized in `en.json` and `pl.json`.
- **Preview Deployment Worker Hardening**:
  - Add `ADMIN_PASSWORD` and `ADMIN_EMAIL` environment variables to `peer-worker` in `docker-compose.federation-preview.yml`, preventing Celery worker boot crashes.

## Capabilities

### Modified Capabilities
- `in-app-notifications`: Extend deep-linking, target URL resolution, requester identity presentation, and actionability to `follow_request` activities alongside existing `friend_request` handling.

## Impact

- **Backend**: `app/core/federation_handlers.py` notification dispatch.
- **Frontend**: `frontend/components/dashboard/notification-center.tsx` navigation, action buttons, and messages (`frontend/messages/en.json`, `frontend/messages/pl.json`).
- **DevOps / Containers**: `docker-compose.federation-preview.yml` (`peer-worker` environment variables).
- **Testing**: Unit tests in `tests/test_notifications_api.py`, `tests/test_federation_inbox.py`, and frontend tests in `frontend/__tests__/components/dashboard/notification-center.test.tsx`.
