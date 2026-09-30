---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

iqoqo uses a FRBR-based ontology (Work → Expression → Manifestation → Item) with a strict RBAC permission system. Manifestation-level metadata (titles, ISBNs, format classifications) is controlled by custodian-tier permissions (`write:metadata`). Regular users (role `member`) can view this data but cannot modify it. The existing `SocialFeedback` and `SocialNote` models in `app/api/social.py` already implement a polymorphic FRBR-level targeting pattern (`work_id`, `expression_id`, `manifestation_id`, `item_id`) with proven sanitization, validation, and access control.

The `item-actions.tsx` and `manifestation-actions.tsx` components already gate admin actions behind `hasPermission()` checks using the `PermissionName` enum from `frontend/lib/permissions.ts`. There is currently no mechanism for non-custodian users to signal that metadata is incorrect.

## Goals / Non-Goals

**Goals:**

- Allow authenticated users to submit structured escalation requests targeting specific FRBR entities and fields
- Provide custodians with a queue of pending requests accessible from the admin panel
- Reuse existing architectural patterns (FRBR polymorphic targeting, `require_auth`, `require_permission` decorators, `PermissionName` enum)
- Keep the UI non-intrusive — a single contextual trigger that appears only when the user lacks write permissions
- Surface escalation status and resolution notes contextually within the Escalation Trigger for the requesting user

**Non-Goals:**

- Real-time push notifications or emails for users or custodians — out of scope for v0.7.12; custodians poll the admin queue, and users see status in-context on the item/manifestation page
- Free-form chat between user and custodian — escalation is a one-shot request with optional resolution note
- Automatic metadata application — custodians manually review and apply approved changes
- Batch escalations (requesting changes to multiple entities at once)

## Decisions

### D1: Extend `app/api/social.py` rather than creating a new module

**Decision**: Add escalation endpoints to the existing `social.py` module.

**Rationale**: The social module already handles user-generated feedback targeting FRBR entities with the same polymorphic pattern. Adding escalations here keeps the FRBR-level targeting logic, validation helpers (`_verify_target_exists`, `_sanitize_text`), and imports consolidated. The module is currently ~326 lines and will grow by ~150 lines — still well within manageable size.

**Alternative considered**: A new `app/api/escalations.py` module. Rejected because it would duplicate the FRBR targeting utilities and fragment the social interaction domain.

### D2: Polymorphic FRBR-level columns (same as SocialFeedback)

**Decision**: The `EscalationRequest` model uses four nullable foreign keys (`work_id`, `expression_id`, `manifestation_id`, `item_id`) with a check constraint ensuring exactly one is set.

**Rationale**: This matches the proven `SocialFeedback` and `SocialNote` pattern. It avoids generic polymorphic associations and keeps queries simple with direct JOINs.

**Alternative considered**: A single `target_type` + `target_id` pair. Rejected because it would require application-level type dispatch and prevent DB-level referential integrity.

### D3: Status lifecycle as a string enum column

**Decision**: `EscalationRequest.status` uses a PostgreSQL `VARCHAR` with application-level validation: `pending`, `accepted`, `rejected`, `duplicate`.

**Rationale**: Matches the existing `Item.status` pattern. A DB-level `ENUM` type adds migration complexity without meaningful benefit at this scale.

### D4: Two new permissions — `escalate:request` and `escalate:resolve`

**Decision**: `escalate:request` is granted to the `member` role (default for all registered users). `escalate:resolve` is granted to the `custodian` and `admin` roles.

**Rationale**: Separating request creation from resolution follows the existing `read:metadata` / `write:metadata` split pattern. The `member` role already exists and is auto-assigned on registration.

### D5: Frontend trigger uses inverse permission gating

**Decision**: The `<EscalationTrigger>` component renders when the user does NOT have `write:metadata` permission. It is hidden for custodians/admins who can directly edit the metadata.

**Rationale**: Custodians already see "Edit FRBR" and "Refetch Metadata" buttons. Showing them an escalation trigger would be redundant and confusing. The inverse-gate pattern (`!hasPermission(...)`) is already used conceptually in the actions panel (admin panel visibility vs. user-only quick actions).

### D6: Minimal requested-field schema

**Decision**: Each escalation captures `field_name` (string, e.g. `"title"`, `"isbn"`, `"format"`), `current_value` (string, optional), and `suggested_value` (string, required). No rich structured payloads.

**Rationale**: Keeps the schema simple and avoids coupling to specific FRBR entity structures. The custodian reads the suggestion and manually applies it through existing FRBR editor tooling.

### D7: In-context user notifications

**Decision**: The `<EscalationTrigger>` component will query for the user's escalations on the current entity and display their status (`pending`, `accepted`, `rejected`) and any `resolution_note` instead of the default "Ask for Help" button.

**Rationale**: This avoids the complexity of building a global notification center or email infrastructure for this release while still closing the loop for the user in the exact context they submitted the request.

## Risks / Trade-offs

- **[Spam/abuse]** → Mitigation: `MAX_SOCIAL_TEXT_LENGTH` (2048 chars) reused for suggestion text; `_sanitize_text` strips HTML; rate limiting deferred to v0.7.14 Redis integration.
- **[Orphaned requests]** → Mitigation: Cascade-delete escalation requests when the target FRBR entity is deleted (same as `SocialFeedback`).
- **[Permission sync]** → Mitigation: `shared/permissions.yaml` is the single source of truth; `scripts/sync_permissions.py` regenerates `frontend/lib/permissions.ts` and seeds the DB.
- **[No real-time updates]** → Trade-off accepted: Custodians must visit the admin queue to see new requests. Real-time push is a v0.9.0 concern (ActivityPub/WebSocket federation layer).
