## MODIFIED Requirements

### Requirement: Error Envelope Lifecycle

The shared daemon core SHALL write error envelopes atomically with size limits, using a temp-file-then-rename pattern, and SHALL sanitize and truncate error text to prevent disk exhaustion and information disclosure.

An error envelope SHALL carry the number of attempts made for that task. Writing an error envelope SHALL increment that count rather than refusing to overwrite, until a configurable retry budget is exhausted; once the budget is spent, further writes SHALL be refused and the existing terminal envelope preserved. Envelopes written before attempt counting existed SHALL be treated as having a single attempt, so they benefit from the retry budget rather than being stranded.

#### Scenario: First failure records attempt one

- **WHEN** a task fails for the first time
- **THEN** the system SHALL write an error envelope recording an attempt count of one

#### Scenario: Subsequent failures increment the attempt count

- **WHEN** a task fails again while its retry budget remains
- **THEN** the system SHALL overwrite the envelope with an incremented attempt count and the new error text

#### Scenario: Terminal error is frozen once the budget is spent

- **WHEN** a task fails after the retry budget is exhausted
- **THEN** the system SHALL NOT overwrite the existing envelope
- **AND** SHALL preserve the error text of the attempt that exhausted the budget

#### Scenario: Legacy envelopes count as a single attempt

- **WHEN** an error envelope exists with no attempt count field
- **THEN** the system SHALL treat it as a single attempt

#### Scenario: Invalid task identifiers are rejected

- **WHEN** a task identifier fails validation
- **THEN** the system SHALL NOT write an error envelope
- **AND** SHALL report the invalid identifier without disclosing path details

## ADDED Requirements

### Requirement: Retry-Aware Task Completion Gate

The shared daemon core SHALL determine task completion from the presence of a valid answer envelope, or from a failure marker whose retry budget is exhausted. A failure marker within an unexhausted budget SHALL NOT mark the task done, so that transient failures are retried on a later run.

A task SHALL be retried across runs only up to the configured budget, so that a permanently failing task does not consume unbounded resources.

#### Scenario: Answered task is done

- **WHEN** both an answer envelope and a done sentinel exist for a task
- **THEN** the system SHALL report the task as done

#### Scenario: Transient failure is not done

- **WHEN** a task has a failure marker with an attempt count below the retry budget and no answer
- **THEN** the system SHALL report the task as not done
- **AND** a subsequent agent run SHALL attempt it again

#### Scenario: Exhausted budget is terminal

- **WHEN** a task has a failure marker whose attempt count has reached the retry budget and no answer
- **THEN** the system SHALL report the task as done
- **AND** the system SHALL NOT attempt it again

#### Scenario: Answer takes precedence over a failure marker

- **WHEN** a task has both a valid answer envelope and a failure marker within budget
- **THEN** the system SHALL report the task as done

#### Scenario: Retry budget is configurable

- **WHEN** the retry budget is configured to a different value
- **THEN** the system SHALL use that value as the number of attempts after which a failure becomes terminal

### Requirement: Successful Recovery Clears Failure Record

When a task that previously failed is subsequently answered, the system SHALL remove its failure marker as part of writing the answer, so that the outbox does not simultaneously report a task as both failed and complete.

#### Scenario: Recovered task no longer advertises a failure

- **WHEN** a task with an existing failure marker is answered successfully
- **THEN** the system SHALL remove the failure marker
- **AND** SHALL report the task as done
