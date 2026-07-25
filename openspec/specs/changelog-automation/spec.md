# changelog-automation Specification

## Purpose

TBD - created by archiving change update-bump-version-changelog. Update Purpose after archive.

## Requirements

### Requirement: Changelog Version Entry Automation

The `make bump-version` process SHALL automatically append a new unreleased version header to `CHANGELOG.md` when the version is successfully bumped.

#### Scenario: Running make bump-version bumps version and updates CHANGELOG

- **WHEN** a developer runs `make bump-version v=patch`
- **THEN** the `CHANGELOG.md` SHALL be updated to include a new section `## [<new-version>] - TBD` at the top of the version list.
