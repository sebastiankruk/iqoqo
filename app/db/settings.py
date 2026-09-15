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
"""Instance-level settings and LLM telemetry models."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from . import db

# Use the "inventory" PostgreSQL schema in production.  SQLite (used in tests)
# does not support named schemas, so we fall back to no schema.
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")

_INVENTORY = "inventory" if _USE_PG else None
_CATALOG = "catalog" if _USE_PG else None
_CONFIG = "config" if _USE_PG else None


class LLMTelemetry(db.Model):  # type: ignore[name-defined]
    """Tracks individual LLM API executions per provider, user, and operation type."""

    __tablename__ = "llm_telemetry"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.String(100), nullable=False)
    operation_type = db.Column(db.String(50), nullable=False, default="cover_generation")
    images_generated = db.Column(db.Integer, default=0)
    estimated_cost_usd = db.Column(db.Float, default=0.0)
    total_duration_seconds = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), nullable=False, default="success")  # success, failed, not_allowed
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        db.Index("ix_llm_telemetry_provider_user_op_time", "provider", "user_id", "operation_type", "created_at"),
        {"schema": _INVENTORY} if _INVENTORY else {},
    )


class ScanTelemetry(db.Model):  # type: ignore[name-defined]
    """Records barcode scan and manual lookup attempts for auditing and link analysis."""

    __tablename__ = "scan_telemetry"

    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), nullable=False, index=True)
    format_hint = db.Column(db.String(50), nullable=True)
    provider = db.Column(db.String(50), nullable=False)  # e.g. "discogs", "isbn", "upc", "tmdb", "bgg"
    status = db.Column(db.String(20), nullable=False)  # "success", "failed"
    manifestation_id = db.Column(
        db.Integer,
        db.ForeignKey(f"{_CATALOG}.manifestations.id" if _CATALOG else "manifestations.id", ondelete="SET NULL"),
        nullable=True,
    )
    raw_request_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = ({"schema": _INVENTORY} if _INVENTORY else {},)


SENSITIVE_SETTING_KEYS = {
    "GOOGLE_BOOKS_API_KEY",
    "DISCOGS_USER_TOKEN",
    "DISCOGS_CONSUMER_KEY",
    "DISCOGS_CONSUMER_SECRET",
    "TMDB_API_KEY",
    "TMDB_API_READ_ACCESS_TOKEN",
    "BGG_API_TOKEN",
    "IGDB_CLIENT_ID",
    "IGDB_CLIENT_SECRET",
    "TWITCH_CLIENT_ID",
    "TWITCH_CLIENT_SECRET",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "UPC_ITEM_DB_KEY",
    "UPC_DATABASE_ORG_KEY",
    "ALLEGRO_CLIENT_ID",
    "ALLEGRO_CLIENT_SECRET",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "ALLEGRO_TOKEN_DATA",
}


def _get_fernet_cipher() -> Fernet:
    """Derive a Fernet cipher instance from the application SECRET_KEY."""
    secret = None
    try:
        from flask import current_app

        if current_app:
            secret = current_app.config.get("SECRET_KEY")
    except RuntimeError:
        pass
    if not secret:
        secret = os.environ.get("SECRET_KEY")
    if not secret:
        from app.config import Config

        secret = getattr(Config, "SECRET_KEY", None)
    if not secret:
        secret = "default-iqoqo-secret-key-for-dev-only"

    key_bytes = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key_bytes)


def is_sensitive_key(key: str) -> bool:
    """Check whether a configuration key contains sensitive credentials or tokens."""
    return key in SENSITIVE_SETTING_KEYS or any(k in key for k in ("_KEY", "_SECRET", "_TOKEN", "_DATA"))


def encrypt_setting_value(key: str, value: Any) -> Any:
    """Encrypt sensitive setting values before persisting to the database."""
    if not is_sensitive_key(key) or value is None:
        return value

    # If already an encrypted envelope, do not re-encrypt
    if isinstance(value, dict) and value.get("_encrypted") is True:
        return value

    cipher = _get_fernet_cipher()
    raw_bytes = json.dumps(value).encode("utf-8")
    ciphertext = cipher.encrypt(raw_bytes).decode("utf-8")
    return {"_encrypted": True, "ciphertext": ciphertext}


def decrypt_setting_value(key: str, stored_value: Any) -> Any:
    """Decrypt a stored setting value if encrypted."""
    if not isinstance(stored_value, dict) or stored_value.get("_encrypted") is not True:
        # Backward-compatibility for raw plaintext
        return stored_value

    ciphertext = stored_value.get("ciphertext")
    if not ciphertext or not isinstance(ciphertext, str):
        return stored_value

    try:
        cipher = _get_fernet_cipher()
        decrypted_bytes = cipher.decrypt(ciphertext.encode("utf-8"))
        return json.loads(decrypted_bytes.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError):
        # Fall back gracefully if decryption fails
        return stored_value


class InstanceSettings(db.Model):  # type: ignore[name-defined]
    """
    Stores global configuration for the iqoqo instance (e.g. federation
    toggles, affiliate links, default language).
    """

    __tablename__ = "instance_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    __table_args__ = ({"schema": _CONFIG},) if _CONFIG else ()

    @property
    def decrypted_value(self) -> Any:
        """Get the decrypted value of this setting."""
        return decrypt_setting_value(self.key, self.value)

    @classmethod
    def get_value(cls, key: str, default: Any = None) -> Any:
        """Get a setting value by key with transparent decryption and a fallback default."""
        from sqlalchemy.exc import DBAPIError, SQLAlchemyError

        from . import db

        try:
            stmt = db.select(cls).filter_by(key=key)
            setting = db.session.execute(stmt).scalar_one_or_none()
            if setting is None:
                return default
            return decrypt_setting_value(key, setting.value)
        except (SQLAlchemyError, DBAPIError, RuntimeError, AttributeError):
            return default

    @classmethod
    def set_value(cls, key: str, value: Any) -> None:
        """Set or update a setting value by key with transparent encryption for sensitive keys."""
        from sqlalchemy.exc import DBAPIError, SQLAlchemyError

        from . import db

        encrypted_val = encrypt_setting_value(key, value)
        try:
            stmt = db.select(cls).filter_by(key=key)
            setting = db.session.execute(stmt).scalar_one_or_none()
            if setting:
                setting.value = encrypted_val
                setting.updated_at = datetime.now(UTC)
            else:
                setting = cls(key=key, value=encrypted_val)
                db.session.add(setting)
            db.session.commit()
        except (SQLAlchemyError, DBAPIError, RuntimeError):
            db.session.rollback()
            raise


@db.event.listens_for(InstanceSettings, "before_insert")
@db.event.listens_for(InstanceSettings, "before_update")
def _encrypt_instance_setting_listener(mapper, connection, target):
    """Automatically encrypt sensitive settings on any insert or update."""
    if target.key and target.value is not None:
        target.value = encrypt_setting_value(target.key, target.value)
