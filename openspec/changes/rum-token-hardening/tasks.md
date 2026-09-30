## 1. Stop Leaking The Token (highest priority — active exposure)

- [ ] 1.1 Remove the `echo` of the fetched token at `run.sh:564`. Replace it with an outcome-only message that distinguishes "provisioned" from "reused". This is a live bearer credential currently reaching stdout, terminal scrollback, `script(1)` captures and CI logs on every deploy.
- [ ] 1.2 Audit the whole `run.sh:547-575` block for any other value emission: the `token_response` and `fetched_token` variables must never be echoed, and no `set -x` or verbose mode may be enabled around them.
- [ ] 1.3 Add a bats regression test using a sentinel token that asserts the value appears in no captured stdout, stderr, or log file on the success, reuse, and every failure path.

## 2. Validate The Browser Ingest Target

- [ ] 2.1 Add ingest-target validation before the token is passed to the frontend: the `site` MUST be an absolute URL whose host is loopback, or an absolute URL matching the deployment's own public origin. Anything else leaves RUM disabled.
- [ ] 2.2 Refuse plaintext ingest to a non-loopback host; stop defaulting `OPENOBSERVE_RUM_INSECURE_HTTP` to `true` in the deploy path.
- [ ] 2.3 Stop overriding the frontend's safe defaults. `run.sh:711-714` currently forces `localhost:5080` and `INSECURE_HTTP=true`, which overrides `window.location.host` and `insecureHTTP === "true"` in `browser-openobserve-rum.tsx`. On a non-local deployment the end user's browser resolves `localhost` to their own machine and POSTs the token there in cleartext.
- [ ] 2.4 Add tests for the target matrix: loopback accepted, public origin accepted over HTTPS, `localhost` on a non-loopback deployment refused, relative site refused, plaintext-to-non-loopback refused.

## 3. Stop Persisting Into Tracked Files

- [ ] 3.1 Make the write path refuse any target reported by `git ls-files`. `.env.test` is explicitly un-ignored (`.gitignore:28`) and is a write target in `test` mode, so a live token can land in a tracked file.
- [ ] 3.2 Stop creating timestamped `.env.bak.<ts>` snapshots for env files containing a live token, without regressing the `MOD-OPS-03` protection that made these backups in the first place. The two requirements must be reconciled explicitly, not traded off silently.
- [ ] 3.3 Verify the token's file permissions are restrictive. Note that `ensure_env_secrets.py` performs no `chmod` and writes via `write_text` at the default umask, so there is no existing 0600 behaviour to inherit; the requirement must be an explicit mode, not a parity claim.

## 4. Management Request Safety

- [ ] 4.1 Derive the management base URL from the same `OPENOBSERVE_HOST_PORT` used to bind the container, and verify the resolved address is loopback before any credential is sent. `run.sh:560` currently hardcodes `http://localhost:5080`, which is already wrong for a multi-stack host using a non-default port.
- [ ] 4.2 Refuse to accept a fully-qualified management URL from the environment. `.env` is `source`d with `allexport` (`run.sh:293-297`), so a value there becomes the host that receives the root Basic credential.
- [ ] 4.3 Disable redirect following on every credentialed request and treat any 3xx as failure, so a redirect cannot resend the root Basic credential off-box.
- [ ] 4.4 Read credentials from the environment only; never accept them as command-line arguments, which are visible in `/proc` and shell history.

## 5. Diagnostics

- [ ] 5.1 Add a distinct 401/403 branch naming the credential variable. This is the most likely real-world failure (rotated or clobbered root password) and currently produces the same quiet warning as a missing route.
- [ ] 5.2 Include the OpenObserve image version in the 404 branch, and compare it against the version the endpoint was verified for, warning distinctly on mismatch rather than degrading generically.
- [ ] 5.3 Warn when the step does not run at all. The whole block is gated on `OTEL_TRACES_EXPORTER=otlp` (`run.sh:536`), so with tracing disabled provisioning silently never happens.
- [ ] 5.4 Add a post-provision assertion that the ingest target resolves as intended, so a "successful" provision that still points the browser at the wrong host is detectable.

## 6. Settings Read Path

- [ ] 6.1 Make `InstanceSettings` treat a decryption failure as unset. `decrypt_setting_value` currently returns the stored envelope on `InvalidToken` (`app/db/settings.py:167-169`), so after a `SECRET_KEY` rotation `get_value("OPENOBSERVE_RUM_CLIENT_TOKEN")` returns a dict rather than a token.
- [ ] 6.2 Validate the value is a non-empty string of the expected shape before any consumer uses it, and treat a mismatch as unset so the ciphertext envelope is never shipped to the browser.
- [ ] 6.3 Document the `SECRET_KEY` rotation consequence for this key, and confirm whether any re-encryption path exists for rotated keys.

## 7. Documentation

- [ ] 7.1 State in `docs/MONITORING.md` that the RUM client token is embedded in the browser bundle and grants unauthenticated write access to the RUM stream, including session replays and log lines, and record that stream's retention and access posture.
- [ ] 7.2 Correct the documented variable names. `docs/MONITORING.md` documents `NEXT_PUBLIC_OPENOBSERVE_RUM_TOKEN` and `NEXT_PUBLIC_OPENOBSERVE_API_URL`; the code reads `NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN` and `NEXT_PUBLIC_OPENOBSERVE_RUM_SITE`.
- [ ] 7.3 Document the accepted limitation if a non-root RUM-scoped service account is not available in OpenObserve v0.91.5, and the consequence of the root credential being used from a script on every deploy.

## 8. Verification

- [ ] 8.1 Run `make lint-shell` and the full pytest suite. Note that `tests/test_linting.py::test_shellcheck` skips when shellcheck is absent, so it MUST be installed locally for this change; CI installs a pinned 0.10.0 and fails the suite outright if it is missing.
- [ ] 8.2 Confirm on a live instance that RUM events still reach OpenObserve after the ingest-target validation, and that the token is unchanged across a restart.
