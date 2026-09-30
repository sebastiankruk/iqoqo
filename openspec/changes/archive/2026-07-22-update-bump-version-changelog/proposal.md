---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

Currently, running `make bump-version` updates the version in files like `pyproject.toml` and `package.json`, but does not enforce or automatically add a version entry to `CHANGELOG.md`. This often results in CI test failures because the `CHANGELOG.md` lacks an entry for the newly bumped version, disrupting the release workflow and requiring manual intervention. We need to ensure that the changelog receives a new version entry when bumping the version.

## What Changes

- Update `scripts/sync_version.py` (which powers `make bump-version`) to append a new version entry template to `docs/CHANGELOG.md`.
- Specifically, when bumping the version, the script should detect the new version and write a header for it (e.g. `## [NEW_VERSION] - YYYY-MM-DD`) at the top of the versions section in `CHANGELOG.md`.

## Capabilities

### New Capabilities

- `changelog-automation`: Automates adding a new version header to `CHANGELOG.md` upon version bump.

### Modified Capabilities

## Impact

- `scripts/sync_version.py` will be modified.
- `docs/CHANGELOG.md` will be updated automatically during version bumps.
