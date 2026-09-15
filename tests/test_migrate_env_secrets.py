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
"""Tests for scripts/migrate_env_secrets_to_db.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.db.models import InstanceSettings
from scripts.migrate_env_secrets_to_db import (
    MIGRATABLE_KEYS,
    migrate_env_secrets,
    parse_env_line,
)


def test_parse_env_line() -> None:
    """Test environment file line parsing with various syntaxes."""
    assert parse_env_line("") is None
    assert parse_env_line("   ") is None
    assert parse_env_line("# A comment line") is None

    # Unquoted
    parsed = parse_env_line("TMDB_API_KEY=test_tmdb_key_123")
    assert parsed == ("", "TMDB_API_KEY", "test_tmdb_key_123")

    # Double quoted
    parsed = parse_env_line('DISCOGS_USER_TOKEN="secret_token_abc"')
    assert parsed == ("", "DISCOGS_USER_TOKEN", "secret_token_abc")

    # Single quoted
    parsed = parse_env_line("IGDB_CLIENT_ID='igdb_client_xyz'")
    assert parsed == ("", "IGDB_CLIENT_ID", "igdb_client_xyz")

    # With export prefix
    parsed = parse_env_line("export OPENAI_API_KEY=sk-test12345")
    assert parsed == ("export ", "OPENAI_API_KEY", "sk-test12345")

    # With trailing inline comment
    parsed = parse_env_line("GEMINI_API_KEY=gemini_secret # api key for gemini")
    assert parsed == ("", "GEMINI_API_KEY", "gemini_secret")


def test_blocklist_excluded_from_migratable() -> None:
    """Ensure core boot keys are never migratable."""
    assert "SECRET_KEY" not in MIGRATABLE_KEYS
    assert "DATABASE_URL" not in MIGRATABLE_KEYS
    assert "REDIS_URL" not in MIGRATABLE_KEYS
    assert "JWT_SECRET_KEY" not in MIGRATABLE_KEYS
    assert "TMDB_API_KEY" in MIGRATABLE_KEYS
    assert "DISCOGS_USER_TOKEN" in MIGRATABLE_KEYS


def test_migrate_env_secrets_dry_run(app: Any, tmp_path: Path) -> None:
    """Test dry-run mode performs no database writes and leaves .env untouched."""
    env_file = tmp_path / ".env"
    env_content = "SECRET_KEY=keep_this_here\nTMDB_API_KEY=dry_run_secret_123\n"
    env_file.write_text(env_content, encoding="utf-8")

    with app.app_context():
        stats = migrate_env_secrets(env_file, dry_run=True, backup=True)

        assert "TMDB_API_KEY" in stats["migrated"]
        assert stats["backup_path"] is None
        # File must be untouched
        assert env_file.read_text(encoding="utf-8") == env_content
        # Database must not contain setting
        assert InstanceSettings.get_value("TMDB_API_KEY") is None


def test_migrate_env_secrets_live(app: Any, tmp_path: Path) -> None:
    """Test live migration persists encrypted keys and comments them out in .env."""
    env_file = tmp_path / ".env"
    initial_content = (
        "# System Boot Config\n"
        "SECRET_KEY=never_touch_this\n"
        "DATABASE_URL=postgresql://localhost/iqoqo\n"
        "\n"
        "# External Providers\n"
        'DISCOGS_USER_TOKEN="token_alpha_123"\n'
        "TMDB_API_KEY=tmdb_bravo_456\n"
        "OPENAI_API_KEY=\n"
        "CUSTOM_VAR=leave_alone\n"
    )
    env_file.write_text(initial_content, encoding="utf-8")

    with app.app_context():
        stats = migrate_env_secrets(env_file, dry_run=False, backup=True)

        assert "DISCOGS_USER_TOKEN" in stats["migrated"]
        assert "TMDB_API_KEY" in stats["migrated"]
        assert "OPENAI_API_KEY" in stats["skipped_empty"]
        assert stats["backup_path"] is not None

        # Verify DB values (transparently decrypted by get_value)
        assert InstanceSettings.get_value("DISCOGS_USER_TOKEN") == "token_alpha_123"
        assert InstanceSettings.get_value("TMDB_API_KEY") == "tmdb_bravo_456"
        assert InstanceSettings.get_value("SECRET_KEY") is None

        # Verify modified .env file
        updated_content = env_file.read_text(encoding="utf-8")
        assert '# [MIGRATED TO DB] DISCOGS_USER_TOKEN="token_alpha_123"' in updated_content
        assert "# [MIGRATED TO DB] TMDB_API_KEY=tmdb_bravo_456" in updated_content
        assert "SECRET_KEY=never_touch_this" in updated_content
        assert "CUSTOM_VAR=leave_alone" in updated_content
        assert "OPENAI_API_KEY=" in updated_content

        # Verify backup exists
        backup = Path(stats["backup_path"])
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == initial_content


def test_migrate_env_secrets_already_synced_and_conflict(app: Any, tmp_path: Path) -> None:
    """Test handling of existing DB settings with same vs conflicting values."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DISCOGS_USER_TOKEN=already_there\nTMDB_API_KEY=new_conflicting_value\n",
        encoding="utf-8",
    )

    with app.app_context():
        InstanceSettings.set_value("DISCOGS_USER_TOKEN", "already_there")
        InstanceSettings.set_value("TMDB_API_KEY", "existing_old_value")

        # Without overwrite: conflict is skipped, identical is commented out
        stats = migrate_env_secrets(env_file, dry_run=False, overwrite=False, backup=False)
        assert "DISCOGS_USER_TOKEN" in stats["already_synced"]
        assert "TMDB_API_KEY" in stats["skipped_conflict"]
        assert InstanceSettings.get_value("TMDB_API_KEY") == "existing_old_value"

        # Now with overwrite: conflicting key is updated
        stats_overwrite = migrate_env_secrets(env_file, dry_run=False, overwrite=True, backup=False)
        assert "TMDB_API_KEY" in stats_overwrite["updated"]
        assert InstanceSettings.get_value("TMDB_API_KEY") == "new_conflicting_value"
