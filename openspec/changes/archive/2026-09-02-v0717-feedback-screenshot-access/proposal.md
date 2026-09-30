## Why

Feedback ticket screenshots are currently only accessible to the ticket owner and system admins. This strict IDOR (Insecure Direct Object Reference) restriction blocks custodians and other authorized users from viewing screenshots during the triage process, slowing down issue resolution. Relaxing these permissions will allow all users with read access to the ticket to view its attachments.

## What Changes

- Modify permission decorators on the `GET /api/feedback/<id>/screenshot` endpoint.
- Screenshots will now be accessible to:
  - The ticket author
  - Assigned custodians
  - Platform admins
- Maintain restrictions preventing unauthorized users from accessing screenshots.

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `feedback-mechanism`: Relax feedback screenshot authorization rules to allow access by assigned custodians.

## Impact

- **API**: `GET /api/feedback/<id>/screenshot` endpoint in `app/api/social.py` will have relaxed permission checks.
- **Tests**: `tests/test_feedback_security.py` will be updated to verify the new access rules.
- **Security**: IDOR restrictions are safely relaxed without exposing screenshots to unauthorized users.
