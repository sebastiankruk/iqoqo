## Why

Items ingested under a shared importer or administrator account appear to belong to that account instead of the person who actually collects them. A privileged, auditable reassignment workflow is needed to correct ownership safely without exposing a general-purpose ownership override to ordinary users.

## What Changes

- Add an admin-only UI and API flow to reassign one physical Item, an explicitly selected set, or all Items owned by a specified source account to a specified target account.
- Require a server-computed preview and explicit confirmation naming the source, target, and affected count; reject stale or mismatched scopes instead of silently applying a changed selection.
- Make each reassignment operation all-or-nothing and record each ownership transfer in the Item custody history, while preserving the Item and its FRBR catalog records.
- Explain that reassignment changes who can access the Item and affect its private/public collection visibility; do not provide a self-service endpoint or permit changing `owner_id` through the normal Item update API.

## Capabilities

### New Capabilities
- `item-ownership-reassignment`: Privileged single, selected-batch, and source-account-wide Item ownership reassignment with preview, confirmation, audit, and access-boundary behavior.

### Modified Capabilities
- `item-custody`: Ownership reassignment is a custody transfer and must be logged with structured source, destination, actor, and timestamp information without rewriting earlier events.

## Impact

- Backend: physical Item APIs, authorization/RBAC, transactional Item and custody-event persistence, user scoping, and API tests.
- Frontend: privileged account selection, Item selection and detail actions, review/confirmation UI, result handling, and cache invalidation.
- Data: extend custody-event provenance as needed while keeping existing history readable; ownership reassignment must not alter Work, Expression, or Manifestation records.
- Release planning: v0.8.3, C34. No application code is part of this proposal change.
