## ADDED Requirements

### Requirement: TSDoc comment restoration
The `CardWrapper` and `InstanceSettings` components in `instance-settings.tsx` SHALL have complete TSDoc block comments documenting their props, including newly added props (`saving`, `extraFooterContent`).

#### Scenario: Developer reads component documentation

- **WHEN** a developer opens `instance-settings.tsx`
- **THEN** both `CardWrapper` and `InstanceSettings` SHALL have TSDoc comments describing all current props

### Requirement: CHANGELOG release date finalization
The `docs/CHANGELOG.md` release header for v0.7.14 SHALL contain the actual release date instead of `TBD`.

#### Scenario: CHANGELOG header updated

- **WHEN** a user reads `docs/CHANGELOG.md`
- **THEN** the v0.7.14 header SHALL read `## [0.7.14] - 2026-08-08`

### Requirement: README version references accuracy
The root `README.md` system architecture section SHALL reference PostgreSQL 18 and Redis 8 to match the actual infrastructure versions used in this release.

#### Scenario: README matches current stack

- **WHEN** a user reads the system architecture overview in `README.md`
- **THEN** database and cache version references SHALL match PostgreSQL 18 and Redis 8
