## Context

Feedback ticket screenshots are currently restricted by strict IDOR checks in `app/api/feedback.py`. The `_validate_screenshot_access` function only allows the ticket's author and platform admins to access the attachments. However, other users who might be granted read access to the ticket (e.g. custodians or escalated support roles) are blocked from viewing the screenshots, which hinders the triage process.

## Goals / Non-Goals

**Goals:**
- Refactor the screenshot access validation (`_validate_screenshot_access`) in `app/api/feedback.py` to allow access if the authenticated user has read access to the associated ticket.
- Ensure the logic accurately reflects the ticket's read permissions rather than duplicating hard-coded role checks.

**Non-Goals:**
- Modifying the underlying upload mechanisms or Celery tasks.
- Modifying the `FeedbackItem` model or introducing new schema tables.

## Decisions

- **Tie Screenshot Access to Ticket Read Access:** Instead of querying the user's items and checking if the filename is in the attachments, the endpoint will query the `FeedbackItem` that contains the requested screenshot `filename` in its attachments. Then, it will evaluate if the current user is authorized to read that `FeedbackItem`.
- **Target File:** Although the proposal referred to `app/api/social.py` and `GET /api/feedback/<id>/screenshot`, the actual implementation resides in `app/api/feedback.py` at `GET /api/feedback/screenshots/<path:filename>`. The design will target the correct existing file and endpoint.

## Risks / Trade-offs

- **[Risk] Multiple tickets containing the same screenshot:** If a screenshot filename is duplicated across tickets (unlikely due to secure filenames but theoretically possible), the user might be granted or denied access based on the first matched ticket. 
  → **Mitigation:** Rely on unique filenames generated during upload, ensuring a 1:1 mapping between a screenshot filename and its parent ticket.

## Migration Plan

- Deploy the updated `app/api/feedback.py`.
- No database migrations or background backfills are required since this is purely a logic change on the API side.
