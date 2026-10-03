## Purpose

Rescopes the `rclone` requirements that `devops-infrastructure-updates`
invalidated. The in-application callers are gone; the host-side callers are not.

**Host-side** `rclone` is unaffected and still supported: `scripts/cloud_backup.sh`,
`cloud_backup_cron.sh` and `cloud_backup_check.sh` run on the operator's machine
and use the operator's own rclone install, because rclone reaches B2, Google
Drive, Dropbox and SFTP which boto3 does not. Only the in-container callers moved
to `app/core/s3_service.py`.

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Rclone configuration directory exists before container startup

Removed. `run.sh` no longer creates `${HOME}/.config/rclone` before starting the
stack, because nothing in the stack mounts a config directory any more.

The block previously manufactured an **empty** `rclone.conf`, which Docker turns
into a *directory* on hosts where the file is missing, breaking the container
restart it was meant to protect. The operator's own `~/.config/rclone/rclone.conf`
is untouched: the host backup scripts still read it.

#### Scenario: Starting the stack without a rclone directory

- **WHEN** a user runs `make dev`, `make start` or `./run.sh` and `$(HOME)/.config/rclone` does not exist
- **THEN** the target SHALL NOT create it
- **AND** the stack SHALL start without a mount-source error

#### Scenario: Host-side rclone configuration still works

- **WHEN** an operator has configured `~/.config/rclone/rclone.conf` for their own use
- **THEN** `scripts/cloud_backup.sh` SHALL continue to read it
- **AND** no container SHALL receive it
