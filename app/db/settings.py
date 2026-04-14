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

import os
import sys
from datetime import UTC, datetime

from . import db

# Use the "inventory" PostgreSQL schema in production.  SQLite (used in tests)
# does not support named schemas, so we fall back to no schema.
# ---------------------------------------------------------------------------
_USE_PG = os.environ.get("DATABASE_URL", "").startswith("postgresql")
# In test environments (pytest), default to non-Postgres (no schemas/FTS) unless
# FTS tests are explicitly enabled. This ensures tests run correctly on SQLite
# even if DATABASE_URL is set in the environment.
if "pytest" in sys.modules and os.environ.get("ENABLE_FTS_TESTS") != "true":
    _USE_PG = False

_INVENTORY = "inventory" if _USE_PG else None
_CATALOG = "catalog" if _USE_PG else None


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = ({"schema": _INVENTORY},) if _INVENTORY else ()


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

    __table_args__ = ({"schema": _CATALOG},) if _CATALOG else ()
