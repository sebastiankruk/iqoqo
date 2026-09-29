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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Validate deploy/nginx.conf.example with a real `nginx -t`.

Why this exists
---------------
``deploy/nginx.conf.example`` is a reference config that operators copy onto
their own hosts. Nothing in CI or the container build parses it, so a syntax
error would sit in the repository until the first person who tried to use it
hit it -- on a production edge proxy, at the worst possible moment.

``nginx -t`` is the only authority on nginx syntax. This script renders the
placeholders, wraps the file in the ``http {}`` context it is designed to be
included into, and hands the result to nginx. When nginx is not available it
falls back to a structural check and says clearly that it did, so a green run is
never mistaken for a parsed one.

Usage:
    scripts/validate_nginx_example.py            # validate, docker preferred
    scripts/validate_nginx_example.py --no-docker
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = REPO_ROOT / "deploy" / "nginx.conf.example"

# Placeholder -> value used for the render. Values only need to be syntactically
# valid, not reachable: `nginx -t` does not resolve upstreams or open sockets.
RENDER_VALUES = {
    "SERVER_NAME": "iqoqo.example.com",
    "LETSENCRYPT_LIVE_DIR": "/etc/letsencrypt/live/iqoqo.example.com",
    "LETSENCRYPT_FULLCHAIN_PEM": "/etc/letsencrypt/live/iqoqo.example.com/fullchain.pem",
    "LETSENCRYPT_PRIVKEY_PEM": "/etc/letsencrypt/live/iqoqo.example.com/privkey.pem",
    "LETSENCRYPT_CHAIN_PEM": "/etc/letsencrypt/live/iqoqo.example.com/chain.pem",
    "RESOLVER": "127.0.0.53",
    "API_UPSTREAM": "127.0.0.1",
    "API_PORT": "5000",
    "FRONTEND_UPSTREAM": "127.0.0.1",
    "FRONTEND_PORT": "3000",
}

# nginx image used for the parse. Pinned to a digest-free tag on purpose: this
# only needs a parser, and a floating tag would make the check non-reproducible
# in the other direction. mainline is used rather than stable so the `http2 on`
# directive (nginx >= 1.25.1) is supported.
NGINX_IMAGE = "nginx:1.29-alpine"

MIN_NGINX = (1, 25, 1)

# Directives that must appear somewhere in the file for the config to be
# considered complete. Checked structurally when nginx is unavailable.
REQUIRED_DIRECTIVES = [
    ("ssl_protocols", "TLS policy (§2.1)"),
    ("ssl_ciphers", "cipher suite restriction (§2.1)"),
    ("return 301 https://", "HTTP to HTTPS redirect (§2.1)"),
    ("server_tokens off", "version suppression (§2.2)"),
    ("X-Frame-Options", "clickjacking header (§2.2)"),
    ("X-Content-Type-Options", "MIME sniffing header (§2.2)"),
    ("Referrer-Policy", "referrer header (§2.2)"),
    ("Permissions-Policy", "feature policy (§2.2)"),
    ("Content-Security-Policy", "CSP (§2.2)"),
    ("Strict-Transport-Security", "HSTS (§2.2)"),
    ("limit_req_zone", "rate limit zones (§2.3)"),
    ("limit_req zone=api_general", "api_general rate limit applied (§2.3)"),
    ("limit_req zone=api_scanner", "api_scanner rate limit applied (§2.3)"),
    ("zone=api_scanner:10m", "api_scanner zone sized (§2.3)"),
    ("zone=api_general:10m", "api_general zone sized (§2.3)"),
    ("immutable", "immutable static caching (§2.3)"),
    ("expires 30d", "30d cover/gallery caching (§2.3)"),
]


class ValidationError(RuntimeError):
    """Raised when the example config fails validation."""


def render(text: str) -> tuple[str, list[str]]:
    """Substitute every ``${NAME}`` placeholder. Returns (rendered, unknown)."""
    unknown: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in RENDER_VALUES:
            unknown.append(name)
            return f"UNRESOLVED_{name}"
        return RENDER_VALUES[name]

    return re.sub(r"\$\{([A-Z0-9_]+)\}", replace, text), unknown


def wrap_as_http_conf(rendered: str) -> str:
    """Wrap the example in the http{} context it is written to be included into.

    The file documents itself as an http-include (limit_req_zone and upstream
    are http-context only), so validating it standalone requires supplying the
    enclosing context. mime.types is pulled from the image at test time.
    """
    return f"""# Generated by scripts/validate_nginx_example.py -- do not edit.
# Wraps deploy/nginx.conf.example in an http {{}} block so `nginx -t` can parse
# it the way a real deployment would.
worker_processes 1;
error_log stderr notice;
pid /tmp/nginx.pid;
events {{ worker_connections 64; }}
http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
{rendered}
}}
"""


def strip_comments(text: str) -> str:
    """Remove ``#`` comments, preserving quoted string contents.

    Two things make this less trivial than a regex:

    * nginx treats ``#`` as a comment start only outside quotes, so a naive
    strip of everything after a ``#`` corrupts ``add_header X "a#b" always;``.
    * String *contents* are deliberately kept. Most of the directives this
    validator looks for live inside quoted values -- the whole CSP, the
    ``immutable`` token in a Cache-Control header -- so blanking them would
    make those needles unfindable.

    Quotes are honoured only so the right characters are blanked; the characters
    themselves are preserved.
    """
    out: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote is not None:
            if char == "\\":
                # Skip the escaped character so a trailing backslash does not
                # swallow the closing quote.
                out.append(" ")
                if index + 1 < len(text):
                    out.append(" ")
                index += 2
                continue
            if char == quote:
                quote = None
            out.append(char)
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            out.append(char)
            index += 1
            continue
        if char == "#":
            # Blank the comment body but keep the newline, so line structure
            # (and any per-line context checks) is preserved.
            while index < len(text) and text[index] != "\n":
                out.append(" ")
                index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def check_structure(rendered: str) -> list[str]:
    """Verify required directives are present, independent of nginx.

    This is a floor, not a substitute for `nginx -t`: it cannot catch a
    misplaced brace or a directive in the wrong context. It exists so the check
    is still meaningful on a machine without nginx or docker.
    """
    # Checked against comment-stripped source. The example documents its own
    # directives in prose -- `server_tokens off` appears in a comment explaining
    # it -- so a naive substring search is satisfied by a *commented-out*
    # directive, which parses cleanly and silently loses the header.
    code = strip_comments(rendered)
    missing = [desc for needle, desc in REQUIRED_DIRECTIVES if needle not in code]

    # Brace balance is a cheap structural proxy for parseability. It will not
    # catch context errors, but it catches the most common copy/paste damage.
    #
    # Comments and quoted strings are stripped first. This file documents itself
    # in comments that contain example directives, and several of those contain
    # braces -- a naive count over the raw text reports a spurious imbalance and
    # would train whoever reads the failure to ignore it.
    depth = 0
    for char in code:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return missing + ["unbalanced braces (an extra '}')"]
    if depth != 0:
        return missing + [f"unbalanced braces (depth {depth} at end of file)"]

    # `upstream` inside a `server` block is a parse error in nginx, and the one
    # structural mistake most likely to be reintroduced when this file is
    # edited, so it is checked explicitly rather than left to nginx.
    server_depth = 0
    for line in rendered.splitlines():
        stripped = line.strip()
        if stripped.startswith("server ") and stripped.endswith("{"):
            server_depth += 1
        elif stripped == "}":
            server_depth = max(0, server_depth - 1)
        elif stripped.startswith("upstream ") and server_depth:
            return missing + ["`upstream` declared inside a `server` block, which nginx rejects"]

    return missing


def validate_with_nginx(rendered: str) -> str:
    """Parse the config with a local nginx binary. Returns the nginx version."""
    binary = shutil.which("nginx")
    if not binary:
        raise ValidationError("nginx is not installed")

    with tempfile.TemporaryDirectory() as tmp:
        conf_dir = Path(tmp)
        (conf_dir / "mime.types").write_text("types { text/plain txt; }\n")
        conf_path = conf_dir / "nginx.conf"
        conf_path.write_text(wrap_as_http_conf(rendered))

        # Certificates do not exist on a validation host, and nginx -t reads
        # them. Generate a throwaway self-signed pair so the TLS directives are
        # exercised rather than skipped.
        cert_dir = conf_dir / "certs"
        cert_dir.mkdir()
        cert = cert_dir / "cert.pem"
        key = cert_dir / "key.pem"
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-nodes",
                "-newkey",
                "rsa:2048",
                "-days",
                "1",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-subj",
                "/CN=iqoqo.example.com",
            ],
            check=True,
            capture_output=True,
        )

        concrete = re.sub(r"\$\{[A-Z0-9_]+\}", "placeholder", rendered)
        concrete = (
            concrete.replace("/etc/letsencrypt/live/iqoqo.example.com/fullchain.pem", str(cert))
            .replace("/etc/letsencrypt/live/iqoqo.example.com/privkey.pem", str(key))
            .replace("/etc/letsencrypt/live/iqoqo.example.com/chain.pem", str(cert))
        )
        conf_path.write_text(wrap_as_http_conf(concrete))

        result = subprocess.run(
            [binary, "-t", "-c", str(conf_path), "-p", str(conf_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValidationError(f"nginx -t failed:\n{result.stderr.strip()}")

        version = subprocess.run([binary, "-v"], capture_output=True, text=True, check=False)
        return (version.stderr or version.stdout).strip().splitlines()[-1]


def validate_with_docker(rendered: str) -> str:
    """Parse the config inside a throwaway nginx container."""
    if not shutil.which("docker"):
        raise ValidationError("docker is not available")

    with tempfile.TemporaryDirectory() as tmp:
        conf_dir = Path(tmp)
        (conf_dir / "mime.types").write_text("types { text/plain txt; }\n")
        cert_dir = conf_dir / "certs"
        cert_dir.mkdir()
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-nodes",
                "-newkey",
                "rsa:2048",
                "-days",
                "1",
                "-keyout",
                str(cert_dir / "key.pem"),
                "-out",
                str(cert_dir / "cert.pem"),
                "-subj",
                "/CN=iqoqo.example.com",
            ],
            check=True,
            capture_output=True,
        )

        concrete = re.sub(r"\$\{[A-Z0-9_]+\}", "placeholder", rendered)
        concrete = (
            concrete.replace("/etc/letsencrypt/live/iqoqo.example.com/fullchain.pem", "/certs/cert.pem")
            .replace("/etc/letsencrypt/live/iqoqo.example.com/privkey.pem", "/certs/key.pem")
            .replace("/etc/letsencrypt/live/iqoqo.example.com/chain.pem", "/certs/cert.pem")
        )
        (conf_dir / "nginx.conf").write_text(wrap_as_http_conf(concrete))

        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{conf_dir}:/test:ro",
                "-v",
                f"{cert_dir}:/certs:ro",
                NGINX_IMAGE,
                "nginx",
                "-t",
                "-c",
                "/test/nginx.conf",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValidationError(f"nginx -t (docker) failed:\n{result.stderr.strip()}")

        version = subprocess.run(
            ["docker", "run", "--rm", NGINX_IMAGE, "nginx", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        return (version.stderr or version.stdout).strip().splitlines()[-1]


def main() -> int:
    """Validate deploy/nginx.conf.example and report the outcome.

    Prefers a real ``nginx -t``. Falls back to a structural check when neither
    nginx nor docker is available, and says so, so a green run is never mistaken
    for a parsed one."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="do not fall back to a container; structural check only if nginx is absent",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=EXAMPLE,
        help="config file to validate (default: deploy/nginx.conf.example)",
    )
    args = parser.parse_args()
    config: Path = args.config

    if not config.exists():
        print(f"FAIL: {config} does not exist", file=sys.stderr)
        return 1

    raw = config.read_text()
    rendered, unknown = render(raw)

    if unknown:
        print(f"FAIL: unknown placeholder(s) in {config.name}: {', '.join(sorted(set(unknown)))}", file=sys.stderr)
        print("      Add it to RENDER_VALUES in this script so validation stays honest.", file=sys.stderr)
        return 1

    # Structure is checked first and unconditionally: it catches a missing
    # directive even when a full parse would also have failed for another
    # reason, and it is the only check available without nginx.
    missing = check_structure(rendered)
    if missing:
        print(f"FAIL: {EXAMPLE.name} is missing or misplaces:", file=sys.stderr)
        for item in missing:
            print(f"      - {item}", file=sys.stderr)
        return 1
    print(f"  [OK]  structure: {len(REQUIRED_DIRECTIVES)} required directives present, braces balanced")

    attempts: list[tuple[str, callable]] = []
    if shutil.which("nginx"):
        attempts.append(("nginx -t (local)", lambda: validate_with_nginx(rendered)))
    if not args.no_docker and shutil.which("docker"):
        attempts.append((f"nginx -t (docker {NGINX_IMAGE})", lambda: validate_with_docker(rendered)))

    if not attempts:
        print("  [SKIP] no nginx binary and docker unavailable or disabled", file=sys.stderr)
        print("         Structural checks passed, but the config was NOT parsed.", file=sys.stderr)
        print("         Install nginx or enable docker for a real syntax check.", file=sys.stderr)
        return 0

    for label, run in attempts:
        try:
            version = run()
        except (ValidationError, subprocess.CalledProcessError) as exc:
            print(f"  [FAIL] {label}", file=sys.stderr)
            print(f"         {exc}", file=sys.stderr)
            return 1

        print(f"  [OK]  {label}: parsed by {version}")

        # The `http2 on` directive needs nginx >= 1.25.1. A parse success on an
        # older build would mean the directive was silently ignored, so the
        # version is checked rather than assumed.
        match = re.search(r"nginx/(\d+)\.(\d+)\.(\d+)", version)
        if match:
            found = tuple(int(g) for g in match.groups())
            if found < MIN_NGINX:
                print(
                    f"  [WARN] validator is {version}, but `http2 on` needs >= "
                    f"{'.'.join(map(str, MIN_NGINX))}. Operators on an older nginx must",
                    file=sys.stderr,
                )
                print("         use `listen 443 ssl http2;` instead.", file=sys.stderr)

    try:
        shown = config.relative_to(REPO_ROOT)
    except ValueError:
        shown = config
    print(f"OK: {shown} is a valid nginx configuration")
    return 0


if __name__ == "__main__":
    sys.exit(main())
