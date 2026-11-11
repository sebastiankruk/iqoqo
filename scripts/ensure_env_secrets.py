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
"""Pre-flight utility ensuring required secrets exist in environment files and DB."""

from __future__ import annotations

import argparse
import base64
import re
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path


def strip_quotes(val: str | None) -> str:
    """Strip surrounding single or double quotes from a string."""
    if not val:
        return ""
    cleaned = val.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def is_placeholder_or_empty(val: str | None, min_length: int = 16) -> bool:
    """Return True if value is empty, None, too short, or an obvious placeholder."""
    if not val or not val.strip():
        return True
    cleaned = val.strip().strip("'\"")
    if len(cleaned) < min_length:
        return True
    lower = cleaned.lower()
    return any(p in lower for p in ("changeme", "placeholder", "your_super_secret"))


def parse_env_file(file_path: Path) -> tuple[list[str], dict[str, str]]:
    """Parse an .env file preserving all lines, comments, and whitespace."""
    if not file_path.exists():
        return [], {}
    lines = file_path.read_text(encoding="utf-8").splitlines()
    env_vars: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            k, v = stripped.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            env_vars[k] = v
    return lines, env_vars


def update_env_lines(lines: list[str], key: str, value: str) -> list[str]:
    """Update or append key=value in the given lines, preserving format."""
    pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    updated = False
    new_lines: list[str] = []
    # Always double-quote and escape. Selecting double quotes *because* the
    # value contains a quote or `$` without escaping them is the bug: the file
    # is later `source`d under `set -o allexport` in run.sh, so an unescaped
    # backtick or `$(...)` becomes command execution as the deploying user.
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
    formatted = f'{key}="{escaped}"'

    for line in lines:
        if pattern.match(line):
            new_lines.append(formatted)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(formatted)

    return new_lines


def ensure_secrets_in_env_file(file_path: Path) -> dict[str, str]:
    """Ensure all required infrastructure and auth secrets exist in the file."""
    lines, current = parse_env_file(file_path)
    modified = False

    # 1. SECRET_KEY
    secret_key = current.get("SECRET_KEY")
    if is_placeholder_or_empty(secret_key, min_length=32):
        secret_key = secrets.token_hex(32)
        lines = update_env_lines(lines, "SECRET_KEY", secret_key)
        current["SECRET_KEY"] = secret_key
        modified = True

    # 2. JWT_SECRET_KEY
    jwt_key = current.get("JWT_SECRET_KEY")
    if is_placeholder_or_empty(jwt_key, min_length=32):
        jwt_key = secrets.token_hex(32)
        lines = update_env_lines(lines, "JWT_SECRET_KEY", jwt_key)
        current["JWT_SECRET_KEY"] = jwt_key
        modified = True

    # 3. AUTH_SECRET
    auth_secret = current.get("AUTH_SECRET")
    if is_placeholder_or_empty(auth_secret, min_length=24):
        auth_secret = secrets.token_urlsafe(32)
        lines = update_env_lines(lines, "AUTH_SECRET", auth_secret)
        current["AUTH_SECRET"] = auth_secret
        modified = True

    # 4. OPENOBSERVE_ROOT_USER
    oo_user = strip_quotes(current.get("OPENOBSERVE_ROOT_USER"))
    if not oo_user:
        oo_user = "admin@iqoqo.local"
        lines = update_env_lines(lines, "OPENOBSERVE_ROOT_USER", oo_user)
        current["OPENOBSERVE_ROOT_USER"] = oo_user
        modified = True

    # 5. OPENOBSERVE_ROOT_PASSWORD
    oo_password = strip_quotes(current.get("OPENOBSERVE_ROOT_PASSWORD"))
    if is_placeholder_or_empty(oo_password, min_length=16):
        oo_password = secrets.token_urlsafe(32)
        lines = update_env_lines(lines, "OPENOBSERVE_ROOT_PASSWORD", oo_password)
        current["OPENOBSERVE_ROOT_PASSWORD"] = oo_password
        modified = True

    # 6. OPENOBSERVE_BASIC_AUTH (base64(oo_user:oo_password))
    expected_auth = base64.b64encode(f"{oo_user}:{oo_password}".encode()).decode("utf-8")
    oo_basic_auth = strip_quotes(current.get("OPENOBSERVE_BASIC_AUTH"))
    if not oo_basic_auth or is_placeholder_or_empty(oo_basic_auth, min_length=8) or oo_basic_auth != expected_auth:
        lines = update_env_lines(lines, "OPENOBSERVE_BASIC_AUTH", expected_auth)
        current["OPENOBSERVE_BASIC_AUTH"] = expected_auth
        modified = True

    if modified:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(lines).rstrip() + "\n"
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ Auto-provisioned missing secrets in {file_path}")

    return current


def probe_openobserve_auth(basic_auth: str, host_port: int = 5080) -> tuple[bool, str]:
    """Test OPENOBSERVE_BASIC_AUTH against a running local OpenObserve instance.

    Returns (is_ok, message). If OpenObserve is not running or unreachable, returns (True, "not_running").
    If OpenObserve is running and responds with 401 or 403, returns (False, warning_message).
    """
    clean_auth = strip_quotes(basic_auth)
    if not clean_auth:
        return False, "Empty basic auth"

    url = f"http://127.0.0.1:{host_port}/api/default/_search"
    req = urllib.request.Request(
        url,
        data=b'{"query":{"sql":"SELECT 1","size":1}}',
        headers={
            "Authorization": f"Basic {clean_auth}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status in (200, 201):
                return True, "Authenticated"
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            msg = (
                f"⚠️ WARNING: OpenObserve rejected OPENOBSERVE_BASIC_AUTH (HTTP {err.code}). "
                "The openobserve_data volume (/data/db) is locked to an older password. "
                "Run 'make monitoring-reset-auth' to resync without losing /data/stream telemetry."
            )
            return False, msg
        return True, f"HTTP {err.code}"
    except (urllib.error.URLError, OSError, TimeoutError):
        return True, "Unreachable (not running)"
    return True, "OK"


def sync_secrets_to_db(secrets_map: dict[str, str]) -> None:
    """Mirror credentials into encrypted InstanceSettings if the DB is available."""
    basic_auth = secrets_map.get("OPENOBSERVE_BASIC_AUTH")
    if not basic_auth:
        return

    try:
        from app import create_app
        from app.db.settings import InstanceSettings

        app = create_app()
        with app.app_context():
            InstanceSettings.set_value("OPENOBSERVE_BASIC_AUTH", basic_auth)
            print("🔒 Synced OPENOBSERVE_BASIC_AUTH into encrypted InstanceSettings in DB")
    except Exception:
        # DB may not be online during early pre-flight; this is safe to pass
        pass


def main() -> None:
    """Generate any missing secrets in .env, leaving existing values untouched."""
    parser = argparse.ArgumentParser(description="Ensure required secrets exist in environment file.")
    parser.add_argument(
        "env_file_pos",
        nargs="?",
        type=Path,
        default=None,
        help="Optional positional target environment file",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Target environment file to check/update (default: .env)",
    )
    parser.add_argument(
        "--sync-db",
        action="store_true",
        help="Mirror secrets into application database InstanceSettings table",
    )
    args = parser.parse_args()

    target_file = args.env_file or args.env_file_pos or Path(".env")
    env_path = target_file.resolve()
    resolved = ensure_secrets_in_env_file(env_path)

    if args.sync_db:
        sync_secrets_to_db(resolved)

    oo_auth = resolved.get("OPENOBSERVE_BASIC_AUTH", "")
    port_str = strip_quotes(resolved.get("OPENOBSERVE_HOST_PORT", "5080"))
    try:
        oo_port = int(port_str) if port_str.isdigit() else 5080
    except ValueError:
        oo_port = 5080

    is_ok, msg = probe_openobserve_auth(oo_auth, host_port=oo_port)
    if not is_ok:
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
