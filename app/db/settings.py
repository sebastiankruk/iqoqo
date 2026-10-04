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
import re
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
    "OPENOBSERVE_ROOT_PASSWORD",
    "OPENOBSERVE_BASIC_AUTH",
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


#: Keys whose value is a browser-bound credential rather than an operator
#: secret. These are validated for shape on read: a value that is not a plain
#: token string is treated as unset, so a malformed or undecryptable row can
#: never be handed to the browser as though it were the token.
BROWSER_BOUND_TOKEN_KEYS = frozenset({"OPENOBSERVE_RUM_CLIENT_TOKEN"})

#: OpenObserve RUM client tokens are opaque URL-safe strings. This mirrors the
#: shape check in scripts/provision_rum_token.py so a token accepted at deploy
#: time is not re-validated away on read (and vice versa).
_TOKEN_VALUE_SHAPE = re.compile(r"\A[A-Za-z0-9_\-.=]{16,512}\Z")


def normalise_setting_value(key: str, value: Any) -> Any:
    """Shape-check a value before any consumer uses it.

    ``decrypt_setting_value`` already returns ``None`` for an undecryptable
    row, but a stored value can still be well-formed JSON of the wrong type —
    a dict, a list, a number. For a browser-bound token that would mean the
    value reaches the client component and breaks the RUM SDK at runtime, so
    validate the type and shape here and treat a mismatch as unset.
    """
    if key not in BROWSER_BOUND_TOKEN_KEYS:
        return value
    if value is None:
        return None
    if not isinstance(value, str) or not _TOKEN_VALUE_SHAPE.match(value):
        _log_decrypt_failure(key, TypeError("value is not a well-formed token string"))
        return None
    return value


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


def _log_decrypt_failure(key: str, exc: Exception) -> None:
    """Record that a setting could not be decrypted, naming the key only.

    Without this a rotated SECRET_KEY is silent: reads quietly degrade and the
    operator finds out when a provider API key stops working.
    """
    try:
        from flask import current_app

        current_app.logger.warning(
            "Setting %s could not be decrypted (%s); treating as unset. "
            "If SECRET_KEY was rotated, run `make migrate-secrets` to re-encrypt stored values.",
            key,
            type(exc).__name__,
        )
    except Exception:  # pragma: no cover - logging must never break a read
        pass


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
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        # A decryption failure means SECRET_KEY has been rotated since this row
        # was written. Report the value as **unset** and never as the stored
        # envelope: returning `stored_value` handed callers a dict shaped like
        # {"_encrypted": True, "ciphertext": ...}, which consumers then used as
        # if it were the credential itself — including, for a RUM token,
        # shipping ciphertext to the browser.
        #
        # Nothing is lost: this path is read-only and the ciphertext remains in
        # the row. Recovery is `make migrate-secrets`, which overwrites the row
        # from .env with None in place of a conflict.
        #
        # The key name is logged; the value is not, because the "value" here is
        # ciphertext whose plaintext is a live credential.
        _log_decrypt_failure(key, exc)
        return None


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
            value = decrypt_setting_value(key, setting.value)
            value = normalise_setting_value(key, value)
            # A decryption failure resolves to None; honour the caller's
            # default in that case rather than silently returning None.
            return default if value is None else value
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
