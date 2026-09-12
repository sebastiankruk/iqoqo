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
"""Tests for database models, schemas, and configurations."""

from app.db.models import InstanceSettings, LLMTelemetry, ScanTelemetry, db
from app.db.settings import _CONFIG, decrypt_setting_value, encrypt_setting_value, is_sensitive_key


def test_instance_settings_schema_configuration():
    """Verify that InstanceSettings targets the 'config' schema when PostgreSQL is enabled."""
    assert InstanceSettings.__tablename__ == "instance_settings"
    # When _CONFIG is defined (PostgreSQL environment), schema in table args must be 'config'
    if _CONFIG:
        assert InstanceSettings.__table_args__[0].get("schema") == "config"


def test_instance_settings_crud_and_encryption(app):
    """Verify transparent get_value and set_value with encryption for sensitive keys."""
    with app.app_context():
        # Non-sensitive setting
        InstanceSettings.set_value("default_language", "pl")
        assert InstanceSettings.get_value("default_language") == "pl"

        raw_row = db.session.execute(db.select(InstanceSettings).filter_by(key="default_language")).scalar_one_or_none()
        assert raw_row is not None
        assert raw_row.value == "pl"

        # Sensitive setting
        secret_token = "ghp_superSecretToken12345"
        InstanceSettings.set_value("OPENAI_API_KEY", secret_token)
        assert InstanceSettings.get_value("OPENAI_API_KEY") == secret_token

        raw_secret_row = db.session.execute(db.select(InstanceSettings).filter_by(key="OPENAI_API_KEY")).scalar_one_or_none()
        assert raw_secret_row is not None
        # Must be encrypted envelope in the database
        assert isinstance(raw_secret_row.value, dict)
        assert raw_secret_row.value.get("_encrypted") is True
        assert raw_secret_row.value.get("ciphertext") != secret_token

        # Decrypted property
        assert raw_secret_row.decrypted_value == secret_token


def test_is_sensitive_key():
    """Verify classification of sensitive credentials and tokens."""
    assert is_sensitive_key("OPENAI_API_KEY") is True
    assert is_sensitive_key("ALLEGRO_TOKEN_DATA") is True
    assert is_sensitive_key("DISCOGS_CONSUMER_SECRET") is True
    assert is_sensitive_key("MY_CUSTOM_SECRET") is True
    assert is_sensitive_key("APP_ACCESS_TOKEN") is True
    assert is_sensitive_key("site_title") is False
    assert is_sensitive_key("default_language") is False
