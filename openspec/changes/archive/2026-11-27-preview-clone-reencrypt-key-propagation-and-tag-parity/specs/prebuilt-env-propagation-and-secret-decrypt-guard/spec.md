## MODIFIED Requirements

### Requirement: Prebuilt Deployments Propagate ENV_FILE

The Makefile prebuilt `start` target SHALL pass `ENV_FILE=$(COMPOSE_ENV_FILE)` to both `docker compose pull` and `up -d`, so `${ENV_FILE:-.env}` in compose resolves to the same file used for interpolation, SHALL preserve the default `ghcr.io/sebastiankruk/` `IMAGE_PREFIX` even if the active `.env` file declares an empty `IMAGE_PREFIX=`, and SHALL ensure `web` and `worker` receive `APP_VERSION` (default `prod`). For `preview` prebuilt deployments (`make start preview prebuilt` / `make preview start prebuilt`), the target SHALL additionally align with `make preview-up` / `make preview-reconcile` by resolving both relative and absolute `COMPOSE_ENV_FILE` paths safely (never double-prefixing `$(CURDIR)/$(COMPOSE_ENV_FILE)` when `COMPOSE_ENV_FILE` is absolute), tightening env permissions to `0600` without causing container `UID 10001` (`appuser`) bind-mount `PermissionError` failures, pre-starting `docker-compose.monitoring.yml` before RUM token provisioning when `OTEL_TRACES_EXPORTER != none`, resolving optional `SRC_SECRET_KEY` or `SRC_LOC` (`SRC_NAME` defaulting to `prod`, optional `SRC_HOST`) in pure POSIX shell when `SKIP_CLONE != 1`, streaming any resolved source `SECRET_KEY` as a framed `__IQOQO_SRC_SECRET_KEY__=` header ahead of `$(ABS_COMPOSE_ENV_FILE)` via shell builtin `printf` over stdin into container-executed `reconcile_preview_settings.py --dotenv-stdin` without `2>/dev/null` stderr suppression or host `python`/`python3`/`node`/`npm` invocations, passing `OPENOBSERVE_RUM_CLIENT_TOKEN`, `OPENOBSERVE_RUM_SITE`, and `OPENOBSERVE_RUM_INSECURE_HTTP` to `frontend`, and force-recreating `web` and `worker` (`docker compose ... up -d --force-recreate --no-deps web worker`) after reconciliation.

#### Scenario: Production env file used by services

- **GIVEN** `COMPOSE_ENV_FILE=.env.prod`
- **WHEN** `make prebuilt prod start` is invoked
- **THEN** both the `pull` and `up -d` commands MUST carry `ENV_FILE=.env.prod`.

#### Scenario: Default unchanged

- **GIVEN** no production env file selected
- **WHEN** a prebuilt target is invoked
- **THEN** `.env` MUST be used.

#### Scenario: Empty IMAGE_PREFIX in env file does not strip GHCR registry prefix

- **GIVEN** `.env.preview` contains `IMAGE_PREFIX=` (empty value) and no explicit `IMAGE_PREFIX` is exported by the caller
- **WHEN** `docker compose -f docker-compose.prebuilt.yml` resolves service image names during `make start preview prebuilt` or `make preview-up`
- **THEN** images MUST resolve with `ghcr.io/sebastiankruk/` (e.g., `ghcr.io/sebastiankruk/iqoqo-backend:<tag>`) rather than an unprefixed local image name.

#### Scenario: Prebuilt preview start reconciles secrets and RUM without requiring host Python or Node

- **GIVEN** a host without `python`, `python3`, `node`, or `npm` on `PATH` and a `.env.preview` file configuring preview origins and `SECRET_KEY`
- **WHEN** `make preview start prebuilt` executes
- **THEN** it MUST complete without invoking host `python`/`python3`/`node`/`npm`, enforce `0600` on `.env.preview`, pre-start monitoring and inject `OPENOBSERVE_RUM_*` into `frontend`, and run container-side `InstanceSettings` / OpenObserve reconciliation against `.env.preview`.

#### Scenario: Prebuilt preview start succeeds with 0600 env file and absolute COMPOSE_ENV_FILE path

- **GIVEN** `COMPOSE_ENV_FILE=/opt/preview.iqoqo/.env` (an absolute path) owned by host `root` or deploy user with mode `0600`
- **WHEN** `make start preview prebuilt COMPOSE_ENV_FILE=/opt/preview.iqoqo/.env` runs
- **THEN** secret verification/generation MUST NOT fail with container `UID 10001` `PermissionError` or a doubled `$(CURDIR)/$(COMPOSE_ENV_FILE)` path, and `preview-reconcile` MUST execute after service startup to synchronize `InstanceSettings` and OpenObserve credentials.

#### Scenario: Prebuilt preview start with SRC_LOC re-encrypts cloned settings without host Python

- **GIVEN** a host without `python`, `python3`, `node`, or `npm` on `PATH`, a cloned preview database, and `SRC_LOC=/opt/iqoqo` (`SRC_NAME=prod`)
- **WHEN** `make start preview prebuilt SRC_LOC=/opt/iqoqo` runs
- **THEN** it MUST extract source `SECRET_KEY` using pure shell, stream `__IQOQO_SRC_SECRET_KEY__=` + `$(ABS_COMPOSE_ENV_FILE)` via builtin `printf` to container-side `reconcile_preview_settings.py --dotenv-stdin`, re-encrypt cloned rows without exposing source `SECRET_KEY` in `argv` or container env, and force-recreate `web` and `worker`.

#### Scenario: Reconciliation stderr remains visible during prebuilt preview start

- **GIVEN** `make start preview prebuilt` invokes `reconcile_preview_settings.py --dotenv-stdin`
- **WHEN** reconciliation encounters a warning or error
- **THEN** stderr MUST NOT be suppressed with `2>/dev/null` so container diagnostics reach the deploy log.
