## ADDED Requirements

### Requirement: Outbound User-Agent reports the real deployed version

The system SHALL build the Allegro User-Agent header as `<ALLEGRO_APP_NAME>/<version> (+https://iqoqo.cc)`, where the application-name prefix SHALL be taken from the `ALLEGRO_APP_NAME` environment configuration (per-environment values such as `iqoqo_cc`, `iqoqo_pre`, `iqoqo_dev`) and MUST NOT be hardcoded, and `<version>` is the actual deployed release version. On a production deployment, the resolved version SHALL NEVER be a development sentinel such as `dev`, `dev-local`, or an empty string.

#### Scenario: Production User-Agent carries the release version

- **WHEN** the backend makes an outbound request to the Allegro API from a production deployment
- **THEN** the `User-Agent` header SHALL match the pattern `<ALLEGRO_APP_NAME>/<semver> (+https://iqoqo.cc)` where the prefix equals the configured `ALLEGRO_APP_NAME` and `<semver>` equals the deployed release version (e.g. `iqoqo_cc/0.7.13 (+https://iqoqo.cc)`)

#### Scenario: Deployment fails fast on unresolved version

- **WHEN** the application starts in a production environment without a resolvable non-development version
- **THEN** a startup/health validation SHALL surface the misconfiguration so it is caught before vendor traffic is sent with a `/dev`-flavored User-Agent

### Requirement: Deployed version is baked into the runtime environment

The deployment pipeline SHALL inject the release version into the runtime environment (e.g. `APP_VERSION` build-time argument promoted to an environment variable), sourced from the single version of record (`pyproject.toml` / repo `VERSION`), so `Config.VERSION` resolves correctly without relying on repository files being present in the image.

#### Scenario: Container resolves version without pyproject.toml

- **WHEN** the production container runs without `pyproject.toml` present in the filesystem
- **THEN** `Config.VERSION` SHALL still resolve to the baked release version from the environment
