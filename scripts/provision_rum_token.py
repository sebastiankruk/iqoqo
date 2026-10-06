#!/usr/bin/env python3
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
"""Provision the per-instance OpenObserve RUM client token from its management API.

Replaces the inline bash implementation that used to live in ``run.sh``. The move
is a security fix, not a style preference — see ``design.md`` Decision 1:

* Credentials are read from ``os.environ`` only. The bash version interpolated
  ``OPENOBSERVE_ROOT_PASSWORD`` into Python source to build a Basic header,
  which put the root credential in a process argument list *and* broke on any
  password containing a quote (silently degrading into an unauthenticated
  request).
* ``http.client`` has no proxy support at all. ``.env`` is ``source``\\ d with
  ``set -o allexport``, so an ``HTTP_PROXY`` line there would otherwise become
  the host that receives the root Basic credential.
* ``HTTPConnection`` never follows redirects, so a 3xx cannot replay the
  credential to another host.
* ``response.status`` distinguishes 401/403/404/3xx/5xx directly, which
  ``grep -q rum_token`` on a response body cannot do.

The token is written to stdout **on its own line, by itself, and only on
success** so that ``run.sh`` can capture it. Every diagnostic goes to stderr
with a ``rum-token:`` prefix and NEVER contains the value, a prefix of the
value, its length, or a hash of it — a partial fingerprint of a bearer
credential is still a disclosure, and it produces a value-derived string in
deploy logs that a secret scanner will eventually flag.

The token is never written to any file. ``/api/default/rumtoken`` is a
server-side get-or-create, so a re-run returns the same value; persisting it
only added a plaintext copy to a file that ``run.sh`` later ``source``\\ s.
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_HOST_PORT = 5080
DEFAULT_BUDGET_SECONDS = 20
DEFAULT_CONNECT_TIMEOUT = 2.0
DEFAULT_REQUEST_TIMEOUT = 4.0
RETRY_BACKOFF_SECONDS = 1.0

RUMTOKEN_PATH = "/api/default/rumtoken"
HEALTHZ_PATH = "/healthz"

#: The management endpoint is always a loopback **literal**, never a hostname.
#: A hostname would have to be resolved to be verified and then resolved again
#: to be connected to, and /etc/hosts is mutable in between (check-then-use).
#: It is also IPv4 rather than "localhost" because docker-compose.monitoring.yml
#: binds 127.0.0.1 only, so getaddrinfo("localhost") tries ::1 first on a
#: dual-stack host and nothing is listening there.
LOOPBACK_HOST = "127.0.0.1"

#: Image tag this change was verified against. Named on the 404 branch so an
#: image bump has something concrete to re-check rather than degrading silently.
VERIFIED_AGAINST_IMAGE_TAG = "v0.91.5"
DEFAULT_IMAGE_TAG = "v0.91.5"

#: RUM client tokens are opaque URL-safe strings. We validate shape before use
#: so a hostile or corrupted response body can never be handed onward, and so an
#: HTML/JSON injection payload in the response is rejected at the boundary.
TOKEN_SHAPE = re.compile(r"\A[A-Za-z0-9_\-.=]{16,512}\Z")

#: Status codes that will never succeed on retry. Retrying them just burns the
#: startup budget and, for 401, resends the root credential repeatedly.
PERMANENT_STATUSES = frozenset({401, 403, 404})


class ProvisionError(Exception):
    """A terminal provisioning failure, safe to render to the operator.

    The message is composed only from operator-controlled values (status codes,
    image tags, variable names). Never interpolate the token, a token prefix,
    or the response body into it.
    """


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def log(outcome: str, reason: str | None = None, **fields: object) -> None:
    """Emit one greppable diagnostic line to stderr.

    Every field is rendered as ``key=value`` so an operator can answer "was RUM
    provisioned, and if not why" from the deploy log alone. Callers must not
    pass a credential in ``fields`` — nothing here redacts, by design: silent
    redaction would imply the value was safe to log in the first place.
    """
    parts = [f"rum-token: {outcome}"]
    if reason:
        parts.append(f"reason={reason}")
    for key, value in fields.items():
        if value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    print(" ".join(parts), file=sys.stderr)


# ---------------------------------------------------------------------------
# Configuration parsing
# ---------------------------------------------------------------------------


def resolve_port(raw: str | None) -> int:
    """Validate ``OPENOBSERVE_HOST_PORT`` as a plain integer in 1..65535.

    This is the guard that matters, not the host. The base URL is built from a
    fixed loopback literal, so the host cannot be influenced — but the port is
    interpolated, and an unvalidated value would be a URL-injection sink:
    ``OPENOBSERVE_HOST_PORT='5080@evil.example/x'`` would send a credentialed
    request off-box. Anything that is not an in-range decimal integer falls
    back to the default rather than being passed through.
    """
    if raw is None:
        return DEFAULT_HOST_PORT
    candidate = raw.strip()
    if not candidate or not candidate.isdigit():
        return DEFAULT_HOST_PORT
    try:
        port = int(candidate)
    except ValueError:  # pragma: no cover - isdigit() already guards this
        return DEFAULT_HOST_PORT
    if not 1 <= port <= 65535:
        return DEFAULT_HOST_PORT
    return port


def resolve_budget(raw: str | None) -> int:
    """Validate the wall-clock startup budget in seconds."""
    if raw is None:
        return DEFAULT_BUDGET_SECONDS
    candidate = raw.strip()
    if not candidate or not candidate.isdigit():
        return DEFAULT_BUDGET_SECONDS
    budget = int(candidate)
    if budget < 0:
        return DEFAULT_BUDGET_SECONDS
    return budget


def resolve_image_tag() -> str:
    """Read the OpenObserve image tag so the 404 branch can name it."""
    return os.environ.get("OPENOBSERVE_IMAGE_TAG", "").strip() or DEFAULT_IMAGE_TAG


def build_basic_auth() -> str | None:
    """Return a Basic credential read from the environment, or None.

    Precedence mirrors the previous bash implementation: a precomputed
    ``OPENOBSERVE_BASIC_AUTH`` wins, otherwise the root user/password pair is
    encoded here. Values are read from ``os.environ`` and never passed as
    arguments, so nothing lands in ``/proc/<pid>/cmdline`` or shell history.

    Returns None (rather than an empty string) when no credential is
    configured, so the caller can distinguish "no credential" from "credential
    that failed to encode".
    """
    precomputed = os.environ.get("OPENOBSERVE_BASIC_AUTH", "").strip()
    if precomputed:
        return precomputed

    user = os.environ.get("OPENOBSERVE_ROOT_USER", "")
    password = os.environ.get("OPENOBSERVE_ROOT_PASSWORD", "")
    if not user or not password:
        return None

    # Encoding happens here, in Python, on the raw values. The previous
    # implementation pasted these into a Python source string, so a password
    # containing an apostrophe raised a SyntaxError that 2>/dev/null swallowed,
    # leaving an empty header and 30 unauthenticated requests.
    raw = f"{user}:{password}".encode()
    return base64.b64encode(raw).decode("ascii")


# ---------------------------------------------------------------------------
# Ingest target validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestTarget:
    """A validated browser ingest target."""

    site: str
    insecure: bool
    topology: str

    def as_env(self) -> dict[str, str]:
        """Render as the environment variables the frontend reads."""
        return {
            "NEXT_PUBLIC_OPENOBSERVE_RUM_SITE": self.site,
            "NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP": "true" if self.insecure else "false",
        }


def _is_loopback_host(host: str) -> bool:
    """Return True when ``host`` is a loopback literal.

    Uses ``ipaddress`` rather than DNS resolution on purpose. ``ipaddress``
    refuses the decimal, octal and hexadecimal IPv4 spellings
    (``2130706433``, ``0177.0.0.1``, ``0x7f000001``) that ``socket`` resolves
    to 127.0.0.1, and it distinguishes the unspecified address from the
    loopback one, so ``0.0.0.0`` is refused.

    Only the bare name ``localhost`` is accepted. RFC 6761 says ``*.localhost``
    resolves to loopback, but this is an allowlist decision made at deploy time
    and a hostile /etc/hosts entry beats the convention.
    """
    import ipaddress

    normalized = host.strip().lower().rstrip(".")
    if normalized.endswith("]"):
        normalized = normalized[1:-1]

    if normalized == "localhost":
        return True

    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return address.is_loopback and not address.is_unspecified


def validate_ingest_site(
    site: str,
    public_origin: str | None,
    *,
    local_only: bool = True,
) -> IngestTarget:
    """Validate a browser ingest target, or raise ProvisionError.

    ``site`` is a host[:port] authority, optionally prefixed with a scheme.
    The OpenObserve SDK's ``site`` contract is a bare authority with no scheme
    — which is why ``browser-openobserve-rum.tsx`` passes
    ``window.location.host`` — so a scheme-less value such as
    ``localhost:5080`` is the normal, correct form and must be accepted.

    Where a scheme *is* given it is enforced: ``http://`` to a non-loopback host
    is refused, because that sends the token in cleartext across the internet.
    A scheme-less non-loopback host is refused too, since the transport cannot
    be inferred safely and the whole point of this check is that plaintext is
    opt-in only on loopback.

    Parsed with ``urlsplit`` rather than a regex: a regex over the whole string
    is defeated by ``https://good.example@evil.example/``, whose ``hostname`` is
    ``evil.example`` while a naive pattern would match the expected name.

    ``local_only`` declares whether this deployment is the operator's own bare
    machine. When it is not, a loopback target is refused: the end user's
    browser resolves ``localhost`` to *their own computer* and POSTs the token
    in cleartext to whatever listens on their port 5080. That is exactly what
    the previous unconditional ``SITE=localhost:5080`` override caused on every
    non-local deployment.
    """
    raw = (site or "").strip()
    if not raw:
        raise ProvisionError("ingest site is empty")

    scheme: str | None = None
    candidate = raw
    if "://" in raw:
        try:
            parts = urlsplit(raw)
        except ValueError as exc:
            raise ProvisionError(f"ingest site is not a valid URL: {exc}") from exc
        if parts.scheme not in ("http", "https"):
            raise ProvisionError(f"ingest site scheme must be http or https, got {parts.scheme!r}")
        scheme = parts.scheme
        candidate = raw.split("://", 1)[1]

    # Re-check the authority form for userinfo and path/query/fragment.
    try:
        parts = urlsplit(f"//{candidate}")
    except ValueError as exc:
        raise ProvisionError(f"ingest site is not a valid authority: {exc}") from exc

    if parts.username or parts.password:
        raise ProvisionError("ingest site must not carry userinfo")
    if parts.path not in ("", "/"):
        raise ProvisionError("ingest site must not carry a path")
    if parts.query or parts.fragment:
        raise ProvisionError("ingest site must not carry a query or fragment")

    try:
        port = parts.port
    except ValueError as exc:
        # urlsplit defers port parsing; an out-of-range port raises here.
        raise ProvisionError(f"ingest site port is invalid: {exc}") from exc

    host = parts.hostname
    if not host:
        raise ProvisionError("ingest site has no host")

    authority = f"{host}:{port}" if port else host

    if _is_loopback_host(host):
        if not local_only:
            raise ProvisionError(
                f"ingest site {authority!r} is a loopback address but this deployment is not "
                "local-only; the end user's browser would send the token to their own machine. "
                "Configure the deployment's own public origin instead."
            )
        # Plaintext is acceptable here and only here: this is the bare `dev`
        # topology, where the browser and OpenObserve share the operator's own
        # machine. Opt out for a caller that wants the uniform secure default.
        insecure = os.environ.get("RUM_ALLOW_INSECURE_LOOPBACK", "true").strip().lower() != "false"
        return IngestTarget(site=authority, insecure=insecure, topology="loopback")

    if not public_origin:
        raise ProvisionError(f"ingest site {authority!r} is not loopback and no public origin is configured")

    if scheme != "https":
        # Either an explicit http://, or no scheme at all — in both cases the
        # transport is plaintext or unknown, which is not acceptable off-box.
        raise ProvisionError(
            f"refusing plaintext or unknown-transport ingest to non-loopback host {authority!r}; "
            "use an https:// URL for this deployment's own public origin"
        )

    # Compare literal normalised strings. Resolving either side, or comparing
    # resolved IPs, would open a rebinding window: this process and the
    # browser resolve independently, so any name that is safe here and
    # attacker-controlled at page-load time is a live bypass.
    if _normalise_authority(public_origin) != _normalise_authority(authority):
        raise ProvisionError(f"ingest site {authority!r} is neither loopback nor this deployment's own public origin")

    return IngestTarget(site=authority, insecure=False, topology="public-origin")


def _normalise_authority(authority: str) -> str:
    """Reduce a URL or a bare ``host[:port]`` to a normalised authority.

    Accepting a full URL here is convenient for the caller (an operator's
    ``NEXT_PUBLIC_FRONTEND_URL``), so the scheme and any path are stripped
    rather than required to be absent.
    """
    value = authority.strip().lower().rstrip(".")
    if "://" in value:
        try:
            parts = urlsplit(value)
        except ValueError:
            return value
        host = parts.hostname or ""
        try:
            port = parts.port
        except ValueError:
            return value
        value = f"[{host}]:{port}" if (":" in host and port) else (f"{host}:{port}" if port else host)
    if value.startswith("[") and "]" in value:
        host, _, remainder = value.partition("]")
        return f"{host}]{remainder}".rstrip(":")
    return value.rstrip(":")


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HttpResult:
    """A management-endpoint response.

    The status is retained rather than inferred from the body: the previous
    implementation grepped the body for "rum_token", which cannot tell a 401
    from a 404 from a 3xx from a 5xx, and that distinction is the whole point of
    the per-failure-class diagnostics.
    """

    status: int
    body: str


def _request(
    path: str,
    port: int,
    auth: str | None,
    timeout: float,
) -> HttpResult:
    """Perform one request against the loopback management endpoint.

    Uses ``http.client.HTTPConnection`` deliberately:

    * No proxy support — an ``HTTP_PROXY`` exported from ``.env`` cannot
      intercept the root Basic credential.
    * No redirect following — a 3xx is returned to the caller as a failure.
    * The ``Authorization`` header lives only in this process's memory. It never
      reaches an argument list, a shell, or a temp file.
    """
    connection = http.client.HTTPConnection(LOOPBACK_HOST, port, timeout=timeout)
    try:
        headers = {"Accept": "application/json"}
        if auth:
            headers["Authorization"] = f"Basic {auth}"
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read(65536).decode("utf-8", errors="replace")
        return HttpResult(status=response.status, body=body)
    finally:
        connection.close()


def wait_until_ready(port: int, deadline: float) -> bool:
    """Poll ``/healthz`` until the container answers or the budget is spent.

    Separating readiness from provisioning avoids hammering a *mutating*
    get-or-create endpoint: readiness is cheap and side-effect free, so we probe
    that first and then issue a single token call.
    """
    while True:
        try:
            result = _request(HEALTHZ_PATH, port, auth=None, timeout=DEFAULT_REQUEST_TIMEOUT)
            if 200 <= result.status < 500:
                return True
        except (OSError, http.client.HTTPException):
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(RETRY_BACKOFF_SECONDS)


def fetch_rum_token(port: int, auth: str | None, deadline: float) -> str:
    """Fetch the RUM client token, degrading with a distinct reason on failure.

    Raises ProvisionError with an operator-safe message. Retries only on 5xx
    and connection errors — 401/403/404/3xx are permanent and retrying them
    both wastes the startup budget and resends the root credential.
    """
    attempts = 0

    while True:
        attempts += 1
        try:
            result = _request(RUMTOKEN_PATH, port, auth, DEFAULT_REQUEST_TIMEOUT)
        except (OSError, http.client.HTTPException) as exc:
            log("DEGRADED", "unreachable", attempts=attempts, detail=type(exc).__name__)
            if time.monotonic() >= deadline:
                raise ProvisionError(f"OpenObserve unreachable after {attempts} attempt(s)") from exc
            time.sleep(RETRY_BACKOFF_SECONDS)
            continue

        status = result.status
        if 200 <= status < 300:
            token = _extract_token(result.body)
            if token is None:
                raise ProvisionError("endpoint returned 2xx with no rum_token field")
            return token

        if status in (401, 403):
            raise ProvisionError("authentication rejected; check OPENOBSERVE_BASIC_AUTH or OPENOBSERVE_ROOT_USER/OPENOBSERVE_ROOT_PASSWORD")
        if status == 404:
            raise ProvisionError(f"management route {RUMTOKEN_PATH} absent on image tag {resolve_image_tag()}")
        if 300 <= status < 400:
            # Not followed, on purpose: a redirected credentialed request would
            # replay the root Basic credential to whatever host the 3xx names.
            location_host = _location_host(result.body)
            raise ProvisionError(f"endpoint returned {status} redirect; not followed (location host: {location_host})")
        if status in PERMANENT_STATUSES:
            raise ProvisionError(f"endpoint returned {status}")

        log("DEGRADED", "server-error", status=status, attempts=attempts)
        if time.monotonic() >= deadline:
            raise ProvisionError(f"endpoint returned {status} after {attempts} attempt(s)")
        time.sleep(RETRY_BACKOFF_SECONDS)


def _extract_token(body: str) -> str | None:
    """Extract and shape-validate ``data.rum_token`` from a response body.

    Returns None when the field is absent, not a string, or fails the shape
    check. A sentinel is never produced here: the value flows to the caller
    unlogged, and an exception raised from this function must never carry it.
    """
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    token = data.get("rum_token")
    if not isinstance(token, str):
        return None
    if not TOKEN_SHAPE.match(token):
        return None
    return token


def _location_host(body: str) -> str:
    """Return only the host of a redirect target, never the full URL.

    A Location header can carry the original query string, which may hold user
    data, so it is reduced to a hostname before being logged.
    """
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return "unknown"
    if not isinstance(payload, dict):
        return "unknown"
    location = payload.get("location")
    if not isinstance(location, str):
        return "unknown"
    try:
        host = urlsplit(location).hostname
    except ValueError:
        return "unknown"
    return host or "unknown"


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def resolve_browser_target(port: int) -> IngestTarget | None:
    """Decide the ingest target the browser should be pointed at.

    Reads the configured ingest site and the deployment's own public origin,
    and returns None when no target is acceptable — in which case RUM must be
    left disabled rather than handed an unsafe destination.
    """
    site = os.environ.get("OPENOBSERVE_RUM_SITE", "").strip()
    if not site:
        # No site configured: the frontend defaults to the host of the page the
        # SDK runs on, which is the safest available answer. We still validate
        # the resulting topology so a non-local deployment gets an explicit
        # diagnostic instead of a silent assumption.
        local_only = resolve_local_only()
        if not local_only:
            log("DEGRADED", "ingest-site-unset", hint="set OPENOBSERVE_RUM_SITE to this deployment's public origin")
            return None
        return IngestTarget(site=f"{LOOPBACK_HOST}:{port}", insecure=True, topology="loopback")

    public_origin = os.environ.get("NEXT_PUBLIC_FRONTEND_URL", "").strip() or os.environ.get("NEXTAUTH_URL", "").strip()
    try:
        return validate_ingest_site(site, public_origin or None, local_only=resolve_local_only())
    except ProvisionError as exc:
        log("DEGRADED", "ingest-site-rejected", detail=str(exc))
        return None


def resolve_local_only() -> bool:
    """Return True when this deployment is the operator's own bare machine.

    ``dev`` is the bare-host topology: Flask, Next.js and OpenObserve all run on
    the operator's machine, so a loopback ingest target is correct. ``preview``
    and ``prod`` are dockerized and reached over the network by other people's
    browsers, where a loopback target would send the token to each visitor's
    own computer.
    """
    raw = os.environ.get("RUM_LOCAL_ONLY")
    if raw is not None:
        return raw.strip().lower() != "false"
    return os.environ.get("MODE", "dev").strip() == "dev"


def provision(*, budget_seconds: int | None = None) -> int:
    """Provision the token and write KEY=VALUE lines to stdout. Always returns 0.

    RUM is optional telemetry. No failure mode here may abort a deployment, so
    every path returns 0 and leaves RUM disabled.
    """
    port = resolve_port(os.environ.get("OPENOBSERVE_HOST_PORT"))
    budget = budget_seconds if budget_seconds is not None else resolve_budget(os.environ.get("RUM_READY_BUDGET_SECONDS"))
    auth = build_basic_auth()
    if not auth:
        log("DEGRADED", "no-credential", hint="set OPENOBSERVE_BASIC_AUTH or OPENOBSERVE_ROOT_USER/PASSWORD")
        return 0

    started = time.monotonic()
    deadline = started + budget

    if not wait_until_ready(port, deadline):
        log("DEGRADED", "not-ready", target=f"{LOOPBACK_HOST}:{port}", budget_s=budget)
        return 0

    try:
        token = fetch_rum_token(port, auth, deadline)
    except ProvisionError as exc:
        # The message is composed from operator-controlled values only; the
        # token is never in scope here, so it cannot leak through it.
        log(
            "DEGRADED",
            "provision-failed",
            target=f"{LOOPBACK_HOST}:{port}",
            image=resolve_image_tag(),
            verified_against=VERIFIED_AGAINST_IMAGE_TAG,
            elapsed_s=round(time.monotonic() - started, 1),
            detail=str(exc),
        )
        return 0

    # Machine-readable output goes to stdout as KEY=VALUE lines so the caller
    # can consume it in a single invocation. Diagnostics go to stderr, which the
    # caller leaves inherited so they land in the deploy log — never in the
    # captured value.
    #
    # The token is deliberately NOT echoed to the terminal. The prior
    # implementation printed it, putting a live bearer credential into terminal
    # scrollback, script(1) captures and CI logs on every single deploy.
    existing = os.environ.get("OPENOBSERVE_RUM_CLIENT_TOKEN", "").strip()
    state = "existing" if token == existing else "created"

    target = resolve_browser_target(port)
    if target is None:
        # The credential is valid but there is nowhere safe to send it. Leave
        # RUM disabled rather than hand the browser an unsafe ingest target.
        log(
            "DEGRADED",
            "ingest-site-rejected",
            target=f"{LOOPBACK_HOST}:{port}",
            elapsed_s=round(time.monotonic() - started, 1),
        )
        return 0

    print(f"RUM_CLIENT_TOKEN={token}")
    print(f"RUM_SITE={target.site}")
    print(f"RUM_INSECURE_HTTP={'true' if target.insecure else 'false'}")
    print(f"RUM_TOPOLOGY={target.topology}")

    log(
        "PROVISIONED",
        state,
        ingest_site=target.site,
        topology=target.topology,
        insecure="true" if target.insecure else "false",
        mgmt_target=f"{LOOPBACK_HOST}:{port}",
        image=resolve_image_tag(),
        elapsed_s=round(time.monotonic() - started, 1),
    )
    return 0


def load_env_file(path: str) -> int:
    """Load ``KEY=value`` pairs from a dotenv file into ``os.environ``.

    Existing environment variables win, matching how ``run.sh`` behaves when it
    ``source``s an env file: the file fills in what is missing rather than
    overriding a value the operator already exported.

    Needed so the Makefile deploy targets (``make preview-up``) can drive this
    step directly. Those call ``docker compose`` without going through
    ``run.sh``, so without this they would have no way to reach the OpenObserve
    credentials and RUM would silently never be provisioned.
    """
    target = Path(path)
    if not target.is_file():
        log("DEGRADED", "env-file-missing", path=path)
        return 1

    for raw_line in target.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=None,
        help="Load OpenObserve credentials and RUM settings from this dotenv file.",
    )
    parser.add_argument(
        "--budget-seconds",
        type=int,
        default=None,
        help="Wall-clock budget for the readiness wait (default: env or 20).",
    )
    args = parser.parse_args(argv)

    if args.env_file and load_env_file(args.env_file) != 0:
        return 0

    return provision(budget_seconds=args.budget_seconds)


if __name__ == "__main__":
    sys.exit(main())
