# OpenSpec Specification: PR-258 Review Fixes

## Purpose

This specification defines the hardening, security, and ontology fixes applied following code review of PR #258.

## Requirements

### Requirement: Feedback Endpoint Access Control
The feedback screenshot endpoint SHALL require the authenticated caller to have ownership or administrative privileges over the feedback item associated with the requested screenshot.

#### Scenario: Unauthorized Access Attempt

- **WHEN** a user requests a screenshot belonging to another user's feedback ticket
- **THEN** the API returns a 403 Forbidden or 404 Not Found error

### Requirement: Database Migration Dialect Safety
All PostgreSQL-specific schema modifications in Alembic migrations SHALL be conditionally executed only when the active database dialect is PostgreSQL.

#### Scenario: Running Migrations on SQLite

- **WHEN** the `f65648a6aaf4_add_feedback_comments_schema.py` migration is executed against a SQLite database
- **THEN** the migration completes successfully without executing unsupported DDL statements

### Requirement: Subprocess Argument Hardening
All subprocess executions involving user-provided or external paths SHALL use the POSIX `--` delimiter to prevent argument injection.

#### Scenario: Generating Images with rclone

- **WHEN** the system invokes rclone via subprocess to process image files
- **THEN** the command array includes `--` preceding the file paths

### Requirement: N+1 Prevention on Feedback Comments
The FeedbackItem model SHALL efficiently load its comments count without executing a separate count query per item during serialization.

#### Scenario: Serializing Feedback Items List

- **WHEN** multiple feedback items are retrieved and serialized to a dictionary
- **THEN** the number of database queries remains constant or scales reasonably (O(1) relation loading via selectin)

### Requirement: Rclone Container Initialization
The Docker entrypoint SHALL configure the rclone directory structure with secure permissions before launching the main application.

#### Scenario: Starting the Container

- **WHEN** the docker-entrypoint.sh script executes
- **THEN** the `${HOME}/.config/rclone` directory is created with `0700` permissions and config files are created with `0600` permissions

### Requirement: Ontology Model Updates
The ontology files SHALL define the `boardgame_mechanics` mappings and `social.feedback_comments` graph mappings as specified in the review.

#### Scenario: Validating the Ontology

- **WHEN** the `iqoqo.ttl` and `iqoqo-shapes.ttl` files are parsed
- **THEN** they contain valid skos:Concept and iqoqo:has_mechanic definitions for boardgames, and sioc:Post/sioc:Thread mappings for feedback comments
