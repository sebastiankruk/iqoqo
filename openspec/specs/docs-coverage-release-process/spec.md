## Requirements

### Requirement: Release process documents OpenSpec workflow

The RELEASE_PROCESS.md SHALL document the OpenSpec-based change proposal and implementation workflow as part of the standard release cycle, including `openspec new change`, `openspec-apply-change`, and `openspec-archive-change` commands.

#### Scenario: Developer reads about creating a release

- **WHEN** a developer follows the release process guide
- **THEN** they SHALL see instructions for using OpenSpec to propose, implement, and archive changes as tracked work items within the release branch

### Requirement: Release process documents multi-agent review

The RELEASE_PROCESS.md SHALL document the tribal matrix review step where PRs undergo automated multi-persona review (Ontologist, Security, DevOps, QA, TechComm, Code Quality) before merge approval.

#### Scenario: Release manager prepares a PR for merge

- **WHEN** a release manager reaches the review step
- **THEN** they SHALL see a documented process for triggering tribal matrix review and interpreting review verdicts

### Requirement: Release process documents mempalace synchronization

The RELEASE_PROCESS.md SHALL document the `make mempalace-index` (or `python3 .agents/skills/iqoqo-mempalace/scripts/run_mine.py`) step that synchronizes release artifacts, architectural decisions, codebase, and implementation notes into the long-term memory graph after each release merge.

#### Scenario: Release is merged to main

- **WHEN** a release branch is merged to main
- **THEN** the documented process SHALL include a step to run mempalace indexing to persist documentation, codebase, and architectural decisions

### Requirement: Release process includes pre-release checklist

The RELEASE_PROCESS.md SHALL include a pre-release checklist covering: roadmap task completion verification, CHANGELOG finalization, version bumps in pyproject.toml and package.json, documentation currency check, and spec synchronization (openspec sync-specs).

#### Scenario: Release manager prepares final release

- **WHEN** all features for a release are implemented
- **THEN** the documented process SHALL include a checklist item to verify documentation is up to date with all merged changes
