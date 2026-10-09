# item-ownership-reassignment Specification

## Purpose

Provides an auditable, administrator-controlled way to correct Item ownership after imports or other account-level data errors, while preserving clear authorization, confirmation, and privacy boundaries.

## Requirements

### Requirement: Ownership reassignment is restricted to authorized administrators

The system SHALL permit Item ownership reassignment only to an authenticated user who has both the `admin` role and the `write:users` permission. Source/target account discovery SHALL additionally require `read:users`. Ordinary owners, borrowers, users with only `update:item` or `write:item`, and callers without authentication SHALL NOT use reassignment operations. Reassignment SHALL NOT be exposed as a public or self-service ownership override, and the ordinary Item update API SHALL continue to reject `owner_id` changes.

#### Scenario: Authorized administrator opens reassignment

- **WHEN** an authenticated administrator with `write:users` requests the reassignment UI or API
- **THEN** the system permits the operation subject to source, target, and scope validation

#### Scenario: Administrator without account-read permission requests account discovery

- **WHEN** an authenticated administrator with `write:users` but without `read:users` requests source or target account discovery
- **THEN** the system denies account discovery without exposing account identities, while reassignment authorization remains independently enforced

#### Scenario: Non-admin with user-write permission attempts reassignment

- **WHEN** an authenticated non-admin has `write:users` and submits a reassignment request
- **THEN** the system denies the request and changes no Item or custody data

#### Scenario: Ordinary owner attempts self-service ownership override

- **WHEN** an ordinary user submits `owner_id` through the Item update API or invokes an ownership-reassignment operation
- **THEN** the system rejects the ownership change and leaves the Item unchanged

### Requirement: Reassignment supports one Item, selected Items, and all Items of a source account

The system SHALL support reassignment of exactly one positive-ID physical Item, an explicit set of selected physical Item IDs, or every physical Item whose current `owner_id` equals the specified source account. Wishlist intents are not physical Items and SHALL NOT be included. The source and target SHALL be distinct existing accounts; the target SHALL be active. The all-Items scope SHALL include every matching physical Item regardless of hidden state, collection/progress status, or lending status. A selected set SHALL be non-empty, contain unique positive IDs, and every selected Item SHALL currently belong to the specified source account. Current borrower/lending fields and the Item's other non-ownership attributes SHALL remain unchanged by reassignment.

#### Scenario: Reassign one source-owned physical Item

- **WHEN** an authorized administrator previews and confirms one physical Item with its actual source account and a different active target account
- **THEN** the system changes only that Item's owner to the target and records the transfer

#### Scenario: Reassign selected Items belonging to one source

- **WHEN** an authorized administrator previews and confirms a non-empty unique set of physical Item IDs, all currently owned by the specified source
- **THEN** the system reassigns exactly that selected set and no other Item

#### Scenario: Reassign all physical Items of a source account

- **WHEN** an authorized administrator previews and confirms the all-Items scope for a specified source account
- **THEN** the system reassigns every physical Item currently owned by that source, including hidden and lent Items, and no Item owned by another account

#### Scenario: Selected Item is not owned by the requested source

- **WHEN** a selected ID is missing, virtual/non-physical, or currently owned by a different account
- **THEN** the system rejects the entire operation without revealing unauthorized Item details or changing any Item

#### Scenario: Source and target are invalid or identical

- **WHEN** either account does not exist, the target is inactive, or source and target are the same account
- **THEN** the system rejects the reassignment and changes no data

### Requirement: Reassignment is previewed and explicitly confirmed

Before any ownership mutation, the system SHALL provide a server-computed preview containing the source account, target account, operation scope, and exact affected count. The confirmation UI SHALL repeat the source, target, and count and warn that ownership changes Item access and collection visibility; all-Items confirmation SHALL clearly state that hidden and currently lent Items are included. Execution SHALL be bound to the previewed scope and SHALL reject a stale or changed scope for fresh review rather than applying an unreviewed set.

#### Scenario: Administrator reviews a bulk or all-Items preview

- **WHEN** an administrator requests a preview for multiple Items or all Items of a source
- **THEN** the preview gives the canonical source and target identities, exact count, scope, and the applicable privacy/lending warning before confirmation is available

#### Scenario: Scope changes after preview

- **WHEN** the Item set or count for the previewed scope changes before confirmation
- **THEN** the system returns a conflict requiring a new preview and makes no reassignment from that stale confirmation

#### Scenario: Zero Items match the source scope

- **WHEN** the server preview finds no Items for the requested source/scope
- **THEN** the UI reports zero affected Items and does not offer a confirmation action

### Requirement: Reassignment is atomic and does not partially transfer a batch

The system SHALL apply each confirmed single, selected, or all-Items operation as one atomic unit, including ownership updates, source-owned collection-link cleanup, and custody-event creation. If validation, a concurrent-change check, or persistence of any Item/event fails, the system SHALL roll back the entire operation and return a failure that identifies that no partial success occurred. A retry after a stale-scope conflict SHALL require a new preview.

#### Scenario: Selected batch succeeds

- **WHEN** every selected Item and its transfer event can be persisted within the confirmed transaction
- **THEN** all selected Items are reassigned and the response reports the complete transferred count

#### Scenario: Any selected transfer fails

- **WHEN** any Item update, related cleanup, or custody-event insert fails during a batch
- **THEN** all changes in that operation are rolled back and the response reports zero transferred Items

#### Scenario: Concurrent all-Items scope changes

- **WHEN** another transaction changes the source-owned Item set while an all-Items reassignment is being confirmed
- **THEN** the system detects a conflict or serializable-transaction failure, performs no partial transfer, and requires the administrator to preview again

### Requirement: Ownership changes preserve custody history and related Item data

Each successful ownership change SHALL append an immutable custody transfer event identifying the Item, previous owner, new owner, acting administrator, and recorded time. Existing custody events SHALL remain unchanged. Reassignment SHALL NOT modify Work, Expression, or Manifestation records, nor rewrite Item status/progress history. Links from the source account's personal collections SHALL be removed atomically; collection trees SHALL NOT be copied or reassigned to the target. Item metadata, visibility flag, status, tags, and lending/borrower fields SHALL otherwise be preserved.

#### Scenario: Successful transfer records provenance

- **WHEN** a physical Item's owner changes through the reassignment workflow
- **THEN** exactly one transfer event is appended with the old owner, new owner, actor, Item, and timestamp, while prior custody events remain unchanged

#### Scenario: Source personal collection links are removed

- **WHEN** an Item linked to one or more collections owned by the source account is reassigned
- **THEN** those source-owned collection links are removed in the same transaction and no target collection links are implicitly created

#### Scenario: Transfer preserves Item and FRBR data

- **WHEN** an Item is successfully reassigned
- **THEN** its metadata, hidden flag, status, tags, open lending fields, Item status history, and associated FRBR catalog entities remain unchanged apart from owner and source collection-link cleanup

### Requirement: Reassignment explains and enforces its access consequences

The reassignment workflow SHALL inform the administrator that the target becomes the Item owner and gains owner-scoped access, while the source loses owner-scoped access; visibility of non-hidden Items in profile/shared collection surfaces follows the new owner, while `is_hidden` remains unchanged. The workflow SHALL identify that active loans remain recorded and are included in the operation. Administrative previews, item lists, and mutation responses SHALL be available only after the reassignment authorization check.

#### Scenario: Ownership changes the access boundary

- **WHEN** an Item is reassigned from one account to another
- **THEN** owner-scoped Item access follows the new owner and the confirmation explains the source and target access change without silently making a hidden Item public

#### Scenario: Lent Item is included with lending preserved

- **WHEN** a preview includes an Item with an active lending state
- **THEN** the count and confirmation identify lent Items as included, the transfer preserves borrower/lending fields, and the target becomes owner while the existing borrower remains recorded

#### Scenario: Unauthorized caller requests preview or source Item list

- **WHEN** a caller without the required admin role and permission requests reassignment discovery or preview data
- **THEN** the system denies the request without disclosing source accounts, Item identities, or counts
