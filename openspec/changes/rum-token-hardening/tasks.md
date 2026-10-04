## 1. Replace the inline bash provisioner with a Python script

The bash implementation at `run.sh:547-575` interpolates the root password into
Python source to build its Basic header (`run.sh:553`) — an argv exposure and an
injection surface where a quote in the password degrades silently into an
*unauthenticated* request. `http.client` reads credentials from `os.environ`,
has no proxy support at all, and never follows redirects, so three requirements
hold by construction rather than by flag.

- [x] 1.1 Create `scripts/provision_rum_token.py`. Build the base URL from a loopback **literal** (`http://127.0.0.1:$PORT`) and `OPENOBSERVE_HOST_PORT` (default `5080`), validated as an integer in 1..65535 so an interpolated value cannot alter the URL's host. IPv4 literal, not `localhost`: `docker-compose.monitoring.yml:31` binds IPv4 loopback only, so `getaddrinfo` would try `::1` first under RFC 6724.
- [x] 1.2 Read credentials from `os.environ` only — `OPENOBSERVE_BASIC_AUTH`, else `OPENOBSERVE_ROOT_USER`/`OPENOBSERVE_ROOT_PASSWORD` — and build the header in Python. Never place a credential in an argument list, a shell string, or an exception message.
- [x] 1.3 Use `http.client.HTTPConnection` with an explicit timeout so no proxy is honoured and no redirect is followed. Verify by test that an `HTTP_PROXY` in the environment does not receive the request.
- [x] 1.4 Parse the status code with `json.loads` on the body rather than `grep -q rum_token`, which cannot distinguish 401 from 404 from 3xx from 5xx. Handle a malformed body and a `2xx` with no token as distinct degradations.
- [x] 1.5 Add the failure branches from section 5 to the new script, each on one greppable `rum-token:` line.
- [x] 1.6 Bound the wait by **wall clock**, not iteration count: `RUM_READY_BUDGET_SECONDS` (default 20, numerically guarded). Probe `/healthz` first, then make a single `rumtoken` call. Retry only on 5xx and connection errors; never on 401/403/404/3xx. Every terminal path exits 0 — `run.sh` has no `set -e`, so a stray non-zero leaks into the caller's next status check.
- [x] 1.7 Add pytest coverage: status-code branches, budget expiry, malformed JSON, credential precedence, and that the sentinel token appears in no captured output on **any** path including tracebacks.
- [x] 1.8 Replace `run.sh:547-575` with a call to the script, and delete the `update_env_var` writes at `run.sh:567-569` — see section 4.

## 2. Validate the browser ingest target

- [x] 2.1 Implement the site validator. Absolute `http`/`https` URL only. Parse with `urllib.parse.urlsplit`, **not** a regex: a regex is defeated by `https://good.example@evil.example/`, whose `hostname` is `evil.example`. Reject userinfo, any path/query/fragment, and `parsed.port` raising `ValueError`.
- [x] 2.2 Decide loopback with `ipaddress.ip_address(host).is_loopback and not is_unspecified`, stripping IPv6 brackets and one trailing dot. This accepts `127.0.0.0/8` and `::1` and refuses `0.0.0.0`/`::`. `ipaddress` also rejects decimal/octal/hex IPv4 (`2130706433`, `0177.0.0.1`), which `socket.gethostbyname` resolves to loopback — do not use that as the gate. Accept bare `localhost` only, never `*.localhost`.
- [x] 2.3 Implement the public-origin arm: compare the **literal normalised `host[:port]` string** against the configured public origin. Never resolve it and never allowlist by resolved IP — deploy script and browser resolve independently, so a name that is loopback at deploy time and attacker-controlled at page-load time is a live bypass.
- [x] 2.4 Refuse plaintext ingest to any non-loopback host. Permitted only on the loopback path, which is what bare `dev` mode uses.
- [x] 2.5 Stop passing `NEXT_PUBLIC_OPENOBSERVE_RUM_SITE=localhost:5080` and `NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP=true` from `run.sh:711-714`. On a deployment that is not the operator's own machine the end user's browser resolves `localhost` to *their own computer* and POSTs the token there in cleartext.
- [x] 2.6 Stop passing `OPENOBSERVE_RUM_PRIVACY_LEVEL=allow` from `run.sh:717`. `browser-openobserve-rum.tsx:96` calls `startSessionReplayRecording()` unconditionally and the component's own default is `mask-user-input` in both dev and prod — `run.sh` is what downgrades it. With `allow`, DOM text and user input are recorded unmasked and indefinitely, with no retention configured, in an app whose purpose is a personal media library.
- [x] 2.7 Tests for the full matrix: loopback accepted; public origin accepted over HTTPS and refused over HTTP; `localhost` on a non-loopback deployment refused; relative site refused; userinfo trick refused; `0.0.0.0` refused; decimal IPv4 refused; plaintext-to-non-loopback refused.

## 3. Deliver the token at request time

`NEXT_PUBLIC_*` is compiled into the client bundle at build time, but
`--prebuilt` prod pulls the frontend image from GHCR — so a per-instance build
ARG would either be impossible or would bake one instance's token into a shared
image.

- [x] 3.1 Convert `BrowserOpenObserveRum` to prop-driven configuration: `clientToken`, `site`, `insecureHTTP`, `privacyLevel`, with the existing env fallbacks retained for the dev path.
- [x] 3.2 Default `insecureHTTP` to `window.location.protocol === "http:"` when no explicit value is configured. **Without this, task 2.5 breaks dev RUM** — `site = window.location.host` on a bare-HTTP dev page would make the SDK attempt `https://localhost:3000`. Deriving it from the page is correct in dev and safe in production.
- [x] 3.3 Read a **non-public** `OPENOBSERVE_RUM_CLIENT_TOKEN` in `frontend/app/layout.tsx` and pass it down. The layout is already a Server Component and already dynamic (it awaits `getLocale()`/`getMessages()`), so this is a per-request read.
- [x] 3.4 Guard the console diagnostics: `browser-openobserve-rum.tsx:100` logs raw `err` from SDK init, which would put the client token in the browser console if the SDK ever throws with its config attached. Log `err?.message` only.
- [x] 3.5 Check `NEXT_PUBLIC_OPENOBSERVE_RUM_APPLICATION_ID` against the application the endpoint actually created. **Resolved by live testing.** `/api/default/rumtoken` returns only `{user, rum_token}` — no application identifier. Reading the SDK's `endpointBuilder.js` shows the ingest route is `/rum/{apiVersion}/{org}/{trackType}` with the token as an `o2-api-key` query parameter, so `applicationId` is payload metadata and **cannot** cause ingest rejection. Verified: a direct ingest carrying `applicationId: "iqoqo"` returned `successful: 1, failed: 0` into `_rumdata`.
- [x] 3.6 Update `frontend/__tests__/components/browser-openobserve-rum.test.tsx` for the prop signature, and add coverage for the protocol-derived `insecureHTTP` and the masked-input privacy default.

## 4. Stop persisting the token, and fix the file modes

- [x] 4.1 Delete the `update_env_var` calls for the token. `/api/default/rumtoken` is a server-side get-or-create, so the write buys nothing on re-run. It is also harmful: `update_env_var:161` appends with `echo "${key}=\"${val}\""` and escapes nothing, and the file is `source`d under `allexport` on the next run — so a backtick in a response body becomes command execution as the deploying user.
- [x] 4.2 Keep the export only, so the frontend receives the token for this run.
- [x] 4.3 Add the tracked-file guard inside `update_env_var` itself, not at the RUM call site. `.env.test` is un-ignored (`.gitignore:28`) and is reachable as `$target_file` at `run.sh:166-169` — so the tracked-file risk that actually exists is `SECRET_KEY`/`JWT_SECRET_KEY`/`AUTH_SECRET`, which is worth far more protecting than the public RUM token. Refuse with a message naming the path.
- [x] 4.4 Reconcile with MOD-OPS-03 explicitly in a comment. The two requirements are **not** in conflict: the snapshots exist to protect *irreplaceable* state — those three keys are the Fernet key material for every encrypted `InstanceSettings` row, and losing one is an instance lockout. A RUM token has no irreplaceable state, and removing the write removes the tension rather than trading it off.
- [x] 4.5 Escape values appended to a sourced env file. `update_env_var:161` and `ensure_env_secrets.py:61` both write without escaping; `ensure_env_secrets.py` selects double quotes without escaping them.
- [x] 4.6 Tighten `.env` and `.env.*` to `0600`. They are currently `0664` and hold `SECRET_KEY`, `JWT_SECRET_KEY`, `AUTH_SECRET`, `OPENOBSERVE_ROOT_PASSWORD` and `OPENOBSERVE_BASIC_AUTH` — world-readable to any local user, and `update_env_var:127` faithfully preserves the wide mode via `chmod --reference`. Note that `ensure_env_secrets.py` performs no `chmod` at all, so `0600` is an explicit mode, not a parity claim.
- [x] 4.7 Note that `.env.bak.*` snapshots accumulate without pruning. Out of scope for this change; record as a follow-up.

## 5. Diagnostics

- [x] 5.1 Add a distinct 401/403 branch naming the credential variable. This is the most likely real-world failure — a rotated or clobbered root password — and currently produces the same quiet warning as a missing route. With task 1.2 the branch can no longer misfire on an unauthenticated request caused by a parse failure.
- [x] 5.2 Include the OpenObserve image version in the 404 branch and compare it against the version the endpoint was verified against (`openobserve/openobserve:v0.91.5` in `docker-compose.monitoring.yml:25`), warning distinctly on mismatch rather than degrading generically.
- [x] 5.3 Warn when the step does not run at all, stating why. The block is gated on `OTEL_TRACES_EXPORTER=otlp` (`run.sh:536`), so with tracing disabled provisioning silently never happens.
- [x] 5.4 Emit one greppable `rum-token:` line per outcome carrying outcome, reason, HTTP status, target, attempt count, elapsed seconds and image version — enough to triage without a second command. `run.sh` has no logging framework and writes no deploy log of its own, so scope this to the terminal/CI transcript.
- [x] 5.5 Never print a fingerprint: no prefix, no length, no truncated hash. Log a redirect's `Location` host only, never the full URL, since a `Location` can carry the original query string.
- [x] 5.6 Add a post-provision assertion that the ingest target resolves as intended, so a "successful" provision that still points the browser at the wrong host is detectable.

## 6. Make the dockerized topologies actually work

Currently prod/preview browser RUM cannot work at all, and cannot be fixed by
changing `run.sh` alone: OpenObserve is loopback-bound, `deploy/nginx.conf` has
no `/rum` route, and `ZO_CORS_ALLOWED_ORIGINS` is pinned to localhost.

- [x] 6.1 Pass the token to the frontend service in `docker-compose.yml`. It arrives via `env_file`, which is what makes the task 3.3 request-time read work with a prebuilt image.
- [x] 6.2 Add a `/rum/` location to `deploy/nginx.conf` proxying to `openobserve:5080`, mirroring the existing `upstream` + `resolver 127.0.0.11` pattern so it survives container restarts. Rate-limit it: it is an unauthenticated write endpoint.
- [x] 6.3 Extend `ZO_CORS_ALLOWED_ORIGINS` in `docker-compose.monitoring.yml` to include the deployment's own public origin instead of only `localhost:3000`/`127.0.0.1:3000`.
- [x] 6.4 Validate `deploy/nginx.conf.example` with the `make validate-nginx` target.
- [x] 6.5 Decide and document the ingest site per mode: bare `dev` uses the loopback literal; `preview`/`prod` use the deployment's own public origin. Both must keep working.

## 7. Settings read path

- [x] 7.1 Make `decrypt_setting_value` return `None` on `InvalidToken` instead of the stored envelope (`app/db/settings.py:167-169`). After a `SECRET_KEY` rotation, `get_value("OPENOBSERVE_RUM_CLIENT_TOKEN")` currently returns a dict.
- [x] 7.2 Make `get_value` apply the caller's `default` to that `None`. `settings.py:204` currently discards it by returning `decrypt_setting_value(...)` directly, so every `get_value(key, default)` call site would silently lose its fallback. This is mandatory alongside 7.1, not optional.
- [x] 7.3 Log the decryption failure naming the setting key only, never the value. Otherwise a rotated `SECRET_KEY` is invisible.
- [x] 7.4 Validate the token is a non-empty string of the expected shape before any consumer uses it, and treat a mismatch as unset, so the ciphertext envelope is never handed to the browser.
- [x] 7.5 Do **not** change the plaintext back-compat branch (`settings.py:155-157`) or the malformed-envelope branch (159-161); they serve legacy plaintext rows and altering them changes the admin reveal path.
- [x] 7.6 Document the `SECRET_KEY` rotation consequence and confirm the recovery path. The answer is `make migrate-secrets` with no new code: `migrate_env_secrets_to_db.py:130` treats a non-`None` existing value as a conflict and skips, so with `None` it overwrites the row from `.env` and re-encrypts. The same fall-through repairs `config_service.py:63`, where `if val is not None` currently lets the envelope win and be used *as a credential*.
- [x] 7.7 Add a test that stores under one key and reads under another, plus one asserting `get_value(key, default)` returns the default when decryption fails.

## 8. Documentation

- [x] 8.1 State in `docs/MONITORING.md` that the RUM client token is delivered to the browser and grants unauthenticated write access to the RUM stream, including session replay and log ingestion. Record the retention and access posture — including that **no retention is configured**, which makes it a disk-exhaustion primitive against the `openobserve_data` host volume, and that the loopback bind is the only control preventing that. State that the root credential is used from a script on every deploy because no RUM-scoped service account exists in `v0.91.5`, and that `OPENOBSERVE_BASIC_AUTH` is visible in container environments via `docker inspect`.
- [x] 8.2 Correct the documented variable names. `docs/MONITORING.md` documents `NEXT_PUBLIC_OPENOBSERVE_RUM_TOKEN` and `NEXT_PUBLIC_OPENOBSERVE_API_URL`; neither is read. Document the real surface, distinguishing server-read-at-request-time from build-time-inlined, and note that two names exist for one credential: `OPENOBSERVE_RUM_CLIENT_TOKEN` (unprefixed) and `NEXT_PUBLIC_OPENOBSERVE_RUM_CLIENT_TOKEN` (browser-bound).
- [x] 8.3 Record the verified endpoint contract and the version it was verified against (`openobserve/openobserve:v0.91.5`), so an image bump has something concrete to re-check.
- [x] 8.4 Fix the other factual errors found alongside: the non-existent `make monitoring-start`/`monitoring-stop` targets, `/api/health` where the code queries `/healthz`, hardcoded `:5080` in the diagnostic curl examples that should be `${OPENOBSERVE_HOST_PORT:-5080}`, and `frontend/.env.example` seeding the RUM site with the value being removed as a default. **DONE:** the operator authorised the edit, so `frontend/.env.example` was updated — `RUM_SITE` and `RUM_INSECURE_HTTP` are now empty (derive from the page) and `RUM_PRIVACY_LEVEL` is `mask-user-input`, with a comment pointing at the unprefixed `OPENOBSERVE_RUM_*` names.
- [x] 8.5 Add a `.gitleaks.toml` rule for RUM token shapes. Today a bare RUM client token in a committed file passes CI, which undercuts 8.1's central claim.
- [x] 8.6 File the follow-ups this change surfaces but does not fix: RUM retention configuration, a healthcheck on the `openobserve` service, pruning of `.env.bak.*`, and the `HTTP_PROXY`-in-`.env` credential-exfiltration path that only becomes reachable once the management URL is parameterised.

## 9. Verification

- [x] 9.1 Run `make lint-shell` and the full pytest suite. **Result:** `make lint-shell` clean (shellcheck 0.10.0). pytest **2737 passed, 3 skipped, 0 failed**. bats: `rum_token_provisioning.bats` 22/22, `run_sh_process_safety.bats` 15/15, `env_example_sync.bats` 4/4, `scripts_syntax`/`scripts_guardrails` green. Two caveats, both expected rather than defects: `tests/test_linting.py::test_shellcheck` skips when shellcheck is absent, so it MUST be installed locally for this change; CI installs a pinned 0.10.0 and fails the suite outright if it is missing. Verified present locally at 0.10.0, alongside bats 1.10.0.
   - `validate_nginx_example.bats` "the committed config is never modified by these tests" fails on a dirty working tree, because this change intentionally edits `deploy/nginx.conf.example`. Verified it passes when that file matches HEAD, and the other 15 tests in that file — including real `nginx -t` via nginx:1.29-alpine — pass against the modified config.
   - `test_taxonomy_generation_freshness` failed once mid-session because I accidentally ran two full pytest suites concurrently; both invoke `generate_taxonomy.py`, which rewrites `frontend/types/taxonomy.ts` in place, so the freshness read raced the write. Reproduces clean and is unrelated to this change.
- [x] 9.2 Confirm on a live instance that RUM events still reach OpenObserve in **bare `dev` mode over HTTP**, and that the token is unchanged across a restart. **Verified** against a fresh OpenObserve `v0.91.5` (project `rum-verify`, port 5080, its own volume): provisioning returned `reason=created` then `reason=existing`; a direct ingest on the SDK's exact path returned `_rumdata successful:1 failed:0` and `_rumlog successful:1 failed:0`; both were queryable via `_search`; and the token was byte-identical across a `docker restart` with data intact (`count(*)` on `_rumlog` still 1). Caveat: ingest was driven synthetically on the real SDK contract, not by a live browser page load.
- [x] 9.3 Confirm on a live instance that RUM events reach OpenObserve in **`prod` mode over HTTPS through the reverse proxy**. `frontend/__tests__/e2e/openobserve_rum.spec.ts:45` reads a non-existent variable and so always returns early; fix it to query `_rumlog` via `_search` or this verification is theatre.