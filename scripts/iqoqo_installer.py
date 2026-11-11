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
#
"""Interactive & non-interactive installer and pre-sync readiness verification wizard.

Provides zero-trust 256-bit cryptographic secret generation, 0600 file permission enforcement,
profile selection (standard, preview, federation_head), and comprehensive pre-flight / post-deploy
readiness checks (`iqopresync`).
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Profiles definition
PROFILES = ("standard", "preview", "federation_head")

# Core secrets requiring at least 32 bytes (256 bits) of entropy
ENTROPY_REQUIRED_SECRETS = (
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "ADMIN_PASSWORD",
)


def is_ai_mode() -> bool:
    """Return True if IQOQO_AI_MODE is set in the environment."""
    return os.environ.get("IQOQO_AI_MODE") in ("1", "true", "yes")


def log_msg(msg: str, *, err: bool = False) -> None:
    """Print log message unless suppressed in concise AI mode."""
    target = sys.stderr if err else sys.stdout
    target.write(f"{msg}\n")
    target.flush()


def parse_env_file(file_path: Path) -> tuple[list[str], dict[str, str]]:
    """Parse an .env file preserving raw lines and extracting key-value map."""
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


def update_or_append_env_line(lines: list[str], key: str, value: str) -> list[str]:
    """Update or append key=value in the given lines, preserving format and escaping safely."""
    pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
    formatted = f'{key}="{escaped}"'
    updated = False
    new_lines: list[str] = []

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


def generate_secure_secret(bytes_count: int = 32) -> str:
    """Generate cryptographically secure URL-safe secret with specified byte length."""
    return secrets.token_urlsafe(bytes_count)


def mask_secret(secret_val: str | None) -> str:
    """Mask secret value for terminal presentation."""
    if not secret_val:
        return "[EMPTY]"
    if len(secret_val) <= 8:
        return "***"
    return f"{secret_val[:4]}...{secret_val[-4:]}"


def configure_env_content(
    example_path: Path,
    target_env_path: Path,
    *,
    domain: str,
    mode: str,
    admin_email: str,
    rotate_secrets: bool = False,
    existing_vars: dict[str, str] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Generate .env lines based on .env.example, profile defaults, and generated secrets."""
    base_lines, _ = parse_env_file(example_path)
    if not base_lines and target_env_path.exists():
        base_lines, _ = parse_env_file(target_env_path)

    existing = existing_vars or {}
    lines = list(base_lines)
    result_vars: dict[str, str] = {}

    # 1. Clean domain and URL targets
    clean_domain = domain.strip().removeprefix("http://").removeprefix("https://").rstrip("/")
    if clean_domain in ("localhost", "127.0.0.1") or clean_domain.startswith("localhost:"):
        base_url = f"http://{clean_domain}"
    else:
        base_url = f"https://{clean_domain}"

    # 2. Assign secrets
    for sec_key in ENTROPY_REQUIRED_SECRETS:
        curr_val = existing.get(sec_key)
        if curr_val and not rotate_secrets and not any(p in curr_val.lower() for p in ("changeme", "placeholder")):
            val = curr_val
        else:
            val = generate_secure_secret(32)
        lines = update_or_append_env_line(lines, sec_key, val)
        result_vars[sec_key] = val

    # 3. Update database URL using postgres password
    pg_pass = result_vars["POSTGRES_PASSWORD"]
    db_url = f"postgresql://iqoqo:{pg_pass}@db:5432/iqoqo"
    lines = update_or_append_env_line(lines, "DATABASE_URL", db_url)
    result_vars["DATABASE_URL"] = db_url

    # 4. Domain & URLs
    lines = update_or_append_env_line(lines, "NEXT_PUBLIC_FRONTEND_URL", base_url)
    lines = update_or_append_env_line(lines, "FEDERATION_BASE_URL", base_url)
    lines = update_or_append_env_line(lines, "NEXT_PUBLIC_INSTANCE_URL", base_url)
    result_vars["NEXT_PUBLIC_FRONTEND_URL"] = base_url
    result_vars["FEDERATION_BASE_URL"] = base_url

    # 5. Admin email
    if admin_email:
        lines = update_or_append_env_line(lines, "ADMIN_EMAIL", admin_email)
        result_vars["ADMIN_EMAIL"] = admin_email

    # 6. Profile specific settings
    if mode == "federation_head":
        lines = update_or_append_env_line(lines, "FEDERATION_ENABLED", "true")
        lines = update_or_append_env_line(lines, "FEDERATION_HEAD_MODE", "true")
        lines = update_or_append_env_line(lines, "FLASK_ENV", "production")
        result_vars["FEDERATION_HEAD_MODE"] = "true"
        result_vars["FEDERATION_ENABLED"] = "true"
        result_vars["FLASK_ENV"] = "production"
    elif mode == "preview":
        lines = update_or_append_env_line(lines, "FEDERATION_ENABLED", "true")
        lines = update_or_append_env_line(lines, "FEDERATION_HEAD_MODE", "false")
        lines = update_or_append_env_line(lines, "FLASK_ENV", "production")
        result_vars["FEDERATION_HEAD_MODE"] = "false"
        result_vars["FEDERATION_ENABLED"] = "true"
        result_vars["FLASK_ENV"] = "production"
    else:  # standard
        lines = update_or_append_env_line(lines, "FEDERATION_ENABLED", "true")
        lines = update_or_append_env_line(lines, "FEDERATION_HEAD_MODE", "false")
        result_vars["FEDERATION_HEAD_MODE"] = "false"
        result_vars["FEDERATION_ENABLED"] = "true"

    return lines, result_vars


def write_env_file_safely(target_path: Path, lines: list[str]) -> None:
    """Write lines to target file with strict 0600 permissions."""
    content = "\n".join(lines).rstrip() + "\n"
    target_path.write_text(content, encoding="utf-8")
    os.chmod(target_path, 0o600)


def check_production_overwrite_guard(target_env_path: Path, clean_domain: str, non_interactive: bool) -> bool:
    """Enforce typed confirmation guard when overwriting production .env file."""
    if not target_env_path.exists():
        return True
    _, curr_vars = parse_env_file(target_env_path)
    if curr_vars.get("FLASK_ENV") == "production":
        if non_interactive:
            log_msg(f"ERROR: Refusing to overwrite production .env at {target_env_path} non-interactively.", err=True)
            return False
        sys.stdout.write(
            f"\n⚠️  WARNING: {target_env_path} is configured for PRODUCTION.\n"
            f"To confirm replacing it, type the target domain '{clean_domain}': "
        )
        sys.stdout.flush()
        entered = sys.stdin.readline().strip()
        if entered != clean_domain:
            log_msg(f"Aborted: Confirmation mismatch ('{entered}' != '{clean_domain}').", err=True)
            return False
    return True


def run_presync_check(target_env_path: Path, base_url_override: str | None = None) -> int:
    """Execute pre-sync / preview readiness verification checks."""
    ai_mode = is_ai_mode()
    issues: list[str] = []
    warnings: list[str] = []

    if not ai_mode:
        log_msg("============================================================")
        log_msg("  iqopresync: Pre-Sync & Preview Readiness Verification")
        log_msg("============================================================")

    # 1. Environment file check
    if not target_env_path.exists():
        issues.append(f"Environment file not found at {target_env_path}")
        _, env_map = [], {}
    else:
        # Check permissions
        st = os.stat(target_env_path)
        file_mode = stat.S_IMODE(st.st_mode)
        if file_mode & 0o077 != 0:
            warnings.append(f"Permissive .env permissions ({oct(file_mode)}). Recommended: 0600.")
        _, env_map = parse_env_file(target_env_path)

        # Check required entropy
        for key in ENTROPY_REQUIRED_SECRETS:
            val = env_map.get(key)
            if not val or len(val) < 24 or any(p in val.lower() for p in ("changeme", "placeholder")):
                issues.append(f"Secret '{key}' is missing, too short, or uses placeholder.")

    # 2. Docker & Compose availability
    docker_bin = shutil.which("docker")
    if not docker_bin:
        warnings.append("Docker binary not found on host PATH.")
    else:
        try:
            res = subprocess.run([docker_bin, "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if res.returncode != 0:
                warnings.append("Docker daemon is not running or current user lacks access.")
        except Exception as e:
            warnings.append(f"Failed to probe docker daemon: {e}")

    # 3. HTTP Endpoints probe if base_url is available
    base_url = base_url_override or env_map.get("NEXT_PUBLIC_FRONTEND_URL") or "http://localhost:5000"
    base_url = base_url.rstrip("/")

    # Probe /api/health
    health_url = f"{base_url}/api/health"
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "iqopresync/1.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                if not ai_mode:
                    log_msg(f"  ✓ /api/health reachable ({response.status})")
            else:
                warnings.append(f"/api/health returned non-200 status: {response.status}")
    except Exception:
        warnings.append(f"/api/health unreachable at {health_url} (Stack may not be started yet)")

    # Probe /.well-known/nodeinfo
    nodeinfo_url = f"{base_url}/.well-known/nodeinfo"
    try:
        req = urllib.request.Request(nodeinfo_url, headers={"User-Agent": "iqopresync/1.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                if not ai_mode:
                    log_msg(f"  ✓ NodeInfo discovery reachable ({response.status})")
    except Exception:
        pass

    # Print summary
    if issues:
        log_msg("❌ Pre-sync check FAILED:", err=True)
        for iss in issues:
            log_msg(f"  - {iss}", err=True)
        return 2

    if warnings and not ai_mode:
        log_msg("⚠️  Pre-sync warnings:")
        for w in warnings:
            log_msg(f"  - {w}")

    if ai_mode:
        log_msg("iqopresync: READY")
    else:
        log_msg("✅ iqopresync: All core pre-sync requirements satisfied.")

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI Entry point for installer and presync checker."""
    parser = argparse.ArgumentParser(
        prog="iqoqo-installer",
        description="iqoqo interactive/non-interactive installer and iqopresync readiness tool.",
    )
    parser.add_argument("--domain", "-d", help="Public domain or hostname (e.g. library.example.com or localhost:3000)")
    parser.add_argument("--mode", "-m", choices=PROFILES, default="standard", help="Deployment profile")
    parser.add_argument("--admin-email", "-e", default="admin@iqoqo.local", help="Initial administrator email")
    parser.add_argument("--env-file", default=".env", help="Target .env file path (default: .env)")
    parser.add_argument("--example-file", default=".env.example", help="Template .env.example path")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts")
    parser.add_argument("--rotate-secrets", action="store_true", help="Force re-generation of all cryptographic keys")
    parser.add_argument("--presync-check", action="store_true", help="Run iqopresync verification checks on environment")
    parser.add_argument("--check-url", help="Base URL to verify during presync check")

    args = parser.parse_args(argv)

    target_env = Path(args.env_file)
    example_env = Path(args.example_file)

    # Mode: Presync check only
    if args.presync_check:
        return run_presync_check(target_env, base_url_override=args.check_url)

    domain = args.domain
    mode = args.mode
    admin_email = args.admin_email

    # Interactive prompt if domain missing and not in non-interactive mode
    if not domain and not args.non_interactive:
        sys.stdout.write("Enter public domain/hostname [localhost:3000]: ")
        sys.stdout.flush()
        val = sys.stdin.readline().strip()
        domain = val if val else "localhost:3000"

        sys.stdout.write(f"Select profile ({'/'.join(PROFILES)}) [standard]: ")
        sys.stdout.flush()
        pval = sys.stdin.readline().strip().lower()
        if pval in PROFILES:
            mode = pval

        sys.stdout.write(f"Admin email [{admin_email}]: ")
        sys.stdout.flush()
        eval_ = sys.stdin.readline().strip()
        if eval_:
            admin_email = eval_
    elif not domain:
        domain = "localhost:3000"

    clean_domain = domain.strip().removeprefix("http://").removeprefix("https://").rstrip("/")

    # Check overwrite guard
    if not check_production_overwrite_guard(target_env, clean_domain, args.non_interactive):
        return 1

    # Backup existing if present
    if target_env.exists():
        backup_path = target_env.with_suffix(f".bak.{int(time.time())}")
        shutil.copy2(target_env, backup_path)
        os.chmod(backup_path, 0o600)
        if not is_ai_mode():
            log_msg(f"Backed up existing {target_env} to {backup_path}")

    _, existing_vars = parse_env_file(target_env) if target_env.exists() else ([], {})
    lines, generated_vars = configure_env_content(
        example_env,
        target_env,
        domain=clean_domain,
        mode=mode,
        admin_email=admin_email,
        rotate_secrets=args.rotate_secrets,
        existing_vars=existing_vars,
    )

    write_env_file_safely(target_env, lines)

    if is_ai_mode():
        log_msg(f"iqoqo-installer: {target_env} written successfully (mode={mode}).")
    else:
        log_msg(f"\n✅ Created hardened {target_env} with 0600 permissions.")
        log_msg(f"  Mode:           {mode}")
        log_msg(f"  Frontend URL:   {generated_vars.get('NEXT_PUBLIC_FRONTEND_URL')}")
        log_msg(f"  Admin Email:    {generated_vars.get('ADMIN_EMAIL')}")
        log_msg(f"  Secret Key:     {mask_secret(generated_vars.get('SECRET_KEY'))}")
        log_msg(f"  JWT Secret Key: {mask_secret(generated_vars.get('JWT_SECRET_KEY'))}")
        log_msg(f"  Postgres Pass:  {mask_secret(generated_vars.get('POSTGRES_PASSWORD'))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
