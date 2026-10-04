# observability/rum-token-hardening Specification

## Purpose
Security and correctness requirements for the deployment-time provisioning of
the per-instance OpenObserve RUM client token. The provisioning path already
ships in `run.sh`; these requirements govern how the credential it creates is
emitted, persisted, and handed to the browser, and require RUM to keep working
in both topologies the project ships.

## Requirements

### Requirement: The RUM Client Token Is Never Emitted As A Value
The provisioning step MUST report its outcome and MUST NOT print, log, or echo the token value on any path, including success.

#### Scenario: Token is freshly provisioned

- **WHEN** the management endpoint returns a client token
- **THEN** the step reports that provisioning succeeded, without the value
- **THEN** the value appears in no file other than process memory

#### Scenario: Provisioning is re-run and the token is unchanged

- **WHEN** the endpoint returns the existing token
- **THEN** the step reports that the existing token was reused, without the value

#### Scenario: An error occurs while handling the token

- **WHEN** any failure occurs after the token has been read into a variable
- **THEN** no diagnostic, exception message, or traceback contains the token
- **THEN** a regression test asserts a sentinel token never appears in captured output

#### Scenario: A partial fingerprint is not acceptable either

- **WHEN** the step reports on a token it holds
- **THEN** it MUST NOT emit any prefix, length, or truncated hash of the value
- **THEN** the provisioned-or-reused state MUST be derived from a boolean comparison only

### Requirement: The Token Is Not Persisted Into Any File
The provisioning step MUST NOT write the token to an env file, and MUST NOT create any copy containing one.

#### Scenario: Provisioning completes

- **WHEN** the token is provisioned or reused
- **THEN** the step exports it for the current process only
- **THEN** it MUST NOT append the value to `.env`, `.env.dev`, or any other file

#### Scenario: An env file is mutated during key rotation

- **WHEN** a mutation writes a value into an env file
- **THEN** the write path MUST refuse any target reported by `git ls-files`
- **THEN** the refusal MUST name the tracked path

#### Scenario: Timestamped snapshots

- **WHEN** a mutation creates a `.env.bak.<ts>` snapshot
- **THEN** the snapshot MUST NOT contain a RUM client token
- **THEN** snapshots of secret key material MUST still be created, because those keys are irreplaceable

#### Scenario: A value is appended to a sourced env file

- **WHEN** any value is written into an env file that is later `source`d
- **THEN** the value MUST be escaped for that sourcing context
- **THEN** shell metacharacters in a value originating from an HTTP response MUST NOT become executable

### Requirement: Env Files Carrying Key Material Are Not World-Readable
The deployment MUST ensure env files holding secrets are readable only by their owner.

#### Scenario: A deployment runs with an existing wide-mode env file

- **WHEN** an env file containing `SECRET_KEY`, `JWT_SECRET_KEY`, `AUTH_SECRET` or an OpenObserve credential exists with group or world permission
- **THEN** the deployment MUST tighten it to `0600`

### Requirement: The Browser Ingest Target Is Validated Before A Credential Is Handed Over
The deployment MUST validate the RUM ingest site before passing the token to the browser, and MUST leave RUM disabled when the target is unsafe.

#### Scenario: Ingest target is loopback

- **WHEN** the configured site is a host[:port] whose host is a loopback address
- **THEN** the token MAY be passed to the browser
- **THEN** plaintext ingest to that host MAY be permitted

#### Scenario: Ingest target is the deployment's public origin

- **WHEN** the configured site is an https URL whose literal `host[:port]` string-equals the deployment's own public origin
- **THEN** the token MAY be passed to the browser
- **THEN** insecure (plaintext) ingest to that host MUST be refused

#### Scenario: Bare development deployment over HTTP

- **WHEN** the deployment is a bare host-mode deployment serving HTTP on loopback
- **THEN** a loopback ingest site MUST be accepted
- **THEN** RUM MUST continue to function in that topology

#### Scenario: Dockerized deployment over HTTPS

- **WHEN** the deployment is dockerized and served over HTTPS
- **THEN** an ingest site equal to the deployment's own public origin MUST be accepted
- **THEN** a reverse-proxy route to the ingest endpoint MUST exist, and the ingest endpoint's CORS configuration MUST permit the deployment's own origin
- **THEN** RUM MUST continue to function in that topology

#### Scenario: Ingest target is localhost on a non-loopback deployment

- **WHEN** the site is `localhost` or a loopback address but the deployment is not local-only
- **THEN** RUM MUST be left disabled
- **THEN** the step MUST warn that the browser would send the token to the end user's own machine

#### Scenario: The site is a bare authority

- **WHEN** the site is a host[:port] with no scheme, such as `localhost:5080`
- **THEN** the site MUST be accepted, because that is the ingest API's native form
- **WHEN** the site is a non-loopback host with no scheme
- **THEN** the site MUST be refused, because the transport cannot be inferred safely

#### Scenario: Hostname-shaped tricks are rejected

- **WHEN** the site contains userinfo, a path, a query or a fragment
- **THEN** the site MUST be refused
- **WHEN** the site host is the unspecified address, or a decimal, octal or hexadecimal IPv4 form
- **THEN** the site MUST be refused

#### Scenario: Frontend safe defaults are not overridden

- **WHEN** the deployment does not set an ingest site
- **THEN** the ingest site defaults to the host of the page the SDK is running on
- **THEN** the deployment MUST NOT substitute a less safe value

#### Scenario: The transport is derived from the page, not assumed

- **WHEN** no explicit transport setting is provided
- **THEN** insecure ingest MUST be enabled if and only if the page itself is served over plaintext HTTP

### Requirement: Session Replay Defaults To Masked Input
RUM MUST NOT record unmasked user input by default.

#### Scenario: No privacy level is configured

- **WHEN** the deployment does not set an explicit privacy level
- **THEN** the RUM session replay privacy level MUST be the masked-input level
- **THEN** the deployment MUST NOT downgrade it to record everything

### Requirement: The Token Is Delivered At Request Time, Not Baked Into The Image
The browser MUST receive the RUM client token from the server at request time, so a prebuilt frontend image cannot carry one instance's token.

#### Scenario: A dockerized deployment runs a prebuilt image

- **WHEN** the frontend is served from an image built elsewhere
- **THEN** the token MUST be read by the server at request time
- **THEN** the token MUST NOT be a build-time value compiled into the client bundle

### Requirement: The Management Endpoint Is Loopback-Pinned And Cannot Be Redirected
The management request MUST target a non-configurable loopback address derived from the deployment's own port configuration, and MUST NOT follow redirects or honour a proxy.

#### Scenario: Endpoint derived from the bound host port

- **WHEN** the management call is made
- **THEN** the base URL is built from a loopback literal and the same host port used to bind the OpenObserve container
- **THEN** the port MUST be validated as an integer within range, so an interpolated value cannot alter the URL's host
- **THEN** no resolvable hostname may be used, so there is no check-then-use window

#### Scenario: Non-loopback target configured

- **WHEN** any configuration offers a non-loopback management target
- **THEN** the step MUST abort before sending any credential
- **THEN** a fully-qualified URL MUST NOT be accepted from the environment as the target

#### Scenario: A proxy is configured in the environment

- **WHEN** an HTTP proxy variable is present in the environment
- **THEN** the management request MUST NOT be sent through it
- **THEN** the root credential MUST NOT be offered to the proxy

#### Scenario: Endpoint returns a redirect

- **WHEN** the management endpoint returns any 3xx status
- **THEN** the step MUST treat it as a failure and MUST NOT follow it
- **THEN** no credentialed request may ever be redirected to another host

### Requirement: Credentials Are Never Passed As Command-Line Arguments
The provisioning step MUST read OpenObserve credentials from the environment and MUST NOT place them in any process argument list, script source, or generated file.

#### Scenario: Credentials are supplied

- **WHEN** the step runs
- **THEN** credentials are read from environment variables
- **THEN** no credential value appears in a process argument list, which is visible to other local users and in shell history

#### Scenario: A credential contains a quote or a newline

- **WHEN** the root password contains a character that is significant in the implementation language or in shell
- **THEN** the credential MUST still be transmitted correctly
- **THEN** it MUST NOT cause a parse failure that results in an unauthenticated request

#### Scenario: A scoped service account is available

- **WHEN** OpenObserve offers a credential restricted to RUM application management
- **THEN** the step MUST prefer it over the root credential
- **WHEN** only the root credential exists
- **THEN** the limitation MUST be recorded in `docs/MONITORING.md`

### Requirement: Each Failure Class Is Diagnosed Distinctly
The step MUST distinguish authentication failure, missing endpoint, redirect, and generic error, and MUST warn when it does not run at all.

#### Scenario: Authentication is rejected

- **WHEN** the management endpoint returns 401 or 403
- **THEN** the step MUST warn that authentication failed and name the credential variable involved
- **THEN** it MUST NOT report this as a missing route

#### Scenario: Route is absent

- **WHEN** the endpoint returns 404
- **THEN** the step MUST warn that the management route is absent and name the OpenObserve version in use
- **THEN** it MUST compare that version against the version the endpoint was verified against and warn distinctly on a mismatch

#### Scenario: Transient server error

- **WHEN** the endpoint returns 5xx
- **THEN** the step retries a bounded number of times and then degrades

#### Scenario: A permanent error is not retried

- **WHEN** the endpoint returns 401, 403, 404 or 3xx
- **THEN** the step MUST NOT retry

#### Scenario: Step is never executed

- **WHEN** the monitoring stack is disabled, the compose file is absent, or tracing is disabled
- **THEN** the deployment MUST warn that RUM was not provisioned and state why

#### Scenario: The wait is bounded by elapsed time

- **WHEN** the management endpoint never becomes available
- **THEN** the step MUST give up after a bounded wall-clock budget, not a bounded iteration count
- **THEN** each individual request MUST carry its own connect and total timeout

#### Scenario: Deployment never fails

- **WHEN** any of the above occurs
- **THEN** the step MUST exit successfully with RUM disabled
- **THEN** no failure mode may abort the deployment

### Requirement: A Decryption Failure Is Treated As Unset
A stored RUM token that cannot be decrypted MUST be treated as absent, never as a token value.

#### Scenario: Secret key was rotated

- **WHEN** `SECRET_KEY` has been rotated since the token was stored
- **THEN** the read path reports the value as unset
- **THEN** the ciphertext envelope MUST NOT be returned as if it were the value
- **THEN** the failure MUST be logged, naming the setting key only

#### Scenario: A caller supplies a default

- **WHEN** a value cannot be decrypted and the caller supplied a default
- **THEN** the read path MUST return that default

#### Scenario: A consumer uses the value

- **WHEN** a consumer reads the token
- **THEN** it MUST validate the value is a non-empty string of the expected shape before use
- **THEN** a shape mismatch MUST be treated as unset, so the ciphertext envelope is never handed to the browser

#### Scenario: Legacy plaintext rows still read

- **WHEN** a stored value is plaintext rather than an encrypted envelope
- **THEN** the read path MUST return it unchanged

### Requirement: The Public Nature Of The Token Is Documented
Deployment documentation MUST state the access the RUM client token grants.

#### Scenario: Operator reviews the monitoring setup

- **WHEN** an operator reads the monitoring documentation
- **THEN** it states that the RUM client token is embedded in the browser payload and grants unauthenticated write access to the RUM stream
- **THEN** it records the retention and access posture of that stream, including where no retention is configured
- **THEN** it names the environment variables the code actually reads, in both their server-side and browser-bound form
- **WHEN** a documented variable name is not one the code reads
- **THEN** it MUST be corrected or removed

### Requirement: Deployment Documentation Accurately Describes The Monitoring Stack
Deployment documentation MUST accurately describe all instrumented layers, their default port topologies, the RUM token workflow, and how each layer is enabled.

#### Scenario: Operator follows a documented command

- **WHEN** an operator runs a command or uses a port taken from the monitoring documentation
- **THEN** it MUST reflect the target that exists in the repository and the port actually bound by the deployment

#### Scenario: Operator looks up a RUM configuration variable

- **WHEN** an operator reads the documentation to configure browser RUM
- **THEN** the documented variable names MUST be the names the code reads
- **THEN** the documentation MUST distinguish variables bound at build time from variables read at request time
