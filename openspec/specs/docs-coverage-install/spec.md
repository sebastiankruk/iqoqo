## Requirements

### Requirement: Installation guide documents format mappings setup

The INSTALL.md SHALL document the `shared/format_mappings.yaml` configuration file, explaining that it is git-tracked, per-instance, and controls how non-canonical physical kind values from external APIs are mapped to canonical MediaFormat identifiers.

#### Scenario: Instance admin configures format normalization

- **WHEN** an instance admin reads the configuration section
- **THEN** they SHALL find documentation of format_mappings.yaml with commented examples showing how to map non-canonical values

### Requirement: Installation guide documents fix-physical-kinds command

The INSTALL.md SHALL document the `make fix-physical-kinds` command with its modes (audit, interactive mapping, apply) and the `--dry-run` flag for previewing SQL changes before execution.

#### Scenario: Instance admin needs to fix non-canonical formats

- **WHEN** an instance admin discovers non-canonical format values in their database
- **THEN** they SHALL find documented steps to audit, map, and apply format fixes using the fix-physical-kinds CLI

### Requirement: Installation guide reflects current version requirements

The INSTALL.md SHALL document that Python 3.14+ is required (reflecting the current `pyproject.toml` and Dockerfile `python:3.14-slim` base image) and Node.js 20+ is required for the frontend.

#### Scenario: New developer sets up environment

- **WHEN** a new developer reads the Prerequisites section
- **THEN** they SHALL see Python 3.14+ and Node.js 20+ as the documented requirements
