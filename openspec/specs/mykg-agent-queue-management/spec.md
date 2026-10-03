# mykg-agent-queue-management Specification

## Purpose

Defines the lifecycle of the myKG agent task queue: how tasks flow from the extraction producer to the sandboxed LLM consumer, how the queue is drained before the sandbox is torn down, how failed tasks are re-queued for another attempt, and how queue state is made observable. The intent is that no task is ever abandoned, retried forever, or lost without a durable record — because a silently dropped task is indistinguishable from a task that was never needed, and the resulting knowledge graph is quietly incomplete.

## Requirements

### Requirement: Bounded Queue Drain Before Sandbox Teardown
The sync pipeline SHALL wait for the agent task queue to reach zero unfinished tasks before removing the agent daemon container, so that tasks accepted but not yet processed are completed rather than abandoned mid-flight.

A task is considered unfinished while it has neither an answer envelope nor a spent retry budget. The wait SHALL be bounded by a configurable timeout, SHALL report outstanding task count at intervals while waiting, and on timeout SHALL exit successfully while printing the outstanding count and the command needed to continue.

#### Scenario: Pending tasks are completed rather than abandoned

- **WHEN** the extraction producer finishes while agent tasks remain unfinished in the inbox
- **THEN** the pipeline SHALL keep the agent daemon running until those tasks produce an answer or exhaust their retry budget
- **AND** SHALL NOT remove the daemon container while unfinished tasks exist

#### Scenario: Drain timeout is bounded and reported

- **WHEN** tasks remain unfinished for longer than the configured drain timeout
- **THEN** the pipeline SHALL stop waiting and print the outstanding task count
- **AND** SHALL print the command to re-run to continue processing
- **AND** SHALL NOT report the run as failed solely because of the timeout

#### Scenario: Drain can be disabled

- **WHEN** drain is explicitly disabled
- **THEN** the pipeline SHALL remove the daemon container immediately after the producer returns, preserving the previous behaviour

#### Scenario: No daemon means no drain wait

- **WHEN** no agent daemon container is running
- **THEN** the pipeline SHALL NOT wait for the queue to drain

### Requirement: Failed Task Re-queueing
The system SHALL provide an operation that makes previously failed tasks eligible for another attempt, without requiring the original source content to be re-derived.

Re-queueing SHALL move failure markers out of the agent outbox into a quarantine location inside the session rather than deleting them, so that a re-queue is reversible and auditable. The operation SHALL classify each failure before acting and SHALL only clear markers for tasks that can actually be retried.

#### Scenario: Transient failures become eligible again

- **WHEN** a task previously failed and its task payload is still present in the inbox
- **THEN** the re-queue operation SHALL remove its failure marker from the outbox
- **AND** the task SHALL be reported as no longer done
- **AND** the next agent run SHALL attempt it again

#### Scenario: Re-queueing is reversible

- **WHEN** a task is re-queued
- **THEN** its failure marker SHALL be preserved under a session-scoped quarantine directory
- **AND** the operation SHALL print the quarantine path so the marker can be restored

#### Scenario: Stale and unrecoverable failures are not cleared

- **WHEN** a task has a failure marker but already has a valid answer
- **THEN** the operation SHALL leave its marker in place and report it separately
- **WHEN** a task has a failure marker and its payload is absent from the inbox
- **THEN** the operation SHALL leave its marker in place and report it as unrecoverable

#### Scenario: Inspection without mutation

- **WHEN** the re-queue operation is invoked in inspection mode
- **THEN** it SHALL report the classification of every failure
- **AND** SHALL NOT modify any file

#### Scenario: Clean session is a no-op

- **WHEN** the session has no failure markers
- **THEN** the operation SHALL report that there is nothing to retry
- **AND** SHALL NOT fail

### Requirement: Session Discovery Through Symlinked Storage
Queue operations SHALL resolve the session store through a symlink when the store is a symlink to shared or synced storage, and SHALL fall back to the alternate store name only when the primary path is absent.

#### Scenario: Symlinked session store is followed

- **WHEN** the session store path is a symlink to an existing directory containing sessions
- **THEN** the operation SHALL enumerate sessions through the symlink

#### Scenario: Missing session is reported

- **WHEN** a specific session is requested that does not exist
- **THEN** the operation SHALL report that no such session was found
- **AND** SHALL NOT silently fall back to a different session
