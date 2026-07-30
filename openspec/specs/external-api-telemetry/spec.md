# external-api-telemetry Specification

## Purpose
Specify outbound HTTP request header logging, sensitive token redaction, and user agent telemetry standards.
## Requirements
### Requirement: Capture Outbound HTTP Headers in Telemetry

The system SHALL capture and attach HTTP request headers to OpenTelemetry spans, AND emit them as structured logs, when making requests to external APIs (e.g., Allegro). All sensitive header values and URL query parameters MUST be redacted before recording.

#### Scenario: Capturing standard headers

- **WHEN** the backend makes an HTTP request to an external API (like Allegro)
- **THEN** it must add `http.request.header.user_agent` and `http.request.header.accept` to the active OpenTelemetry span AND emit a structured log containing these fields.

#### Scenario: Redacting sensitive headers

- **WHEN** the backend makes an HTTP request that includes an `Authorization` header
- **THEN** it must redact the header value (e.g., `***REDACTED***`) before attaching it as an attribute to the active OpenTelemetry span and structured log.

#### Scenario: Redacting cookie and session headers

- **WHEN** the backend makes an HTTP request that includes headers with names containing `cookie` or `session` (case-insensitive)
- **THEN** those header values MUST be replaced with `***REDACTED***` before attaching to the OpenTelemetry span or structured log

#### Scenario: Redacting sensitive URL query parameters

- **WHEN** the backend records telemetry for an outbound HTTP request whose URL contains query parameters with names matching any of: `key`, `token`, `secret`, `auth`, `signature`, `credential` (case-insensitive substring match)
- **THEN** the values of those query parameters MUST be replaced with `***REDACTED***` before attaching the URL to the OpenTelemetry span attribute or structured log
- **AND** non-sensitive query parameters (e.g., `page`, `limit`, `format`) SHALL be preserved verbatim

#### Scenario: Malformed URL fallback

- **WHEN** the URL provided to the sanitization function cannot be parsed
- **THEN** the system SHALL replace the entire URL with a safe sentinel value (e.g., `***REDACTED_URL_PARSE_ERROR***`) rather than logging the raw URL or raising an exception

### Requirement: Parameterized test coverage for telemetry sanitization

Backend pytest tests MUST validate the telemetry sanitization functions using parameterized test cases covering realistic header and URL patterns from all integrated external APIs.

#### Scenario: Header redaction covers API key patterns

- **WHEN** the test suite runs parameterized cases against `sanitize_headers`
- **THEN** it SHALL verify redaction for at least: `Authorization`, `X-API-KEY`, `x-amz-security-token`, `Cookie`, `Set-Cookie`, and `X-Session-ID`
- **AND** it SHALL verify that non-sensitive headers like `User-Agent`, `Accept`, and `Content-Type` are preserved verbatim

#### Scenario: URL sanitization covers presigned URL patterns

- **WHEN** the test suite runs parameterized cases against `sanitize_url`
- **THEN** it SHALL verify redaction for URLs containing `?api_key=`, `?X-Amz-Signature=`, `?token=`, and `?credential=`
- **AND** it SHALL verify that URLs with no sensitive parameters are returned unchanged

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
