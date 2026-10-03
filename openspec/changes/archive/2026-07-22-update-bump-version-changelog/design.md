---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

Currently, the `scripts/sync_version.py` automates the version bumping in `pyproject.toml`, `package.json`, etc., but leaves `CHANGELOG.md` untouched. Project rules require the changelog to receive an entry matching the bumped version. Missing this entry results in CI test failures, breaking the release pipeline and necessitating manual fixes.

## Goals / Non-Goals

**Goals:**

- Update `CHANGELOG.md` automatically during a `make bump-version` operation via the `scripts/sync_version.py`.
- Correctly format the new version header with a TBD date, e.g., `## [<new_version>] - TBD`.
- Insert the new header at the correct position (at the top of the version list).

**Non-Goals:**

- Automating the generation of changelog commit messages or extracting them from Git history (users will still manually add entries under the header if needed).
- Parsing or validating existing changelog contents beyond finding the correct insertion point.

## Decisions

- **Injection Logic in `scripts/sync_version.py`**: The logic will be added to `scripts/sync_version.py`, which is already the central authority for parsing and bumping the version text. We will add a function `update_changelog(new_version)` that gets called during the bump process.
- **Insertion Strategy**: The script will read `docs/CHANGELOG.md` and use a robust regular expression (e.g., `^## \[\d+\.\d+\.\d+\]`) to find the first version header. It will then insert the new version header (and placeholder sections like `### Added`, `### Changed`, `### Fixed`) directly above it.
- **Date Generation**: We will use a static `TBD` placeholder for the date instead of extracting the current date, as the exact release date is usually unknown at the time of version bump.

## Risks / Trade-offs

- **Risk: Varying `CHANGELOG.md` formats might confuse the script.**
  - **Mitigation**: Using a regex to match the exact start of the version list (`## [X.Y.Z]`) is robust for the Keep a Changelog format. If no such header is found, the script will append to the end or raise a clear error indicating the changelog format is unsupported.
