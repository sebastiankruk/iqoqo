## ADDED Requirements

### Requirement: Two-Stage Linear Alembic Migration Pipeline
The database migration pipeline MUST consist of a historical baseline migration representing the exact canonical state of release v0.7.17 (`v0_7_17_baseline`) and a linear incremental migration (`v0_7_18_fixes`) containing all schema modifications introduced in v0.7.18.

#### Scenario: Running migrations on a fresh empty database
- **WHEN** `flask db upgrade` executes on an empty database
- **THEN** Alembic executes `v0_7_17_baseline` to create the 0.7.17 schema
- **THEN** Alembic executes `v0_7_18_fixes` to apply 0.7.18 updates (`auth.token_blocklist.expires_at`, `config.instance_settings`, CheckConstraints)
- **THEN** the final database schema matches current application models with head `v0_7_18_fixes`

### Requirement: Automated Backward-Compatible Migration Bridge
The system MUST provide an automated migration bridge that detects legacy 0.7.17 production revisions (including `f65648a6aaf4`), stamps the database with `v0_7_17_baseline` without re-creating historical tables, and allows standard `flask db upgrade` to execute subsequent migration scripts.

#### Scenario: Upgrading an existing 0.7.17 production database
- **GIVEN** a database at revision `f65648a6aaf4`
- **WHEN** the container boots or `flask db upgrade` executes
- **THEN** the bridge detects `f65648a6aaf4` and stamps `v0_7_17_baseline`
- **THEN** Alembic executes `v0_7_18_fixes` to alter `auth.token_blocklist`, move `instance_settings` to `config`, and add check constraints
- **THEN** the database version advances to `v0_7_18_fixes` without requiring manual SQL fixes in cloning scripts
