## Why

Release 0.7.13 built the full backend infrastructure for concert modeling — `expression.kind = 'live_performance'`, Performance Event contributions, concert ingestion detection, and facet separation. However, no code path exists to **set** or **change** an Expression's `kind` from the UI, the admin API, or the escalation system. The admin `update_expression` endpoint silently drops the `kind` parameter; the escalation validation rejects `change_type` requests; and the FRBR editor has no `kind` dropdown. The roadmap promise "Support for Concerts" is backend-complete but user-facing-broken.

Additionally, `scripts/fix_manifestation_1984.py` is a one-shot data-correction script that served its purpose. It should not ship to `main` as permanent code.

## What Changes

- **Bug Fix**: `app/api/admin.py` `update_expression` endpoint now passes `kind` from the request body to `frbr_service.update_expression()`. Admins can set `expression.kind` via the API.
- **Bug Fix**: `app/api/social.py` escalation validation now accepts `change_type` alongside `correction` and `deletion`, unblocking the type-change escalation route for non-admin users.
- **Feature**: FRBR editor (`frontend/components/admin/frbr-editor.tsx`) gains an `expression.kind` dropdown (parallel to the existing `content_type` selector), populated from the `EXPRESSION_KINDS` controlled vocabulary. Selecting `live_performance` marks the Expression as a concert; clearing it returns to studio/default.
- **Cleanup**: Remove `scripts/fix_manifestation_1984.py` — one-off data-correction script that should not persist in the release branch.

## Capabilities

### New Capabilities

- `concert-kind-ui`: Expression-kind selector in the FRBR editor and the two bug fixes that make `expression.kind` settable via admin API and escalation requests.

### Modified Capabilities

- `concert-modeling`: The spec promised concerts as Performance Event Expressions. This change adds the operational requirement that `expression.kind` must be settable through the admin UI and escalation system, not just at ingestion time.
- `frbr-ontology`: `expression.kind` is now a mutable field exposed through the standard admin update API, not a write-once ingestion artifact.

## Impact

- **Backend**: `app/api/admin.py` (pass `kind` parameter), `app/api/social.py` (accept `change_type` in validation), `app/core/frbr_service.py` (no changes needed — already supports `kind`).
- **Frontend**: `frontend/components/admin/frbr-editor.tsx` (add kind dropdown), `frontend/types/frbr.ts` (add `kind` to `Expression` interface).
- **Scripts**: Remove `scripts/fix_manifestation_1984.py`.
- **Tests**: Backend pytest for API `kind` forwarding and `change_type` escalation; frontend Vitest for kind dropdown rendering.
