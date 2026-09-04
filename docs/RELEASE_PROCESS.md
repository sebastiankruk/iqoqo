# iqoqo Release Process

We use an automated release process tied to GitHub Actions, supported by OpenSpec change tracking and multi-persona AI quality assurance.

## Development Workflow & OpenSpec Integration

Before creating a release, all major features, refactorings, and bug fixes follow the OpenSpec specification-driven development cycle:

1. **Propose Change**: Create a tracked change using `npx openspec new change "<change-name>" --schema spec-driven` (or the `/opsx-propose` skill).
2. **Implement & Verify**: Apply tasks using `npx openspec instructions apply` (or `/opsx-apply`), write unit and integration tests, and ensure local test suite passes (`make test`).
3. **Archive Change**: Sync delta specs to canonical main specs (`npx openspec sync-specs`) and archive completed changes (`npx openspec archive`).

## Pre-Release Checklist

Before branching a release, complete the following verification steps:

- [ ] **Roadmap Verification**: Verify all target version tasks in `.context/notes/🚧 iqoqo roadmap.md` are completed.
- [ ] **Documentation Currency Check**: Verify `docs/ARCHITECTURE.md`, `docs/CONTRIBUTING.md`, and `docs/INSTALL.md` reflect all new capabilities.
- [ ] **Spec Synchronization**: Ensure all active OpenSpec changes have synced their delta specs to `openspec/specs/`.
- [ ] **CHANGELOG Finalization**: Finalize the version section in `docs/CHANGELOG.md` with the release date (`## [x.y.z] - YYYY-MM-DD`).
- [ ] **Version Bumps**: Synchronize `version` strings in `pyproject.toml` and `frontend/package.json`.
- [ ] **Pre-Release Docker Image Validation**: Build local container images and verify the prebuilt deployment in a test environment (e.g., `/opt/pre.iqoqo`) before merging to `main`:

  ```bash
  # 1. Build backend, frontend, and nginx images locally with preview tag:
  make docker-build-preview
  # (or: ./scripts/build_docker_images.sh --tag <version>)

  # 2. Test launch in isolated preview directory:
  cd /opt/pre.iqoqo
  COMPOSE_PROJECT_NAME=iqoqo-preview APP_VERSION=preview docker compose --env-file .env -f docker-compose.prebuilt.yml up -d

  # 3. Clone production database and media assets if verifying production parity:
  make clone src_host=user@remote-ip src_loc=/opt/iqoqo.cc src_name=prod dst_loc=/opt/pre.iqoqo dst_name=preview

  # 4. Verify health:
  make status STACK=preview
  ```

## How to Create a New Release

1. **Create a Release Branch**: Branch off from `main` (e.g., `git checkout -b release/0.7.11`).
2. **Update Versions & Changelog**:
   - Update `pyproject.toml` and `frontend/package.json`.
   - Update `docs/CHANGELOG.md` date header.
3. **Automated Multi-Agent Tribal Matrix Review**:
   Before submitting the PR, execute or verify automated reviews across the core domain personas:
   - **Ontologist Expert**: Validates FRBR tier alignment (Work -> Expression -> Manifestation -> Item).
   - **Security Auditor**: Checks authentication decorators (`@require_auth`, `@require_physical_item`), RBAC permissions, and inputs.
   - **DevOps/SRE Expert**: Checks Docker build specs, database migrations, and background jobs context safety.
   - **Test Craftsman / QA**: Ensures unit, integration, and E2E coverage.
   - **TechComm Specialist**: Validates documentation currency, ATX markdown syntax, and code block tags.
   - **Code Quality / Linter**: Runs `make lint-python` and `make lint-js`.
4. **Commit and Push**: `git commit -am "chore(release): prep release v0.7.11"` and push the branch.
5. **Create & Merge Pull Request**: Open a PR from `release/0.7.11` into `main`. Once approved and merged, GitHub Actions will trigger image builds and release tagging.
6. **Memory Graph Synchronization**:
   After the release PR is merged into `main`, sync architectural decisions and release notes to the persistent memory graph:

   ```bash
   make mempalace-index
   # or: python3 .agents/skills/iqoqo-mempalace/scripts/run_mine.py
   ```

Upon PR merge to `main`, GitHub Actions automatically:

- Reads the version from `pyproject.toml`.
- Extracts the release notes from `docs/CHANGELOG.md`.
- Builds and pushes `iqoqo-backend`, `iqoqo-frontend`, and `iqoqo-nginx` images to GHCR.
- Creates the Git Tag (e.g., `v0.7.11`) and formal GitHub Release.
