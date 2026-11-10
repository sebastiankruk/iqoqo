## Why

Self-hosting `iqoqo` currently requires manually copying `.env.example`, generating cryptographic secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, PostgreSQL/Redis passwords, RSA-2048 federation keys), and running separate Docker Compose and status commands. A CI-built interactive CLI installer with pre-sync/preview readiness verification (`iqopresync`) lowers onboarding friction for home-lab builders to a single guided command while enforcing zero-trust secret generation and production safeguards.

## What Changes

- **Interactive CLI Installer & Config Generator (`scripts/iqoqo-installer.py` / `iqoqo-install`):** Build a self-contained CLI installer (packaged in CI) that prompts interactively (or accepts non-interactive flags) for core deployment variables (domain/hostname, stack mode `prod | preview | federation_head`, admin email, optional S3 backup and OAuth/lookup keys), auto-generates cryptographically strong `SECRET_KEY`, `JWT_SECRET_KEY`, and DB/Redis credentials with `0600` file permissions, and initializes `.env`.
- **`iqopresync` & Preview / Stack Readiness Check (`--check` / `iqopresync`):** Include a built-in pre-flight and post-deploy verification mode (`iqopresync` / `--preview-check`) that validates Docker/Compose availability, port collisions, linear Alembic migration head parity, `/api/health`, `/api/system/status`, and ActivityPub WebFinger/NodeInfo reachability before declaring the node ready.
- **GitHub Actions CI Artifact Packaging:** Add a CI build step packaging the standalone installer script/binary and checksums (`sha256sum`) on release tags (`v1.*`) alongside `Makefile` target `make install-wizard`.

## Capabilities

### New Capabilities
- `cli-installer-and-presync-check`: Interactive and non-interactive CLI installer for `iqoqo` with cryptographic secret generation, `.env` hardening, and `iqopresync` preview/production readiness verification.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- **Scripts & CLI:** `scripts/iqoqo_installer.py`, `scripts/iqoqo-status.sh`, `Makefile` (`make install-wizard`, `make presync-check`)
- **CI/CD & Docs:** `.github/workflows/release-installer.yml` (or `ci.yml`), `docs/INSTALL.md`
- **Tests:** `tests/scripts/test_iqoqo_installer.py`, `tests/bash/iqoqo_installer.bats`
