"""Tests for the OpenObserve RUM client-token provisioner.

The provisioner replaces an inline bash block that echoed a live bearer
credential to stdout on every deploy. The invariants locked here are:

* the token value never reaches a diagnostic line, on **any** path;
* the management request cannot be redirected, proxied, or pointed off-box;
* the ingest target is validated before any credential is handed to the browser.
"""

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
#

from __future__ import annotations

import base64
import http.client
import json
import socket

import pytest

from scripts import provision_rum_token as prt

# A syntactically plausible token. The shape check requires >=16 chars.
SENTINEL = "SENTINEL-RUM-TOKEN-a1b2c3d4e5f6g7h8"


def _basic_auth(user: str = "root", password: str = "rum-fixture-password") -> str:
    """Base64(user:password), computed rather than committed.

    A hardcoded base64 credential literal in a tracked test file is a
    credential-shaped string that gitleaks flags, which trains reviewers to
    ignore the scanner. Deriving it keeps the fixture honest and the scanner
    quiet without an allowlist that would also hide a real leak.
    """
    return base64.b64encode(f"{user}:{password}".encode()).decode()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Clear every variable the provisioner reads.

    The developer's shell environment must not decide what these tests assert.
    """
    for name in (
        "OPENOBSERVE_BASIC_AUTH",
        "OPENOBSERVE_ROOT_USER",
        "OPENOBSERVE_ROOT_PASSWORD",
        "OPENOBSERVE_HOST_PORT",
        "OPENOBSERVE_RUM_CLIENT_TOKEN",
        "OPENOBSERVE_RUM_SITE",
        "OPENOBSERVE_IMAGE_TAG",
        "NEXT_PUBLIC_FRONTEND_URL",
        "NEXTAUTH_URL",
        "MODE",
        "RUM_LOCAL_ONLY",
        "RUM_READY_BUDGET_SECONDS",
        "RUM_ALLOW_INSECURE_LOOPBACK",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENOBSERVE_BASIC_AUTH", _basic_auth())
    monkeypatch.setenv("RUM_READY_BUDGET_SECONDS", "0")


def _ok_body(token: str = SENTINEL) -> str:
    return json.dumps({"data": {"rum_token": token}})


def _stub(monkeypatch, *, status: int = 200, body: str | None = None, paths=("/healthz", "/api/default/rumtoken")):
    """Patch _request so every path returns the same canned response."""
    calls: list[str] = []

    def fake_request(path, port, auth, timeout):
        calls.append(path)
        if path not in paths and paths is not None:
            raise ConnectionRefusedError
        if body is not None and path == prt.RUMTOKEN_PATH:
            return prt.HttpResult(status=status, body=body)
        if path == prt.HEALTHZ_PATH:
            return prt.HttpResult(status=200, body="OK")
        return prt.HttpResult(status=status, body=body if body is not None else _ok_body())

    monkeypatch.setattr(prt, "_request", fake_request)
    return calls


# ---------------------------------------------------------------------------
# Port resolution — the injection guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, 5080),
        ("", 5080),
        ("5081", 5081),
        ("  5081  ", 5081),
        # Not a plain decimal integer -> default, never passed through.
        ("5080@evil.example/x", 5080),
        ("http://evil.example", 5080),
        ("0", 5080),
        ("65536", 5080),
        ("-1", 5080),
        ("8080; rm -rf /", 5080),
        ("0x1f90", 5080),
        ("999999999999999999999", 5080),
    ],
)
def test_resolve_port_rejects_anything_not_an_in_range_integer(raw, expected):
    assert prt.resolve_port(raw) == expected


def test_management_url_is_a_loopback_literal_not_a_resolvable_name():
    """A hostname would be resolved twice — once to verify, once to connect.

    There is no name here at all, so the check-then-use window cannot exist.
    """
    assert prt.LOOPBACK_HOST == "127.0.0.1"


def test_request_targets_the_literal_and_passes_no_proxy(monkeypatch):
    """http.client has no proxy support; an exported HTTP_PROXY cannot intercept."""
    captured = {}

    class FakeConn:
        def __init__(self, host, port, timeout=None):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def request(self, method, path, headers=None):
            captured["headers"] = headers

        def getresponse(self):
            class R:
                status = 200

                @staticmethod
                def read(_n):
                    return _ok_body().encode()

            return R()

        def close(self):
            pass

    monkeypatch.setenv("HTTP_PROXY", "http://evil.example:3128")
    monkeypatch.setenv("ALL_PROXY", "socks5://evil.example:1080")
    monkeypatch.setattr(http.client, "HTTPConnection", FakeConn)

    result = prt._request(prt.RUMTOKEN_PATH, 5081, "Y3JlZA==", 4.0)

    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 5081
    assert result.status == 200
    # No proxy-related keyword was accepted at all — the fake's signature has
    # no room for one, mirroring http.client's real constructor.


def test_authorization_header_is_built_in_python_not_passed_through_a_shell():
    """A password with a quote used to produce an unauthenticated request."""
    import base64
    import os

    os.environ["OPENOBSERVE_BASIC_AUTH"] = ""
    os.environ["OPENOBSERVE_ROOT_USER"] = "admin@iqoqo.local"
    os.environ["OPENOBSERVE_ROOT_PASSWORD"] = "pa'ss'w\\ord\"with`stuff`"
    try:
        auth = prt.build_basic_auth()
        assert auth is not None
        decoded = base64.b64decode(auth).decode()
        assert decoded == "admin@iqoqo.local:pa'ss'w\\ord\"with`stuff`"
    finally:
        del os.environ["OPENOBSERVE_ROOT_USER"]
        del os.environ["OPENOBSERVE_ROOT_PASSWORD"]
        os.environ["OPENOBSERVE_BASIC_AUTH"] = _basic_auth()


def test_basic_auth_prefers_precomputed_value(monkeypatch):
    monkeypatch.setenv("OPENOBSERVE_BASIC_AUTH", _basic_auth("precomputed"))
    monkeypatch.setenv("OPENOBSERVE_ROOT_USER", "ignored")
    monkeypatch.setenv("OPENOBSERVE_ROOT_PASSWORD", "ignored")
    assert prt.build_basic_auth() == _basic_auth("precomputed")


def test_basic_auth_returns_none_when_nothing_configured(monkeypatch):
    monkeypatch.delenv("OPENOBSERVE_BASIC_AUTH", raising=False)
    assert prt.build_basic_auth() is None


# ---------------------------------------------------------------------------
# Status-code branches
# ---------------------------------------------------------------------------


def test_successful_provisioning_emits_machine_readable_output(monkeypatch, capsys):
    _stub(monkeypatch)
    assert prt.provision() == 0
    captured = capsys.readouterr()
    fields = dict(line.split("=", 1) for line in captured.out.strip().splitlines() if "=" in line)
    assert fields["RUM_CLIENT_TOKEN"] == SENTINEL
    # The default dev topology: loopback, plaintext permitted.
    assert fields["RUM_SITE"] == "127.0.0.1:5080"
    assert fields["RUM_INSECURE_HTTP"] == "true"
    assert fields["RUM_TOPOLOGY"] == "loopback"
    # The diagnostic reports state, never a value or a fingerprint of one.
    assert "rum-token: PROVISIONED" in captured.err
    assert SENTINEL not in captured.err
    assert SENTINEL[:8] not in captured.err


def test_reused_token_is_reported_as_existing(monkeypatch, capsys):
    monkeypatch.setenv("OPENOBSERVE_RUM_CLIENT_TOKEN", SENTINEL)
    _stub(monkeypatch)
    assert prt.provision() == 0
    captured = capsys.readouterr()
    assert "reason=existing" in captured.err
    assert SENTINEL not in captured.err


def test_output_never_contains_a_bare_token_line(monkeypatch, capsys):
    """The caller parses KEY=VALUE; a bare value would be ambiguous."""
    _stub(monkeypatch)
    prt.provision()
    for line in capsys.readouterr().out.strip().splitlines():
        assert "=" in line, f"bare token on stdout: {line!r}"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "authentication rejected"),
        (403, "authentication rejected"),
        (404, "absent on image tag"),
        (301, "redirect; not followed"),
        (302, "redirect; not followed"),
        (500, "returned 500"),
        (503, "returned 503"),
    ],
)
def test_each_failure_class_is_diagnosed_distinctly(monkeypatch, capsys, status, expected):
    monkeypatch.setenv("RUM_READY_BUDGET_SECONDS", "1")
    _stub(monkeypatch, status=status, body='{"message":"no"}')
    assert prt.provision() == 0
    err = capsys.readouterr().err
    assert expected in err
    # stdout stays empty on every failure path.
    assert capsys.readouterr().out == ""


def test_401_names_the_credential_variable(monkeypatch, capsys):
    """The most likely real-world failure deserves an actionable message."""
    _stub(monkeypatch, status=401, body="{}")
    prt.provision()
    err = capsys.readouterr().err
    assert "OPENOBSERVE_BASIC_AUTH" in err
    assert "OPENOBSERVE_ROOT_USER" in err


def test_404_names_the_image_version_and_the_verified_version(monkeypatch, capsys):
    _stub(monkeypatch, status=404, body="{}")
    prt.provision()
    err = capsys.readouterr().err
    assert "v0.91.5" in err
    assert f"verified_against={prt.VERIFIED_AGAINST_IMAGE_TAG}" in err


def test_404_reports_a_mismatched_image_tag(monkeypatch, capsys):
    monkeypatch.setenv("OPENOBSERVE_IMAGE_TAG", "v0.99.0")
    _stub(monkeypatch, status=404, body="{}")
    prt.provision()
    assert "v0.99.0" in capsys.readouterr().err


def test_redirect_location_is_reduced_to_a_host(monkeypatch, capsys):
    """A Location header can carry the original query string."""
    _stub(
        monkeypatch,
        status=302,
        body=json.dumps({"location": "https://evil.example/ingest?token=SECRET-QUERY"}),
    )
    prt.provision()
    err = capsys.readouterr().err
    assert "evil.example" in err
    assert "SECRET-QUERY" not in err
    assert "https://evil.example/ingest" not in err


def test_transient_server_error_is_retried_within_budget(monkeypatch, capsys):
    monkeypatch.setenv("RUM_READY_BUDGET_SECONDS", "5")
    attempts = {"n": 0}

    def fake_request(path, port, auth, timeout):
        if path == prt.HEALTHZ_PATH:
            return prt.HttpResult(status=200, body="OK")
        attempts["n"] += 1
        if attempts["n"] < 3:
            return prt.HttpResult(status=503, body="{}")
        return prt.HttpResult(status=200, body=_ok_body())

    monkeypatch.setattr(prt, "_request", fake_request)
    monkeypatch.setattr(prt.time, "sleep", lambda _s: None)
    assert prt.provision() == 0
    assert attempts["n"] == 3
    assert "rum-token: PROVISIONED" in capsys.readouterr().err


def test_permanent_errors_are_not_retried(monkeypatch, capsys):
    """Retrying a 401 both wastes the budget and resends the root credential."""
    calls = {"n": 0}

    def fake_request(path, port, auth, timeout):
        calls["n"] += 1
        return prt.HttpResult(status=401, body="{}")

    monkeypatch.setattr(prt, "_request", fake_request)
    monkeypatch.setattr(prt.time, "sleep", lambda _s: None)
    prt.provision()
    # healthz + exactly one rumtoken attempt
    assert calls["n"] == 2


@pytest.mark.parametrize(
    "body",
    [
        "not json at all",
        "{}",
        '{"data": {}}',
        '{"data": {"rum_token": 12345}}',
        '{"data": {"rum_token": null}}',
        '{"data": "not-an-object"}',
        "[1, 2, 3]",
        "",
    ],
)
def test_malformed_or_unusable_bodies_degrade_without_leaking(monkeypatch, capsys, body):
    _stub(monkeypatch, status=200, body=body)
    assert prt.provision() == 0
    captured = capsys.readouterr()
    assert "no rum_token" in captured.err
    assert captured.out.strip() == ""


def test_token_of_the_wrong_shape_is_rejected(monkeypatch, capsys):
    """A hostile response body must not flow onward unvalidated."""
    _stub(monkeypatch, status=200, body=json.dumps({"data": {"rum_token": "short"}}))
    assert prt.provision() == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    assert "no rum_token" in captured.err


def test_unreachable_endpoint_is_bounded_by_wall_clock(monkeypatch, capsys):
    monkeypatch.setenv("RUM_READY_BUDGET_SECONDS", "0")

    def fake_request(path, port, auth, timeout):
        raise ConnectionRefusedError("nope")

    monkeypatch.setattr(prt, "_request", fake_request)
    assert prt.provision() == 0
    err = capsys.readouterr().err
    assert "reason=not-ready" in err
    assert "budget_s=0" in err


def test_connection_error_during_token_fetch_degrades(monkeypatch, capsys):
    def fake_request(path, port, auth, timeout):
        if path == prt.HEALTHZ_PATH:
            return prt.HttpResult(status=200, body="OK")
        raise TimeoutError("timed out")

    monkeypatch.setattr(prt, "_request", fake_request)
    assert prt.provision() == 0
    assert "unreachable" in capsys.readouterr().err


def test_no_credential_configured_degrades(monkeypatch, capsys):
    monkeypatch.delenv("OPENOBSERVE_BASIC_AUTH", raising=False)
    assert prt.provision() == 0
    err = capsys.readouterr().err
    assert "no-credential" in err
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# The no-leak invariant, across every path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, _ok_body()),
        (401, "{}"),
        (403, "{}"),
        (404, "{}"),
        (302, json.dumps({"location": "https://evil.example/x"})),
        (500, _ok_body()),
        (200, "malformed"),
    ],
)
def test_sentinel_never_appears_in_a_diagnostic(monkeypatch, capsys, status, body):
    """No captured diagnostic may contain the token on any path."""
    _stub(monkeypatch, status=status, body=body)
    prt.provision()
    err = capsys.readouterr().err
    assert SENTINEL not in err
    # Also assert against a common partial-disclosure mistake.
    assert SENTINEL[:8] not in err


def test_sentinel_never_escapes_through_a_parse_failure(monkeypatch, capsys):
    """A body carrying the token in an unusable position must not surface it.

    This is the shape of the original bug in miniature: a value arrives inside a
    response and an implementation hands it onward (or into a message) without
    having validated it first.
    """
    _stub(
        monkeypatch,
        status=200,
        body=json.dumps({"data": {"rum_token": {"nested": SENTINEL}}}),
    )
    assert prt.provision() == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    assert SENTINEL not in captured.err


def test_log_helper_renders_key_value_pairs(capsys):
    prt.log("DEGRADED", "route-missing", status=404, image="v0.91.5")
    err = capsys.readouterr().err
    assert err.strip() == "rum-token: DEGRADED reason=route-missing status=404 image=v0.91.5"


# ---------------------------------------------------------------------------
# Ingest target validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "site",
    [
        "http://127.0.0.1:5080",
        "http://127.1.2.3:5080",
        "http://[::1]:5080",
        "http://localhost:5080",
        "http://LOCALHOST.:5080",
    ],
)
def test_loopback_sites_are_accepted(site):
    target = prt.validate_ingest_site(site, public_origin=None)
    assert target.topology == "loopback"
    assert target.insecure is True


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "[::]", "2130706433", "0177.0.0.1", "0x7f000001"])
def test_unspecified_and_obfuscated_addresses_are_refused(host):
    with pytest.raises(prt.ProvisionError):
        prt.validate_ingest_site(f"http://{host}:5080", public_origin=None)


def test_wildcard_localhost_is_refused():
    """RFC 6761 says *.localhost is loopback; a hostile /etc/hosts beats that."""
    with pytest.raises(prt.ProvisionError):
        prt.validate_ingest_site("http://evil.localhost:5080", public_origin=None)


@pytest.mark.parametrize(
    "site",
    [
        "",
        "   ",
        "/rum",  # relative
        "ftp://localhost:5080",  # wrong scheme
        "file:///etc/passwd",
        "https://user:pw@localhost:5080",  # userinfo
        "https://good.example@evil.example/",  # the @ trick
        "http://localhost:5080/api/default",  # path
        "http://localhost:5080/?a=b",  # query
        "http://localhost:5080/#frag",  # fragment
    ],
)
def test_malformed_sites_are_refused(site):
    with pytest.raises(prt.ProvisionError):
        prt.validate_ingest_site(site, public_origin=None)


@pytest.mark.parametrize(
    "site",
    [
        "localhost:5080",
        "127.0.0.1:5080",
        "127.0.0.1",
        "[::1]:5080",
        # Trailing slash is tolerated; the SDK ignores it.
        "http://localhost:5080/",
    ],
)
def test_scheme_less_loopback_authority_is_accepted(site):
    """The OpenObserve SDK's `site` is a bare host[:port] with no scheme.

    browser-openobserve-rum.tsx passes `window.location.host`, which has no
    scheme, and every pre-existing .env in the wild carries `localhost:5080`.
    Requiring a scheme here would reject the normal form and silently disable
    RUM everywhere. This was found by running against a live instance.
    """
    target = prt.validate_ingest_site(site, public_origin=None)
    assert target.topology == "loopback"
    # Emitted without a scheme, which is what the SDK expects.
    assert "://" not in target.site


@pytest.mark.parametrize("site", ["iqoqo.example", "iqoqo.example:443", "evil.example"])
def test_scheme_less_non_loopback_authority_is_refused(site):
    """No scheme off-box means an unknown transport, which is not acceptable."""
    with pytest.raises(prt.ProvisionError, match="plaintext or unknown-transport"):
        prt.validate_ingest_site(site, public_origin="https://iqoqo.example")


def test_bare_authority_with_userinfo_is_refused():
    with pytest.raises(prt.ProvisionError, match="userinfo"):
        prt.validate_ingest_site("user:pw@localhost:5080", public_origin=None)


def test_userinfo_trick_resolves_to_the_attacking_host():
    """A naive regex would match "good.example" here; urlsplit does not."""
    parts = prt.urlsplit("https://good.example@evil.example/")
    assert parts.hostname == "evil.example"


def test_public_origin_accepted_over_https():
    target = prt.validate_ingest_site("https://iqoqo.example", public_origin="https://iqoqo.example")
    assert target.topology == "public-origin"
    assert target.insecure is False
    assert target.as_env()["NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP"] == "false"


def test_public_origin_refused_over_plaintext():
    """Plaintext ingest to a non-loopback host sends the token in the clear."""
    with pytest.raises(prt.ProvisionError, match="plaintext"):
        prt.validate_ingest_site("http://iqoqo.example", public_origin="https://iqoqo.example")


def test_a_different_public_origin_is_refused():
    with pytest.raises(prt.ProvisionError):
        prt.validate_ingest_site("https://evil.example", public_origin="https://iqoqo.example")


def test_non_loopback_without_a_configured_public_origin_is_refused():
    with pytest.raises(prt.ProvisionError, match="public origin"):
        prt.validate_ingest_site("https://iqoqo.example", public_origin=None)


def test_loopback_still_works_when_a_public_origin_is_configured():
    """The bare dev topology must survive an operator configuring a public one."""
    target = prt.validate_ingest_site("http://127.0.0.1:5080", public_origin="https://iqoqo.example")
    assert target.topology == "loopback"


# ---------------------------------------------------------------------------
# Local-only deployment gating
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "site",
    ["http://localhost:5080", "http://127.0.0.1:5080", "http://[::1]:5080"],
)
def test_loopback_is_refused_on_a_non_local_only_deployment(site):
    """The end user's browser would send the token to their own machine."""
    with pytest.raises(prt.ProvisionError, match="not local-only"):
        prt.validate_ingest_site(site, public_origin=None, local_only=False)


def test_public_origin_is_accepted_on_a_non_local_only_deployment():
    target = prt.validate_ingest_site("https://iqoqo.example", public_origin="https://iqoqo.example", local_only=False)
    assert target.topology == "public-origin"
    assert target.insecure is False


def test_non_local_deployment_with_only_a_loopback_site_is_refused_end_to_end():
    """Neither topology available => the deployment must refuse, not guess."""
    with pytest.raises(prt.ProvisionError):
        prt.validate_ingest_site("http://localhost:5080", public_origin=None, local_only=False)


def test_local_only_deployment_refuses_a_public_origin_it_does_not_own():
    with pytest.raises(prt.ProvisionError, match="neither loopback"):
        prt.validate_ingest_site("https://evil.example", public_origin="https://iqoqo.example")


def test_loopback_plaintext_can_be_opted_out(monkeypatch):
    monkeypatch.setenv("RUM_ALLOW_INSECURE_LOOPBACK", "false")
    target = prt.validate_ingest_site("http://127.0.0.1:5080", public_origin=None)
    assert target.insecure is False


def test_validated_target_renders_safe_env():
    target = prt.validate_ingest_site("https://iqoqo.example", public_origin="https://iqoqo.example")
    env = target.as_env()
    assert env["NEXT_PUBLIC_OPENOBSERVE_RUM_SITE"] == "iqoqo.example"
    assert env["NEXT_PUBLIC_OPENOBSERVE_RUM_INSECURE_HTTP"] == "false"


# ---------------------------------------------------------------------------
# End-to-end: deployment topology decides whether the token is handed over
# ---------------------------------------------------------------------------


def _provisioned_fields(monkeypatch, capsys) -> dict[str, str]:
    _stub(monkeypatch)
    prt.provision()
    captured = capsys.readouterr()
    return {
        "stdout": captured.out,
        "stderr": captured.err,
        **dict(ln.split("=", 1) for ln in captured.out.strip().splitlines() if "=" in ln),
    }


def test_dev_mode_defaults_to_a_loopback_site(monkeypatch, capsys):
    """Bare dev over HTTP must keep working — this is the primary topology."""
    monkeypatch.setenv("MODE", "dev")
    fields = _provisioned_fields(monkeypatch, capsys)
    assert fields["RUM_TOPOLOGY"] == "loopback"
    assert fields["RUM_INSECURE_HTTP"] == "true"
    assert fields["RUM_CLIENT_TOKEN"] == SENTINEL


def test_dockerized_mode_refuses_to_hand_over_without_a_site(monkeypatch, capsys):
    """No site on a networked deployment => RUM stays off, and says why."""
    monkeypatch.setenv("MODE", "prod")
    fields = _provisioned_fields(monkeypatch, capsys)
    assert "RUM_CLIENT_TOKEN" not in fields
    assert SENTINEL not in fields["stdout"]
    assert "ingest-site-unset" in fields["stderr"]


def test_dockerized_mode_refuses_a_loopback_site(monkeypatch, capsys):
    """The original bug: localhost on a deployment other people reach."""
    monkeypatch.setenv("MODE", "prod")
    monkeypatch.setenv("OPENOBSERVE_RUM_SITE", "http://localhost:5080")
    monkeypatch.setenv("NEXT_PUBLIC_FRONTEND_URL", "https://iqoqo.example")
    fields = _provisioned_fields(monkeypatch, capsys)
    assert "RUM_CLIENT_TOKEN" not in fields
    assert SENTINEL not in fields["stdout"]
    assert "not local-only" in fields["stderr"]


def test_dockerized_mode_accepts_its_own_public_origin_over_tls(monkeypatch, capsys):
    monkeypatch.setenv("MODE", "prod")
    monkeypatch.setenv("OPENOBSERVE_RUM_SITE", "https://iqoqo.example")
    monkeypatch.setenv("NEXT_PUBLIC_FRONTEND_URL", "https://iqoqo.example")
    fields = _provisioned_fields(monkeypatch, capsys)
    assert fields["RUM_TOPOLOGY"] == "public-origin"
    assert fields["RUM_INSECURE_HTTP"] == "false"
    assert fields["RUM_SITE"] == "iqoqo.example"
    assert fields["RUM_CLIENT_TOKEN"] == SENTINEL


def test_dockerized_mode_refuses_plaintext_to_its_own_origin(monkeypatch, capsys):
    monkeypatch.setenv("MODE", "prod")
    monkeypatch.setenv("OPENOBSERVE_RUM_SITE", "http://iqoqo.example")
    monkeypatch.setenv("NEXT_PUBLIC_FRONTEND_URL", "https://iqoqo.example")
    fields = _provisioned_fields(monkeypatch, capsys)
    assert "RUM_CLIENT_TOKEN" not in fields
    assert "plaintext" in fields["stderr"]


def test_explicit_local_only_override_wins(monkeypatch, capsys):
    monkeypatch.setenv("MODE", "prod")
    monkeypatch.setenv("RUM_LOCAL_ONLY", "true")
    fields = _provisioned_fields(monkeypatch, capsys)
    assert fields["RUM_TOPOLOGY"] == "loopback"


# ---------------------------------------------------------------------------
# Ingest API contract, verified against a live OpenObserve v0.91.5
# ---------------------------------------------------------------------------


def test_site_is_emitted_without_a_scheme():
    """The ingest SDK's `site` is a bare host[:port]; it adds the protocol itself.

    `@openobserve/browser-core`'s endpointBuilder does
    `${insecureHTTP ? 'http' : 'https'}://${site}/rum/${apiVersion}/...`, and
    `buildEndpointHost()` returns `site` verbatim. Emitting a scheme here would
    produce `https://https://host/rum/...`.
    """
    target = prt.validate_ingest_site("localhost:5080", public_origin=None)
    assert target.site == "localhost:5080"
    assert prt.validate_ingest_site("http://127.0.0.1:5080", None).site == "127.0.0.1:5080"
    assert prt.validate_ingest_site("https://iqoqo.example", "https://iqoqo.example").site == "iqoqo.example"


def test_rendered_env_is_directly_usable_as_the_sdk_site():
    """What we export must be exactly what the SDK wants, not a URL."""
    env = prt.validate_ingest_site("localhost:5080", public_origin=None).as_env()
    assert env["NEXT_PUBLIC_OPENOBSERVE_RUM_SITE"] == "localhost:5080"
    assert "://" not in env["NEXT_PUBLIC_OPENOBSERVE_RUM_SITE"]


def test_application_id_is_not_part_of_the_ingest_route():
    """`/api/default/rumtoken` returns only `user` and `rum_token`.

    Verified live: the ingest path is `/rum/{apiVersion}/{org}/{trackType}` with
    the token as an `o2-api-key` query parameter, so `applicationId` is payload
    metadata rather than a routing key. A mismatch therefore cannot cause ingest
    rejection, which was the original worry behind this check.
    """
    assert "applicationId" not in prt.RUMTOKEN_PATH


# ---------------------------------------------------------------------------
# --env-file, for the Makefile deploy path
# ---------------------------------------------------------------------------


def test_env_file_supplies_credentials(tmp_path, monkeypatch):
    """`make preview-up` calls docker compose directly, never run.sh.

    Without this the Makefile path has no way to reach the OpenObserve
    credentials, so RUM would silently never be provisioned there.
    """
    env_file = tmp_path / ".env.preview"
    env_file.write_text(
        '# comment\nexport OPENOBSERVE_BASIC_AUTH="dGVzdDp0ZXN0"\n'
        "OPENOBSERVE_HOST_PORT=5081\n"
        "OPENOBSERVE_RUM_SITE=https://iqoqo.example\n"
        "\nmalformed-line-without-equals\n",
        encoding="utf-8",
    )
    for name in ("OPENOBSERVE_BASIC_AUTH", "OPENOBSERVE_HOST_PORT", "OPENOBSERVE_RUM_SITE"):
        monkeypatch.delenv(name, raising=False)

    assert prt.load_env_file(str(env_file)) == 0
    import os

    assert os.environ["OPENOBSERVE_BASIC_AUTH"] == "dGVzdDp0ZXN0"
    assert os.environ["OPENOBSERVE_HOST_PORT"] == "5081"
    assert os.environ["OPENOBSERVE_RUM_SITE"] == "https://iqoqo.example"


def test_existing_environment_wins_over_env_file(tmp_path, monkeypatch):
    """Mirrors run.sh: the file fills gaps, it does not override the operator."""
    env_file = tmp_path / ".env"
    env_file.write_text("OPENOBSERVE_HOST_PORT=5081\n", encoding="utf-8")
    monkeypatch.setenv("OPENOBSERVE_HOST_PORT", "9999")

    prt.load_env_file(str(env_file))
    import os

    assert os.environ["OPENOBSERVE_HOST_PORT"] == "9999"


def test_missing_env_file_degrades_without_raising(tmp_path):
    assert prt.load_env_file(str(tmp_path / "nope.env")) == 1


def test_env_file_does_not_execute_anything(tmp_path, monkeypatch):
    """A dotenv value must never be evaluated."""
    env_file = tmp_path / ".env"
    env_file.write_text("OPENOBSERVE_ROOT_USER=$(touch pwned)\n", encoding="utf-8")
    prt.load_env_file(str(env_file))
    import os

    assert os.environ["OPENOBSERVE_ROOT_USER"] == "$(touch pwned)"
    assert not (tmp_path / "pwned").exists()
