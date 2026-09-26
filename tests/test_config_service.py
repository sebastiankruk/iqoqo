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
"""Tests for ConfigService plus startup SECRET_KEY validation regressions."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from app.core.config_service import CONFIG_KEY_BLOCKLIST, ConfigService
from app.db.models import InstanceSettings, db

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_config_key_blocklist_contains_boot_keys():
    """Ensure boot keys are in CONFIG_KEY_BLOCKLIST."""
    expected = {"SECRET_KEY", "DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY"}
    assert expected.issubset(CONFIG_KEY_BLOCKLIST)
    assert ConfigService.CONFIG_KEY_BLOCKLIST == CONFIG_KEY_BLOCKLIST


def test_db_override_ignored_for_blocklisted_keys(app):
    """Ensure DB overrides for blocklisted keys are completely ignored."""
    with app.app_context():
        for key in CONFIG_KEY_BLOCKLIST:
            setting = InstanceSettings.query.filter_by(key=key).first()
            if not setting:
                setting = InstanceSettings(key=key, value="malicious_db_value")
                db.session.add(setting)
            else:
                setting.value = "malicious_db_value"
        db.session.commit()

        for key in CONFIG_KEY_BLOCKLIST:
            assert ConfigService.get(key) != "malicious_db_value"


def test_db_override_used_for_non_blocklisted_keys(app):
    """Ensure normal keys still read from DB if present."""
    with app.app_context():
        key = "TEST_CUSTOM_SETTING"
        setting = InstanceSettings.query.filter_by(key=key).first()
        if not setting:
            setting = InstanceSettings(key=key, value="custom_value_from_db")
            db.session.add(setting)
        else:
            setting.value = "custom_value_from_db"
        db.session.commit()

        assert ConfigService.get(key) == "custom_value_from_db"


def test_fallback_to_env_var(app):
    """Ensure fallback to environment variable when not in DB."""
    with app.app_context():
        with patch.dict(os.environ, {"SOME_RANDOM_ENV_VAR": "hello_env"}):
            assert ConfigService.get("SOME_RANDOM_ENV_VAR") == "hello_env"


def test_config_service_helpers():
    """Ensure get_list and get_bool work as expected."""
    with patch.dict(os.environ, {"TEST_LIST": "a, b, c", "TEST_BOOL": "true"}):
        assert ConfigService.get_list("TEST_LIST") == ["a", "b", "c"]
        assert ConfigService.get_bool("TEST_BOOL") is True


def _run_config_import(secret_key: str) -> subprocess.CompletedProcess[str]:
    """Import application config under production settings in an isolated process."""
    env = os.environ.copy()
    env.update(
        {
            "FLASK_ENV": "production",
            "SECRET_KEY": secret_key,
            "JWT_SECRET_KEY": secret_key,
            "ADMIN_PASSWORD": "test-admin-password",
        }
    )
    return subprocess.run(
        [sys.executable, "-c", "from app.config import Config; assert Config.SECRET_KEY"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_startup_rejects_default_secret_key() -> None:
    """Config import must stop startup for a known placeholder secret."""
    result = _run_config_import("changeme_generate_strong_key_for_production")

    assert result.returncode != 0
    assert "default or placeholder" in result.stderr
    assert "changeme_generate_strong_key_for_production" not in result.stderr


def test_production_startup_accepts_strong_secret_key() -> None:
    """Config import proceeds with a strong, non-placeholder key."""
    result = _run_config_import("test-only-strong-secret-key-0123456789abcdef")

    assert result.returncode == 0, "strong production secret was unexpectedly rejected"
