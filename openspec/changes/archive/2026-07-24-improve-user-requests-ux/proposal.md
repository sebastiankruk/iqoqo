## Why

The User Requests (escalation) feature suffers from discoverability gaps, inconsistent terminology, and layout issues that degrade the user experience for both regular users and admins. Users struggle to find their submitted requests and status updates; admins face ambiguous action labels and incomplete tooling. An audit revealed 9 UX issues across navigation, labeling, layout, and functional gaps — all addressable in a single targeted improvement cycle.

## What Changes

- **Navbar dropdown**: Add a direct "My Help Requests" link from the user icon dropdown menu, reducing navigation friction from 2+ clicks + scroll to 1 click.
- **Manifestation/Item page layout**: Move the escalation trigger into a collapsible "Requests" accordion section (mirroring the existing "Admin Actions" / "FRBR Actions" pattern). Show unresolved requests outside the accordion for immediate visibility.
- **Multi-request support**: Allow users to submit more than one help request per target entity, removing the single-request limitation.
- **Terminology alignment**: Rename "Escalation Queue" tab to "User Requests" in admin view; rename "Duplicate" action button to "Mark as Duplicate"; change internal jargon "Escalation: pending" to "Help Request: pending" in status cards.
- **Admin queue improvements**: Make manifestation/item target labels clickable links (matching user view behavior). Add an expandable "Processed Requests" section (hidden by default) for resolved request history.
- **Card padding fix**: Increase internal padding on help request cards from `p-3.5` to `p-4` so borders no longer touch text content.

## Capabilities

### New Capabilities

- `user-requests-navigation`: Direct navbar dropdown link to help requests, pending count badge, and profile panel section improvements.
- `user-requests-manifestation-layout`: "Requests" accordion panel on manifestation/item pages with multi-request support and unresolved-request visibility.

### Modified Capabilities

- `custodian-escalation`: Multi-request per target (API now returns array for same user+target), terminology changes (field labels, status display).
- `escalation-queue-ui`: Tab renamed to "User Requests", target labels become clickable links, "Duplicate" action renamed to "Mark as Duplicate", resolved requests toggle added.

## Impact

- **Frontend components**: `navbar.tsx`, `manifestation-actions.tsx`, `item-actions.tsx`, `escalation-trigger.tsx`, `my-escalations.tsx`, `escalation-queue.tsx`, `admin/content/page.tsx`
- **API**: `GET /api/escalations/queue` extended with `?status=` query parameter for resolved requests; escalation-trigger component logic changes to handle arrays instead of single `.find()`
- **API client**: `frontend/lib/api/escalations.ts` — new hook for resolved escalations
- **i18n**: `frontend/messages/en.json`, `frontend/messages/pl.json` — new translation keys for all user-facing labels
- **No database changes**: Existing `escalation_requests` table and `EscalationRequest` model remain unchanged
