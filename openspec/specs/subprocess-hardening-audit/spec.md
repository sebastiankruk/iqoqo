# subprocess-hardening-audit Specification

## Purpose

Prevent command option injection in rclone subprocess calls by requiring the POSIX `--` end-of-options delimiter before user-controlled path arguments, and provide comprehensive pytest coverage validating the hardening.

## Requirements

### Requirement: All rclone subprocess calls include POSIX end-of-options delimiter

The system SHALL include a `--` (double-dash) POSIX end-of-options delimiter in every `subprocess.run(["rclone", ...])` invocation, placed immediately before any user-controlled path arguments, to prevent command option injection via crafted filenames.

#### Scenario: rclone copy with user-provided file path

- **WHEN** a backup task invokes `subprocess.run(["rclone", "copy", ...])` with a file path derived from user input or database content
- **THEN** the argument list MUST contain `"--"` before the file path argument

#### Scenario: rclone copyto with cover filename

- **WHEN** the cover upload or LLM cover cache check invokes `subprocess.run(["rclone", "copyto", ...])` with a filename
- **THEN** the argument list MUST contain `"--"` before both the source and target path arguments

#### Scenario: Malicious filename with leading dashes

- **WHEN** a file path contains leading dashes (e.g., `--config=/etc/shadow`)
- **THEN** the `--` delimiter SHALL prevent `rclone` from interpreting the path as a command-line option

### Requirement: Comprehensive test coverage for subprocess hardening

The system SHALL have pytest test cases validating the presence of `--` delimiter in all rclone subprocess calls.

#### Scenario: Test verifies delimiter presence in tasks.py

- **WHEN** running `tests/test_subprocess_hardening.py`
- **THEN** tests SHALL assert that `subprocess.run` calls in `app/core/tasks.py` include `"--"` in the argument list before path arguments

#### Scenario: Test verifies delimiter presence in images.py

- **WHEN** running `tests/test_subprocess_hardening.py`
- **THEN** tests SHALL assert that `subprocess.run` calls in `app/utils/images.py` include `"--"` in the argument list before path arguments

#### Scenario: Test verifies delimiter presence in llm_covers.py

- **WHEN** running `tests/test_subprocess_hardening.py`
- **THEN** tests SHALL assert that `subprocess.run` calls in `app/utils/llm_covers.py` include `"--"` in the argument list before path arguments
