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

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose CLI is unavailable")
def test_compose_rejects_missing_postgres_password() -> None:
    """Compose configuration must fail without an explicitly supplied DB password."""
    env = {"PATH": os.environ.get("PATH", "")}
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
    env = {"PATH": os.environ.get("PATH", ""), "POSTGRES_PASSWORD": "compose-test-password-only"}
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
