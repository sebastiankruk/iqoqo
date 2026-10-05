## Context

OpenObserve runs as a per-deployment local image, so its RUM client token is
inherently per-instance and cannot be shipped in the repository.

**The provisioning path already exists and already works.** `run.sh:547-575`
waits for OpenObserve, authenticates with the root Basic credential, calls
`GET /api/default/rumtoken` and persists the result. There is no unknown API to
discover and no spike to run — the endpoint, auth method and response field are
all confirmed by the shipping call site. This change **remediates** that path;
it does not construct one.

> **Historical note.** An earlier draft of this change (numbered C18, a number
> later taken by `moderate-findings-sweep`) proposed building the phase from
> scratch, on the mistaken premise that no provisioning path existed. That draft
> — including its `scripts/provision_rum_token.py`, its "verification spike
> task 1", and its line-number table — is **discarded**. This document has been
> rewritten so that no reader concludes the work is blocked on a retired
> precondition.

### Structural facts that constrain every decision

These were established by reading the shipped code and are load-bearing:

1. **The provisioning block is dev-mode only.** `run.sh:462` opens
   `if [ "$MODE" == "dev" ]` and `run.sh:741` closes it. The RUM block
   (547-576) and the frontend start (699-721) are both inside it. `preview` and
   `prod` take the full-Docker branch, where the monitoring stack is composed
   separately (`run.sh:841-844`).
2. **The token cannot be a build-time value.** `Dockerfile.prod:37-40` declares
   `NEXT_PUBLIC_*` build ARGs, but in `--prebuilt` mode
   `docker-compose.prebuilt.yml:57-59` pulls `ghcr.io/...iqoqo-frontend` and
   resets `build` — so the bundle is built on CI, not on the operator's host. A
   per-instance token baked in at build time would leak one instance's token
   into every instance's image. `NEXT_PUBLIC_*` values are inlined by the
   Next.js compiler into the client bundle, so a build ARG is structurally
   unusable here.
3. **OpenObserve is loopback-bound.** `docker-compose.monitoring.yml:31` binds
   `127.0.0.1:${OPENOBSERVE_HOST_PORT:-5080}:5080`. A remote browser cannot
   reach it directly; it needs a reverse-proxy route.
4. **`deploy/nginx.conf` has no `/rum` location**, and
   `docker-compose.monitoring.yml:35` pins `ZO_CORS_ALLOWED_ORIGINS` to
   localhost origins. Production browser RUM therefore cannot work today, and
   cannot be made to work by changing `run.sh` alone.

## Goals / Non-Goals

**Goals:**

- Stop the token reaching stdout, and stop it reaching any file that version
  control, a backup, or a `source`d env file can pick up.
- Never hand the browser a credential aimed at somewhere other than the
  deployment's own ingest endpoint.
- Make the root OpenObserve credential impossible to leak to a proxy, a
  redirect target, `/proc`, or shell history.
- **Keep RUM working in both topologies the project actually ships**: bare
  `dev` over HTTP on loopback, and dockerized `preview`/`prod` over HTTPS via
  the reverse proxy.
- Diagnose each failure class distinctly, and warn when the step does not run.
- Keep RUM fail-soft: never block, slow materially, or fail a deployment.

**Non-Goals:**

- Changing the `/api/default/rumtoken` get-or-create contract. It is a single
  idempotent server-side call and is strictly better than list-then-create.
- Extending `scripts/ensure_env_secrets.py`. A RUM token cannot exist at
  `run.sh:313` because OpenObserve is not running yet; that pre-boot pass is
  correct as-is.
- Changing the `InstanceSettings` encryption scheme. `is_sensitive_key`
  (`app/db/settings.py:135`) already matches `_TOKEN`, so
  `OPENOBSERVE_RUM_CLIENT_TOKEN` is **already** encrypted at rest.
- Making RUM mandatory.

## Decisions

### Decision 1: The provisioner is a Python script, not bash

**Decision:** implement the step as `scripts/provision_rum_token.py`, called
from `run.sh`.

The bash version cannot satisfy the requirements cleanly. `run.sh:553` builds
the Basic header by interpolating the root password into Python source:

```bash
encoded=$(python3 -c "...b'${OPENOBSERVE_ROOT_USER}:${OPENOBSERVE_ROOT_PASSWORD}'...")
```

That is an argv exposure **and** a source-injection surface. A password
containing `'` raises a `SyntaxError`, which `2>/dev/null` swallows, leaving
`auth_header=""` — so the request goes out **unauthenticated**, returns 401,
and a new 401 diagnostic would confidently blame the wrong variable.

In bash, every remaining credential-passing option is also imperfect:
`-H "Authorization: $b64"` and `-u "$user:$pass"` are both argv; a `--netrc-file`
adds a file; and `curl --config -` uses a config format that is not shell, so a
password containing `"` or a newline corrupts it.

`http.client` sidesteps all of it:

- Credentials are read from `os.environ` — never argv, never a shell string.
- **`http.client` has no proxy support at all**, so `HTTP_PROXY` in `.env`
  (which `run.sh:296` exports via `set -o allexport`) cannot become the host
  that receives the root credential. This is free, and it is not free in bash.
- `HTTPConnection` **never follows redirects**, satisfying the requirement by
  construction rather than by flag.
- `response.status` distinguishes 401/403/404/3xx/5xx directly, which the
  current `grep -q rum_token` on the body cannot do at all.
- `json.loads` replaces a shell `grep`, and the `{1..30}` bashism goes away.

This also reconciles the two expert reviews: the SRE's testability concern is
satisfied by testing the Python script directly, which is stronger than
extracting a bash function with an `awk`/`eval` harness — and it avoids the
harness's known trap where a column-0 `}` inside a heredoc silently truncates
the extracted function.

### Decision 2: The management target is a non-configurable loopback literal

**Decision:** build the base URL as `http://127.0.0.1:$PORT`, where `$PORT` is
`OPENOBSERVE_HOST_PORT` (default `5080`) validated as an integer in 1..65535.

Using a loopback **literal** rather than a hostname makes the guarantee hold by
construction: there is nothing to resolve, so there is no check-then-use race.
A hostname would have to be verified at deploy time and resolved again by the
client, and `/etc/hosts`/`nsswitch` is mutable between those two moments.

It is also correct for the actual bind. `docker-compose.monitoring.yml:31`
binds **IPv4** loopback only, so on a dual-stack host `getaddrinfo("localhost")`
returns `::1` first (RFC 6724), where nothing listens.

The thing that actually needs validating is the **port**, not the host.
Interpolating `OPENOBSERVE_HOST_PORT` without validation is a URL-injection
sink: `OPENOBSERVE_HOST_PORT='5080@evil.example/x'` would produce a
credentialed request to `evil.example`. The numeric guard follows the idiom
already used in `run.sh:389-391`.

### Decision 3: No fully-qualified management URL is accepted from the environment

**Decision:** ignore any environment variable that offers a full URL for the
management endpoint.

`.env` is `source`d with `set -o allexport` (`run.sh:293-297`), so any key
there becomes the host that receives the root Basic credential. Accepting
`OPENOBSERVE_URL=http://attacker/` would make the root password a one-line
`.env` edit away from leaving the box.

### Decision 4: The token is exported, never written

**Decision:** delete the `update_env_var` calls at `run.sh:567-569`. Keep only
the `export`.

The write buys nothing: `/api/default/rumtoken` is a server-side get-or-create,
so re-running the step returns the same token forever. And the write is
actively harmful, because `update_env_var:161` appends with
`echo "${key}=\"${val}\""` and performs **no escaping** of `"`, `$` or
backtick. The value originates in an HTTP response body, and the file is
`source`d under `allexport` on the next run — so a token containing a backtick
becomes command execution as the deploying user.

Deleting the write resolves three otherwise-conflicting tasks:

- **Task 3.1** (refuse tracked files) becomes moot — and is instead enforced
  where it actually matters: inside `update_env_var`, which is what rewrites
  `SECRET_KEY`/`JWT_SECRET_KEY`/`AUTH_SECRET` into a `.env.$MODE` file that
  `.env.test` proves can be version-controlled.
- **Task 3.2** (no `.env.bak.<ts>` for the token) becomes moot. Note the two
  concerns are **not** actually in conflict: MOD-OPS-03 snapshots exist to
  protect *irreplaceable* state — those three keys are the Fernet key material
  for every encrypted `InstanceSettings` row, and losing one is an instance
  lockout. A RUM token has no irreplaceable state. Removing the write removes
  the tension rather than trading it off.
- **Task 3.3** (restrictive permissions) is answered on the file that actually
  needs it — see Decision 9.

### Decision 5: The browser receives the token at request time, not at build time

**Decision:** the root layout — already a Server Component, already dynamic
(it awaits `getLocale()`/`getMessages()`) — reads a **non-public**
`OPENOBSERVE_RUM_CLIENT_TOKEN` and passes `clientToken`, `site` and
`insecureHTTP` to `BrowserOpenObserveRum` as props.

This is forced by fact 2 above: `--prebuilt` prod pulls the frontend image from
GHCR, so a per-instance `NEXT_PUBLIC_*` build ARG would either be impossible or
would bake one instance's token into a shared image. Reading a server-side env
var at request time works with a prebuilt image and is also **safer for cache
purposes** — the value is per-request, not frozen into a long-lived asset.

This does not weaken the posture: a RUM client token is **public by
construction** — it is a bearer credential for a write-only ingest endpoint and
it is necessarily readable by anyone who can view the page source. Serving it
through the HTML instead of the bundle changes nothing about what an attacker
can do with it.

### Decision 6: Ingest target topology, per mode

**Decision:** the accepted ingest target depends on mode, and both topologies
ship.

| Mode | Serving model | Accepted `site` | `insecureHTTP` | Route |
|---|---|---|---|---|
| `dev` | bare host, HTTP, loopback | loopback literal (`127.0.0.0/8`, `::1`, or bare `localhost`) | permitted | direct |
| `preview` / `prod` | dockerized, HTTPS | the deployment's **own** public origin, exact `host[:port]` match | **refused** | `deploy/nginx.conf` `/rum/` → `openobserve:5080` |

Rules that apply to both:

- The `site` MUST be an absolute `http`/`https` URL with **no** userinfo, path,
  query or fragment. Parsed with `urllib.parse.urlsplit`, not a regex: a regex
  is defeated by `https://good.example@evil.example/`, whose `hostname` is
  `evil.example`.
- Loopback is decided by `ipaddress.ip_address(host).is_loopback and not
  is_unspecified` — so `127.0.0.0/8` and `::1` pass while `0.0.0.0` and `::` are
  refused. `ipaddress` also rejects decimal/octal/hex IPv4 (`2130706433`,
  `0177.0.0.1`), which `socket.gethostbyname()` happily resolves to `127.0.0.1`.
- Only bare `localhost` is accepted, never `*.localhost`: RFC 6761 says the
  wildcard is loopback, but this is an allowlist decision and a hostile
  `/etc/hosts` beats the convention.
- The public-origin arm compares the **literal normalised `host[:port]` string**
  against the configured origin. It never resolves it and never allowlists by
  resolved IP — deploy script and browser resolve independently, so any name
  that is loopback at deploy time and attacker-controlled at page-load time is
  a live bypass.
- Plaintext ingest to any non-loopback host is refused outright.

### Decision 7: Remove the deploy-time overrides that downgrade the frontend

**Decision:** `run.sh` no longer forces `RUM_SITE` or `RUM_INSECURE_HTTP`, and no
longer forces `RUM_PRIVACY_LEVEL` to `allow`.

Today `run.sh:711-714` sets `SITE=localhost:5080` and `INSECURE_HTTP=true`,
overriding the component's own safe defaults. On a deployment that is not the
operator's own machine, the end user's browser resolves `localhost` to *their
own computer* and POSTs the token there in cleartext.

Removing the override **without** fixing the component would break dev RUM,
because `site = window.location.host` on a bare-HTTP dev page would make the
SDK attempt `https://localhost:3000`. So the component derives the flag from
the page it is running on:

```ts
const insecureHTTP = configured
  ? configured === "true"
  : window.location.protocol === "http:";
```

which is both correct in dev and the safe default in production.

`PRIVACY_LEVEL` is removed on the same edit, not left alone.
`browser-openobserve-rum.tsx:96` calls `startSessionReplayRecording()`
unconditionally, and the component's own default is `mask-user-input` in both
dev and prod — `run.sh:717` is what downgrades it. With `allow`, DOM text and
user input are recorded unmasked and indefinitely, with no retention policy
(see Risk 3), in an application whose entire purpose is a personal media
library. Defaulting to `mask-user-input` is the only defensible posture.

### Decision 8: Decrypt failure is unset, and `get_value` honours its default

**Decision:** `decrypt_setting_value` returns `None` on `InvalidToken` instead
of the stored envelope, and `get_value` applies the caller's `default` to that
`None`.

Today `app/db/settings.py:167-169` returns the envelope, so after a
`SECRET_KEY` rotation `get_value("OPENOBSERVE_RUM_CLIENT_TOKEN")` returns a
`dict`. A consumer that ships that to the browser ships ciphertext to the
browser.

Two amendments are mandatory, because the first change alone is a regression:

- **`get_value` currently discards its `default`** (`settings.py:204` returns
  `decrypt_setting_value(...)` directly). Without
  `return default if val is None else val`, every `get_value(key, default)`
  call site silently loses its fallback.
- **Log the failure**, naming the key only, never the value. Otherwise a
  rotated `SECRET_KEY` becomes invisible.

This is strictly better, and `make migrate-secrets` becomes the answer to
task 6.3 with no new code: `migrate_env_secrets_to_db.py:130` treats a
non-`None` existing value as a conflict and skips. With `None` it overwrites
the row from `.env`, re-populating and re-encrypting. The same fall-through
repairs `config_service.py:63`, where `if val is not None` currently lets the
envelope win and be used *as a credential*.

The plaintext back-compat branch (`settings.py:155-157`) and the
malformed-envelope branch (159-161) must **not** change; they serve legacy
plaintext rows, and altering them changes the admin reveal path.

### Decision 9: `.env` permissions, fixed on the file that needs it

**Decision:** tighten `.env` (and the mode-specific `.env.*`) to `0600`, rather
than only tightening permissions after the RUM token write.

`.env` is currently mode `0664` and holds `SECRET_KEY`, `JWT_SECRET_KEY`,
`AUTH_SECRET`, `OPENOBSERVE_ROOT_PASSWORD` and `OPENOBSERVE_BASIC_AUTH` —
world-readable to any local user right now. `update_env_var:127` uses
`chmod --reference`, faithfully preserving the wide mode. Applying `0600` only
after the RUM token write would tighten the one credential that is public by
construction and leave the crown jewels. `0600` is also the mode already used
as the fallback at `run.sh:127`.

### Decision 10: Fail-soft, with a wall-clock bound

**Decision:** bounded by **wall-clock**, not iteration count; fail fast on
permanent errors.

The current loop is 30 iterations of `sleep 1` plus a `curl` with no
`--max-time`; curl's default connect timeout is 300s, so the worst case against
a blackholed port is ~2.5 hours before the frontend starts. Iteration counting
gives no latency bound; only a deadline does.

- Budget `RUM_READY_BUDGET_SECONDS`, default **20**, numerically guarded.
- Probe `/healthz` first (cheap, side-effect-free), then make a single
  `rumtoken` call — retrying only on 5xx and connection errors, never on 401,
  403, 404 or 3xx, which are permanent.
- Every terminal outcome returns `0`. `run.sh` deliberately runs without
  `set -e`, so a stray non-zero would leak into the caller's next status check.

### Decision 11: Logging that is safe by construction

**Decision:** a single greppable prefix, `rum-token:`, one line per outcome,
carrying enough to triage without a second command — outcome, reason, HTTP
status, target, attempt count, elapsed seconds, image version.

Two rules make the output trustworthy:

- **Never print a fingerprint.** No prefix, no length, no truncated hash. "It's
  just the first 8 characters" is partial disclosure of a bearer credential and
  produces a value-derived string in the log that a secret scanner will one day
  flag. `state=created|existing` is derived from a boolean equality against the
  already-loaded token and nothing more.
- **Never print a full `Location` header** on a redirect — log the host only,
  since a `Location` can carry the original query string.

`run.sh` has no logging framework and writes no deploy log of its own, so the
promise is scoped to the terminal/CI transcript.

## Risks / Trade-offs

1. **[Risk] Retention is unbounded and this is now an availability problem, not
   just a privacy one.** No `ZO_*` retention or stream setting exists anywhere
   in the repository. Because the token grants unauthenticated write, anyone who
   can read the bundle can write to the `openobserve_data` volume on the host
   disk until it is full — taking down Postgres, Redis and iqoqo with it. The
   loopback bind (`docker-compose.monitoring.yml:31`) is the **only** control
   preventing this, and this change does not touch it. It must be recorded as
   load-bearing, and configuring retention is a required follow-up before any
   long-lived or disk-constrained deployment.
2. **[Risk] The management endpoint is unverified against future OpenObserve
   versions.** Mitigated by a distinct 404 branch that names the image version
   in use and the version the endpoint was verified against
   (`openobserve/openobserve:v0.91.5`), so an image bump has something concrete
   to re-check. Verified against `v0.91.5` by the shipping call site.
3. **[Risk] RUM stays silently off and nobody notices.** Accepted. Every
   degradation path emits one actionable warning, and the not-run case warns
   with its reason. This is the correct trade against failing deployments.
4. **[Risk] `OPENOBSERVE_BASIC_AUTH` is visible in container environments.**
   `docker-compose.monitoring.yml:62` passes it to the collector, so `docker
   inspect` and `/proc/<pid>/environ` expose it to any local user. Fixing it
   needs a secrets file with `_FILE` indirection; documented, not built here.
5. **[Trade-off] A bounded wait adds up to ~20s of startup latency on the
   degraded path.** Accepted, and only elapsed when OpenObserve is actually
   absent or wedged. A container healthcheck would make this near-zero in the
   common case and is a follow-up.
6. **[Trade-off] Serving the token per request rather than freezing it into the
   bundle** means the value is present in the HTML payload. Accepted — it is a
   public credential by construction, and this is what makes prebuilt images
   work at all.
7. **[Trade-off] Removing the env-file write** means the token lives only in
   process memory for the current run, re-fetched on the next. Accepted: the
   get-or-create endpoint returns the same value, and it removes an
   injection-shaped write to a `source`d file.
8. **[Trade-off] `0600` on `.env`** breaks group-shared CI runners that expect
   group-read. Accepted; the alternative is world-readable key material.

## Migration Plan

1. Add `scripts/provision_rum_token.py` with the full fail-soft path and unit
   coverage; delete the bash implementation and its env-file writes.
2. Wire the script into the `dev` path after the monitoring stack starts.
3. Fix `.env` permissions and add the tracked-file guard inside
   `update_env_var`.
4. Convert `BrowserOpenObserveRum` to prop-driven configuration with the
   protocol-derived `insecureHTTP` default; read the token in the root layout.
5. Add the `preview`/`prod` path: `docker-compose.yml` environment, the
   `deploy/nginx.conf` `/rum/` route, and `ZO_CORS_ALLOWED_ORIGINS`.
6. Fix the `InstanceSettings` read path and document the `SECRET_KEY` rotation
   consequence.
7. Verify on a real instance: RUM reaches OpenObserve in **both** `dev` and
   `prod` mode, and the token is unchanged across a restart.

**No migration is required for existing deployments.** RUM was already
non-functional in `preview`/`prod`, and the hardcoded token was already removed
from `.env.test` and `frontend/.env.example`. This change can only turn a
currently-absent feature on. The one behaviour change is `.env` becoming
`0600`.