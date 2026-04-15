"""Defines the configuration for the Flask application."""

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

import os
import tomllib

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Default secret key must be at least 32 bytes for HMAC-SHA256 (JWT requirement)
    SECRET_KEY = os.environ.get("SECRET_KEY", "iqoqo-default-secret-key-32-chars-at-least")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)

    # Protect against huge payload attacks
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB max

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Set to True to see all SQL queries emitted to the console
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "false").lower() in {"true", "1", "yes"}

    # CORS setup...
    CORS_ENABLED = os.environ.get("CORS_ENABLED", "false")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")
    CORS_METHODS = os.environ.get("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
    CORS_ALLOW_HEADERS = os.environ.get("CORS_ALLOW_HEADERS", "Content-Type,Authorization")
    CORS_SUPPORTS_CREDENTIALS = os.environ.get("CORS_SUPPORTS_CREDENTIALS", "false")

    # OAuth
    FEDERATION_ENABLED = os.environ.get("FEDERATION_ENABLED", "false").lower() == "true"
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Admin Init
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@iqoqo.local")
    _admin_password = os.environ.get("ADMIN_PASSWORD")

    if not _admin_password:
        raise RuntimeError("ADMIN_PASSWORD environment variable is required and must not be empty.")

    ADMIN_PASSWORD = _admin_password

    # LLM feature gate: set ALLOW_LLM=true to enable LLM cover generation for
    # users who also hold the llm_generate:* RBAC permission.
    # When False, LLM tiers are never invoked regardless of user permissions.
    ALLOW_LLM: bool = os.environ.get("ALLOW_LLM", "false").lower() in {"true", "1", "yes"}

    # Scheduled Backups Configuration
    BACKUP_CRON_HOUR = os.environ.get("BACKUP_CRON_HOUR", "3")
    BACKUP_CRON_MINUTE = os.environ.get("BACKUP_CRON_MINUTE", "0")
    BACKUP_DIR = os.environ.get("BACKUP_DIR", os.path.join(BASE_DIR, "exports"))
    SCHEDULER_AUTOSTART = os.environ.get("SCHEDULER_AUTOSTART", "false").lower() in {"true", "1", "yes"}

    # Base URL for static cover image serving mapping
    COVERS_BASE_URL = os.environ.get("COVERS_BASE_URL", "/static/covers")

    # Discogs credentials — v2 OAuth preferred, legacy token as fallback
    DISCOGS_CONSUMER_KEY = os.environ.get("DISCOGS_CONSUMER_KEY")
    DISCOGS_CONSUMER_SECRET = os.environ.get("DISCOGS_CONSUMER_SECRET")
    # DISCOGS_USER_TOKEN is read directly in discogs.py as a legacy fallback

    @staticmethod
    def _get_version():
        """Resolve application version from environment or pyproject.toml.

        The resolution order is:
        1. APP_VERSION environment variable.
        2. project.version field in pyproject.toml located in BASE_DIR.
        3. Fallback to "dev-local" if neither source is available.
        """
        env_version = os.environ.get("APP_VERSION")
        if env_version:
            return env_version

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        pyproject_path = os.path.join(base_dir, "pyproject.toml")
        try:
            with open(pyproject_path, "rb") as pyproject_file:
                pyproject_data = tomllib.load(pyproject_file)
        except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
            return "dev-local"

        return pyproject_data.get("project", {}).get("version", "dev-local")

    VERSION = _get_version()
