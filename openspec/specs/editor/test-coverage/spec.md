# editor/test-coverage Specification

## Purpose

Provides comprehensive test coverage for the FRBR editor orchestrator dialog lifecycle (Add Child, Delete, Escalate), permission-based action gating, and TanStack Query hook optimistic cache synchronization with rollback — ensuring that the decomposed editor's state management and mutation flows are verified against regression.

## Requirements

### Requirement: Delete Dialog Lifecycle Verification
The system SHALL have test coverage verifying the complete Delete dialog lifecycle: opening the confirmation dialog, displaying cascade warning text appropriate to the entity level, confirming deletion, invoking the delete mutation, evicting the entity from the query cache, and shifting focus to the parent entity.

#### Scenario: Delete dialog full flow for a Work entity

- **WHEN** an authorized user clicks "Delete" on a Work node and confirms the deletion dialog
- **THEN** the system SHALL invoke `deleteEntity.mutateAsync` with the correct entity ID, close the dialog, and reset the active tab to the parent level

#### Scenario: Delete dialog cascade warning text for Work

- **WHEN** the Delete dialog is opened on a Work entity
- **THEN** the dialog SHALL display a warning mentioning "and all its expressions" to indicate cascading deletion

#### Scenario: Delete dialog cascade warning text for Expression

- **WHEN** the Delete dialog is opened on an Expression entity
- **THEN** the dialog SHALL display a warning mentioning "and all its manifestations"

#### Scenario: Delete dialog cascade warning text for Manifestation

- **WHEN** the Delete dialog is opened on a Manifestation entity
- **THEN** the dialog SHALL display a warning mentioning "and all its items"

#### Scenario: Delete dialog error handling

- **WHEN** the delete mutation rejects with an error
- **THEN** the system SHALL display an error toast notification and keep the dialog open for retry

### Requirement: Escalate Dialog Lifecycle Verification
The system SHALL have test coverage verifying the complete Escalate dialog lifecycle: opening the escalation dialog, entering a note, submitting via `useCreateEscalation`, and closing on success.

#### Scenario: Escalate dialog full flow

- **WHEN** a user opens the Escalate dialog, enters a note, and submits
- **THEN** the system SHALL invoke `createEscalation.mutateAsync` with the entity level, target ID, and note, then close the dialog

#### Scenario: Escalate dialog error handling

- **WHEN** the escalation mutation rejects
- **THEN** the system SHALL display an error toast and keep the dialog open

### Requirement: Multi-Tier Add Child Verification
The system SHALL have test coverage verifying that "Add Child" creates the correct child entity type for each parent tier: Work creates Expression, Expression creates Manifestation, Manifestation creates Item.

#### Scenario: Add Child on Work creates Expression

- **WHEN** an authorized user executes "Add Child" on a Work entity and submits the dialog
- **THEN** the system SHALL create a new Expression associated with the parent Work

#### Scenario: Add Child on Expression creates Manifestation

- **WHEN** an authorized user executes "Add Child" on an Expression entity and submits the dialog
- **THEN** the system SHALL create a new Manifestation associated with the parent Expression

#### Scenario: Add Child on Manifestation creates Item

- **WHEN** an authorized user executes "Add Child" on a Manifestation entity and submits the dialog
- **THEN** the system SHALL create a new Item associated with the parent Manifestation

#### Scenario: Add Child API error handling

- **WHEN** the child creation mutation fails
- **THEN** the system SHALL display an error toast and keep the dialog open

### Requirement: Manifestation Type Change Permission Branches
The system SHALL have test coverage verifying the permission-based branching logic when a user attempts to change a Manifestation's type without WRITE_METADATA permission.

#### Scenario: Type change with escalation request available

- **WHEN** a user without WRITE_METADATA permission changes a Manifestation's type AND the entity has an existing ESCALATE_REQUEST
- **THEN** the system SHALL invoke `createEscalation` instead of `updateEntity`

#### Scenario: Type change denied without escalation request

- **WHEN** a user without WRITE_METADATA permission changes a Manifestation's type AND no ESCALATE_REQUEST exists
- **THEN** the system SHALL display a "You do not have permission" error toast

### Requirement: Orchestrator Callback and Lifecycle Verification
The system SHALL have test coverage verifying the orchestrator's `onClose` callback invocation, retry button behavior, and dialog state reset on `onOpenChange`.

#### Scenario: onClose callback invocation

- **WHEN** the user clicks the close button in the editor header
- **THEN** the `onClose` callback prop SHALL be invoked

#### Scenario: Retry button refetches data

- **WHEN** the editor is in an error state and the user clicks "Retry"
- **THEN** the system SHALL call `refetch()` on the tree query

#### Scenario: Dialog state reset on backdrop close

- **WHEN** a dialog (Add Child, Delete, or Escalate) is dismissed via backdrop click or escape key
- **THEN** the system SHALL reset the dialog state to closed

### Requirement: FRBR Hook Optimistic Cache Update Verification
The system SHALL have test coverage verifying that FRBR TanStack Query hooks perform correct optimistic cache updates, rollback on error, and query invalidation on settlement.

#### Scenario: useUpdateFrbrEntity optimistic update for Work

- **WHEN** `useUpdateFrbrEntity` mutates a Work entity
- **THEN** the hook SHALL optimistically patch `tree.work` in the query cache before network confirmation

#### Scenario: useUpdateFrbrEntity optimistic update for Expression

- **WHEN** `useUpdateFrbrEntity` mutates an Expression entity
- **THEN** the hook SHALL optimistically patch the target expression in `tree.expressions`

#### Scenario: useUpdateFrbrEntity optimistic update for Manifestation

- **WHEN** `useUpdateFrbrEntity` mutates a Manifestation entity
- **THEN** the hook SHALL optimistically patch the target manifestation in the cache

#### Scenario: useUpdateFrbrEntity optimistic update for Item

- **WHEN** `useUpdateFrbrEntity` mutates an Item entity
- **THEN** the hook SHALL optimistically patch the target item in `tree.items`

#### Scenario: useUpdateFrbrEntity rollback on error

- **WHEN** the update mutation fails on the server
- **THEN** the hook SHALL revert the query cache to its pre-mutation snapshot

#### Scenario: useUpdateFrbrEntity cache invalidation on settled

- **WHEN** the update mutation settles (success or failure)
- **THEN** the hook SHALL invalidate the `frbrTree` query to reconcile with server state

#### Scenario: useAddFrbrChild successful creation

- **WHEN** `useAddFrbrChild` successfully creates a child entity
- **THEN** the hook SHALL invalidate the `frbrTree` query to refresh the hierarchy

#### Scenario: useAddFrbrChild API failure

- **WHEN** the API returns `success: false`
- **THEN** the hook SHALL throw an error

#### Scenario: useDeleteFrbrEntity optimistic removal of Work

- **WHEN** `useDeleteFrbrEntity` deletes a Work entity
- **THEN** the hook SHALL optimistically set `tree.work` to `null`

#### Scenario: useDeleteFrbrEntity optimistic removal of Item

- **WHEN** `useDeleteFrbrEntity` deletes an Item entity
- **THEN** the hook SHALL optimistically filter the item from `tree.items`

#### Scenario: useDeleteFrbrEntity rollback on error

- **WHEN** the delete mutation fails
- **THEN** the hook SHALL revert the query cache to its pre-mutation snapshot

### Requirement: useFrbrTree Hook Verification
The system SHALL have test coverage verifying that `useFrbrTree` correctly fetches, caches, and guards FRBR tree data.

#### Scenario: useFrbrTree fetches tree data

- **WHEN** `useFrbrTree` is called with a valid `manifestationId > 0`
- **THEN** the hook SHALL fetch the tree data and return it

#### Scenario: useFrbrTree disabled for invalid ID

- **WHEN** `useFrbrTree` is called with `manifestationId <= 0`
- **THEN** the hook SHALL NOT initiate a fetch (respects `enabled` guard)

#### Scenario: useFrbrTree error propagation

- **WHEN** the tree fetch fails
- **THEN** the hook SHALL propagate the error state to the consumer
