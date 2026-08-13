# rclone-subprocess-hardening Specification

## Purpose

Enforce POSIX end-of-options delimiter positioning for all rclone subprocess calls.

## Requirements

### Requirement: Rclone subprocess end-of-options delimiter

The system SHALL place a POSIX `--` end-of-options delimiter in all `subprocess.run()` calls to `rclone` to separate command flags from file path operands. All rclone options (e.g., `--s3-no-check-bucket`) MUST appear before the `--` delimiter, and all path arguments MUST appear after it.

#### Scenario: File path beginning with hyphen does not inject flags

- **WHEN** the system invokes `rclone copy` or `rclone copyto` with a file path argument that begins with a hyphen (e.g., `--config=/etc/passwd`)
- **THEN** rclone SHALL treat the argument as a literal file path operand, not as a command-line flag

#### Scenario: Normal backup upload preserves behavior

- **WHEN** the system uploads a backup file to Glacier via `rclone copy`
- **THEN** the subprocess call SHALL include `["rclone", "copy", "--s3-no-check-bucket", "--", file_path, target]` with the `--` delimiter separating flags from paths

#### Scenario: Cover image sync preserves behavior

- **WHEN** the system syncs a cover image to/from rclone remote via `rclone copyto`
- **THEN** the subprocess call SHALL include the `--` delimiter between flags and path arguments

### Requirement: Rclone configuration directory exists before container startup
The system SHALL create the host rclone configuration directory before Docker Compose starts services that mount it, preventing Docker from creating the mount source with incorrect ownership.

#### Scenario: Starting services without an existing rclone directory

- **WHEN** a user runs the Makefile `dev` or `start` target and `$(HOME)/.config/rclone` does not exist
- **THEN** the target SHALL create the directory before invoking Docker Compose or `run.sh`
- **AND** the directory SHALL be owned and writable by the invoking host user
