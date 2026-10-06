## Context

The User Requests feature (internally called "escalation") was built in two phases: the backend API + data model (`custodian-escalation`) and the admin queue UI (`escalation-queue-ui`). The current implementation has several UX gaps:

- **Navigation**: No direct link from the navbar dropdown to help requests; users must navigate through profile settings or remember the `/profile` URL.
- **Layout**: The escalation trigger on manifestation/item pages sits as a standalone element outside any accordion grouping, making it visually orphaned.
- **Single-request limit**: `EscalationTrigger` uses `.find()` to pick one escalation per target, preventing multiple requests on the same entity.
- **Inconsistent terminology**: "Escalation Queue" vs "Help Requests", "Escalation: pending" vs user-facing language, "Duplicate" button ambiguity.
- **Missing admin functionality**: No way to view resolved/processed requests, no clickable links to target entities.

All changes are frontend-only except one API extension (query parameter on `/api/escalations/queue`).

## Goals / Non-Goals

**Goals:**

- Give users one-click access to their help requests from the navbar dropdown
- Restructure manifestation/item page actions to group help requests under an accordion panel
- Support multiple help requests per FRBR target entity
- Align all user-facing terminology ("Help Requests", "User Requests", "Mark as Duplicate")
- Make admin queue more functional (clickable targets, processed requests history)
- Fix visual polish (card padding)

**Non-Goals:**

- No database schema changes
- No backend permission changes
- No notification system for request status changes (future feature)
- No batch operations on admin queue
- No real-time updates (polling/refresh remains manual)

## Decisions

### Decision 1: Accordion pattern reuse for "Requests" panel

**Chosen**: Reuse the existing Shadcn UI collapsible pattern from "Admin Actions" / "FRBR Actions" sections in `ManifestationActions` and `ItemActions`.

**Rationale**: Consistent UX, minimal new code. The accordion header pattern (`ChevronUp`/`ChevronDown` + label) is already well-tested. Users familiar with the admin panel will instantly understand the "Requests" section.

**Alternative considered**: Tab-based layout (Admin / Requests / FRBR tabs). Rejected — adds visual weight for a section that most users won't use (many won't need help requests). Accordion keeps the page clean.

### Decision 2: Unresolved requests render OUTSIDE the accordion

**Chosen**: When a user has an active pending request, render a compact status card ABOVE the "Requests" accordion header. Inside the accordion, show the "Submit new request" button and any resolved request history.

**Rationale**: Users must see unresolved request status at a glance without expanding anything. The accordion hides the "new request" button and resolved history behind a click, reducing clutter for the 90% case where the user has no pending requests.

### Decision 3: Multi-request via array instead of single `.find()`

**Chosen**: Change `EscalationTrigger` to accept/fetch ALL escalations for a target (not just the first match). The status card shows the most recent pending request; clicking "Submit new request" opens a dialog regardless of existing requests.

**Rationale**: Minimal API change needed — `GET /api/escalations/mine` already returns all user escalations. Only the frontend filter logic changes. The dialog's submit handler already creates independent records.

**Alternative considered**: Adding a "status=open" filter to the API to exclude resolved requests. Rejected as unnecessary — frontend filtering on the full list is simpler and gives the component full context.

### Decision 4: Terminology — keep backend/internal names, change only frontend-facing labels

**Chosen**: Keep `EscalationRequest` model, `escalation_requests` table, API endpoints (`/api/escalations/*`), and internal variable names unchanged. Only change user-facing display labels and component names.

**Rationale**: Avoids backend refactoring risk and API-breaking changes. Backend term "escalation" is precise and well-documented. Users see "Help Requests" / "User Requests" which are more intuitive. The mapping is trivial and documented.

**Alternative considered**: Full rename of database tables and API endpoints. Rejected — high risk, low user value, requires migration.

### Decision 5: API extension for resolved requests

**Chosen**: Extend `GET /api/escalations/queue` with an optional `?status=accepted,rejected,duplicate` query parameter. No new endpoint.

**Rationale**: Minimal change, backward compatible (existing calls with no parameter return `pending` as before). The `escalate:resolve` permission check remains unchanged.

**Alternative considered**: New endpoint `GET /api/escalations/resolved`. Rejected — adds route bloat for a single query variation.

### Decision 6: i18n — English and Polish

**Chosen**: Add translation keys for all new/changed user-facing labels in `en.json` and `pl.json`. Use `useTranslations()` hook consistently.

**Rationale**: iqoqo already has i18n infrastructure. Adding keys now prevents future rework. Polish is the project's secondary language (maintainer's primary language).

## Risks / Trade-offs

- **[Risk]** Changing "Escalation Queue" tab name to "User Requests" may disorient existing admins → **Mitigation**: Sidebar icon (LifeBuoy) remains unchanged as visual anchor; tooltip on hover shows "formerly Escalation Queue".
- **[Risk]** Multi-request support could lead to UI clutter if a user submits many requests on one entity → **Mitigation**: Show max 5 most recent; "View all N requests" link to collapse overflow.
- **[Risk]** Accordion wrapping may add one click to request submission flow → **Mitigation**: Accordion state persists in session or defaults open when unresolved requests exist, maintaining zero-click visibility for active cases.
- **[Trade-off]** Frontend-only filtering for multi-request (instead of API-level dedup) means more data transferred → **Acceptable**: EscalationRequest objects are small (~200 bytes each); typical user has < 10 requests total.
