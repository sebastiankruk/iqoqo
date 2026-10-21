## Why
Users need immediate alerts for incoming follow requests, loan approvals, custodian escalations, and metadata merge proposals.
## What Changes

- Create `social.notifications` table (`id`, `user_id`, `type`, `actor_uri`, `target_iri`, `payload_json`, `read_at`, `created_at`).
- Expose `/api/v1/notifications` (`GET`, `PATCH /read`, `POST /read-all`).
- Emit notifications on follow requests, loan events, custodian escalations, and federation metadata proposals.
- Add `frontend/components/dashboard/notification-center.tsx` bell dropdown with unread badge in `navbar.tsx`.

## Capabilities

### New Capabilities
- `in-app-notifications`: social.notifications database schema, REST API, navbar notification dropdown, and real-time alerts

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

New database table, notification API endpoints, and navbar component.
