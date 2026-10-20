## ADDED Requirements

### Requirement: Follower Relation Unique Constraint
The database SHALL enforce a composite unique constraint on `FederationFollower(local_user_id, remote_actor_id)` to prevent race conditions and duplicate follower records.

#### Scenario: Duplicate follow delivery does not create duplicate follower row
- **WHEN** concurrent or duplicate Follow activities for the same target user and remote actor are processed
- **THEN** the database enforces uniqueness without creating duplicate rows in `federation.followers`.

### Requirement: User Visibility Check Constraint Migration
The Alembic migration lineage SHALL include explicit database-level check constraints enforcing permitted values for `default_item_visibility`.

#### Scenario: Migration enforces permitted visibility values
- **WHEN** database migrations are executed
- **THEN** a check constraint ensures `default_item_visibility` is either 'private' or 'public'.
