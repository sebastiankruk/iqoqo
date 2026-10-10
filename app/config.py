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
    """Environment-derived application configuration.

    Every value is read from the environment once at import time, and a missing
    required variable raises here rather than at first use -- a container that is
    misconfigured should fail to start, not fail on the first request that happens
    to touch the value."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Default secret key logic: random in dev, mandatory in production to prevent JWT forgery
    _default_secret = None
    if os.environ.get("FLASK_ENV") != "production":
        import secrets

        _default_secret = secrets.token_hex(32)

    SECRET_KEY = os.environ.get("SECRET_KEY", _default_secret)

    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable is missing. This is required! Please set it in your .env file.")

    @staticmethod
    def validate_secret_key(key: str) -> None:
        """Enforce minimum SECRET_KEY length in production (OWASP A02)."""
        insecure_keys = {
            "changeme_generate_strong_key_for_production",
            "your_super_secret_jwt_key",
            "your_super_secret_auth_key",
        }
        if key in insecure_keys or "changeme" in key.lower() or "placeholder" in key.lower():
            raise RuntimeError("SECRET_KEY must not be a default or placeholder value.")
        if len(key.encode()) < 32:
            raise RuntimeError(
                'SECRET_KEY must be at least 32 bytes (OWASP A02). Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
            )

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)

    if SECRET_KEY:
        validate_secret_key(SECRET_KEY)
    if JWT_SECRET_KEY:
        validate_secret_key(JWT_SECRET_KEY)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Safely parse an integer environment variable with a default fallback."""
        try:
            val = os.environ.get(key)
            return int(val) if val else default
        except ValueError:
            return default

    # Protect against huge payload attacks
    MAX_CONTENT_LENGTH = _get_int_env("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)  # 16 MB max

    REDIS_URL = os.environ.get("REDIS_URL")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Set to True to see all SQL queries emitted to the console
    SQLALCHEMY_ECHO = os.environ.get("SQLALCHEMY_ECHO", "false").lower() in {"true", "1", "yes"}
    # Connection pool settings to prevent exhaustion under concurrent workloads
    # Only apply to PostgreSQL, not SQLite (tests use SQLite which doesn't support pooling)
    _is_postgres = bool(SQLALCHEMY_DATABASE_URI and "postgres" in SQLALCHEMY_DATABASE_URI.lower())
    SQLALCHEMY_ENGINE_OPTIONS = (
        {
            "pool_size": _get_int_env("SQLALCHEMY_POOL_SIZE", 5),
            "max_overflow": _get_int_env("SQLALCHEMY_MAX_OVERFLOW", 10),
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        if _is_postgres
        else {}
    )

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

    # Public origin used to build links in outbound email (email verification,
    # account-deletion confirmation).  Never derived from the request: a link
    # built from the Host header is whatever an attacker chose to send, which
    # for a mailbox-control token means handing it to a domain of their
    # choosing.  Required for the mail features and left unset by default, so
    # an instance that never configures it fails a send loudly instead of
    # mailing `http://localhost/...` to a real person.
    PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL")

    # Transactional mail (see app/core/mail_service.py).  Disabled by default
    # because an instance with no relay must still boot and serve its catalogue;
    # the credential itself is held in InstanceSettings and Fernet-encrypted at
    # rest once set from the admin UI.
    MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "false")
    MAIL_HOST = os.environ.get("MAIL_HOST")
    MAIL_PORT = _get_int_env("MAIL_PORT", 587)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true")
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false")
    MAIL_FROM_ADDRESS = os.environ.get("MAIL_FROM_ADDRESS")
    MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "iQoQo")
    MAIL_TIMEOUT_SECONDS = _get_int_env("MAIL_TIMEOUT_SECONDS", 10)
    #: ``smtp`` talks to a relay; ``memory`` records messages instead of sending
    #: them.  The latter exists for the end-to-end stack and for local
    #: development; it must never be set on a deployment that expects real mail.
    MAIL_TRANSPORT = os.environ.get("MAIL_TRANSPORT", "smtp")

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
    # Max words to display on the generated cover overlay (0 = no limit)
    LLM_TITLE_MAX_WORDS = _get_int_env("LLM_TITLE_MAX_WORDS", 12)

    # Remote object storage is configured entirely through `app/core/s3_service.py`,
    # which reads AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / S3_* directly from
    # the environment. The former RCLONE_REMOTE_FAST and RCLONE_REMOTE_ARCHIVE
    # settings are gone: they named rclone remotes, and nothing reads them now.
    # Each storage role (backup, covers, feedback) degrades to a local no-op when
    # its bucket is unset, so no config-level flag is needed here.

    # Background scheduler (cover cleanup watchdog)
    SCHEDULER_AUTOSTART = os.environ.get("SCHEDULER_AUTOSTART", "false").lower() in {"true", "1", "yes"}
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() in {"true", "1", "yes"}

    # Base URL for static cover image serving mapping
    COVERS_BASE_URL = os.environ.get("COVERS_BASE_URL", "/static/covers")

    # Allegro API — app identifier used in User-Agent header.
    # Allegro validates this against the registered application name.
    # Set per-environment: iqoqo_cc (prod), iqoqo_pre (preview), iqoqo_dev (dev).
    ALLEGRO_APP_NAME = os.environ.get("ALLEGRO_APP_NAME", "iqoqo")

    # Discogs credentials — v2 OAuth preferred, legacy token as fallback
    DISCOGS_CONSUMER_KEY = os.environ.get("DISCOGS_CONSUMER_KEY")
    DISCOGS_CONSUMER_SECRET = os.environ.get("DISCOGS_CONSUMER_SECRET")
    # DISCOGS_USER_TOKEN is read directly in discogs.py as a legacy fallback

    # Isolated SPARQL Execution Service (v0.8.3)
    SPARQL_SERVICE_URL = os.environ.get("SPARQL_SERVICE_URL")
    SPARQL_SERVICE_SECRET = os.environ.get("SPARQL_SERVICE_SECRET", os.environ.get("SECRET_KEY", "dev-sparql-service-secret"))
    SPARQL_EXECUTION_MODE = os.environ.get("SPARQL_EXECUTION_MODE", "auto")
    SPARQL_SERVICE_ENABLED = os.environ.get("SPARQL_SERVICE_ENABLED", "true").lower() in {"true", "1", "yes"}
    SPARQL_QUERY_TIMEOUT = float(os.environ.get("SPARQL_QUERY_TIMEOUT", 15.0))

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
