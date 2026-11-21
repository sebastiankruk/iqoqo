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
"""Fail-closed configuration tests for the Docker Compose database password."""

import base64
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose CLI is unavailable")
def test_compose_rejects_missing_postgres_password() -> None:
    """Compose configuration must fail without an explicitly supplied DB password."""
    env = {"PATH": os.environ.get("PATH", ""), "ENV_FILE": "/dev/null"}
    result = subprocess.run(
        ["docker", "compose", "--env-file", "/dev/null", "-f", str(REPO_ROOT / "docker-compose.yml"), "config", "--quiet"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose CLI is unavailable")
def test_compose_accepts_explicit_postgres_password_without_echoing_it() -> None:
    """Compose validates explicit credentials without printing resolved secrets."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "ENV_FILE": "/dev/null",
        "POSTGRES_PASSWORD": "compose-test-password-only",
    }
    result = subprocess.run(
        ["docker", "compose", "--env-file", "/dev/null", "-f", str(REPO_ROOT / "docker-compose.yml"), "config", "--quiet"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, "Compose rejected an explicitly supplied database password"
    assert "compose-test-password-only" not in result.stdout + result.stderr


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose CLI is unavailable")
def test_monitoring_compose_rejects_missing_openobserve_credentials() -> None:
    """Monitoring Compose configuration must fail without explicitly supplied OpenObserve credentials."""
    env = {"PATH": os.environ.get("PATH", ""), "ENV_FILE": "/dev/null"}
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-f",
            str(REPO_ROOT / "docker-compose.monitoring.yml"),
            "config",
            "--quiet",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "OPENOBSERVE_ROOT_PASSWORD" in result.stderr or "OPENOBSERVE_BASIC_AUTH" in result.stderr


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose CLI is unavailable")
def test_monitoring_compose_accepts_valid_credentials() -> None:
    """Monitoring Compose validates when OpenObserve credentials are provided."""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "ENV_FILE": "/dev/null",
        "OPENOBSERVE_ROOT_PASSWORD": "valid-secret-password-123",
        "OPENOBSERVE_BASIC_AUTH": base64.b64encode(b"test-monitor-user:test-secret-password-123").decode("utf-8"),
    }
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-f",
            str(REPO_ROOT / "docker-compose.monitoring.yml"),
            "config",
            "--quiet",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0


def test_ensure_env_secrets_provisions_missing_keys(tmp_path: Path) -> None:
    """ensure_env_secrets_in_env_file should auto-generate all required secrets into an empty or partial env file."""
    from scripts.ensure_env_secrets import ensure_secrets_in_env_file, is_openobserve_password_strong

    env_file = tmp_path / ".env.test_sample"
    env_file.write_text("SOME_EXISTING_KEY=hello\n", encoding="utf-8")

    result = ensure_secrets_in_env_file(env_file)

    assert result["SOME_EXISTING_KEY"] == "hello"
    assert "SECRET_KEY" in result and len(result["SECRET_KEY"]) >= 32
    assert "JWT_SECRET_KEY" in result and len(result["JWT_SECRET_KEY"]) >= 32
    assert "AUTH_SECRET" in result and len(result["AUTH_SECRET"]) >= 24
    assert "OPENOBSERVE_ROOT_USER" in result
    assert "OPENOBSERVE_ROOT_PASSWORD" in result and is_openobserve_password_strong(result["OPENOBSERVE_ROOT_PASSWORD"])
    assert "OPENOBSERVE_BASIC_AUTH" in result and len(result["OPENOBSERVE_BASIC_AUTH"]) >= 16

    content = env_file.read_text(encoding="utf-8")
    assert "SECRET_KEY=" in content
    assert "OPENOBSERVE_ROOT_PASSWORD=" in content
    assert "OPENOBSERVE_BASIC_AUTH=" in content


def test_ensure_env_secrets_regenerates_weak_openobserve_password_on_reset(tmp_path: Path) -> None:
    """The auth-reset path rotates weak passwords so a fresh OO db can boot."""
    import base64

    from scripts.ensure_env_secrets import ensure_secrets_in_env_file, is_openobserve_password_strong

    weak_password = "abcdefghijklmnopqrstuvwxyz0123456789"  # no uppercase / special
    env_file = tmp_path / ".env.weak_oo_password"
    env_file.write_text(
        f"OPENOBSERVE_ROOT_USER=admin@iqoqo.local\nOPENOBSERVE_ROOT_PASSWORD={weak_password}\n",
        encoding="utf-8",
    )

    resolved = ensure_secrets_in_env_file(env_file, enforce_openobserve_password_policy=True)

    new_password = resolved["OPENOBSERVE_ROOT_PASSWORD"]
    assert is_openobserve_password_strong(weak_password) is False
    assert new_password != weak_password
    assert is_openobserve_password_strong(new_password) is True
    expected_auth = base64.b64encode(f"admin@iqoqo.local:{new_password}".encode()).decode()
    assert resolved["OPENOBSERVE_BASIC_AUTH"] == expected_auth


def test_ensure_env_secrets_preserves_existing_openobserve_password(tmp_path: Path) -> None:
    """Routine starts do not rotate a weak-but-working root credential."""
    from scripts.ensure_env_secrets import ensure_secrets_in_env_file

    existing_password = "abcdefghijklmnopqrstuvwxyz0123456789"  # weak, but valid in existing volume
    env_file = tmp_path / ".env.existing_oo_password"
    env_file.write_text(f"OPENOBSERVE_ROOT_PASSWORD={existing_password}\n", encoding="utf-8")

    resolved = ensure_secrets_in_env_file(env_file)

    assert resolved["OPENOBSERVE_ROOT_PASSWORD"] == existing_password
