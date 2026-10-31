## Context

See proposal.md - Why.
Inbound ActivityPub `Follow` activities are handled by `handle_follow` in `app/core/federation_handlers.py`, which records a `FederationFollower` and dispatches an in-app notification with `notification_type="follow_request"`.
The frontend `NotificationCenter` component (`frontend/components/dashboard/notification-center.tsx`) resolves target deep-links but currently omits `follow_request`. Furthermore, notification messages omit the requester's handle, and the popover offers no inline action controls.
Finally, `peer-worker` in `docker-compose.federation-preview.yml` lacks bootstrap admin credentials, causing immediate exit on boot due to strict `app/config.py` password assertions.

## Goals / Non-Goals

**Goals:**
- Unify deep-link navigation for both local `friend_request` and federated `follow_request` to `/profile?tab=incoming#friends`.
- Enrich notification payloads with requester identity (`actor_name`, `actor_handle`, origin domain) and `friendship_id` (`fed:<id>`).
- Add actionable controls (direct Accept/Reject or quick-review link) inside the `NotificationCenter` popover for pending requests.
- Provide full bilingual localization (`en.json` and `pl.json`) for notification action labels and messages.
- Eliminate the crash loop of `peer-worker` in preview compose configurations by injecting required admin environment variables.

**Non-Goals:**
- Modifying the underlying ActivityPub `Follow`, `Accept`, or `Reject` protocol JSON schemas.
- Changing database migrations or table columns for notifications or followers.

## Decisions

### Decision 1: Consistent `friendship_id` in Notification Payloads
- **Choice**: Include `friendship_id` in the notification payload (`str(new_friendship.id)` for local, `f"fed:{follower.id}"` for federated).
- **Rationale**: `app/core/friend_service.py:respond_friend_request` already accepts either an integer or a `fed:<id>` string. Supplying this ID in the notification payload allows the frontend `NotificationCenter` to dispatch response mutations directly without first needing to query `/profile/friends`.
- **Alternatives Considered**: Navigating exclusively to `/profile` without inline action buttons. Inline buttons improve mobile and desktop UX significantly.

### Decision 2: Deep Link Routing to Incoming Friends Tab
- **Choice**: Set `target_iri="/profile?tab=incoming#friends"` on all `follow_request` notifications and update `getNotificationTargetUrl` in `NotificationCenter` to return this route.
- **Rationale**: Ensures clicking any part of the notification navigates directly to the incoming friend requests list where full profile context is available.

### Decision 3: Worker Environment Parity in Compose
- **Choice**: Add `ADMIN_EMAIL=${PEER_ADMIN_EMAIL:-peer-admin@iqoqo.cc}` and `ADMIN_PASSWORD=${PEER_ADMIN_PASSWORD:-PeerBootstrapPassword123!}` to `peer-worker` in `docker-compose.federation-preview.yml`.
- **Rationale**: Matches the configuration of `peer-web` and satisfies `app/config.py` bootstrap password assertions during Celery app initialization.

## Risks / Trade-offs

- **[Risk] Multiple clicks or race conditions on inline Accept/Reject buttons** → Mitigation: Disable action buttons while mutation is pending (`disabled={isResponding}`) and optimistically remove/mark the notification as read upon success.
- **[Risk] Stale notification when friendship already accepted from Profile page** → Mitigation: API response handles 404/409 gracefully, toasts current status, and marks notification read.
