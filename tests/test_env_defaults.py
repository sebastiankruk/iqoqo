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

"""Tests for DATABASE_URL derivation and BASE_URL canonical origin fallbacks (C122)."""

from __future__ import annotations

import pytest

from app.core.mail_service import MailConfigurationError, public_origin
from app.db.env import (
    ensure_database_url_env,
    resolve_database_url,
    resolve_frontend_url,
    resolve_public_app_url,
)


def test_resolve_database_url_derives_from_postgres_vars_and_percent_encodes(monkeypatch) -> None:
    """When DATABASE_URL is unset, derive PostgreSQL URI from POSTGRES_* with safe quoting."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "iqoqo_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:w/o?rd#1")
    monkeypatch.setenv("POSTGRES_DB", "iqoqo_preview")
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)

    derived = resolve_database_url()
    assert derived == "postgresql://iqoqo_user:p%40ss%3Aw%2Fo%3Frd%231@db:5432/iqoqo_preview"

    monkeypatch.setenv("DATABASE_URL", "   ")
    assert ensure_database_url_env() == derived
    assert resolve_database_url() == derived


def test_resolve_database_url_prefers_explicit_database_url(monkeypatch) -> None:
    """Explicit DATABASE_URL always takes precedence over POSTGRES_*."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://custom:secret@localhost:5433/customdb")
    monkeypatch.setenv("POSTGRES_PASSWORD", "other_password")
    assert resolve_database_url() == "postgresql://custom:secret@localhost:5433/customdb"


def test_base_url_acts_as_default_for_frontend_and_public_app_url(monkeypatch) -> None:
    """BASE_URL supplies default for NEXT_PUBLIC_FRONTEND_URL and PUBLIC_APP_URL."""
    monkeypatch.setenv("BASE_URL", "https://preview.iqoqo.cc/")
    monkeypatch.delenv("NEXT_PUBLIC_FRONTEND_URL", raising=False)
    monkeypatch.delenv("PUBLIC_APP_URL", raising=False)

    assert resolve_frontend_url() == "https://preview.iqoqo.cc"
    assert resolve_public_app_url() == "https://preview.iqoqo.cc"

    monkeypatch.setenv("NEXT_PUBLIC_FRONTEND_URL", "https://ui.iqoqo.cc/")
    assert resolve_frontend_url() == "https://ui.iqoqo.cc"
    assert resolve_public_app_url() == "https://ui.iqoqo.cc"

    monkeypatch.setenv("PUBLIC_APP_URL", "https://mail.iqoqo.cc/")
    assert resolve_public_app_url() == "https://mail.iqoqo.cc"


def test_mail_public_origin_falls_back_to_base_url_while_enforcing_https(app, monkeypatch) -> None:
    """mail_service.public_origin() uses BASE_URL fallback and still rejects insecure origins."""
    with app.app_context():
        monkeypatch.delenv("PUBLIC_APP_URL", raising=False)
        monkeypatch.delenv("NEXT_PUBLIC_FRONTEND_URL", raising=False)
        app.config["PUBLIC_APP_URL"] = None
        app.config["NEXT_PUBLIC_FRONTEND_URL"] = None
        app.config["BASE_URL"] = "https://preview.iqoqo.cc/"
        assert public_origin() == "https://preview.iqoqo.cc"

        app.config["BASE_URL"] = "http://insecure.example.com"
        with pytest.raises(MailConfigurationError):
            public_origin()
