## 1. Quick Wins: Terminology and Navigation

- [x] 1.1 Rename "Escalation Queue" tab label to "User Requests" in `frontend/app/admin/content/page.tsx` (line 189) and update empty state messages in `escalation-queue.tsx` ("No pending escalation requests" → "No pending user requests")
- [x] 1.2 Rename "Duplicate" action button label to "Mark as Duplicate" in `frontend/components/admin/escalation-queue.tsx` (line 118), keeping the ClipboardCopy icon
- [x] 1.3 Rename status card label from "Escalation: {status}" to "Help Request: {status}" in `frontend/components/escalation/escalation-trigger.tsx` (line 99)
- [x] 1.4 Add "My Help Requests" dropdown menu item to `frontend/components/dashboard/navbar.tsx` between "Manage Collections" and "Admin Configuration", linking to `/admin/settings?tab=profile#help-requests`
- [x] 1.5 Add pending request count badge to the dropdown menu item using `useMyEscalations()` hook; show badge only when pending count > 0
- [x] 1.6 Fix card padding in `frontend/components/escalation/my-escalations.tsx` (line 165) — change `p-3.5 space-y-2` to `p-4 space-y-3`

## 2. API Extension for Resolved Requests

- [x] 2.1 Extend `GET /api/escalations/queue` in `app/api/social.py` to accept optional `?status=` query parameter (comma-separated statuses); default to `pending` when absent for backward compatibility
- [x] 2.2 Add `useResolvedEscalations()` or parameterized `useEscalationQueue(status?)` hook in `frontend/lib/api/escalations.ts`
- [x] 2.3 Add `getTargetLabel()` helper to produce clickable target link (manifestation or item) — extract from existing pattern in `my-escalations.tsx` if reusable

## 3. Admin Queue Improvements

- [x] 3.1 Make target entity labels clickable in `frontend/components/admin/escalation-queue.tsx` — wrap target badge in `<Link>` to `/manifestation/{id}` or `/item/{id}`, matching the link pattern from `my-escalations.tsx`
- [x] 3.2 Add expandable "Processed Requests" section below the pending queue with a toggle button (chevron + label); hidden by default
- [x] 3.3 Implement the resolved requests list component — fetch resolved escalations using the new API hook, display each with status badge, resolution note, resolver name, and resolved date

## 4. Manifestation/Item Page Restructuring

- [x] 4.1 Create "Requests" accordion panel in `frontend/components/manifestation/manifestation-actions.tsx` — add collapsible section using existing Shadcn UI pattern (ChevronUp/Down + "Requests" label) wrapping the EscalationTrigger; render only for users without `write:metadata`
- [x] 4.2 Apply the same "Requests" accordion pattern to `frontend/components/item/item-actions.tsx`
- [x] 4.3 Modify `frontend/components/escalation/escalation-trigger.tsx` to receive/filter multiple escalations per target instead of using single `.find()` — accept array of escalations, show most recent pending outside accordion, render all inside when expanded
- [x] 4.4 Implement unresolved-request visibility: when a pending request exists, render a compact status card OUTSIDE the collapsed "Requests" accordion header; hide "Ask custodians" button until accordion expands
- [x] 4.5 Ensure multiple-request submission works: expand accordion → show existing requests + "Ask custodians for help" button → dialog opens with empty fields regardless of existing requests

## 5. i18n and Polish

- [x] 5.1 Add translation keys to `frontend/messages/en.json` for all new user-facing labels: "My Help Requests", "User Requests", "Help Request", "Mark as Duplicate", "Processed Requests", "No pending user requests", "Requests" (accordion label), "Ask custodians for help", "Submit Request", "Field to correct", "Suggested value", "Current value (optional)", "Reason / Note (optional)", "No help requests submitted"
- [x] 5.2 Add corresponding Polish translations to `frontend/messages/pl.json`
- [x] 5.3 Update `escalation-trigger.tsx` to use `useTranslations()` hook for all user-facing labels
- [x] 5.4 Update `my-escalations.tsx` to use `useTranslations()` hook
- [x] 5.5 Update `escalation-queue.tsx` to use `useTranslations()` hook for all labels including action buttons and empty states
- [x] 5.6 Update `navbar.tsx` to use translation for "My Help Requests" label
- [x] 5.7 Verify all components render correctly across viewport sizes (320px to 2560px) and no text touches card borders

## 6. Validation

- [x] 6.1 Run frontend lint and type-check: `npm run lint && npx tsc --noEmit`
- [x] 6.2 Run backend lint: `pytest` (or relevant test suite) to verify API changes
- [x] 6.3 Manual smoke test: submit a help request as non-custodian user, verify it appears in admin "User Requests" queue, resolve it, verify "Processed Requests" shows it
- [x] 6.4 Manual smoke test: verify navbar dropdown shows "My Help Requests" link, verify "Requests" accordion works on manifestation and item pages, verify multiple requests can be submitted
- [x] 6.5 Run i18n validation to ensure no missing translation keys
