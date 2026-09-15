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
"""Tests for ConfigService and CONFIG_KEY_BLOCKLIST."""

import os
from unittest.mock import patch

from app.core.config_service import CONFIG_KEY_BLOCKLIST, ConfigService
from app.db.models import InstanceSettings, db


def test_config_key_blocklist_contains_boot_keys():
    """Ensure boot keys are in CONFIG_KEY_BLOCKLIST."""
    expected = {"SECRET_KEY", "DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY"}
    assert expected.issubset(CONFIG_KEY_BLOCKLIST)
    assert ConfigService.CONFIG_KEY_BLOCKLIST == CONFIG_KEY_BLOCKLIST


def test_db_override_ignored_for_blocklisted_keys(app):
    """Ensure DB overrides for blocklisted keys are completely ignored."""
    with app.app_context():
        # Inject rogue settings into InstanceSettings table
        for key in CONFIG_KEY_BLOCKLIST:
            setting = InstanceSettings.query.filter_by(key=key).first()
            if not setting:
                setting = InstanceSettings(key=key, value="malicious_db_value")
                db.session.add(setting)
            else:
                setting.value = "malicious_db_value"
        db.session.commit()

        # App config or env must take precedence, DB value ignored
        for key in CONFIG_KEY_BLOCKLIST:
            val = ConfigService.get(key)
            assert val != "malicious_db_value"


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

        val = ConfigService.get(key)
        assert val == "custom_value_from_db"


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
