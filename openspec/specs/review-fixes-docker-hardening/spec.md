## Purpose

Record the container-hardening fixes from the v0.8.x review: secrets are excluded from the Docker build context, and AI cover generation no longer uploads duplicate copies to remote storage.

## Requirements

### Requirement: Docker secret exclusion
The `.dockerignore` file SHALL explicitly exclude environment files (`.env`, `.env.*`), compose overrides (`docker-compose.override.yml`), and SSL/TLS private keys (`*.pem`, `*.key`, `*.crt`) to prevent secret leakage into Docker image layers.

#### Scenario: Docker build excludes secrets

- **WHEN** `docker build` is run with the project root as build context
- **THEN** no `.env`, `.env.*`, `*.pem`, `*.key`, or `*.crt` files SHALL be included in the build context

### Requirement: No duplicate rclone uploads in AI cover generation
The `save_image()` function in `llm_covers.py` SHALL NOT perform a redundant rclone push when `optimize_and_save_image()` already handles the rclone cache synchronization.

#### Scenario: AI cover generation with RCLONE_COVERS_REMOTE set

- **WHEN** an AI cover is generated and `RCLONE_COVERS_REMOTE` environment variable is set
- **THEN** exactly one rclone upload SHALL occur, not two
