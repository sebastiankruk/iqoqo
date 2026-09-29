# rclone-subprocess-hardening Specification

## Purpose

Enforce POSIX end-of-options delimiter positioning for the `rclone` subprocess
calls that remain, and reject unsafe S3 object keys in place of the ones that
were removed.

Rescoped by `devops-infrastructure-updates`, which deleted every `rclone` call
from `app/`. The delimiter requirement still binds the **host-side** backup
scripts, which use the operator's own rclone install and can reach backends boto3
cannot. The in-application half is superseded by object-key validation in
`app/core/s3_service.py`, which removes the ambiguity rather than delimiting
around it.

## Requirements

### Requirement: Rclone subprocess end-of-options delimiter

The system SHALL place a POSIX `--` end-of-options delimiter in all `subprocess.run()` calls to `rclone` to separate command flags from file path operands. All rclone options (e.g., `--s3-no-check-bucket`) MUST appear before the `--` delimiter, and all path arguments MUST appear after it.

**Rescoped from `devops-infrastructure-updates`**, which removed every `rclone`
subprocess call from `app/`. The requirement previously applied to call sites in
`app/core/tasks.py`, `app/utils/images.py` and `app/utils/llm_covers.py`; those
now go through `app/core/s3_service.py`, which forks no process at all.

The requirement still binds where `rclone` is actually invoked: the host-side
backup scripts.

#### Scenario: File path beginning with hyphen does not inject flags

- **WHEN** a `rclone` invocation receives a file path argument that begins with a hyphen (e.g., `--config=/etc/passwd`)
- **THEN** rclone SHALL treat the argument as a literal file path operand, not as a command-line flag

#### Scenario: Normal backup upload preserves behavior

- **WHEN** the system uploads a backup file via `rclone copy`
- **THEN** the subprocess call SHALL include `["rclone", "copy", "--s3-no-check-bucket", "--", file_path, target]` with the `--` delimiter separating flags from paths

#### Scenario: Cover image sync preserves behavior

- **WHEN** a cover image is synced to or from a remote via `rclone copyto`
- **THEN** the subprocess call SHALL include the `--` delimiter between flags and path arguments

#### Scenario: In-application paths cannot inject an object key

- **WHEN** a cover or feedback filename is attacker-influenced
- **THEN** the S3 object key construction MUST **reject** a component containing a slash, a dot segment, a leading dash or a control character
- **AND** it MUST NOT rewrite the component into a different, apparently-valid key

The last scenario is the successor to the in-application cases this requirement
used to cover. A delimiter protects a command line; key validation removes the
ambiguity entirely, so a filename cannot select a different prefix or traverse
out of one.
