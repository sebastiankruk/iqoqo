## ADDED Requirements

### Requirement: Rclone configuration directory exists before container startup
The system SHALL create the host rclone configuration directory before Docker Compose starts services that mount it, preventing Docker from creating the mount source with incorrect ownership.

#### Scenario: Starting services without an existing rclone directory

- **WHEN** a user runs the Makefile `dev` or `start` target and `$(HOME)/.config/rclone` does not exist
- **THEN** the target SHALL create the directory before invoking Docker Compose or `run.sh`
- **AND** the directory SHALL be owned and writable by the invoking host user
