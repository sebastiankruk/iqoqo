## Purpose

Security requirements for the deployment-time provisioning of the per-instance OpenObserve RUM client token, which already ships in `run.sh` and currently leaks and misroutes the credential it creates.

## ADDED Requirements

### Requirement: The RUM Client Token Is Never Emitted As A Value
The provisioning step MUST report its outcome and MUST NOT print, log, or echo the token value on any path, including success.

#### Scenario: Token is freshly provisioned
- **WHEN** the management endpoint returns a client token
- **THEN** the step reports that provisioning succeeded, without the value
- **THEN** the value appears in no file other than the deployment's own restricted env state

#### Scenario: Provisioning is re-run and the token is unchanged
- **WHEN** the endpoint returns the existing token
- **THEN** the step reports that the existing token was reused, without the value

#### Scenario: An error occurs while handling the token
- **WHEN** any failure occurs after the token has been read into a variable
- **THEN** no diagnostic, exception message, or traceback contains the token
- **THEN** a regression test asserts a sentinel token never appears in captured output

### Requirement: The Browser Ingest Target Is Validated Before A Credential Is Handed Over
The deployment MUST validate the RUM ingest site before passing the token to the browser, and MUST leave RUM disabled when the target is unsafe.

#### Scenario: Ingest target is loopback
- **WHEN** the configured site resolves to a loopback address
- **THEN** the token MAY be passed to the browser

#### Scenario: Ingest target is the deployment's public origin
- **WHEN** the configured site is an absolute URL whose host matches the deployment's own public origin
- **THEN** the token MAY be passed to the browser
- **THEN** insecure (plaintext) ingest to that host MUST be refused

#### Scenario: Ingest target is localhost on a non-loopback deployment
- **WHEN** the site is `localhost` or a loopback address but the deployment is not local-only
- **THEN** RUM MUST be left disabled
- **THEN** the step MUST warn that the browser would send the token to the end user's own machine

#### Scenario: Frontend safe defaults are not overridden
- **WHEN** the deployment does not set an ingest site
- **THEN** the frontend's own default of the current page host is used
- **THEN** the deployment MUST NOT substitute a less safe value

### Requirement: The Token Is Not Persisted Into Tracked Files
The provisioning step MUST NOT write a live token to any file tracked by version control, and MUST NOT create backup copies containing one.

#### Scenario: Target env file is tracked
- **WHEN** the env file the step would write to is reported as tracked by `git ls-files`
- **THEN** the step MUST refuse to write the token there
- **THEN** RUM MUST be left disabled with a warning naming the tracked path

#### Scenario: Env file is snapshotted
- **WHEN** a mutation writes a value into an env file
- **THEN** no timestamped backup copy containing a live token may be created

### Requirement: The Management Endpoint Is Loopback-Pinned And Redirects Are Not Followed
The management request MUST target a loopback address derived from the deployment's own port configuration, and MUST NOT follow redirects.

#### Scenario: Endpoint derived from the bound host port
- **WHEN** the management call is made
- **THEN** the base URL is derived from the same host port used to bind the OpenObserve container
- **THEN** the resolved address MUST be a loopback address

#### Scenario: Non-loopback target configured
- **WHEN** the configured endpoint does not resolve to a loopback address
- **THEN** the step MUST abort before sending any credential
- **THEN** a fully-qualified URL MUST NOT be accepted from the environment as the target

#### Scenario: Endpoint returns a redirect
- **WHEN** the management endpoint returns any 3xx status
- **THEN** the step MUST treat it as a failure and MUST NOT follow it
- **THEN** no credentialed request may ever be redirected to another host

### Requirement: Credentials Are Never Passed As Command-Line Arguments
The provisioning step MUST read OpenObserve credentials from the environment and MUST NOT accept them as arguments.

#### Scenario: Credentials are supplied
- **WHEN** the step runs
- **THEN** credentials are read from environment variables
- **THEN** no credential value appears in a process argument list, which is visible to other local users and in shell history

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

#### Scenario: Transient server error
- **WHEN** the endpoint returns 5xx
- **THEN** the step retries a bounded number of times and then degrades

#### Scenario: Step is never executed
- **WHEN** the monitoring stack is disabled, the compose file is absent, or tracing is disabled
- **THEN** the deployment MUST warn that RUM was not provisioned and state why

#### Scenario: Deployment never fails
- **WHEN** any of the above occurs
- **THEN** the step MUST exit successfully with RUM disabled
- **THEN** no failure mode may abort the deployment

### Requirement: A Decryption Failure Is Treated As Unset
A stored RUM token that cannot be decrypted MUST be treated as absent, never as a token value.

#### Scenario: Secret key was rotated
- **WHEN** `SECRET_KEY` has been rotated since the token was stored
- **THEN** the read path returns an undecryptable marker rather than a usable value
- **THEN** a consumer MUST validate the value is a non-empty string of the expected shape before using it
- **THEN** a shape mismatch MUST be treated as unset, and the ciphertext envelope MUST NOT be handed to the browser

### Requirement: The Public Nature Of The Token Is Documented
Deployment documentation MUST state the access the RUM client token grants.

#### Scenario: Operator reviews the monitoring setup
- **WHEN** an operator reads the monitoring documentation
- **THEN** it states that the RUM client token is embedded in the browser bundle and grants unauthenticated write access to the RUM stream
- **THEN** it records the retention and access posture of that stream
- **THEN** it names the environment variables the code actually reads
