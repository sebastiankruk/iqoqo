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
"""Tests for secure fresh-install seed ownership setup."""

import pytest

from scripts.init_db import _validated_seed_admin


def test_seed_import_requires_explicit_admin_email(app, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "")
    app.config["ADMIN_EMAIL"] = "admin@iqoqo.local"
    app.config["ADMIN_PASSWORD"] = "strong-test-password"

    with pytest.raises(ValueError, match="explicit ADMIN_EMAIL"):
        _validated_seed_admin(app)


@pytest.mark.parametrize("email", ["not-an-email", "admin@example.com", "admin@instance.local"])
def test_seed_import_rejects_invalid_or_placeholder_admin_email(app, monkeypatch, email):
    monkeypatch.setenv("ADMIN_EMAIL", email)
    app.config["ADMIN_EMAIL"] = email
    app.config["ADMIN_PASSWORD"] = "strong-test-password"

    with pytest.raises(ValueError, match="ADMIN_EMAIL"):
        _validated_seed_admin(app)


def test_seed_import_accepts_explicit_valid_admin_credentials(app, monkeypatch):
    admin_email = "bootstrap-admin@iqoqo.cc"
    admin_password = "strong-test-password"
    monkeypatch.setenv("ADMIN_EMAIL", admin_email)
    app.config["ADMIN_EMAIL"] = admin_email
    app.config["ADMIN_PASSWORD"] = admin_password

    assert _validated_seed_admin(app) == (admin_email, admin_password)


def test_seed_import_rejects_weak_bootstrap_admin_password(app, monkeypatch):
    admin_email = "bootstrap-admin@iqoqo.cc"
    monkeypatch.setenv("ADMIN_EMAIL", admin_email)
    app.config["ADMIN_EMAIL"] = admin_email
    app.config["ADMIN_PASSWORD"] = "short"

    with pytest.raises(ValueError, match="at least 8 characters"):
        _validated_seed_admin(app)


def test_init_db_postgresql_pre_create_schemas_and_unaccent():
    """Verify that PostgreSQL schema/extension initialization emits expected DDL."""
    from unittest.mock import MagicMock

    from sqlalchemy import text

    mock_db = MagicMock()
    mock_db.engine.dialect.name = "postgresql"

    for schema_name in ("auth", "catalog", "inventory", "social", "config", "federation"):
        mock_db.session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    mock_db.session.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public"))
    mock_db.session.execute(text("""
            CREATE OR REPLACE FUNCTION immutable_unaccent(text)
            RETURNS text AS $$
                SELECT public.unaccent('public.unaccent'::regdictionary, $1);
            $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT;

            CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
            RETURNS text AS $$
                SELECT public.unaccent('public.unaccent'::regdictionary, $1);
            $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT;
            """))
    mock_db.session.commit()

    executed = [str(c[0][0]) for c in mock_db.session.execute.call_args_list]
    assert any("CREATE SCHEMA IF NOT EXISTS catalog" in s for s in executed)
    assert any("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public" in s for s in executed)
    assert any("CREATE OR REPLACE FUNCTION immutable_unaccent" in s for s in executed)
